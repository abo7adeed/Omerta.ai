"""Candidate model configurations and provider factory for side-by-side benchmarking.

Allows configuring candidate models (Model A and Model B) independently,
validating their API availability, and building runnable LLMProvider instances.
"""

from __future__ import annotations

import logging
from typing import Any
from pydantic import BaseModel, Field

from infrastructure.config import get_settings
from infrastructure.llm.base import LLMProvider
from infrastructure.llm.fake_provider import FakeLLMProvider
from infrastructure.llm.openai_provider import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class BenchmarkModelConfig(BaseModel):
    """Specification of an evaluated candidate model."""

    model_id: str = Field(description="Unique model identifier, e.g. 'openai/gpt-oss-120b' or 'fake'")
    provider: str = Field(default="groq", description="Provider backend: groq, openai, ollama, or fake")
    display_name: str | None = Field(default=None, description="Human-friendly label for dashboard")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1500, ge=100, le=8192)
    timeout_seconds: float = Field(default=60.0, ge=5.0, le=300.0)
    max_retries: int = Field(default=2, ge=0, le=5)

    def get_display_name(self) -> str:
        if self.display_name:
            return self.display_name
        return f"{self.provider.upper()}: {self.model_id}"


class ModelAvailabilityInfo(BaseModel):
    """Status indicating whether a candidate model can be called with active credentials."""

    model_id: str
    provider: str
    display_name: str
    is_available: bool
    status_message: str
    pricing_info: dict[str, Any] = Field(default_factory=dict)


def get_available_model_catalog() -> list[ModelAvailabilityInfo]:
    """Return catalog of recognized candidate models with live credential availability."""
    settings = get_settings()
    from domain.evaluation.benchmark.pricing import get_model_pricing

    has_groq_key = bool(
        getattr(settings, "groq_api_keys", None)
        or getattr(settings, "groq_api_key", None)
        or settings.llm_api_keys
        or settings.llm_api_key
    )
    has_openai_key = bool(settings.llm_api_keys or settings.llm_api_key)

    has_ollama = False
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1.0) as resp:
            if resp.status == 200:
                has_ollama = True
    except Exception:
        has_ollama = False

    catalog = [
        ModelAvailabilityInfo(
            model_id="openai/gpt-oss-120b",
            provider="groq",
            display_name="Groq: GPT-OSS 120B (Deep Reasoning)",
            is_available=has_groq_key,
            status_message="API key configured" if has_groq_key else "Missing GROQ_API_KEY",
            pricing_info=get_model_pricing("openai/gpt-oss-120b"),
        ),
        ModelAvailabilityInfo(
            model_id="openai/gpt-oss-20b",
            provider="groq",
            display_name="Groq: GPT-OSS 20B (High Speed & Efficiency)",
            is_available=has_groq_key,
            status_message="API key configured" if has_groq_key else "Missing GROQ_API_KEY",
            pricing_info=get_model_pricing("openai/gpt-oss-20b"),
        ),
        ModelAvailabilityInfo(
            model_id="qwen/qwen3.8-27b",
            provider="groq",
            display_name="Groq: Qwen 3.8 27B (High Accuracy)",
            is_available=has_groq_key,
            status_message="API key configured" if has_groq_key else "Missing GROQ_API_KEY",
            pricing_info=get_model_pricing("qwen/qwen3.8-27b"),
        ),
        ModelAvailabilityInfo(
            model_id="llama-3.3-70b-versatile",
            provider="groq",
            display_name="Groq: Llama 3.3 70B Versatile",
            is_available=has_groq_key,
            status_message="API key configured" if has_groq_key else "Missing GROQ_API_KEY",
            pricing_info=get_model_pricing("llama-3.3-70b-versatile"),
        ),
        ModelAvailabilityInfo(
            model_id="llama-3.1-8b-instant",
            provider="groq",
            display_name="Groq: Llama 3.1 8B Instant (Ultra Fast)",
            is_available=has_groq_key,
            status_message="API key configured" if has_groq_key else "Missing GROQ_API_KEY",
            pricing_info=get_model_pricing("llama-3.1-8b-instant"),
        ),
        ModelAvailabilityInfo(
            model_id="gpt-4o",
            provider="openai",
            display_name="OpenAI: GPT-4o (Omni Frontier)",
            is_available=has_openai_key,
            status_message="API key configured" if has_openai_key else "Missing LLM_API_KEY",
            pricing_info=get_model_pricing("gpt-4o"),
        ),
        ModelAvailabilityInfo(
            model_id="gpt-4o-mini",
            provider="openai",
            display_name="OpenAI: GPT-4o Mini (Cost-Effective)",
            is_available=has_openai_key,
            status_message="API key configured" if has_openai_key else "Missing LLM_API_KEY",
            pricing_info=get_model_pricing("gpt-4o-mini"),
        ),
        ModelAvailabilityInfo(
            model_id="qwen3.5:4b",
            provider="ollama",
            display_name="Ollama: Qwen 3.5 4B (Local GPU)",
            is_available=has_ollama,
            status_message="Local GPU Service Ready" if has_ollama else "Ollama offline on :11434",
            pricing_info=get_model_pricing("qwen3.5:4b"),
        ),
        ModelAvailabilityInfo(
            model_id="qwen2.5:1.5b",
            provider="ollama",
            display_name="Ollama: Qwen 2.5 1.5B (Local GPU Fast)",
            is_available=has_ollama,
            status_message="Local GPU Service Ready" if has_ollama else "Ollama offline on :11434",
            pricing_info=get_model_pricing("qwen2.5:1.5b"),
        ),
        ModelAvailabilityInfo(
            model_id="fake",
            provider="fake",
            display_name="Deterministic Rule-Based Mock (Offline/CI)",
            is_available=True,
            status_message="Always available without network",
            pricing_info=get_model_pricing("fake"),
        ),
    ]
    return catalog


def build_candidate_llm_provider(config: BenchmarkModelConfig) -> LLMProvider:
    """Build an active LLMProvider instance corresponding to the benchmark model config."""
    settings = get_settings()
    provider_name = (config.provider or "fake").strip().lower()

    if provider_name == "fake" or config.model_id.lower() == "fake":
        return FakeLLMProvider()

    if provider_name == "groq":
        keys: list[str] = []
        raw_candidates = [
            getattr(settings, "groq_api_keys", None),
            getattr(settings, "groq_api_key", None),
            settings.llm_api_keys,
            settings.llm_api_key,
        ]
        import re
        for cand in raw_candidates:
            if cand:
                extracted = [k.strip() for k in re.split(r"[\s,;]+", str(cand)) if k.strip()]
                for k in extracted:
                    if k not in keys:
                        keys.append(k)

        primary_key = keys[0] if keys else "dummy-groq-key"
        return OpenAICompatibleProvider(
            name="groq",
            model=config.model_id,
            api_key=primary_key,
            api_keys=keys,
            base_url="https://api.groq.com/openai/v1",
            timeout=config.timeout_seconds,
            max_tokens=config.max_tokens,
        )

    if provider_name == "openai":
        primary_key = settings.llm_api_key or "dummy-openai-key"
        return OpenAICompatibleProvider(
            name="openai",
            model=config.model_id,
            api_key=primary_key,
            base_url="https://api.openai.com/v1",
            timeout=config.timeout_seconds,
            max_tokens=config.max_tokens,
        )

    if provider_name == "ollama":
        base_url = getattr(settings, "ollama_base_url", None) or "http://localhost:11434/v1"
        return OpenAICompatibleProvider(
            name="ollama",
            model=config.model_id,
            api_key="ollama",
            base_url=base_url,
            timeout=config.timeout_seconds,
            max_tokens=config.max_tokens,
        )

    raise ValueError(f"Unsupported benchmark model provider: '{provider_name}'")

