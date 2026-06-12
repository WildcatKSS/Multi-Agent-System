"""ProviderRegistry: a factory mapping configs to LLM provider instances.

The registry decouples *which* provider to build from the call site: a provider
class is registered under a name together with the :class:`LLMConfig` subclass it
consumes, and :meth:`ProviderRegistry.from_config` then builds the right provider
for a given config. Custom/plugin providers use the same :meth:`register` entry
point as the built-ins.

The concrete built-in provider classes (Ollama, HuggingFace, OpenAI, Anthropic)
are implemented in Phase 2 and self-register there. This module ships the
registry machinery plus :data:`BUILTIN_PROVIDER_CONFIGS`, the canonical mapping
of built-in provider names to their config types.
"""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from mas.llm.config import (
    AnthropicConfig,
    HuggingFaceConfig,
    LLMConfig,
    OllamaConfig,
    OpenAIConfig,
)
from mas.llm.contracts import ConfigError, LLMProvider

_logger = logging.getLogger("mas.llm.registry")

#: Canonical built-in provider names and the config type each consumes. The
#: concrete provider classes are registered in Phase 2 (#55-#58). Read-only.
BUILTIN_PROVIDER_CONFIGS: Mapping[str, type[LLMConfig]] = MappingProxyType(
    {
        "ollama": OllamaConfig,
        "huggingface": HuggingFaceConfig,
        "openai": OpenAIConfig,
        "anthropic": AnthropicConfig,
    }
)


@dataclass(frozen=True)
class _Registration:
    """A registered provider: its factory plus the config type it accepts."""

    provider_class: Callable[..., LLMProvider]
    config_type: type[LLMConfig]


class ProviderRegistry:
    """A factory that builds LLM providers from their configuration.

    Maps a provider *name* to a provider class and the :class:`LLMConfig`
    subclass it consumes. Use :meth:`register` to add providers (built-in or
    plugin), :meth:`create` to build by name, and :meth:`from_config` to build by
    inferring the provider from the config's type.
    """

    def __init__(self) -> None:
        self._providers: dict[str, _Registration] = {}

    def register(
        self,
        name: str,
        provider_class: type[LLMProvider],
        config_type: type[LLMConfig],
        *,
        override: bool = False,
    ) -> None:
        """Register a provider under ``name``.

        Args:
            name: Unique provider name (e.g. ``"ollama"``).
            provider_class: The provider class to instantiate. Called as
                ``provider_class(config)``.
            config_type: The :class:`LLMConfig` subclass this provider consumes.
            override: If ``True``, replace an existing registration with the same
                name. If ``False`` (default), a duplicate name raises.

        Raises:
            ValueError: If ``name`` is empty, or already registered and
                ``override`` is ``False``.
        """
        if not name:
            raise ValueError("provider name cannot be empty")
        if name in self._providers and not override:
            raise ValueError(
                f"provider {name!r} is already registered; pass override=True to replace it"
            )
        self._providers[name] = _Registration(provider_class, config_type)

    def unregister(self, name: str) -> None:
        """Remove a registered provider.

        Args:
            name: The provider name to remove.

        Raises:
            ConfigError: If ``name`` is not registered.
        """
        if name not in self._providers:
            raise ConfigError(
                f"Cannot unregister unknown provider {name!r}. "
                f"Available providers: {self.available() or 'none'}."
            )
        del self._providers[name]

    def is_registered(self, name: str) -> bool:
        """Return whether a provider is registered under ``name``."""
        return name in self._providers

    def available(self) -> list[str]:
        """Return the sorted names of all registered providers."""
        return sorted(self._providers)

    def create(self, name: str, config: LLMConfig) -> LLMProvider:
        """Build the provider registered under ``name`` from ``config``.

        The config is accepted if it is an *instance* of the provider's expected
        config type (so a subclass config is allowed). This is intentionally more
        lenient than :meth:`from_config`, which dispatches on the config's exact
        type to avoid ambiguity; here the provider is named explicitly.

        Args:
            name: The registered provider name.
            config: The configuration to pass to the provider.

        Returns:
            A new provider instance.

        Raises:
            ConfigError: If ``name`` is not registered, or ``config`` is not an
                instance of the provider's expected config type.
        """
        registration = self._providers.get(name)
        if registration is None:
            raise ConfigError(
                f"Unknown provider {name!r}. Available providers: {self.available() or 'none'}. "
                f"Register it first with ProviderRegistry.register()."
            )
        if not isinstance(config, registration.config_type):
            raise ConfigError(
                f"Provider {name!r} expects {registration.config_type.__name__}, "
                f"got {type(config).__name__}."
            )
        provider = registration.provider_class(config)
        _logger.info(
            "provider_instantiated",
            extra={"provider": name, "config_type": type(config).__name__},
        )
        return provider

    def from_config(self, config: LLMConfig) -> LLMProvider:
        """Build the provider whose config type matches ``config``.

        Args:
            config: A provider configuration.

        Returns:
            A new provider instance.

        Raises:
            ConfigError: If ``config`` is ``None``, no provider is registered for
                its type, or more than one provider matches (ambiguous).
        """
        if config is None:
            raise ConfigError("config cannot be None")

        matches = [
            name
            for name, reg in self._providers.items()
            if type(config) is reg.config_type
        ]
        if not matches:
            raise ConfigError(
                f"No provider registered for config type {type(config).__name__}. "
                f"Available providers: {self.available() or 'none'}. "
                f"Register one with ProviderRegistry.register()."
            )
        if len(matches) > 1:
            raise ConfigError(
                f"Multiple providers registered for {type(config).__name__}: "
                f"{sorted(matches)}. Use create(name, config) to disambiguate."
            )
        return self.create(matches[0], config)


#: Process-wide default registry. Built-in providers self-register here in Phase 2.
default_registry = ProviderRegistry()
