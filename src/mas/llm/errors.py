"""LLM error hierarchy.

A small, structured set of exceptions for the LLM provider layer. The central
distinction is :attr:`LLMError.transient`: transient errors (timeouts, rate
limits, transient API failures) are safe to retry; permanent errors
(misconfiguration, bad input, failed auth) are not. Callers -- notably
:class:`mas.llm.base.BaseProvider` -- branch on this flag to decide whether to
retry.

This module is the canonical home of the hierarchy; ``mas.llm.contracts``
re-exports these names for backward compatibility.
"""


class LLMError(Exception):
    """Base class for all LLM provider errors.

    Raise a more specific subclass where possible; catch :class:`LLMError` to
    handle any provider failure generically.

    Attributes:
        message: Human-readable description of the error.
        original_exception: The underlying exception that triggered this error,
            if any. Useful for preserving the root cause when wrapping.
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
    """Raised when a provider is given an invalid configuration.

    Permanent: retrying with the same configuration will fail again. Raise this
    for missing/invalid config fields or an unknown/unregistered provider.
    """


class TimeoutError(LLMError):  # noqa: A001 - intentional domain-specific timeout error
    """Raised when a provider call exceeds its time budget.

    Transient: the request may succeed on a subsequent attempt. Raise this when
    an API call does not return within the configured timeout.
    """

    default_transient = True


class APIError(LLMError):
    """Raised when a provider's API returns an error response.

    Transient by default, since many API errors (5xx, network blips) resolve on
    retry. Raise with ``transient=False`` for responses known to be permanent
    (e.g. a 4xx caused by a malformed request).
    """

    default_transient = True


class ValidationError(LLMError):
    """Raised when input to a provider fails validation.

    Permanent: the same input will fail again. Raise this for empty messages,
    invalid config values, or other malformed input detected before the call.
    """


class RateLimitError(LLMError):
    """Raised when a provider's rate limit is hit.

    Transient: retry after backing off. Set ``retry_after_seconds`` from the
    provider's ``Retry-After`` hint when available so callers can wait the
    advised duration.
    """

    default_transient = True


class AuthenticationError(LLMError):
    """Raised when provider credentials are invalid or rejected.

    Permanent: retrying with the same credentials will fail again. Raise this for
    a missing/invalid API key or a rejected token.
    """
