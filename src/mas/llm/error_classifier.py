"""Error classification and retry-strategy recommendation for LLM providers.

:class:`ErrorClassifier` analyses an :class:`~mas.llm.errors.LLMError` and
returns a rich :class:`ClassificationResult` that goes beyond the binary
``error.transient`` flag:

- **Retry strategy** — ``NO_RETRY``, ``IMMEDIATE_RETRY``, ``EXPONENTIAL_BACKOFF``,
  or ``FIXED_WAIT`` (use when the provider gives an explicit ``Retry-After``
  hint).
- **Recommended wait** — a concrete number of seconds to wait before the next
  attempt, given the current attempt number.
- **User message** — a human-readable sentence suitable for display or logging.

The module is additive to :class:`~mas.llm.base.BaseProvider`'s built-in retry
logic: callers that want finer control can consult the classifier; callers that
don't can ignore it entirely.

The module-level :data:`default_classifier` is a ready-to-use instance.
"""

from __future__ import annotations

from enum import Enum

from mas.llm.errors import (
    APIError,
    AuthenticationError,
    ConfigError,
    LLMError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)


class RetryStrategy(Enum):
    """Recommended retry strategy for a classified error.

    Attributes:
        NO_RETRY: Do not retry; the error is permanent.
        IMMEDIATE_RETRY: Retry immediately (or after a minimal delay).
        EXPONENTIAL_BACKOFF: Retry with ``2**attempt`` seconds of wait, capped.
        FIXED_WAIT: Retry after the number of seconds specified by the provider
            (e.g. from a ``Retry-After`` header).
    """

    NO_RETRY = "no_retry"
    IMMEDIATE_RETRY = "immediate_retry"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_WAIT = "fixed_wait"


class ClassificationResult:
    """Result of classifying an :class:`~mas.llm.errors.LLMError`.

    Attributes:
        error: The original error that was classified.
        is_retryable: Whether a retry attempt may succeed.
        strategy: The recommended :class:`RetryStrategy`.
        user_message: A human-readable description of the error and action.
    """

    def __init__(
        self,
        error: LLMError,
        *,
        is_retryable: bool,
        strategy: RetryStrategy,
        user_message: str,
    ) -> None:
        self.error = error
        self.is_retryable = is_retryable
        self.strategy = strategy
        self.user_message = user_message

    def recommended_wait(self, attempt: int = 0, max_backoff: float = 60.0) -> float:
        """Return the recommended wait in seconds before the next attempt.

        Args:
            attempt: 0-based attempt index (used to scale exponential backoff).
            max_backoff: Upper bound on the returned wait time in seconds.
                Only applied for :attr:`RetryStrategy.EXPONENTIAL_BACKOFF`.

        Returns:
            Seconds to wait.  ``0.0`` for :attr:`~RetryStrategy.NO_RETRY` and
            :attr:`~RetryStrategy.IMMEDIATE_RETRY`.
        """
        if self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return float(min(2**attempt, max_backoff))
        if self.strategy == RetryStrategy.FIXED_WAIT:
            hint = self.error.retry_after_seconds
            return float(hint) if hint is not None else 0.0
        return 0.0

    def __repr__(self) -> str:
        return (
            f"ClassificationResult("
            f"strategy={self.strategy.value!r}, "
            f"is_retryable={self.is_retryable}, "
            f"user_message={self.user_message!r})"
        )


# ---------------------------------------------------------------------------
# ErrorClassifier
# ---------------------------------------------------------------------------


class ErrorClassifier:
    """Classifies :class:`~mas.llm.errors.LLMError` instances into actionable results.

    The default implementation dispatches on the concrete error type, then
    refines the result based on ``error.transient`` and
    ``error.retry_after_seconds``. Subclass and override :meth:`classify` (or
    the individual ``_classify_*`` methods) to customise behaviour.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(self, error: LLMError) -> ClassificationResult:
        """Return a :class:`ClassificationResult` for ``error``.

        Dispatches to a per-type handler, then applies common refinements:
        if a ``retry_after_seconds`` hint is present the strategy is upgraded
        to :attr:`~RetryStrategy.FIXED_WAIT`.

        Args:
            error: The :class:`~mas.llm.errors.LLMError` to classify.

        Returns:
            A :class:`ClassificationResult` describing the error and what to do.
        """
        result = self._dispatch(error)
        # If the provider gave an explicit retry-after hint, honour it.
        if result.is_retryable and error.retry_after_seconds is not None:
            return ClassificationResult(
                error=error,
                is_retryable=True,
                strategy=RetryStrategy.FIXED_WAIT,
                user_message=result.user_message,
            )
        return result

    def is_retryable(self, error: LLMError) -> bool:
        """Return whether ``error`` should trigger a retry attempt.

        Args:
            error: The error to check.

        Returns:
            ``True`` if retrying may succeed.
        """
        return self.classify(error).is_retryable

    def recommended_wait(self, error: LLMError, attempt: int = 0) -> float:
        """Return the recommended wait in seconds before retrying ``error``.

        Args:
            error: The error that occurred.
            attempt: 0-based attempt index.

        Returns:
            Seconds to wait before the next attempt.
        """
        return self.classify(error).recommended_wait(attempt)

    def user_message(self, error: LLMError) -> str:
        """Return a human-readable message describing ``error``.

        Args:
            error: The error to describe.

        Returns:
            A concise, user-facing description.
        """
        return self.classify(error).user_message

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, error: LLMError) -> ClassificationResult:
        """Route to the appropriate per-type classifier."""
        if isinstance(error, AuthenticationError):
            return self._classify_authentication(error)
        if isinstance(error, ConfigError):
            return self._classify_config(error)
        if isinstance(error, ValidationError):
            return self._classify_validation(error)
        if isinstance(error, RateLimitError):
            return self._classify_rate_limit(error)
        if isinstance(error, TimeoutError):
            return self._classify_timeout(error)
        if isinstance(error, APIError):
            return self._classify_api(error)
        return self._classify_generic(error)

    def _classify_authentication(self, error: AuthenticationError) -> ClassificationResult:
        return ClassificationResult(
            error=error,
            is_retryable=False,
            strategy=RetryStrategy.NO_RETRY,
            user_message="Authentication failed. Check your API key and try again.",
        )

    def _classify_config(self, error: ConfigError) -> ClassificationResult:
        return ClassificationResult(
            error=error,
            is_retryable=False,
            strategy=RetryStrategy.NO_RETRY,
            user_message="Provider configuration is invalid. Review your settings.",
        )

    def _classify_validation(self, error: ValidationError) -> ClassificationResult:
        return ClassificationResult(
            error=error,
            is_retryable=False,
            strategy=RetryStrategy.NO_RETRY,
            user_message=f"Input validation failed: {error.message}",
        )

    def _classify_rate_limit(self, error: RateLimitError) -> ClassificationResult:
        strategy = (
            RetryStrategy.FIXED_WAIT
            if error.retry_after_seconds is not None
            else RetryStrategy.EXPONENTIAL_BACKOFF
        )
        return ClassificationResult(
            error=error,
            is_retryable=True,
            strategy=strategy,
            user_message="Rate limit reached. The request will be retried after a short wait.",
        )

    def _classify_timeout(self, error: TimeoutError) -> ClassificationResult:
        return ClassificationResult(
            error=error,
            is_retryable=True,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            user_message="The request timed out. It will be retried automatically.",
        )

    def _transient_or_permanent(
        self,
        error: LLMError,
        transient_msg: str,
        permanent_msg: str,
    ) -> ClassificationResult:
        if error.transient:
            return ClassificationResult(
                error=error,
                is_retryable=True,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                user_message=transient_msg,
            )
        return ClassificationResult(
            error=error,
            is_retryable=False,
            strategy=RetryStrategy.NO_RETRY,
            user_message=permanent_msg,
        )

    def _classify_api(self, error: APIError) -> ClassificationResult:
        return self._transient_or_permanent(
            error,
            transient_msg="A transient API error occurred. The request will be retried.",
            permanent_msg=f"The API returned a permanent error: {error.message}",
        )

    def _classify_generic(self, error: LLMError) -> ClassificationResult:
        return self._transient_or_permanent(
            error,
            transient_msg="A transient error occurred. The request will be retried.",
            permanent_msg=f"An error occurred: {error.message}",
        )


# ---------------------------------------------------------------------------
# Module-level default instance
# ---------------------------------------------------------------------------

#: Process-wide :class:`ErrorClassifier` with default classification logic.
default_classifier: ErrorClassifier = ErrorClassifier()


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def classify(error: LLMError) -> ClassificationResult:
    """Classify ``error`` using :data:`default_classifier`.

    Args:
        error: The error to classify.

    Returns:
        A :class:`ClassificationResult`.
    """
    return default_classifier.classify(error)


def is_retryable(error: LLMError) -> bool:
    """Return whether ``error`` should trigger a retry, using :data:`default_classifier`.

    Args:
        error: The error to check.
    """
    return default_classifier.is_retryable(error)


def recommended_wait(error: LLMError, attempt: int = 0) -> float:
    """Return the recommended wait in seconds, using :data:`default_classifier`.

    Args:
        error: The error that occurred.
        attempt: 0-based attempt index.
    """
    return default_classifier.recommended_wait(error, attempt)


def user_message(error: LLMError) -> str:
    """Return a human-readable description of ``error``, using :data:`default_classifier`.

    Args:
        error: The error to describe.
    """
    return default_classifier.user_message(error)
