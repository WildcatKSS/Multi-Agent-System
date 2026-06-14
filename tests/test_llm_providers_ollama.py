"""Tests for OllamaProvider."""

import asyncio
import urllib.error
from collections.abc import Awaitable, Callable
from http.client import HTTPMessage
from typing import Any
from unittest.mock import patch

import pytest

from mas.llm.config import HuggingFaceConfig, OllamaConfig
from mas.llm.contracts import LLMMessage, LLMResponse
from mas.llm.errors import APIError, AuthenticationError, ConfigError, RateLimitError, ValidationError
from mas.llm.providers.ollama import OllamaProvider, _build_headers, _map_http_error

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_Transport = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


def _config(
    model: str = "llama2",
    base_url: str = "http://localhost:11434",
    *,
    api_key: str | None = None,
    timeout_seconds: int = 30,
    max_retries: int = 3,
) -> OllamaConfig:
    return OllamaConfig(
        model=model,
        base_url=base_url,
        api_key=api_key,
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
    "model": "llama2",
    "message": {"role": "assistant", "content": "Hello!"},
    "done": True,
    "prompt_eval_count": 10,
    "eval_count": 5,
}

_MESSAGES = [LLMMessage(role="user", content="Hello")]


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestOllamaProviderConstruction:
    def test_name_is_ollama(self) -> None:
        provider = OllamaProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.name == "ollama"

    def test_default_model_from_config(self) -> None:
        provider = OllamaProvider(_config(model="mistral"), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.default_model == "mistral"

    def test_supports_streaming_is_false(self) -> None:
        provider = OllamaProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.supports_streaming is False

    def test_invalid_config_raises_config_error(self) -> None:
        with pytest.raises(ConfigError):
            OllamaProvider(HuggingFaceConfig(model="x", api_key="k"))  # type: ignore[arg-type]

    def test_timeout_from_config_honored(self) -> None:
        cfg = _config(timeout_seconds=5)
        provider = OllamaProvider(cfg, _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.timeout_seconds == 5

    def test_max_retries_from_config_honored(self) -> None:
        cfg = _config(max_retries=0)
        provider = OllamaProvider(cfg, _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.max_retries == 0


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


class TestValidateConfig:
    def test_accepts_ollama_config(self) -> None:
        provider = OllamaProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config(_config()) is True

    def test_rejects_none(self) -> None:
        provider = OllamaProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config(None) is False

    def test_rejects_wrong_type(self) -> None:
        provider = OllamaProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config(HuggingFaceConfig(model="x", api_key="k")) is False

    def test_rejects_plain_dict(self) -> None:
        provider = OllamaProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config({"model": "llama2"}) is False


# ---------------------------------------------------------------------------
# estimate_tokens
# ---------------------------------------------------------------------------


class TestEstimateTokens:
    def test_default_heuristic(self) -> None:
        provider = OllamaProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.estimate_tokens("abcd") == 1  # 4 chars / 4 = 1
        assert provider.estimate_tokens("hello world") == 3  # 11 chars / 4 = 2.75 → ceil → 3

    def test_empty_string(self) -> None:
        provider = OllamaProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.estimate_tokens("") == 0


# ---------------------------------------------------------------------------
# Happy-path call()
# ---------------------------------------------------------------------------


class TestOllamaProviderCall:
    def test_call_returns_llm_response(self) -> None:
        provider = OllamaProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        resp = _run(provider.call(_MESSAGES))
        assert isinstance(resp, LLMResponse)
        assert resp.message.role == "assistant"
        assert resp.message.content == "Hello!"

    def test_call_uses_correct_url(self) -> None:
        transport, calls = _capture_transport()
        provider = OllamaProvider(_config(base_url="http://myhost:11434"), _transport=transport)
        _run(provider.call(_MESSAGES))
        assert calls[0][0] == "http://myhost:11434/api/chat"

    def test_call_sends_messages(self) -> None:
        transport, calls = _capture_transport()
        provider = OllamaProvider(_config(), _transport=transport)
        _run(provider.call([LLMMessage(role="user", content="ping")]))
        assert calls[0][1]["messages"] == [{"role": "user", "content": "ping"}]

    def test_call_includes_stream_false(self) -> None:
        transport, calls = _capture_transport()
        provider = OllamaProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES))
        assert calls[0][1]["stream"] is False

    def test_call_uses_model_from_arg(self) -> None:
        transport, calls = _capture_transport()
        provider = OllamaProvider(_config(model="llama2"), _transport=transport)
        _run(provider.call(_MESSAGES, "mistral"))
        assert calls[0][1]["model"] == "mistral"

    def test_call_uses_default_model_when_no_arg(self) -> None:
        transport, calls = _capture_transport()
        provider = OllamaProvider(_config(model="codellama"), _transport=transport)
        _run(provider.call(_MESSAGES))
        assert calls[0][1]["model"] == "codellama"

    def test_tokens_used_is_sum_of_prompt_and_eval(self) -> None:
        response = {**_DEFAULT_RESPONSE, "prompt_eval_count": 7, "eval_count": 13}
        provider = OllamaProvider(_config(), _transport=_make_transport(response))
        resp = _run(provider.call(_MESSAGES))
        assert resp.tokens_used == 20

    def test_tokens_used_defaults_to_zero_when_absent(self) -> None:
        response: dict[str, Any] = {
            "model": "llama2",
            "message": {"role": "assistant", "content": "Hello!"},
            "done": True,
        }
        provider = OllamaProvider(_config(), _transport=_make_transport(response))
        resp = _run(provider.call(_MESSAGES))
        assert resp.tokens_used == 0

    def test_model_in_response_taken_from_api(self) -> None:
        response = {**_DEFAULT_RESPONSE, "model": "mistral:latest"}
        provider = OllamaProvider(_config(), _transport=_make_transport(response))
        resp = _run(provider.call(_MESSAGES))
        assert resp.model == "mistral:latest"

    def test_metadata_contains_done_flag(self) -> None:
        provider = OllamaProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        resp = _run(provider.call(_MESSAGES))
        assert resp.metadata is not None
        assert resp.metadata["done"] is True

    def test_generation_kwargs_nested_under_options(self) -> None:
        transport, calls = _capture_transport()
        provider = OllamaProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES, temperature=0.7, top_p=0.9))
        assert calls[0][1]["options"]["temperature"] == pytest.approx(0.7)
        assert calls[0][1]["options"]["top_p"] == pytest.approx(0.9)
        assert "temperature" not in calls[0][1]

    def test_top_level_fields_not_nested(self) -> None:
        transport, calls = _capture_transport()
        provider = OllamaProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES, format="json", keep_alive="5m"))
        assert calls[0][1]["format"] == "json"
        assert calls[0][1]["keep_alive"] == "5m"
        assert "options" not in calls[0][1]

    def test_caller_supplied_options_dict_merged(self) -> None:
        transport, calls = _capture_transport()
        provider = OllamaProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES, options={"seed": 42}, temperature=0.5))
        assert calls[0][1]["options"]["seed"] == 42
        assert calls[0][1]["options"]["temperature"] == pytest.approx(0.5)

    def test_content_whitespace_preserved(self) -> None:
        response = {**_DEFAULT_RESPONSE, "message": {"role": "assistant", "content": "  hello\n"}}
        provider = OllamaProvider(_config(), _transport=_make_transport(response))
        resp = _run(provider.call(_MESSAGES))
        assert resp.message.content == "  hello\n"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestOllamaProviderErrors:
    def test_empty_content_raises_api_error(self) -> None:
        response = {**_DEFAULT_RESPONSE, "message": {"role": "assistant", "content": ""}}
        provider = OllamaProvider(_config(), _transport=_make_transport(response))
        with pytest.raises(APIError, match="empty content"):
            _run(provider.call(_MESSAGES))

    def test_whitespace_only_content_raises_api_error(self) -> None:
        response = {**_DEFAULT_RESPONSE, "message": {"role": "assistant", "content": "   "}}
        provider = OllamaProvider(_config(), _transport=_make_transport(response))
        with pytest.raises(APIError):
            _run(provider.call(_MESSAGES))

    def test_missing_message_key_raises_api_error(self) -> None:
        response: dict[str, Any] = {"model": "llama2", "done": True}
        provider = OllamaProvider(_config(), _transport=_make_transport(response))
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

        provider = OllamaProvider(_config(), _transport=_flaky)
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

        provider = OllamaProvider(_config(), _transport=_transport)
        with pytest.raises(APIError):
            _run(provider.call(_MESSAGES))
        assert call_count == 1

    def test_rate_limit_error_is_transient(self) -> None:
        provider = OllamaProvider(
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

        provider = OllamaProvider(_config(), _transport=_transport)
        with pytest.raises(AuthenticationError):
            _run(provider.call(_MESSAGES))
        assert call_count == 1

    def test_empty_messages_raises_validation_error(self) -> None:
        provider = OllamaProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        with pytest.raises(ValidationError):
            _run(provider.call([]))


# ---------------------------------------------------------------------------
# _map_http_error (unit)
# ---------------------------------------------------------------------------


def _make_http_error(code: int, reason: str = "reason") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url="http://x", code=code, msg=reason, hdrs=HTTPMessage(), fp=None)


class TestMapHttpError:
    def test_429_returns_rate_limit_error(self) -> None:
        exc = _make_http_error(429, "Too Many Requests")
        err = _map_http_error(exc)
        assert isinstance(err, RateLimitError)
        assert err.transient is True

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

    def test_404_returns_permanent_api_error(self) -> None:
        err = _map_http_error(_make_http_error(404))
        assert isinstance(err, APIError)
        assert err.transient is False

    def test_429_parses_retry_after_header(self) -> None:
        exc = _make_http_error(429)
        exc.headers["Retry-After"] = "30"
        err = _map_http_error(exc)
        assert isinstance(err, RateLimitError)
        assert err.retry_after_seconds == 30

    def test_429_ignores_non_integer_retry_after(self) -> None:
        exc = _make_http_error(429)
        exc.headers["Retry-After"] = "not-a-number"
        err = _map_http_error(exc)
        assert isinstance(err, RateLimitError)
        assert err.retry_after_seconds is None


# ---------------------------------------------------------------------------
# _build_headers (unit)
# ---------------------------------------------------------------------------


class TestBuildHeaders:
    def test_no_api_key_returns_content_type_only(self) -> None:
        headers = _build_headers(None)
        assert headers == {"Content-Type": "application/json"}
        assert "Authorization" not in headers

    def test_empty_api_key_returns_content_type_only(self) -> None:
        headers = _build_headers("")
        assert "Authorization" not in headers

    def test_api_key_adds_bearer_header(self) -> None:
        headers = _build_headers("sk-secret")
        assert headers["Authorization"] == "Bearer sk-secret"
        assert headers["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# default_registry integration (fix 3)
# ---------------------------------------------------------------------------


class TestDefaultRegistryIntegration:
    def test_ollama_registered_when_mas_llm_imported(self) -> None:
        from mas.llm import default_registry

        assert default_registry.is_registered("ollama")

    def test_from_config_builds_ollama_provider(self) -> None:
        from mas.llm import default_registry
        from mas.llm.config import OllamaConfig

        provider = default_registry.from_config(OllamaConfig(model="llama2"))
        assert provider.name == "ollama"
