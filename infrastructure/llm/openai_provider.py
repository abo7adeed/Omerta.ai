"""OpenAI-compatible chat-completions provider over httpx.

Works with OpenAI, Groq, Ollama, vLLM, and other compatible gateways by
combining ``LLM_PROVIDER``/``LLM_MODEL``/``LLM_API_KEY`` with an optional
``LLM_BASE_URL`` override. The API key never appears in exceptions or logs
that reach tool consumers.
"""

import logging
from typing import Any

import httpx

from infrastructure.llm.base import LLMResponse

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_MAX_TOKENS = 1024
TEMPERATURE = 0.0  # investigations must be reproducible


class OpenAICompatibleProvider:
    """Minimal chat-completions client with deterministic settings and key rotation."""

    def __init__(
        self,
        *,
        name: str,
        model: str,
        api_key: str | None = None,
        api_keys: list[str] | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self.name = name
        self.model = model
        # Gather all valid keys
        keys: list[str] = []
        if api_keys:
            keys.extend([k.strip() for k in api_keys if k and k.strip()])
        if api_key and api_key.strip() and api_key.strip() not in keys:
            keys.append(api_key.strip())
        self._api_keys = keys
        self._key_index = 0
        self._base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self._timeout = timeout
        self._max_tokens = max_tokens

    @property
    def base_url(self) -> str:
        """Current base URL."""
        return self._base_url

    @property
    def _api_key(self) -> str | None:
        """Current active API key."""
        if not self._api_keys:
            return None
        return self._api_keys[self._key_index]

    async def complete(self, system: str, user: str, **kwargs: Any) -> LLMResponse:
        total_keys = len(self._api_keys)
        attempts = max(1, total_keys)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": kwargs.get("temperature", TEMPERATURE),
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
        }

        last_status_err: httpx.HTTPStatusError | None = None
        last_transport_err: httpx.HTTPError | None = None

        for attempt in range(attempts):
            current_key = self._api_keys[self._key_index] if self._api_keys else None
            headers = {"Content-Type": "application/json"}
            if current_key:
                headers["Authorization"] = f"Bearer {current_key}"

            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        f"{self._base_url}/chat/completions", json=payload, headers=headers
                    )
                    response.raise_for_status()
                    data = response.json()

                content = data["choices"][0]["message"]["content"]
                return LLMResponse(content=content, provider=self.name, model=self.model)

            except httpx.HTTPStatusError as exc:
                last_status_err = exc
                status_code = exc.response.status_code
                logger.warning(
                    "LLM key #%d failed with HTTP %d.",
                    self._key_index + 1,
                    status_code,
                )
                if total_keys > 1 and attempt < attempts - 1:
                    # Rotate to next key; wrap around if at the end
                    self._key_index = (self._key_index + 1) % total_keys
                    logger.info("Rotating to next API key (#%d/%d)...", self._key_index + 1, total_keys)
                    continue
                else:
                    if total_keys > 1:
                        self._key_index = (self._key_index + 1) % total_keys
                    logger.error("llm http status %s", status_code)
                    raise RuntimeError(f"LLM request failed with status {status_code}") from None

            except httpx.HTTPError as exc:
                last_transport_err = exc
                logger.warning(
                    "LLM transport error on key #%d: %s",
                    self._key_index + 1,
                    type(exc).__name__,
                )
                if total_keys > 1 and attempt < attempts - 1:
                    self._key_index = (self._key_index + 1) % total_keys
                    logger.info("Rotating to next API key (#%d/%d)...", self._key_index + 1, total_keys)
                    continue
                else:
                    if total_keys > 1:
                        self._key_index = (self._key_index + 1) % total_keys
                    logger.error("llm transport error: %s", type(exc).__name__)
                    raise RuntimeError("LLM transport error") from None

            except (KeyError, IndexError, TypeError) as exc:
                raise RuntimeError("LLM response missing expected content") from exc

        if last_status_err:
            raise RuntimeError(f"LLM request failed with status {last_status_err.response.status_code}") from None
        if last_transport_err:
            raise RuntimeError("LLM transport error") from None
        raise RuntimeError("LLM completion failed across all available keys.")
