"""LLM provider abstraction layer.

This package defines the core contracts for interacting with language model
providers: immutable message/response data structures, the ``LLMProvider``
abstract base class, and the LLM error hierarchy.
"""

from mas.llm.contracts import (
    APIError,
    AuthenticationError,
    ConfigError,
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    RateLimitError,
    TimeoutError,
    ValidationError,
)

__all__ = [
    "LLMMessage",
    "LLMResponse",
    "LLMProvider",
    "LLMError",
    "ConfigError",
    "TimeoutError",
    "APIError",
    "ValidationError",
    "RateLimitError",
    "AuthenticationError",
]
