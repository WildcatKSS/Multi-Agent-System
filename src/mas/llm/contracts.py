"""LLM contracts: core data structures, provider interface, and error hierarchy.

This module defines the foundational contracts for the LLM provider layer:

- :class:`LLMMessage` and :class:`LLMResponse`: immutable (frozen) data
  structures exchanged with providers.
- :class:`LLMProvider`: the abstract base class every concrete provider
  (Ollama, HuggingFace, OpenAI, Anthropic, ...) must implement.
- The :class:`LLMError` hierarchy: a structured set of exceptions that
  distinguish transient failures (safe to retry) from permanent ones.

The data structures follow the ``__post_init__`` validation pattern established
by the domain contracts (``Task``, ``Plan``, ``Step``) and additionally make
their instances immutable via ``frozen=True`` (the domain contracts themselves
are mutable).
"""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal, get_args

Role = Literal["system", "user", "assistant"]
"""Valid roles for an :class:`LLMMessage`."""

#: Runtime set of valid roles, derived from :data:`Role` so the two cannot drift.
_VALID_ROLES: frozenset[str] = frozenset(get_args(Role))


@dataclass(frozen=True)
class LLMMessage:
    """A single message in an LLM conversation.

    Messages are immutable: once created their attributes cannot be reassigned
    (``frozen=True``), which makes them safe to share across concurrent provider
    calls. Note that immutability is shallow -- the contents of a ``metadata``
    dict are not deep-frozen, and an instance carrying a ``metadata`` dict is not
    hashable.

    Attributes:
        role: The author of the message. One of ``"system"``, ``"user"`` or
            ``"assistant"``.
        content: The textual content of the message. Must not be empty or
            whitespace-only.
        metadata: Optional provider- or caller-specific metadata. ``None`` when
            no metadata is attached.

    Raises:
        ValueError: If ``role`` is not a valid role or ``content`` is empty or
            whitespace-only.
    """

    role: Role
    content: str
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate the message on creation."""
        if self.role not in _VALID_ROLES:
            raise ValueError(
                f"LLMMessage role must be one of {sorted(_VALID_ROLES)}, got {self.role!r}"
            )
        if not self.content or not self.content.strip():
            raise ValueError("LLMMessage content cannot be empty or whitespace-only")


@dataclass(frozen=True)
class LLMResponse:
    """The result of a single LLM provider call.

    Responses are immutable. They always carry an assistant-authored message
    along with usage and timing metadata describing the call. As with
    :class:`LLMMessage`, immutability is shallow: a ``metadata`` dict is not
    deep-frozen and makes the instance non-hashable.

    Attributes:
        message: The assistant message returned by the provider. Its ``role``
            must be ``"assistant"``.
        tokens_used: Total number of tokens consumed by the call. Must be
            non-negative.
        model: Identifier of the model that produced the response.
        latency_ms: Wall-clock latency of the call in milliseconds. Must be a
            finite, non-negative number.
        metadata: Optional provider-specific metadata (e.g. finish reason,
            prompt/completion token split). ``None`` when not provided.

    Raises:
        ValueError: If ``tokens_used`` is negative, ``latency_ms`` is negative
            or non-finite (NaN/inf), ``model`` is empty, or ``message.role`` is
            not ``"assistant"``.
    """

    message: LLMMessage
    tokens_used: int
    model: str
    latency_ms: float
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate the response on creation."""
        if self.message.role != "assistant":
            raise ValueError(
                f"LLMResponse message must have role 'assistant', got {self.message.role!r}"
            )
        if self.tokens_used < 0:
            raise ValueError(f"LLMResponse tokens_used cannot be negative, got {self.tokens_used}")
        if math.isnan(self.latency_ms) or math.isinf(self.latency_ms):
            raise ValueError(
                f"LLMResponse latency_ms must be finite, got {self.latency_ms}. "
                f"Ensure latency_ms is a real number >= 0.0."
            )
        if self.latency_ms < 0:
            raise ValueError(f"LLMResponse latency_ms cannot be negative, got {self.latency_ms}")
        if not self.model:
            raise ValueError("LLMResponse model cannot be empty")


class LLMProvider(ABC):
    """Abstract interface for an LLM provider.

    Concrete providers (Ollama, HuggingFace, OpenAI, Anthropic, ...) subclass
    this and implement the three abstract methods. Implementations are expected
    to raise the appropriate :class:`LLMError` subclass on failure so callers
    can distinguish transient from permanent errors.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable, human-readable identifier for the provider (e.g. ``"ollama"``)."""

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Model identifier used when a caller does not specify one."""

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether this provider can stream responses incrementally."""

    @abstractmethod
    async def call(
        self,
        messages: list[LLMMessage],
        model: str,
        **kwargs: Any,
    ) -> LLMResponse:
        """Invoke the model with a conversation and return its response.

        Args:
            messages: The conversation history to send to the model.
            model: The model identifier to use for this call.
            **kwargs: Provider-specific options (temperature, max tokens, ...).

        Returns:
            The model's response.

        Raises:
            LLMError: Or one of its subclasses, on failure.
        """

    @abstractmethod
    def validate_config(self, config: Any) -> bool:
        """Validate that ``config`` is usable by this provider.

        Args:
            config: The provider configuration to validate.

        Returns:
            ``True`` if the configuration is valid.

        Raises:
            ConfigError: If the configuration is invalid.
        """

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate the number of tokens ``text`` will consume.

        Args:
            text: The text to estimate.

        Returns:
            A non-negative estimated token count.
        """


class LLMError(Exception):
    """Base class for all LLM provider errors.

    Attributes:
        message: Human-readable description of the error.
        original_exception: The underlying exception that triggered this error,
            if any.
        transient: Whether the error is transient (i.e. retrying the operation
            may succeed). Permanent errors should not be retried.
        retry_after_seconds: Suggested wait time before retrying, in seconds, or
            ``None`` if no hint is available.
    """

    #: Default transient classification for this error type. Subclasses override
    #: this to express whether the failure is generally safe to retry.
    default_transient: bool = False

    def __init__(
        self,
        message: str,
        *,
        original_exception: Exception | None = None,
        transient: bool | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.original_exception = original_exception
        self.transient = self.default_transient if transient is None else transient
        self.retry_after_seconds = retry_after_seconds


class ConfigError(LLMError):
    """Raised when a provider is given an invalid configuration. Permanent."""

    default_transient = False


class TimeoutError(LLMError):  # noqa: A001 - intentional domain-specific timeout error
    """Raised when a provider call exceeds its time budget. Transient."""

    default_transient = True


class APIError(LLMError):
    """Raised when a provider's API returns an error response.

    Transient by default, since many API errors (5xx, network blips) resolve on
    retry. Callers may override ``transient`` for known-permanent responses.
    """

    default_transient = True


class ValidationError(LLMError):
    """Raised when input to a provider fails validation. Permanent."""

    default_transient = False


class RateLimitError(LLMError):
    """Raised when a provider's rate limit is hit. Transient."""

    default_transient = True


class AuthenticationError(LLMError):
    """Raised when provider credentials are invalid or rejected. Permanent."""

    default_transient = False
