"""Observability and tracing integration for Omerta.ai workflows using Langfuse."""

from __future__ import annotations

import logging
import sys
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

