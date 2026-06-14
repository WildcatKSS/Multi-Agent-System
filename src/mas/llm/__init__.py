"""LLM provider abstraction layer.

This package defines the building blocks for interacting with language model
providers:

- **Contracts** (:mod:`mas.llm.contracts`): immutable ``LLMMessage`` /
  ``LLMResponse`` data structures, the ``LLMProvider`` ABC, and the ``LLMError``
  hierarchy.
- **BaseProvider** (:mod:`mas.llm.base`): a reusable provider base adding
  timeout, retry with capped backoff, error classification, and structured
  logging.
- **Configs** (:mod:`mas.llm.config`): frozen, validated ``LLMConfig`` and
  provider-specific configurations.
- **Registry** (:mod:`mas.llm.provider_registry`): ``ProviderRegistry``, a
  factory that builds providers from their config, plus a process-wide
  ``default_registry``.
"""

from mas.llm.base import (
    DEFAULT_MAX_BACKOFF_SECONDS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    BaseProvider,
)
from mas.llm.config import (
    AnthropicConfig,
    AnthropicVersion,
    HFTask,
    HuggingFaceConfig,
    LLMConfig,
    OllamaConfig,
    OpenAIConfig,
)
from mas.llm.contracts import (
    APIError,
    AuthenticationError,
    ConfigError,
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    RateLimitError,
    Role,
    TimeoutError,
    ValidationError,
)
from mas.llm.provider_registry import (
    BUILTIN_PROVIDER_CONFIGS,
    ProviderRegistry,
    default_registry,
)

# Import providers last so they self-register with default_registry on package import.
from mas.llm.providers.huggingface import HuggingFaceProvider  # noqa: E402
from mas.llm.providers.ollama import OllamaProvider  # noqa: E402
from mas.llm.providers.openai import OpenAIProvider  # noqa: E402

__all__ = [
    "Role",
    "LLMMessage",
    "LLMResponse",
    "LLMProvider",
    "BaseProvider",
    "DEFAULT_TIMEOUT_SECONDS",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_MAX_BACKOFF_SECONDS",
    "LLMConfig",
    "OllamaConfig",
    "HuggingFaceConfig",
    "OpenAIConfig",
    "AnthropicConfig",
    "HFTask",
    "AnthropicVersion",
    "HuggingFaceProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "ProviderRegistry",
    "default_registry",
    "BUILTIN_PROVIDER_CONFIGS",
    "LLMError",
    "ConfigError",
    "TimeoutError",
    "APIError",
    "ValidationError",
    "RateLimitError",
    "AuthenticationError",
]
