"""Tests for the ProviderRegistry factory."""

import logging
from typing import Any

import pytest

from mas.llm.base import BaseProvider
from mas.llm.config import (
    AnthropicConfig,
    HuggingFaceConfig,
    LLMConfig,
    OllamaConfig,
    OpenAIConfig,
)
from mas.llm.contracts import ConfigError, LLMMessage, LLMResponse
from mas.llm.provider_registry import (
    BUILTIN_PROVIDER_CONFIGS,
    ProviderRegistry,
    default_registry,
)


class _FakeProvider(BaseProvider):
    """Minimal concrete provider for registry tests."""

    @property
    def name(self) -> str:
        return "fake"

    @property
    def default_model(self) -> str:
        return "fake-model"

    def validate_config(self, config: Any) -> bool:
        return True

    async def _invoke(self, messages: list[LLMMessage], model: str, **kwargs: Any) -> LLMResponse:
        raise NotImplementedError


class _OtherProvider(_FakeProvider):
    @property
    def name(self) -> str:
        return "other"


@pytest.fixture
def registry() -> ProviderRegistry:
    return ProviderRegistry()


class TestRegistration:
    def test_register_and_is_registered(self, registry: ProviderRegistry) -> None:
        registry.register("fake", _FakeProvider, OllamaConfig)
        assert registry.is_registered("fake")
        assert not registry.is_registered("missing")

    def test_empty_name_rejected(self, registry: ProviderRegistry) -> None:
        with pytest.raises(ValueError, match="provider name cannot be empty"):
            registry.register("", _FakeProvider, OllamaConfig)

    def test_duplicate_without_override_rejected(self, registry: ProviderRegistry) -> None:
        registry.register("fake", _FakeProvider, OllamaConfig)
        with pytest.raises(ValueError, match="already registered"):
            registry.register("fake", _OtherProvider, OllamaConfig)

    def test_override_replaces(self, registry: ProviderRegistry) -> None:
        registry.register("fake", _FakeProvider, OllamaConfig)
        registry.register("fake", _OtherProvider, OpenAIConfig, override=True)
        provider = registry.create("fake", OpenAIConfig(model="gpt-4", api_key="k"))
        assert provider.name == "other"

    def test_available_is_sorted(self, registry: ProviderRegistry) -> None:
        registry.register("zeta", _FakeProvider, OllamaConfig)
        registry.register("alpha", _OtherProvider, OpenAIConfig)
        assert registry.available() == ["alpha", "zeta"]

    def test_available_empty_by_default(self, registry: ProviderRegistry) -> None:
        assert registry.available() == []

    def test_unregister(self, registry: ProviderRegistry) -> None:
        registry.register("fake", _FakeProvider, OllamaConfig)
        registry.unregister("fake")
        assert not registry.is_registered("fake")

    def test_unregister_unknown_raises(self, registry: ProviderRegistry) -> None:
        with pytest.raises(ConfigError, match="Cannot unregister unknown provider 'missing'"):
            registry.unregister("missing")


class TestCreate:
    def test_create_returns_provider(self, registry: ProviderRegistry) -> None:
        registry.register("ollama", _FakeProvider, OllamaConfig)
        provider = registry.create("ollama", OllamaConfig(model="llama3"))
        assert isinstance(provider, _FakeProvider)
        assert provider.config.model == "llama3"

    def test_create_unknown_provider_raises(self, registry: ProviderRegistry) -> None:
        with pytest.raises(ConfigError, match="Unknown provider 'nope'"):
            registry.create("nope", OllamaConfig(model="llama3"))

    def test_create_unknown_lists_available(self, registry: ProviderRegistry) -> None:
        registry.register("ollama", _FakeProvider, OllamaConfig)
        with pytest.raises(ConfigError, match="Available providers: \\['ollama'\\]"):
            registry.create("nope", OllamaConfig(model="llama3"))

    def test_create_config_type_mismatch_raises(self, registry: ProviderRegistry) -> None:
        registry.register("ollama", _FakeProvider, OllamaConfig)
        with pytest.raises(ConfigError, match="expects OllamaConfig, got OpenAIConfig"):
            registry.create("ollama", OpenAIConfig(model="gpt-4", api_key="k"))

    def test_create_accepts_subclass_config(self, registry: ProviderRegistry) -> None:
        # create() is intentionally lenient: a subclass of the expected config
        # type is accepted (unlike from_config, which matches exactly).
        class _SubOllamaConfig(OllamaConfig):
            pass

        registry.register("ollama", _FakeProvider, OllamaConfig)
        provider = registry.create("ollama", _SubOllamaConfig(model="llama3"))
        assert isinstance(provider, _FakeProvider)


class TestFromConfig:
    def test_from_config_returns_provider(self, registry: ProviderRegistry) -> None:
        registry.register("ollama", _FakeProvider, OllamaConfig)
        provider = registry.from_config(OllamaConfig(model="llama3"))
        assert isinstance(provider, _FakeProvider)

    def test_from_config_none_rejected(self, registry: ProviderRegistry) -> None:
        with pytest.raises(ConfigError, match="config cannot be None"):
            registry.from_config(None)  # type: ignore[arg-type]

    def test_from_config_unregistered_type_raises(self, registry: ProviderRegistry) -> None:
        with pytest.raises(ConfigError, match="No provider registered for config type OllamaConfig"):
            registry.from_config(OllamaConfig(model="llama3"))

    def test_from_config_ambiguous_raises(self, registry: ProviderRegistry) -> None:
        registry.register("ollama-a", _FakeProvider, OllamaConfig)
        registry.register("ollama-b", _OtherProvider, OllamaConfig)
        with pytest.raises(ConfigError, match="Multiple providers registered for OllamaConfig"):
            registry.from_config(OllamaConfig(model="llama3"))

    def test_from_config_exact_type_match_only(self, registry: ProviderRegistry) -> None:
        # Registering for the base LLMConfig must not match an OllamaConfig instance.
        registry.register("base", _FakeProvider, LLMConfig)
        with pytest.raises(ConfigError, match="No provider registered for config type OllamaConfig"):
            registry.from_config(OllamaConfig(model="llama3"))


class TestPlugins:
    def test_custom_plugin_provider(self, registry: ProviderRegistry) -> None:
        class _CustomConfig(LLMConfig):
            pass

        class _CustomProvider(_FakeProvider):
            @property
            def name(self) -> str:
                return "custom"

        registry.register("custom", _CustomProvider, _CustomConfig)
        provider = registry.from_config(_CustomConfig(model="x"))
        assert provider.name == "custom"


class TestBuiltins:
    def test_builtin_provider_configs(self) -> None:
        assert {
            "ollama": OllamaConfig,
            "huggingface": HuggingFaceConfig,
            "openai": OpenAIConfig,
            "anthropic": AnthropicConfig,
        } == BUILTIN_PROVIDER_CONFIGS

    def test_default_registry_is_registry(self) -> None:
        assert isinstance(default_registry, ProviderRegistry)


class TestLogging:
    def test_instantiation_is_logged_without_secrets(
        self, registry: ProviderRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="mas.llm.registry")
        registry.register("openai", _FakeProvider, OpenAIConfig)
        registry.create("openai", OpenAIConfig(model="gpt-4", api_key="sk-SECRET"))

        records = [r for r in caplog.records if r.message == "provider_instantiated"]
        assert len(records) == 1
        assert records[0].provider == "openai"  # type: ignore[attr-defined]
        assert records[0].config_type == "OpenAIConfig"  # type: ignore[attr-defined]
        for rec in caplog.records:
            for value in rec.__dict__.values():
                assert "sk-SECRET" not in str(value)
