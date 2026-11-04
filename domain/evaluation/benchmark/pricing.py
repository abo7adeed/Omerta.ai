"""Inference pricing metadata and cost estimation for LLM model benchmarking.

Provides versioned pricing rates, token usage estimation, and cost calculations
per candidate model to allow transparent cost comparisons without hardcoded
hidden constants.
"""

from typing import Any

PRICING_VERSION = "2026-10-31"

# Published reference rates in USD per 1,000,000 tokens
MODEL_PRICING_REGISTRY: dict[str, dict[str, float]] = {
    # Groq Cloud published reference rates
    "openai/gpt-oss-120b": {"prompt_per_m": 0.59, "completion_per_m": 0.79},
    "openai/gpt-oss-20b": {"prompt_per_m": 0.10, "completion_per_m": 0.20},
    "qwen/qwen3.8-27b": {"prompt_per_m": 0.20, "completion_per_m": 0.40},
    "llama-3.3-70b-versatile": {"prompt_per_m": 0.59, "completion_per_m": 0.79},
    "llama-3.1-8b-instant": {"prompt_per_m": 0.05, "completion_per_m": 0.08},
    # OpenAI published reference rates
    "gpt-4o": {"prompt_per_m": 2.50, "completion_per_m": 10.00},
    "gpt-4o-mini": {"prompt_per_m": 0.15, "completion_per_m": 0.60},
    # Local & Deterministic Mock
    "qwen3.5:4b": {"prompt_per_m": 0.0, "completion_per_m": 0.0},
    "qwen2.5:1.5b": {"prompt_per_m": 0.0, "completion_per_m": 0.0},
    "ollama/local": {"prompt_per_m": 0.0, "completion_per_m": 0.0},
    "fake": {"prompt_per_m": 0.0, "completion_per_m": 0.0},
}

DEFAULT_FALLBACK_PRICING = {"prompt_per_m": 0.25, "completion_per_m": 0.50}


def get_model_pricing(model_id: str) -> dict[str, Any]:
    """Retrieve pricing rates and metadata for a given model ID."""
    clean_id = (model_id or "").strip().lower()
    for registered_id, rates in MODEL_PRICING_REGISTRY.items():
        if registered_id.lower() == clean_id or clean_id.endswith(registered_id.lower()):
            return {
                "model_id": model_id,
                "pricing_version": PRICING_VERSION,
                "rates": rates,
                "is_fallback": False,
            }
    return {
        "model_id": model_id,
        "pricing_version": PRICING_VERSION,
        "rates": DEFAULT_FALLBACK_PRICING,
        "is_fallback": True,
    }


def calculate_cost(
    model_id: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> dict[str, Any]:
    """Calculate inference cost in USD from token counts and pricing registry."""
    pricing = get_model_pricing(model_id)
    rates = pricing["rates"]

    prompt_cost = (prompt_tokens / 1_000_000.0) * rates["prompt_per_m"]
    completion_cost = (completion_tokens / 1_000_000.0) * rates["completion_per_m"]
    total_cost = prompt_cost + completion_cost

    return {
        "total_cost_usd": round(total_cost, 6),
        "prompt_cost_usd": round(prompt_cost, 6),
        "completion_cost_usd": round(completion_cost, 6),
        "pricing_version": pricing["pricing_version"],
        "pricing_is_fallback": pricing["is_fallback"],
    }


def estimate_tokens(text: str) -> int:
    """Heuristic token count estimation when provider does not report exact usage."""
    if not text:
        return 0
    # Standard rule of thumb: ~4 characters per token in English financial text
    return max(1, len(text) // 4)

