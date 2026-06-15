"""Tests for OpenAIProvider."""

import asyncio
import urllib.error
from collections.abc import Awaitable, Callable
from http.client import HTTPMessage
from typing import Any
from unittest.mock import patch

import pytest

from mas.llm.config import HuggingFaceConfig, OllamaConfig, OpenAIConfig
from mas.llm.contracts import LLMMessage, LLMResponse
from mas.llm.errors import APIError, AuthenticationError, ConfigError, RateLimitError, ValidationError
from mas.llm.providers.openai import (
    OpenAIProvider,
    _build_headers,
    _map_http_error,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_Transport = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


def _config(
    model: str = "gpt-4o",
    organization: str | None = None,
    *,
    api_key: str = "sk-test",
    timeout_seconds: int = 30,
    max_retries: int = 3,
) -> OpenAIConfig:
    return OpenAIConfig(
        model=model,
        api_key=api_key,
        organization=organization,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )


def _make_transport(response: dict[str, Any]) -> _Transport:
    async def _t(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        return response

    return _t


def _make_error_transport(error: Exception) -> _Transport:
    async def _t(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise error

    return _t


def _capture_transport() -> tuple[_Transport, list[tuple[str, dict[str, Any]]]]:
    calls: list[tuple[str, dict[str, Any]]] = []

    async def _t(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        calls.append((url, payload))
        return _DEFAULT_RESPONSE

    return _t, calls


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


_DEFAULT_RESPONSE: dict[str, Any] = {
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Hello!"},
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 5,
        "completion_tokens": 2,
        "total_tokens": 7,
    },
    "model": "gpt-4o",
}

_MESSAGES = [LLMMessage(role="user", content="Hello")]


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestOpenAIProviderConstruction:
    def test_name_is_openai(self) -> None:
        provider = OpenAIProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.name == "openai"

    def test_default_model_from_config(self) -> None:
        provider = OpenAIProvider(_config(model="gpt-3.5-turbo"), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.default_model == "gpt-3.5-turbo"

    def test_supports_streaming_is_false(self) -> None:
        provider = OpenAIProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.supports_streaming is False

    def test_invalid_config_raises_config_error(self) -> None:
        with pytest.raises(ConfigError):
            OpenAIProvider(OllamaConfig(model="llama2"))  # type: ignore[arg-type]

    def test_timeout_from_config_honored(self) -> None:
        provider = OpenAIProvider(_config(timeout_seconds=10), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.timeout_seconds == 10

    def test_max_retries_from_config_honored(self) -> None:
        provider = OpenAIProvider(_config(max_retries=1), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.max_retries == 1


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


class TestValidateConfig:
    def test_accepts_openai_config(self) -> None:
        provider = OpenAIProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config(_config()) is True

    def test_rejects_none(self) -> None:
        provider = OpenAIProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config(None) is False

    def test_rejects_ollama_config(self) -> None:
        provider = OpenAIProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config(OllamaConfig(model="llama2")) is False

    def test_rejects_huggingface_config(self) -> None:
        provider = OpenAIProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config(HuggingFaceConfig(model="gpt2", api_key="hf-x")) is False


# ---------------------------------------------------------------------------
# estimate_tokens
# ---------------------------------------------------------------------------


class TestEstimateTokens:
    def test_default_heuristic(self) -> None:
        provider = OpenAIProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.estimate_tokens("abcd") == 1
        assert provider.estimate_tokens("hello world") == 3

    def test_empty_string(self) -> None:
        provider = OpenAIProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.estimate_tokens("") == 0


# ---------------------------------------------------------------------------
# Happy-path call()
# ---------------------------------------------------------------------------


class TestOpenAIProviderCall:
    def test_call_returns_llm_response(self) -> None:
        provider = OpenAIProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        resp = _run(provider.call(_MESSAGES))
        assert isinstance(resp, LLMResponse)
        assert resp.message.role == "assistant"
        assert resp.message.content == "Hello!"

    def test_call_uses_chat_completions_url(self) -> None:
        transport, calls = _capture_transport()
        provider = OpenAIProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES))
        assert calls[0][0] == "https://api.openai.com/v1/chat/completions"

    def test_call_sends_messages(self) -> None:
        transport, calls = _capture_transport()
        provider = OpenAIProvider(_config(), _transport=transport)
        _run(provider.call([LLMMessage(role="user", content="ping")]))
        assert calls[0][1]["messages"] == [{"role": "user", "content": "ping"}]

    def test_call_sends_multiple_messages(self) -> None:
        transport, calls = _capture_transport()
        provider = OpenAIProvider(_config(), _transport=transport)
        messages = [
            LLMMessage(role="user", content="Hello"),
            LLMMessage(role="assistant", content="Hi"),
            LLMMessage(role="user", content="Bye"),
        ]
        _run(provider.call(messages))
        assert calls[0][1]["messages"] == [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "Bye"},
        ]

    def test_call_sends_stream_false(self) -> None:
        transport, calls = _capture_transport()
        provider = OpenAIProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES))
        assert calls[0][1]["stream"] is False

    def test_call_uses_model_arg(self) -> None:
        transport, calls = _capture_transport()
        provider = OpenAIProvider(_config(model="gpt-4o"), _transport=transport)
        _run(provider.call(_MESSAGES, "gpt-3.5-turbo"))
        assert calls[0][1]["model"] == "gpt-3.5-turbo"

    def test_call_uses_default_model_when_no_arg(self) -> None:
        transport, calls = _capture_transport()
        provider = OpenAIProvider(_config(model="gpt-4o"), _transport=transport)
        _run(provider.call(_MESSAGES))
        assert calls[0][1]["model"] == "gpt-4o"

    def test_tokens_used_from_usage_total_tokens(self) -> None:
        provider = OpenAIProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        resp = _run(provider.call(_MESSAGES))
        assert resp.tokens_used == 7

    def test_model_in_response_comes_from_api(self) -> None:
        response = {**_DEFAULT_RESPONSE, "model": "gpt-4o-2024-08-06"}
        provider = OpenAIProvider(_config(), _transport=_make_transport(response))
        resp = _run(provider.call(_MESSAGES))
        assert resp.model == "gpt-4o-2024-08-06"

    def test_model_falls_back_to_request_model_when_absent(self) -> None:
        response = {k: v for k, v in _DEFAULT_RESPONSE.items() if k != "model"}
        provider = OpenAIProvider(_config(model="gpt-4o"), _transport=_make_transport(response))
        resp = _run(provider.call(_MESSAGES))
        assert resp.model == "gpt-4o"

    def test_metadata_finish_reason(self) -> None:
        provider = OpenAIProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        resp = _run(provider.call(_MESSAGES))
        assert resp.metadata is not None
        assert resp.metadata["finish_reason"] == "stop"

    def test_metadata_token_breakdown(self) -> None:
        provider = OpenAIProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        resp = _run(provider.call(_MESSAGES))
        assert resp.metadata is not None
        assert resp.metadata["prompt_tokens"] == 5
        assert resp.metadata["completion_tokens"] == 2

    def test_content_whitespace_preserved(self) -> None:
        response = {
            **_DEFAULT_RESPONSE,
            "choices": [{"message": {"role": "assistant", "content": "  hi\n"}, "finish_reason": "stop"}],
        }
        provider = OpenAIProvider(_config(), _transport=_make_transport(response))
        resp = _run(provider.call(_MESSAGES))
        assert resp.message.content == "  hi\n"


# ---------------------------------------------------------------------------
# Generation kwargs — must go at top level of request body
# ---------------------------------------------------------------------------


class TestGenerationKwargs:
    def test_temperature_goes_to_top_level(self) -> None:
        transport, calls = _capture_transport()
        provider = OpenAIProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES, temperature=0.7))
        assert calls[0][1]["temperature"] == pytest.approx(0.7)

    def test_max_tokens_goes_to_top_level(self) -> None:
        transport, calls = _capture_transport()
        provider = OpenAIProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES, max_tokens=256))
        assert calls[0][1]["max_tokens"] == 256

    def test_multiple_kwargs_all_top_level(self) -> None:
        transport, calls = _capture_transport()
        provider = OpenAIProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES, temperature=0.5, top_p=0.9, presence_penalty=0.1))
        payload = calls[0][1]
        assert payload["temperature"] == pytest.approx(0.5)
        assert payload["top_p"] == pytest.approx(0.9)
        assert payload["presence_penalty"] == pytest.approx(0.1)

    def test_kwargs_do_not_nest_under_options(self) -> None:
        transport, calls = _capture_transport()
        provider = OpenAIProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES, temperature=0.5))
        assert "options" not in calls[0][1]

    def test_no_kwargs_sends_only_model_messages_stream(self) -> None:
        transport, calls = _capture_transport()
        provider = OpenAIProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES))
        expected_keys = {"model", "messages", "stream"}
        assert set(calls[0][1].keys()) == expected_keys


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestOpenAIProviderErrors:
    def test_empty_choices_raises_api_error(self) -> None:
        response = {**_DEFAULT_RESPONSE, "choices": []}
        provider = OpenAIProvider(_config(), _transport=_make_transport(response))
        with pytest.raises(APIError, match="no choices"):
            _run(provider.call(_MESSAGES))

    def test_missing_choices_raises_api_error(self) -> None:
        response = {k: v for k, v in _DEFAULT_RESPONSE.items() if k != "choices"}
        provider = OpenAIProvider(_config(), _transport=_make_transport(response))
        with pytest.raises(APIError, match="no choices"):
            _run(provider.call(_MESSAGES))

    def test_empty_content_raises_api_error(self) -> None:
        response = {
            **_DEFAULT_RESPONSE,
            "choices": [{"message": {"role": "assistant", "content": ""}, "finish_reason": "stop"}],
        }
        provider = OpenAIProvider(_config(), _transport=_make_transport(response))
        with pytest.raises(APIError, match="empty content"):
            _run(provider.call(_MESSAGES))

    def test_whitespace_only_content_raises_api_error(self) -> None:
        response = {
            **_DEFAULT_RESPONSE,
            "choices": [{"message": {"role": "assistant", "content": "   "}, "finish_reason": "stop"}],
        }
        provider = OpenAIProvider(_config(), _transport=_make_transport(response))
        with pytest.raises(APIError):
            _run(provider.call(_MESSAGES))

    def test_transient_api_error_retried(self) -> None:
        call_count = 0

        async def _flaky(url: str, payload: dict[str, Any]) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APIError("blip", transient=True)
            return _DEFAULT_RESPONSE

        provider = OpenAIProvider(_config(), _transport=_flaky)
        with patch.object(provider, "_sleep"):
            resp = _run(provider.call(_MESSAGES))
        assert resp.message.content == "Hello!"
        assert call_count == 2

    def test_permanent_api_error_not_retried(self) -> None:
        call_count = 0

        async def _transport(url: str, payload: dict[str, Any]) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            raise APIError("bad request", transient=False)

        provider = OpenAIProvider(_config(), _transport=_transport)
        with pytest.raises(APIError):
            _run(provider.call(_MESSAGES))
        assert call_count == 1

    def test_rate_limit_error_is_retried(self) -> None:
        provider = OpenAIProvider(
            _config(), _transport=_make_error_transport(RateLimitError("429"))
        )
        with patch.object(provider, "_sleep"), pytest.raises(RateLimitError):
            _run(provider.call(_MESSAGES))

    def test_auth_error_not_retried(self) -> None:
        call_count = 0

        async def _transport(url: str, payload: dict[str, Any]) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            raise AuthenticationError("401")

        provider = OpenAIProvider(_config(), _transport=_transport)
        with pytest.raises(AuthenticationError):
            _run(provider.call(_MESSAGES))
        assert call_count == 1

    def test_empty_messages_raises_validation_error(self) -> None:
        provider = OpenAIProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        with pytest.raises(ValidationError):
            _run(provider.call([]))


# ---------------------------------------------------------------------------
# _build_headers (unit)
# ---------------------------------------------------------------------------


class TestBuildHeaders:
    def test_adds_bearer_and_content_type(self) -> None:
        headers = _build_headers("sk-secret")
        assert headers["Authorization"] == "Bearer sk-secret"
        assert headers["Content-Type"] == "application/json"

    def test_without_organization_no_org_header(self) -> None:
        headers = _build_headers("sk-secret")
        assert "OpenAI-Organization" not in headers

    def test_with_organization_adds_org_header(self) -> None:
        headers = _build_headers("sk-secret", organization="org-abc")
        assert headers["OpenAI-Organization"] == "org-abc"


# ---------------------------------------------------------------------------
# _map_http_error (unit)
# ---------------------------------------------------------------------------


def _make_http_error(code: int, reason: str = "reason") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url="http://x", code=code, msg=reason, hdrs=HTTPMessage(), fp=None)


class TestMapHttpError:
    def test_429_returns_rate_limit_error(self) -> None:
        err = _map_http_error(_make_http_error(429, "Too Many Requests"))
        assert isinstance(err, RateLimitError)
        assert err.transient is True

    def test_429_parses_retry_after_header(self) -> None:
        exc = _make_http_error(429)
        exc.headers["Retry-After"] = "60"
        err = _map_http_error(exc)
        assert isinstance(err, RateLimitError)
        assert err.retry_after_seconds == 60

    def test_429_ignores_non_integer_retry_after(self) -> None:
        exc = _make_http_error(429)
        exc.headers["Retry-After"] = "not-a-number"
        err = _map_http_error(exc)
        assert isinstance(err, RateLimitError)
        assert err.retry_after_seconds is None

    def test_401_returns_auth_error(self) -> None:
        err = _map_http_error(_make_http_error(401))
        assert isinstance(err, AuthenticationError)
        assert err.transient is False

    def test_403_returns_auth_error(self) -> None:
        err = _map_http_error(_make_http_error(403))
        assert isinstance(err, AuthenticationError)

    def test_500_returns_transient_api_error(self) -> None:
        err = _map_http_error(_make_http_error(500))
        assert isinstance(err, APIError)
        assert err.transient is True

    def test_503_returns_transient_api_error(self) -> None:
        err = _map_http_error(_make_http_error(503))
        assert isinstance(err, APIError)
        assert err.transient is True

    def test_400_returns_permanent_api_error(self) -> None:
        err = _map_http_error(_make_http_error(400))
        assert isinstance(err, APIError)
        assert err.transient is False

    def test_404_returns_permanent_api_error(self) -> None:
        err = _map_http_error(_make_http_error(404))
        assert isinstance(err, APIError)
        assert err.transient is False


# ---------------------------------------------------------------------------
# default_registry integration
# ---------------------------------------------------------------------------


class TestDefaultRegistryIntegration:
    def test_openai_registered_when_mas_llm_imported(self) -> None:
        from mas.llm import default_registry

        assert default_registry.is_registered("openai")

    def test_from_config_builds_openai_provider(self) -> None:
        from mas.llm import default_registry

        provider = default_registry.from_config(OpenAIConfig(model="gpt-4o", api_key="sk-test"))
        assert provider.name == "openai"
