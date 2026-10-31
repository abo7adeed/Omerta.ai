"""Observability and tracing integration for Omerta.ai workflows using Langfuse."""

from __future__ import annotations

import logging
import sys
import time
import types
from typing import Any

from infrastructure.config import get_settings

logger = logging.getLogger(__name__)

# Compatibility bridge for LangChain 0.3+ with Langfuse v2 CallbackHandler
def _setup_langchain_compat():
    try:
        import langchain_core.callbacks.base
        import langchain_core.documents

        if "langchain.callbacks" not in sys.modules:
            m = types.ModuleType("langchain.callbacks")
            mb = types.ModuleType("langchain.callbacks.base")
            mb.BaseCallbackHandler = langchain_core.callbacks.base.BaseCallbackHandler
            sys.modules["langchain.callbacks"] = m
            sys.modules["langchain.callbacks.base"] = mb

        if "langchain.schema" not in sys.modules:
            s = types.ModuleType("langchain.schema")
            sa = types.ModuleType("langchain.schema.agent")
            sd = types.ModuleType("langchain.schema.document")
            sa.AgentAction = type("AgentAction", (), {})
            sa.AgentFinish = type("AgentFinish", (), {})
            sd.Document = langchain_core.documents.Document
            sys.modules["langchain.schema"] = s
            sys.modules["langchain.schema.agent"] = sa
            sys.modules["langchain.schema.document"] = sd
    except Exception as exc:
        logger.debug("Langchain compat bridge error: %s", exc)


def get_langfuse_callback(
    *,
    session_id: str | None = None,
    user_id: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Any | None:
    """Instantiate and return a Langfuse CallbackHandler for LangGraph / LangChain runs.

    Returns None if Langfuse is disabled or credentials are not provided.
    Fails safely without raising exceptions to protect workflow execution.
    """
    settings = get_settings()
    if not settings.langfuse_enabled:
        return None

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.debug("Langfuse is enabled but public/secret keys are missing. Tracing skipped.")
        return None

    try:
        _setup_langchain_compat()
        from langfuse.callback import CallbackHandler

        handler = CallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            session_id=session_id,
            user_id=user_id,
            tags=tags,
            metadata=metadata,
        )
        return handler
    except Exception as exc:
        logger.warning("Failed to initialize Langfuse CallbackHandler: %s", exc)
        return None


def get_langfuse_client() -> Any | None:
    """Instantiate and return a direct Langfuse client for tracing spans and events."""
    settings = get_settings()
    if not settings.langfuse_enabled:
        return None
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None
    try:
        from langfuse import Langfuse
        return Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception as exc:
        logger.debug("Failed to initialize direct Langfuse client: %s", exc)
        return None


def flush_langfuse(handler: Any | None = None) -> None:
    """Flush pending Langfuse spans before process termination."""
    try:
        if handler and hasattr(handler, "flush"):
            handler.flush()
        elif handler and hasattr(handler, "langfuse") and hasattr(handler.langfuse, "flush"):
            handler.langfuse.flush()
    except Exception as exc:
        logger.debug("Langfuse flush failed: %s", exc)


_PROMPT_CACHE: dict[str, tuple[float, Any]] = {}
CACHE_TTL_SUCCESS_SEC = 300.0
CACHE_TTL_FAILURE_SEC = 60.0


def get_managed_prompt(
    name: str,
    fallback: str,
    label: str = "production",
    **variables: Any,
) -> str:
    """Retrieve and compile a versioned prompt from Langfuse Prompt Management.

    If Langfuse is disabled, unreachable, or the prompt does not exist,
    gracefully returns the in-code fallback string with safe variable interpolation.
    """
    def _interpolate_fallback(text: str) -> str:
        if not variables:
            return text
        res = text
        for k, v in variables.items():
            res = res.replace(f"{{{{{k}}}}}", str(v)).replace(f"{{{k}}}", str(v))
        return res

    cache_key = f"{name}:{label}"
    now = time.monotonic()
    if cache_key in _PROMPT_CACHE:
        cached_time, cached_obj = _PROMPT_CACHE[cache_key]
        ttl = CACHE_TTL_SUCCESS_SEC if cached_obj is not None else CACHE_TTL_FAILURE_SEC
        if now - cached_time < ttl:
            if cached_obj is None:
                return _interpolate_fallback(fallback)
            if hasattr(cached_obj, "compile"):
                return cached_obj.compile(**variables)
            return str(getattr(cached_obj, "prompt", _interpolate_fallback(fallback)))

    lf = get_langfuse_client()
    if not lf:
        _PROMPT_CACHE[cache_key] = (now, None)
        return _interpolate_fallback(fallback)

    try:
        prompt_obj = lf.get_prompt(name, label=label)
        _PROMPT_CACHE[cache_key] = (now, prompt_obj)
        if hasattr(prompt_obj, "compile"):
            return prompt_obj.compile(**variables)
        return str(getattr(prompt_obj, "prompt", _interpolate_fallback(fallback)))
    except Exception as exc:
        _PROMPT_CACHE[cache_key] = (now, None)
        logger.debug("Langfuse prompt retrieval fallback for '%s': %s", name, exc)
        return _interpolate_fallback(fallback)
