"""Cross-provider integration tests.

These tests verify that all four built-in providers share a consistent
interface, that the registry dispatches correctly, and that multi-provider
workflows behave as expected. They use only the injectable transport seam —
no real HTTP calls are made.
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from mas.llm.config import AnthropicConfig, HuggingFaceConfig, LLMConfig, OllamaConfig, OpenAIConfig
from mas.llm.contracts import LLMMessage, LLMProvider, LLMResponse
from mas.llm.errors import APIError, AuthenticationError, ConfigError, RateLimitError
from mas.llm.provider_registry import ProviderRegistry, default_registry
from mas.llm.providers.anthropic import AnthropicProvider
from mas.llm.providers.huggingface import HuggingFaceProvider
from mas.llm.providers.ollama import OllamaProvider
from mas.llm.providers.openai import OpenAIProvider

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_Transport = Callable[[str, dict[str, Any]], Awaitable[Any]]

_MESSAGES = [LLMMessage(role="user", content="Hello")]


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _make_transport(response: Any) -> _Transport:
    async def _t(url: str, payload: dict[str, Any]) -> Any:
        return response

    return _t


def _make_error_transport(error: Exception) -> _Transport:
    async def _t(url: str, payload: dict[str, Any]) -> Any:
        raise error

    return _t


# ---------------------------------------------------------------------------
# Provider construction fixtures
# ---------------------------------------------------------------------------

_OLLAMA_RESPONSE: dict[str, Any] = {
    "message": {"role": "assistant", "content": "Hi from Ollama"},
    "prompt_eval_count": 5,
    "eval_count": 10,
    "model": "llama2",
    "done": True,
}

_HF_RESPONSE: list[dict[str, Any]] = [{"generated_text": "Hi from HuggingFace"}]

_OPENAI_RESPONSE: dict[str, Any] = {
    "id": "chatcmpl-1",
    "choices": [{"message": {"role": "assistant", "content": "Hi from OpenAI"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    "model": "gpt-4o",
}

_ANTHROPIC_RESPONSE: dict[str, Any] = {
    "id": "msg_1",
    "type": "message",
    "content": [{"type": "text", "text": "Hi from Anthropic"}],
    "model": "claude-3-5-sonnet-20241022",
    "usage": {"input_tokens": 5, "output_tokens": 4},
    "stop_reason": "end_turn",
}


def _make_ollama() -> OllamaProvider:
    return OllamaProvider(
        OllamaConfig(model="llama2"),
        _transport=_make_transport(_OLLAMA_RESPONSE),
    )


def _make_huggingface() -> HuggingFaceProvider:
    return HuggingFaceProvider(
        HuggingFaceConfig(model="gpt2", api_key="hf-test"),
        _transport=_make_transport(_HF_RESPONSE),
    )


def _make_openai() -> OpenAIProvider:
    return OpenAIProvider(
        OpenAIConfig(model="gpt-4o", api_key="sk-test"),
        _transport=_make_transport(_OPENAI_RESPONSE),
    )


def _make_anthropic() -> AnthropicProvider:
    return AnthropicProvider(
        AnthropicConfig(model="claude-3-5-sonnet-20241022", api_key="sk-ant-test"),
        _transport=_make_transport(_ANTHROPIC_RESPONSE),
    )


# ---------------------------------------------------------------------------
# Registry: all four providers are registered
# ---------------------------------------------------------------------------


class TestRegistryCompleteness:
    def test_all_four_providers_registered(self) -> None:
        for name in ["ollama", "huggingface", "openai", "anthropic"]:
            assert default_registry.is_registered(name), f"{name!r} not registered"

    def test_available_includes_all_four(self) -> None:
        available = default_registry.available()
        for name in ["ollama", "huggingface", "openai", "anthropic"]:
            assert name in available

    def test_available_is_sorted(self) -> None:
        available = default_registry.available()
        assert available == sorted(available)

    def test_from_config_ollama(self) -> None:
        provider = default_registry.from_config(OllamaConfig(model="llama2"))
        assert isinstance(provider, OllamaProvider)

    def test_from_config_huggingface(self) -> None:
        provider = default_registry.from_config(HuggingFaceConfig(model="gpt2", api_key="hf-x"))
        assert isinstance(provider, HuggingFaceProvider)

    def test_from_config_openai(self) -> None:
        provider = default_registry.from_config(OpenAIConfig(model="gpt-4o", api_key="sk-x"))
        assert isinstance(provider, OpenAIProvider)

    def test_from_config_anthropic(self) -> None:
        provider = default_registry.from_config(
            AnthropicConfig(model="claude-3-5-sonnet-20241022", api_key="sk-ant-x")
        )
        assert isinstance(provider, AnthropicProvider)

    def test_from_config_raises_for_unknown_config(self) -> None:
        isolated = ProviderRegistry()
        with pytest.raises(ConfigError):
            isolated.from_config(OllamaConfig(model="llama2"))

    def test_create_by_name_ollama(self) -> None:
        provider = default_registry.create("ollama", OllamaConfig(model="llama2"))
        assert isinstance(provider, OllamaProvider)

    def test_create_by_name_wrong_config_raises(self) -> None:
        with pytest.raises(ConfigError):
            default_registry.create("openai", OllamaConfig(model="llama2"))


# ---------------------------------------------------------------------------
# Interface contract: all providers implement LLMProvider
# ---------------------------------------------------------------------------


@pytest.fixture(
    params=["ollama", "huggingface", "openai", "anthropic"],
    ids=["ollama", "huggingface", "openai", "anthropic"],
)
def any_provider(request: pytest.FixtureRequest) -> LLMProvider:
    makers = {
        "ollama": _make_ollama,
        "huggingface": _make_huggingface,
        "openai": _make_openai,
        "anthropic": _make_anthropic,
    }
    return makers[request.param]()  # type: ignore[operator]


class TestProviderInterfaceContract:
    def test_is_llm_provider_instance(self, any_provider: LLMProvider) -> None:
        assert isinstance(any_provider, LLMProvider)

    def test_has_non_empty_name(self, any_provider: LLMProvider) -> None:
        assert isinstance(any_provider.name, str)
        assert any_provider.name

    def test_has_non_empty_default_model(self, any_provider: LLMProvider) -> None:
        assert isinstance(any_provider.default_model, str)
        assert any_provider.default_model

    def test_supports_streaming_is_false(self, any_provider: LLMProvider) -> None:
        assert any_provider.supports_streaming is False

    def test_call_returns_llm_response(self, any_provider: LLMProvider) -> None:
        resp = _run(any_provider.call(_MESSAGES))
        assert isinstance(resp, LLMResponse)

    def test_response_has_assistant_role(self, any_provider: LLMProvider) -> None:
        resp = _run(any_provider.call(_MESSAGES))
        assert resp.message.role == "assistant"

    def test_response_content_is_non_empty_string(self, any_provider: LLMProvider) -> None:
        resp = _run(any_provider.call(_MESSAGES))
        assert isinstance(resp.message.content, str)
        assert resp.message.content.strip()

    def test_response_has_model(self, any_provider: LLMProvider) -> None:
        resp = _run(any_provider.call(_MESSAGES))
        assert isinstance(resp.model, str)
        assert resp.model

    def test_response_latency_ms_is_non_negative(self, any_provider: LLMProvider) -> None:
        resp = _run(any_provider.call(_MESSAGES))
        assert resp.latency_ms >= 0.0

    def test_response_tokens_used_is_non_negative(self, any_provider: LLMProvider) -> None:
        resp = _run(any_provider.call(_MESSAGES))
        assert resp.tokens_used >= 0

    def test_validate_config_accepts_own_config(self, any_provider: LLMProvider) -> None:
        assert any_provider.validate_config(any_provider.config) is True

    def test_validate_config_rejects_none(self, any_provider: LLMProvider) -> None:
        assert any_provider.validate_config(None) is False


# ---------------------------------------------------------------------------
# Error consistency: all providers raise the same error types
# ---------------------------------------------------------------------------


@pytest.fixture(
    params=["ollama", "huggingface", "openai", "anthropic"],
    ids=["ollama", "huggingface", "openai", "anthropic"],
)
def provider_with_error(request: pytest.FixtureRequest) -> tuple[LLMProvider, str]:
    """Return (provider, provider_name) for parametrized error tests."""
    name: str = request.param

    def _build(error: Exception) -> LLMProvider:
        transport = _make_error_transport(error)
        if name == "ollama":
            return OllamaProvider(OllamaConfig(model="llama2"), _transport=transport)
        if name == "huggingface":
            return HuggingFaceProvider(
                HuggingFaceConfig(model="gpt2", api_key="hf-x"), _transport=transport
            )
        if name == "openai":
            return OpenAIProvider(OpenAIConfig(model="gpt-4o", api_key="sk-x"), _transport=transport)
        return AnthropicProvider(
            AnthropicConfig(model="claude-3-5-sonnet-20241022", api_key="sk-ant-x"),
            _transport=transport,
        )

    return _build, name  # type: ignore[return-value]


class TestErrorConsistency:
    def test_api_error_propagates(self, provider_with_error: Any) -> None:
        build, _ = provider_with_error
        provider = build(APIError("test failure", transient=False))
        with pytest.raises(APIError):
            _run(provider.call(_MESSAGES))

    def test_auth_error_propagates(self, provider_with_error: Any) -> None:
        build, _ = provider_with_error
        provider = build(AuthenticationError("unauthorized"))
        with pytest.raises(AuthenticationError):
            _run(provider.call(_MESSAGES))

    def test_rate_limit_error_propagates(self, provider_with_error: Any) -> None:
        build, _ = provider_with_error
        provider = build(RateLimitError("rate limited"))
        with pytest.raises(RateLimitError):
            _run(provider.call(_MESSAGES))


# ---------------------------------------------------------------------------
# Multi-provider workflow: a generic function works with any provider
# ---------------------------------------------------------------------------


async def _call_any(provider: LLMProvider, message: str) -> str:
    """A generic function that accepts any LLMProvider."""
    resp = await provider.call([LLMMessage(role="user", content=message)])
    return resp.message.content


class TestMultiProviderWorkflow:
    def test_ollama_usable_as_llm_provider(self) -> None:
        result = _run(_call_any(_make_ollama(), "Hello"))
        assert result == "Hi from Ollama"

    def test_huggingface_usable_as_llm_provider(self) -> None:
        result = _run(_call_any(_make_huggingface(), "Hello"))
        assert result == "Hi from HuggingFace"

    def test_openai_usable_as_llm_provider(self) -> None:
        result = _run(_call_any(_make_openai(), "Hello"))
        assert result == "Hi from OpenAI"

    def test_anthropic_usable_as_llm_provider(self) -> None:
        result = _run(_call_any(_make_anthropic(), "Hello"))
        assert result == "Hi from Anthropic"

    def test_all_providers_return_non_empty_content(self) -> None:
        providers = [_make_ollama(), _make_huggingface(), _make_openai(), _make_anthropic()]
        for provider in providers:
            resp = _run(provider.call(_MESSAGES))
            assert resp.message.content.strip(), f"{provider.name} returned empty content"

    def test_provider_names_are_unique(self) -> None:
        providers = [_make_ollama(), _make_huggingface(), _make_openai(), _make_anthropic()]
        names = [p.name for p in providers]
        assert len(names) == len(set(names))

    def test_provider_names_match_registry_keys(self) -> None:
        providers = [_make_ollama(), _make_huggingface(), _make_openai(), _make_anthropic()]
        for provider in providers:
            assert default_registry.is_registered(provider.name)

    def test_sequential_calls_same_provider(self) -> None:
        provider = _make_openai()
        for _ in range(3):
            resp = _run(provider.call(_MESSAGES))
            assert resp.message.content


# ---------------------------------------------------------------------------
# Registry isolation: custom registry does not pollute default_registry
# ---------------------------------------------------------------------------


class TestRegistryIsolation:
    def test_custom_registry_is_independent(self) -> None:
        isolated = ProviderRegistry()
        assert not isolated.is_registered("openai")
        assert default_registry.is_registered("openai")

    def test_register_in_isolated_does_not_affect_default(self) -> None:
        isolated = ProviderRegistry()
        isolated.register("test-provider", OpenAIProvider, OpenAIConfig)
        assert not default_registry.is_registered("test-provider")

    def test_unregister_raises_for_unknown_name(self) -> None:
        isolated = ProviderRegistry()
        with pytest.raises(ConfigError):
            isolated.unregister("nonexistent")

    def test_override_replaces_registration(self) -> None:
        isolated = ProviderRegistry()
        isolated.register("openai", OpenAIProvider, OpenAIConfig)
        isolated.register("openai", OpenAIProvider, OpenAIConfig, override=True)
        assert isolated.is_registered("openai")

    def test_duplicate_registration_raises_without_override(self) -> None:
        isolated = ProviderRegistry()
        isolated.register("openai", OpenAIProvider, OpenAIConfig)
        with pytest.raises(ValueError, match="already registered"):
            isolated.register("openai", OpenAIProvider, OpenAIConfig)


# ---------------------------------------------------------------------------
# Config type dispatch
# ---------------------------------------------------------------------------


class TestConfigTypeDispatch:
    @pytest.mark.parametrize(
        ("config", "expected_name"),
        [
            (OllamaConfig(model="llama2"), "ollama"),
            (HuggingFaceConfig(model="gpt2", api_key="hf-x"), "huggingface"),
            (OpenAIConfig(model="gpt-4o", api_key="sk-x"), "openai"),
            (AnthropicConfig(model="claude-3-5-sonnet-20241022", api_key="sk-ant-x"), "anthropic"),
        ],
        ids=["ollama", "huggingface", "openai", "anthropic"],
    )
    def test_from_config_dispatches_correctly(
        self, config: LLMConfig, expected_name: str
    ) -> None:
        provider = default_registry.from_config(config)
        assert provider.name == expected_name

    def test_base_config_has_no_dispatch(self) -> None:
        isolated = ProviderRegistry()
        with pytest.raises(ConfigError):
            isolated.from_config(LLMConfig(model="x"))
