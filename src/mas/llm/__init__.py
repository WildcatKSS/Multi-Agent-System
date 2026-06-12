"""LLM provider abstraction layer.

This package defines the core contracts for interacting with language model
providers: immutable message/response data structures, the ``LLMProvider``
abstract base class, and the LLM error hierarchy.
"""

from mas.llm.base import (
    DEFAULT_MAX_BACKOFF_SECONDS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    BaseProvider,
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

__all__ = [
    "Role",
    "LLMMessage",
    "LLMResponse",
    "LLMProvider",
    "BaseProvider",
    "DEFAULT_TIMEOUT_SECONDS",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_MAX_BACKOFF_SECONDS",
    "LLMError",
    "ConfigError",
    "TimeoutError",
    "APIError",
    "ValidationError",
    "RateLimitError",
    "AuthenticationError",
]
