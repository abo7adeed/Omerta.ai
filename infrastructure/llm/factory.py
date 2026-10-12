"""LLM provider factory: environment-driven selection.

``LLM_PROVIDER`` selects the implementation; when it is unset (or ``fake``)
the deterministic no-network provider is used so the platform remains fully
runnable offline. Unknown provider names raise a clear error instead of
silently falling back.
"""

from infrastructure.config import get_settings
from infrastructure.llm.base import LLMProvider
from infrastructure.llm.fake_provider import FakeLLMProvider
from infrastructure.llm.openai_provider import OpenAICompatibleProvider


def get_llm_provider() -> LLMProvider:
    """Build the configured provider; unset/``fake`` means deterministic local."""
    settings = get_settings()
    provider_name = (settings.llm_provider or "fake").strip().lower()

    if provider_name == "fake" or provider_name == "":
        return FakeLLMProvider()

    if provider_name in {"openai", "groq", "ollama", "openai_compatible"}:
        import re

        keys: list[str] = []
        raw_candidates = []
        if provider_name == "groq":
            raw_candidates = [
                getattr(settings, "groq_api_keys", None),
                getattr(settings, "groq_api_key", None),
                settings.llm_api_keys,
                settings.llm_api_key,
            ]
        elif provider_name == "openai":
            raw_candidates = [
                settings.llm_api_keys,
                settings.llm_api_key,
            ]
        else:
            raw_candidates = [
                settings.llm_api_keys,
                settings.llm_api_key,
            ]

        for raw in raw_candidates:
            if raw:
                for k in re.split(r"[\s,;]+", str(raw)):
                    if k.strip() and k.strip() not in keys:
                        keys.append(k.strip())

        primary_api_key = keys[0] if keys else settings.llm_api_key
        if provider_name in {"openai", "groq"} and not keys and not primary_api_key:
            raise ValueError(f"LLM_PROVIDER={provider_name} requires LLM_API_KEY to be set")
        default_base = {
            "openai": "https://api.openai.com/v1",
            "groq": "https://api.groq.com/openai/v1",
            "ollama": "http://localhost:11434/v1",
        }.get(provider_name)
        base_url = settings.llm_base_url or default_base
        if not base_url:
            raise ValueError(f"LLM_PROVIDER={provider_name} requires LLM_BASE_URL")
        model = settings.llm_model
        if not model:
            if provider_name == "groq":
                model = "openai/gpt-oss-20b"
            elif provider_name == "openai":
                model = "gpt-4o"
            else:
                raise ValueError(f"LLM_PROVIDER={provider_name} requires LLM_MODEL")
        return OpenAICompatibleProvider(
            name=provider_name,
            model=model,
            api_key=primary_api_key,
            api_keys=keys,
            base_url=base_url,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider_name}'; "
        "expected one of: fake, openai, groq, ollama, openai_compatible."
    )
