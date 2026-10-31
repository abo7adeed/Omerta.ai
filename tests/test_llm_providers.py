"""LLM provider layer tests: factory selection, fake determinism, and the
OpenAI-compatible provider exercised over a mocked transport (no network)."""

import json

import httpx
import pytest
from infrastructure.config import get_settings
from infrastructure.llm.factory import get_llm_provider
from infrastructure.llm.fake_provider import FakeLLMProvider
from infrastructure.llm.openai_provider import OpenAICompatibleProvider


@pytest.fixture(autouse=True)
def _disable_local_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USE_LOCAL_LLM", "false")
    settings = get_settings()
    monkeypatch.setattr(settings, "use_local_llm", False, raising=False)


def test_factory_defaults_to_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_provider", "fake", raising=False)
    assert (settings.llm_provider or "fake") in {"", "fake", None}
    provider = get_llm_provider()
    assert provider.name == "fake"


def test_factory_rejects_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "definitely-not-real")
    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            get_llm_provider()
    finally:
        get_settings.cache_clear()


def test_factory_requires_api_key_for_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_provider", "openai", raising=False)
    monkeypatch.setattr(settings, "llm_api_key", None, raising=False)
    monkeypatch.setattr(settings, "llm_api_keys", None, raising=False)
    monkeypatch.setattr(settings, "llm_model", "gpt-test", raising=False)
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        get_llm_provider()


def test_factory_builds_openai_compatible(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_provider", "openai", raising=False)
    monkeypatch.setattr(settings, "llm_api_key", "test-key-123", raising=False)
    monkeypatch.setattr(settings, "llm_model", "gpt-test", raising=False)
    monkeypatch.setattr(settings, "llm_base_url", "https://example.invalid/v1", raising=False)
    provider = get_llm_provider()
    assert provider.name == "openai"
    assert provider.model == "gpt-test"
    assert provider._base_url == "https://example.invalid/v1"


async def test_fake_provider_is_deterministic() -> None:
    provider = FakeLLMProvider()
    first = await provider.complete("system", "user-payload")
    second = await provider.complete("system", "user-payload")
    assert first == second
    assert first.provider == "fake"


async def test_openai_provider_parses_completion() -> None:
    provider = OpenAICompatibleProvider(
        name="openai", model="gpt-test", api_key="test-key-123", base_url="https://x.test/v1"
    )

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("Authorization")
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"risk_level": "HIGH"}'}}]},
        )

    transport = httpx.MockTransport(handler)
    monkey_http = httpx.AsyncClient(transport=transport)
    import unittest.mock as mock

    with mock.patch("httpx.AsyncClient", return_value=monkey_http):
        result = await provider.complete("system prompt", "user prompt")

    assert result.content.startswith('{"risk_level"')
    assert captured["auth"] == "Bearer test-key-123"
    assert captured["payload"]["model"] == "gpt-test"
    assert captured["payload"]["temperature"] == 0.0


async def test_openai_provider_http_error_has_no_secrets() -> None:
    provider = OpenAICompatibleProvider(
        name="openai", model="gpt-test", api_key="super-secret-key", base_url="https://x.test/v1"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    import unittest.mock as mock

    transport = httpx.MockTransport(handler)
    monkey_http = httpx.AsyncClient(transport=transport)
    with (
        mock.patch("httpx.AsyncClient", return_value=monkey_http),
        pytest.raises(RuntimeError, match="status 500") as exc_info,
    ):
        await provider.complete("s", "u")
    assert "super-secret-key" not in str(exc_info.value)


async def test_openai_provider_malformed_response_raises() -> None:
    provider = OpenAICompatibleProvider(
        name="openai", model="gpt-test", api_key="k", base_url="https://x.test/v1"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    import unittest.mock as mock

    transport = httpx.MockTransport(handler)
    monkey_http = httpx.AsyncClient(transport=transport)
    with (
        mock.patch("httpx.AsyncClient", return_value=monkey_http),
        pytest.raises(RuntimeError, match="missing expected content"),
    ):
        await provider.complete("s", "u")


async def test_openai_provider_key_rotation_and_wrap_around() -> None:
    keys = ["key-alpha", "key-beta", "key-gamma"]
    provider = OpenAICompatibleProvider(
        name="groq",
        model="gpt-test",
        api_keys=keys,
        base_url="https://api.groq.com/openai/v1",
    )

    seen_auths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("Authorization", "")
        seen_auths.append(auth)
        # First key fails with 429 Rate Limit
        if "key-alpha" in auth:
            return httpx.Response(429, json={"error": "Rate limit reached"})
        # Second key fails with 401 Unauthorized / quota expired
        if "key-beta" in auth:
            return httpx.Response(401, json={"error": "Expired key"})
        # Third key succeeds
        return httpx.Response(200, json={"choices": [{"message": {"content": "Rotated successfully"}}]})

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient
    import unittest.mock as mock

    with mock.patch("httpx.AsyncClient", side_effect=lambda **kw: real_client(transport=transport, **kw)):
        res = await provider.complete("system", "user")

    assert res.content == "Rotated successfully"
    assert seen_auths == ["Bearer key-alpha", "Bearer key-beta", "Bearer key-gamma"]
    # Verify active key
    assert provider._api_key == "key-gamma"

