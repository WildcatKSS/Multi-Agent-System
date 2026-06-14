"""Tests for HuggingFaceProvider."""

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
from mas.llm.providers.huggingface import (
    HuggingFaceProvider,
    _build_headers,
    _format_prompt,
    _map_http_error,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_Transport = Callable[[str, dict[str, Any]], Awaitable[Any]]


def _config(
    model: str = "gpt2",
    task: str = "text-generation",
    *,
    api_key: str = "hf-test-key",
    timeout_seconds: int = 30,
    max_retries: int = 3,
) -> HuggingFaceConfig:
    return HuggingFaceConfig(
        model=model,
        api_key=api_key,
        task=task,  # type: ignore[arg-type]
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )


def _make_transport(response: Any) -> _Transport:
    async def _t(url: str, payload: dict[str, Any]) -> Any:
        return response

    return _t


def _make_error_transport(error: Exception) -> _Transport:
    async def _t(url: str, payload: dict[str, Any]) -> Any:
        raise error

    return _t


def _capture_transport() -> tuple[_Transport, list[tuple[str, dict[str, Any]]]]:
    calls: list[tuple[str, dict[str, Any]]] = []

    async def _t(url: str, payload: dict[str, Any]) -> Any:
        calls.append((url, payload))
        return _DEFAULT_RESPONSE

    return _t, calls


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


_DEFAULT_RESPONSE: list[dict[str, Any]] = [{"generated_text": "Hello!"}]
_MESSAGES = [LLMMessage(role="user", content="Hello")]


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestHuggingFaceProviderConstruction:
    def test_name_is_huggingface(self) -> None:
        provider = HuggingFaceProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.name == "huggingface"

    def test_default_model_from_config(self) -> None:
        provider = HuggingFaceProvider(
            _config(model="mistralai/Mistral-7B-v0.1"),
            _transport=_make_transport(_DEFAULT_RESPONSE),
        )
        assert provider.default_model == "mistralai/Mistral-7B-v0.1"

    def test_supports_streaming_is_false(self) -> None:
        provider = HuggingFaceProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.supports_streaming is False

    def test_invalid_config_raises_config_error(self) -> None:
        with pytest.raises(ConfigError):
            HuggingFaceProvider(OllamaConfig(model="llama2"))  # type: ignore[arg-type]

    def test_timeout_from_config_honored(self) -> None:
        cfg = _config(timeout_seconds=5)
        provider = HuggingFaceProvider(cfg, _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.timeout_seconds == 5

    def test_max_retries_from_config_honored(self) -> None:
        cfg = _config(max_retries=0)
        provider = HuggingFaceProvider(cfg, _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.max_retries == 0


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


class TestValidateConfig:
    def test_accepts_huggingface_config(self) -> None:
        provider = HuggingFaceProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config(_config()) is True

    def test_rejects_none(self) -> None:
        provider = HuggingFaceProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config(None) is False

    def test_rejects_ollama_config(self) -> None:
        provider = HuggingFaceProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config(OllamaConfig(model="llama2")) is False

    def test_rejects_plain_dict(self) -> None:
        provider = HuggingFaceProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.validate_config({"model": "gpt2"}) is False


# ---------------------------------------------------------------------------
# estimate_tokens
# ---------------------------------------------------------------------------


class TestEstimateTokens:
    def test_default_heuristic(self) -> None:
        provider = HuggingFaceProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.estimate_tokens("abcd") == 1
        assert provider.estimate_tokens("hello world") == 3

    def test_empty_string(self) -> None:
        provider = HuggingFaceProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        assert provider.estimate_tokens("") == 0


# ---------------------------------------------------------------------------
# Happy-path call()
# ---------------------------------------------------------------------------


class TestHuggingFaceProviderCall:
    def test_call_returns_llm_response(self) -> None:
        provider = HuggingFaceProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        resp = _run(provider.call(_MESSAGES))
        assert isinstance(resp, LLMResponse)
        assert resp.message.role == "assistant"
        assert resp.message.content == "Hello!"

    def test_call_uses_correct_url(self) -> None:
        transport, calls = _capture_transport()
        provider = HuggingFaceProvider(_config(model="gpt2"), _transport=transport)
        _run(provider.call(_MESSAGES))
        assert calls[0][0] == "https://api-inference.huggingface.co/models/gpt2"

    def test_call_sends_formatted_prompt_single_message(self) -> None:
        transport, calls = _capture_transport()
        provider = HuggingFaceProvider(_config(), _transport=transport)
        _run(provider.call([LLMMessage(role="user", content="ping")]))
        assert calls[0][1]["inputs"] == "user: ping"

    def test_call_sends_formatted_prompt_multiple_messages(self) -> None:
        transport, calls = _capture_transport()
        provider = HuggingFaceProvider(_config(), _transport=transport)
        messages = [
            LLMMessage(role="user", content="Hello"),
            LLMMessage(role="assistant", content="Hi"),
            LLMMessage(role="user", content="Bye"),
        ]
        _run(provider.call(messages))
        assert calls[0][1]["inputs"] == "user: Hello\nassistant: Hi\nuser: Bye"

    def test_call_uses_model_from_arg(self) -> None:
        transport, calls = _capture_transport()
        provider = HuggingFaceProvider(_config(model="gpt2"), _transport=transport)
        _run(provider.call(_MESSAGES, "mistralai/Mistral-7B-v0.1"))
        assert "mistralai/Mistral-7B-v0.1" in calls[0][0]

    def test_call_uses_default_model_when_no_arg(self) -> None:
        transport, calls = _capture_transport()
        provider = HuggingFaceProvider(_config(model="bigscience/bloom"), _transport=transport)
        _run(provider.call(_MESSAGES))
        assert "bigscience/bloom" in calls[0][0]

    def test_tokens_used_is_zero(self) -> None:
        provider = HuggingFaceProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        resp = _run(provider.call(_MESSAGES))
        assert resp.tokens_used == 0

    def test_model_in_response_is_from_request(self) -> None:
        provider = HuggingFaceProvider(_config(model="gpt2"), _transport=_make_transport(_DEFAULT_RESPONSE))
        resp = _run(provider.call(_MESSAGES, "bigscience/bloom"))
        assert resp.model == "bigscience/bloom"

    def test_metadata_contains_task(self) -> None:
        provider = HuggingFaceProvider(_config(task="text-generation"), _transport=_make_transport(_DEFAULT_RESPONSE))
        resp = _run(provider.call(_MESSAGES))
        assert resp.metadata is not None
        assert resp.metadata["task"] == "text-generation"

    def test_metadata_task_reflects_text2text(self) -> None:
        provider = HuggingFaceProvider(
            _config(task="text2text"),
            _transport=_make_transport(_DEFAULT_RESPONSE),
        )
        resp = _run(provider.call(_MESSAGES))
        assert resp.metadata is not None
        assert resp.metadata["task"] == "text2text"

    def test_content_whitespace_preserved(self) -> None:
        response = [{"generated_text": "  hello\n"}]
        provider = HuggingFaceProvider(_config(), _transport=_make_transport(response))
        resp = _run(provider.call(_MESSAGES))
        assert resp.message.content == "  hello\n"


# ---------------------------------------------------------------------------
# Generation kwargs / parameters routing
# ---------------------------------------------------------------------------


class TestGenerationKwargs:
    def test_text_generation_adds_return_full_text_false_by_default(self) -> None:
        transport, calls = _capture_transport()
        provider = HuggingFaceProvider(_config(task="text-generation"), _transport=transport)
        _run(provider.call(_MESSAGES))
        assert calls[0][1]["parameters"]["return_full_text"] is False

    def test_text_generation_does_not_override_explicit_return_full_text(self) -> None:
        transport, calls = _capture_transport()
        provider = HuggingFaceProvider(_config(task="text-generation"), _transport=transport)
        _run(provider.call(_MESSAGES, return_full_text=True))
        assert calls[0][1]["parameters"]["return_full_text"] is True

    def test_text2text_does_not_add_return_full_text(self) -> None:
        transport, calls = _capture_transport()
        provider = HuggingFaceProvider(_config(task="text2text"), _transport=transport)
        _run(provider.call(_MESSAGES, temperature=0.5))
        assert "return_full_text" not in calls[0][1]["parameters"]
        assert calls[0][1]["parameters"]["temperature"] == pytest.approx(0.5)

    def test_text2text_with_no_kwargs_has_no_parameters_in_payload(self) -> None:
        transport, calls = _capture_transport()
        provider = HuggingFaceProvider(_config(task="text2text"), _transport=transport)
        _run(provider.call(_MESSAGES))
        assert "parameters" not in calls[0][1]

    def test_kwargs_go_under_parameters(self) -> None:
        transport, calls = _capture_transport()
        provider = HuggingFaceProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES, temperature=0.7, max_new_tokens=100))
        assert calls[0][1]["parameters"]["temperature"] == pytest.approx(0.7)
        assert calls[0][1]["parameters"]["max_new_tokens"] == 100
        assert "temperature" not in calls[0][1]

    def test_caller_supplied_parameters_dict_merged(self) -> None:
        transport, calls = _capture_transport()
        provider = HuggingFaceProvider(_config(), _transport=transport)
        _run(provider.call(_MESSAGES, parameters={"top_p": 0.9}, temperature=0.5))
        assert calls[0][1]["parameters"]["top_p"] == pytest.approx(0.9)
        assert calls[0][1]["parameters"]["temperature"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestHuggingFaceProviderErrors:
    def test_response_not_a_list_raises_api_error(self) -> None:
        provider = HuggingFaceProvider(
            _config(), _transport=_make_transport({"error": "bad format"})
        )
        with pytest.raises(APIError, match="unexpected response format"):
            _run(provider.call(_MESSAGES))

    def test_empty_list_raises_api_error(self) -> None:
        provider = HuggingFaceProvider(_config(), _transport=_make_transport([]))
        with pytest.raises(APIError, match="unexpected response format"):
            _run(provider.call(_MESSAGES))

    def test_empty_content_raises_api_error(self) -> None:
        provider = HuggingFaceProvider(
            _config(), _transport=_make_transport([{"generated_text": ""}])
        )
        with pytest.raises(APIError, match="empty content"):
            _run(provider.call(_MESSAGES))

    def test_whitespace_only_content_raises_api_error(self) -> None:
        provider = HuggingFaceProvider(
            _config(), _transport=_make_transport([{"generated_text": "   "}])
        )
        with pytest.raises(APIError):
            _run(provider.call(_MESSAGES))

    def test_transient_api_error_retried(self) -> None:
        call_count = 0

        async def _flaky(url: str, payload: dict[str, Any]) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APIError("blip", transient=True)
            return _DEFAULT_RESPONSE

        provider = HuggingFaceProvider(_config(), _transport=_flaky)
        with patch.object(provider, "_sleep"):
            resp = _run(provider.call(_MESSAGES))
        assert resp.message.content == "Hello!"
        assert call_count == 2

    def test_permanent_api_error_not_retried(self) -> None:
        call_count = 0

        async def _transport(url: str, payload: dict[str, Any]) -> Any:
            nonlocal call_count
            call_count += 1
            raise APIError("bad request", transient=False)

        provider = HuggingFaceProvider(_config(), _transport=_transport)
        with pytest.raises(APIError):
            _run(provider.call(_MESSAGES))
        assert call_count == 1

    def test_rate_limit_error_is_transient(self) -> None:
        provider = HuggingFaceProvider(
            _config(), _transport=_make_error_transport(RateLimitError("429"))
        )
        with patch.object(provider, "_sleep"), pytest.raises(RateLimitError):
            _run(provider.call(_MESSAGES))

    def test_auth_error_not_retried(self) -> None:
        call_count = 0

        async def _transport(url: str, payload: dict[str, Any]) -> Any:
            nonlocal call_count
            call_count += 1
            raise AuthenticationError("401")

        provider = HuggingFaceProvider(_config(), _transport=_transport)
        with pytest.raises(AuthenticationError):
            _run(provider.call(_MESSAGES))
        assert call_count == 1

    def test_empty_messages_raises_validation_error(self) -> None:
        provider = HuggingFaceProvider(_config(), _transport=_make_transport(_DEFAULT_RESPONSE))
        with pytest.raises(ValidationError):
            _run(provider.call([]))


# ---------------------------------------------------------------------------
# _format_prompt (unit)
# ---------------------------------------------------------------------------


class TestFormatPrompt:
    def test_single_message(self) -> None:
        result = _format_prompt([LLMMessage(role="user", content="Hello")])
        assert result == "user: Hello"

    def test_multiple_messages(self) -> None:
        messages = [
            LLMMessage(role="user", content="Hi"),
            LLMMessage(role="assistant", content="Hello"),
            LLMMessage(role="user", content="Bye"),
        ]
        result = _format_prompt(messages)
        assert result == "user: Hi\nassistant: Hello\nuser: Bye"


# ---------------------------------------------------------------------------
# _build_headers (unit)
# ---------------------------------------------------------------------------


class TestBuildHeaders:
    def test_adds_bearer_and_content_type(self) -> None:
        headers = _build_headers("hf-secret")
        assert headers["Authorization"] == "Bearer hf-secret"
        assert headers["Content-Type"] == "application/json"


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

    def test_401_returns_auth_error(self) -> None:
        err = _map_http_error(_make_http_error(401))
        assert isinstance(err, AuthenticationError)
        assert err.transient is False

    def test_403_returns_auth_error(self) -> None:
        err = _map_http_error(_make_http_error(403))
        assert isinstance(err, AuthenticationError)

    def test_503_without_body_is_transient(self) -> None:
        err = _map_http_error(_make_http_error(503, "Service Unavailable"))
        assert isinstance(err, APIError)
        assert err.transient is True
        assert "estimated_time" not in err.message

    def test_503_with_estimated_time_includes_it_in_message(self) -> None:
        exc = _make_http_error(503, "Service Unavailable")
        err = _map_http_error(exc, body={"estimated_time": 20, "error": "Model loading"})
        assert isinstance(err, APIError)
        assert err.transient is True
        assert "estimated_time=20" in err.message

    def test_500_returns_transient_api_error(self) -> None:
        err = _map_http_error(_make_http_error(500))
        assert isinstance(err, APIError)
        assert err.transient is True

    def test_404_returns_permanent_api_error(self) -> None:
        err = _map_http_error(_make_http_error(404))
        assert isinstance(err, APIError)
        assert err.transient is False


# ---------------------------------------------------------------------------
# default_registry integration
# ---------------------------------------------------------------------------


class TestDefaultRegistryIntegration:
    def test_huggingface_registered_when_mas_llm_imported(self) -> None:
        from mas.llm import default_registry

        assert default_registry.is_registered("huggingface")

    def test_from_config_builds_huggingface_provider(self) -> None:
        from mas.llm import default_registry

        provider = default_registry.from_config(
            HuggingFaceConfig(model="gpt2", api_key="hf-test")
        )
        assert provider.name == "huggingface"
