"""Tests for AnthropicProvider."""

import asyncio
import urllib.error
from collections.abc import Awaitable, Callable
from http.client import HTTPMessage
from typing import Any
from unittest.mock import patch

import pytest

from mas.llm.config import AnthropicConfig, OllamaConfig, OpenAIConfig
from mas.llm.contracts import LLMMessage, LLMResponse
from mas.llm.errors import APIError, AuthenticationError, ConfigError, RateLimitError, ValidationError
from mas.llm.providers.anthropic import (
    _DEFAULT_MAX_TOKENS,
    AnthropicProvider,
    _build_headers,
    _map_http_error,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_Transport = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


def _config(
    model: str = "claude-3-5-sonnet-20241022",
    version: str = "2023-06-01",
    *,
    api_key: str = "sk-ant-test",
    timeout_seconds: int = 30,
    max_retries: int = 3,
) -> AnthropicConfig:
    return AnthropicConfig(
        model=model,
        api_key=api_key,
        version=version,  # type: ignore[arg-type]
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
    "id": "msg_123",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "Hello!"}],
    "model": "claude-3-5-sonnet-20241022",
    "usage": {
        "input_tokens": 10,
        "output_tokens": 5,
    },
    "stop_reason": "end_turn",
}

_MESSAGES = [LLMMessage(role="user", content="Hello")]


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestAnthropicProviderConstruction:
    def test_name_is_anthropic(self) -> None:
        provider = AnthropicProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.name == "anthropic"

    def test_default_model_from_config(self) -> None:
        provider = AnthropicProvider(
            _config(model="claude-3-opus-20240229"),
            _transport=_make_transport(_DEFAULT_RESPONSE),
        )
        assert provider.default_model == "claude-3-opus-20240229"

    def test_supports_streaming_is_false(self) -> None:
        provider = AnthropicProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.supports_streaming is False

    def test_invalid_config_raises_config_error(self) -> None:
        with pytest.raises(ConfigError):
            AnthropicProvider(OllamaConfig(model="llama2"))  # type: ignore[arg-type]

    def test_timeout_from_config_honored(self) -> None:
        provider = AnthropicProvider(
            _config(timeout_seconds=15), _transport=_make_transport(_DEFAULT_RESPONSE)
        )
        assert provider.timeout_seconds == 15

    def test_max_retries_from_config_honored(self) -> None:
        provider = AnthropicProvider(
            _config(max_retries=0), _transport=_make_transport(_DEFAULT_RESPONSE)
        )
        assert provider.max_retries == 0


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


class TestValidateConfig:
    def test_accepts_anthropic_config(self) -> None:
        provider = AnthropicProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config(_config()) is True

    def test_rejects_none(self) -> None:
        provider = AnthropicProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config(None) is False

    def test_rejects_ollama_config(self) -> None:
        provider = AnthropicProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config(OllamaConfig(model="llama2")) is False

    def test_rejects_openai_config(self) -> None:
        provider = AnthropicProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config(OpenAIConfig(model="gpt-4o", api_key="sk-x")) is False


# ---------------------------------------------------------------------------
# estimate_tokens
# ---------------------------------------------------------------------------


class TestEstimateTokens:
    def test_default_heuristic(self) -> None:
        provider = AnthropicProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.estimate_tokens("abcd") == 1
        assert provider.estimate_tokens("hello world") == 3

    def test_empty_string(self) -> None:
        provider = AnthropicProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.estimate_tokens("") == 0


# ---------------------------------------------------------------------------
# Happy-path call()
# ---------------------------------------------------------------------------


class TestAnthropicProviderCall:
    def test_call_returns_llm_response(self) -> None:
        provider = AnthropicProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        resp = _run(provider.call(_MESSAGES))
        assert isinstance(resp, LLMResponse)
        assert resp.message.role == "assistant"
        assert resp.message.content == "Hello!"

    def test_call_uses_messages_url(self) -> None:
        transport, calls = _capture_transport()
        provider = AnthropicProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES))
        assert calls[0][0] == "https://api.anthropic.com/v1/messages"

    def test_call_sends_messages(self) -> None:
        transport, calls = _capture_transport()
        provider = AnthropicProvider(_config(), _transport=transport)
        _run(provider.call([LLMMessage(role="user", content="ping")]))
        assert calls[0][1]["messages"] == [{"role": "user", "content": "ping"}]

    def test_call_sends_multiple_messages(self) -> None:
        transport, calls = _capture_transport()
        provider = AnthropicProvider(_config(), _transport=transport)
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

    def test_call_uses_model_arg(self) -> None:
        transport, calls = _capture_transport()
        provider = AnthropicProvider(_config(model="claude-3-5-sonnet-20241022"), _transport=transport)
        _run(provider.call(_MESSAGES, "claude-3-opus-20240229"))
        assert calls[0][1]["model"] == "claude-3-opus-20240229"

    def test_call_uses_default_model_when_no_arg(self) -> None:
        transport, calls = _capture_transport()
        provider = AnthropicProvider(_config(model="claude-3-5-sonnet-20241022"), _transport=transport)
        _run(provider.call(_MESSAGES))
        assert calls[0][1]["model"] == "claude-3-5-sonnet-20241022"

    def test_tokens_used_sum_of_input_and_output(self) -> None:
        provider = AnthropicProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        resp = _run(provider.call(_MESSAGES))
        assert resp.tokens_used == 15  # 10 + 5

    def test_model_in_response_comes_from_api(self) -> None:
        response = {**_DEFAULT_RESPONSE, "model": "claude-3-5-sonnet-20241022-v2"}
        provider = AnthropicProvider(_config(), _transport=_make_transport(response))
        resp = _run(provider.call(_MESSAGES))
        assert resp.model == "claude-3-5-sonnet-20241022-v2"

    def test_model_falls_back_to_request_model_when_absent(self) -> None:
        response = {k: v for k, v in _DEFAULT_RESPONSE.items() if k != "model"}
        provider = AnthropicProvider(
            _config(model="claude-3-5-sonnet-20241022"), _transport=_make_transport(response)
        )
        resp = _run(provider.call(_MESSAGES))
        assert resp.model == "claude-3-5-sonnet-20241022"

    def test_metadata_stop_reason(self) -> None:
        provider = AnthropicProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        resp = _run(provider.call(_MESSAGES))
        assert resp.metadata is not None
        assert resp.metadata["stop_reason"] == "end_turn"

    def test_metadata_token_breakdown(self) -> None:
        provider = AnthropicProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        resp = _run(provider.call(_MESSAGES))
        assert resp.metadata is not None
        assert resp.metadata["input_tokens"] == 10
        assert resp.metadata["output_tokens"] == 5

    def test_content_whitespace_preserved(self) -> None:
        response = {
            **_DEFAULT_RESPONSE,
            "content": [{"type": "text", "text": "  hi\n"}],
        }
        provider = AnthropicProvider(_config(), _transport=_make_transport(response))
        resp = _run(provider.call(_MESSAGES))
        assert resp.message.content == "  hi\n"

    def test_extracts_first_content_block(self) -> None:
        response = {
            **_DEFAULT_RESPONSE,
            "content": [
                {"type": "text", "text": "First block"},
                {"type": "text", "text": "Second block"},
            ],
        }
        provider = AnthropicProvider(_config(), _transport=_make_transport(response))
        resp = _run(provider.call(_MESSAGES))
        assert resp.message.content == "First block"


# ---------------------------------------------------------------------------
# max_tokens handling
# ---------------------------------------------------------------------------


class TestMaxTokens:
    def test_default_max_tokens_sent_when_not_supplied(self) -> None:
        transport, calls = _capture_transport()
        provider = AnthropicProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES))
        assert calls[0][1]["max_tokens"] == _DEFAULT_MAX_TOKENS

    def test_caller_max_tokens_overrides_default(self) -> None:
        transport, calls = _capture_transport()
        provider = AnthropicProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES, max_tokens=2048))
        assert calls[0][1]["max_tokens"] == 2048

    def test_no_kwargs_sends_only_model_messages_max_tokens(self) -> None:
        transport, calls = _capture_transport()
        provider = AnthropicProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES))
        assert set(calls[0][1].keys()) == {"model", "messages", "max_tokens"}


# ---------------------------------------------------------------------------
# Generation kwargs — must go at top level of request body
# ---------------------------------------------------------------------------


class TestGenerationKwargs:
    def test_temperature_goes_to_top_level(self) -> None:
        transport, calls = _capture_transport()
        provider = AnthropicProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES, temperature=0.8))
        assert calls[0][1]["temperature"] == pytest.approx(0.8)

    def test_top_p_goes_to_top_level(self) -> None:
        transport, calls = _capture_transport()
        provider = AnthropicProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES, top_p=0.95))
        assert calls[0][1]["top_p"] == pytest.approx(0.95)

    def test_multiple_kwargs_all_top_level(self) -> None:
        transport, calls = _capture_transport()
        provider = AnthropicProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES, temperature=0.5, top_p=0.9))
        payload = calls[0][1]
        assert payload["temperature"] == pytest.approx(0.5)
        assert payload["top_p"] == pytest.approx(0.9)

    def test_kwargs_do_not_nest_under_options(self) -> None:
        transport, calls = _capture_transport()
        provider = AnthropicProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES, temperature=0.5))
        assert "options" not in calls[0][1]


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestAnthropicProviderErrors:
    def test_empty_content_blocks_raises_api_error(self) -> None:
        response = {**_DEFAULT_RESPONSE, "content": []}
        provider = AnthropicProvider(_config(), _transport=_make_transport(response))
        with pytest.raises(APIError, match="no content blocks"):
            _run(provider.call(_MESSAGES))

    def test_missing_content_raises_api_error(self) -> None:
        response = {k: v for k, v in _DEFAULT_RESPONSE.items() if k != "content"}
        provider = AnthropicProvider(_config(), _transport=_make_transport(response))
        with pytest.raises(APIError, match="no content blocks"):
            _run(provider.call(_MESSAGES))

    def test_empty_text_raises_api_error(self) -> None:
        response = {**_DEFAULT_RESPONSE, "content": [{"type": "text", "text": ""}]}
        provider = AnthropicProvider(_config(), _transport=_make_transport(response))
        with pytest.raises(APIError, match="empty content"):
            _run(provider.call(_MESSAGES))

    def test_whitespace_only_text_raises_api_error(self) -> None:
        response = {**_DEFAULT_RESPONSE, "content": [{"type": "text", "text": "   "}]}
        provider = AnthropicProvider(_config(), _transport=_make_transport(response))
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

        provider = AnthropicProvider(_config(), _transport=_flaky)
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

        provider = AnthropicProvider(_config(), _transport=_transport)
        with pytest.raises(APIError):
            _run(provider.call(_MESSAGES))
        assert call_count == 1

    def test_rate_limit_error_is_retried(self) -> None:
        provider = AnthropicProvider(
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

        provider = AnthropicProvider(_config(), _transport=_transport)
        with pytest.raises(AuthenticationError):
            _run(provider.call(_MESSAGES))
        assert call_count == 1

    def test_empty_messages_raises_validation_error(self) -> None:
        provider = AnthropicProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        with pytest.raises(ValidationError):
            _run(provider.call([]))


# ---------------------------------------------------------------------------
# _build_headers (unit)
# ---------------------------------------------------------------------------


class TestBuildHeaders:
    def test_sets_x_api_key(self) -> None:
        headers = _build_headers("sk-ant-secret", "2023-06-01")
        assert headers["x-api-key"] == "sk-ant-secret"

    def test_sets_anthropic_version(self) -> None:
        headers = _build_headers("sk-ant-secret", "2023-06-01")
        assert headers["anthropic-version"] == "2023-06-01"

    def test_sets_content_type(self) -> None:
        headers = _build_headers("sk-ant-secret", "2023-06-01")
        assert headers["Content-Type"] == "application/json"

    def test_no_authorization_bearer_header(self) -> None:
        headers = _build_headers("sk-ant-secret", "2023-06-01")
        assert "Authorization" not in headers

    def test_version_reflected_in_header(self) -> None:
        headers = _build_headers("key", "2023-01-01")
        assert headers["anthropic-version"] == "2023-01-01"


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
        exc.headers["Retry-After"] = "45"
        err = _map_http_error(exc)
        assert isinstance(err, RateLimitError)
        assert err.retry_after_seconds == 45

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

    def test_529_returns_transient_api_error(self) -> None:
        err = _map_http_error(_make_http_error(529, "Overloaded"))
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
    def test_anthropic_registered_when_mas_llm_imported(self) -> None:
        from mas.llm import default_registry

        assert default_registry.is_registered("anthropic")

    def test_from_config_builds_anthropic_provider(self) -> None:
        from mas.llm import default_registry

        provider = default_registry.from_config(
            AnthropicConfig(model="claude-3-5-sonnet-20241022", api_key="sk-ant-test")
        )
        assert provider.name == "anthropic"
