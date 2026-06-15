"""Tests for mas.llm.error_classifier."""


from mas.llm.error_classifier import (
    ClassificationResult,
    ErrorClassifier,
    RetryStrategy,
    classify,
    default_classifier,
    is_retryable,
    recommended_wait,
    user_message,
)
from mas.llm.errors import (
    APIError,
    AuthenticationError,
    ConfigError,
    LLMError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)

# ---------------------------------------------------------------------------
# RetryStrategy enum
# ---------------------------------------------------------------------------


class TestRetryStrategy:
    def test_all_values_distinct(self) -> None:
        values = [s.value for s in RetryStrategy]
        assert len(values) == len(set(values))

    def test_no_retry_value(self) -> None:
        assert RetryStrategy.NO_RETRY.value == "no_retry"

    def test_immediate_retry_value(self) -> None:
        assert RetryStrategy.IMMEDIATE_RETRY.value == "immediate_retry"

    def test_exponential_backoff_value(self) -> None:
        assert RetryStrategy.EXPONENTIAL_BACKOFF.value == "exponential_backoff"

    def test_fixed_wait_value(self) -> None:
        assert RetryStrategy.FIXED_WAIT.value == "fixed_wait"


# ---------------------------------------------------------------------------
# ClassificationResult
# ---------------------------------------------------------------------------


class TestClassificationResult:
    def _make(
        self,
        *,
        error: LLMError | None = None,
        is_retryable: bool = False,
        strategy: RetryStrategy = RetryStrategy.NO_RETRY,
        user_message: str = "test",
    ) -> ClassificationResult:
        err = error or LLMError("base error")
        return ClassificationResult(
            error=err,
            is_retryable=is_retryable,
            strategy=strategy,
            user_message=user_message,
        )

    def test_attributes_set(self) -> None:
        err = LLMError("oops")
        result = ClassificationResult(
            error=err,
            is_retryable=True,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            user_message="retry it",
        )
        assert result.error is err
        assert result.is_retryable is True
        assert result.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert result.user_message == "retry it"

    def test_repr_contains_strategy(self) -> None:
        result = self._make(strategy=RetryStrategy.FIXED_WAIT)
        assert "fixed_wait" in repr(result)

    # recommended_wait branches

    def test_no_retry_wait_is_zero(self) -> None:
        result = self._make(strategy=RetryStrategy.NO_RETRY)
        assert result.recommended_wait(attempt=3) == 0.0

    def test_immediate_retry_wait_is_zero(self) -> None:
        result = self._make(strategy=RetryStrategy.IMMEDIATE_RETRY)
        assert result.recommended_wait(attempt=3) == 0.0

    def test_exponential_backoff_scales_with_attempt(self) -> None:
        result = self._make(strategy=RetryStrategy.EXPONENTIAL_BACKOFF)
        assert result.recommended_wait(attempt=0) == 1.0
        assert result.recommended_wait(attempt=1) == 2.0
        assert result.recommended_wait(attempt=2) == 4.0

    def test_exponential_backoff_capped_by_max_backoff(self) -> None:
        result = self._make(strategy=RetryStrategy.EXPONENTIAL_BACKOFF)
        # attempt=10 would give 1024s, max_backoff=60 should cap it
        assert result.recommended_wait(attempt=10, max_backoff=60.0) == 60.0

    def test_fixed_wait_returns_hint(self) -> None:
        err = RateLimitError("rate limited", retry_after_seconds=30)
        result = ClassificationResult(
            error=err,
            is_retryable=True,
            strategy=RetryStrategy.FIXED_WAIT,
            user_message="wait 30s",
        )
        assert result.recommended_wait() == 30.0

    def test_fixed_wait_without_hint_returns_zero(self) -> None:
        err = RateLimitError("rate limited")  # no retry_after_seconds
        result = ClassificationResult(
            error=err,
            is_retryable=True,
            strategy=RetryStrategy.FIXED_WAIT,
            user_message="wait",
        )
        assert result.recommended_wait() == 0.0


# ---------------------------------------------------------------------------
# ErrorClassifier — authentication errors
# ---------------------------------------------------------------------------


class TestClassifyAuthentication:
    def test_not_retryable(self) -> None:
        r = default_classifier.classify(AuthenticationError("invalid key"))
        assert r.is_retryable is False

    def test_no_retry_strategy(self) -> None:
        r = default_classifier.classify(AuthenticationError("invalid key"))
        assert r.strategy == RetryStrategy.NO_RETRY

    def test_user_message_mentions_api_key(self) -> None:
        r = default_classifier.classify(AuthenticationError("invalid key"))
        assert "API key" in r.user_message or "Authentication" in r.user_message


# ---------------------------------------------------------------------------
# ErrorClassifier — config errors
# ---------------------------------------------------------------------------


class TestClassifyConfig:
    def test_not_retryable(self) -> None:
        r = default_classifier.classify(ConfigError("bad config"))
        assert r.is_retryable is False

    def test_no_retry_strategy(self) -> None:
        r = default_classifier.classify(ConfigError("bad config"))
        assert r.strategy == RetryStrategy.NO_RETRY

    def test_user_message_mentions_configuration(self) -> None:
        r = default_classifier.classify(ConfigError("bad config"))
        assert "configuration" in r.user_message.lower()


# ---------------------------------------------------------------------------
# ErrorClassifier — validation errors
# ---------------------------------------------------------------------------


class TestClassifyValidation:
    def test_not_retryable(self) -> None:
        r = default_classifier.classify(ValidationError("empty messages"))
        assert r.is_retryable is False

    def test_no_retry_strategy(self) -> None:
        r = default_classifier.classify(ValidationError("empty messages"))
        assert r.strategy == RetryStrategy.NO_RETRY

    def test_user_message_includes_error_text(self) -> None:
        r = default_classifier.classify(ValidationError("empty messages"))
        assert "empty messages" in r.user_message


# ---------------------------------------------------------------------------
# ErrorClassifier — rate limit errors
# ---------------------------------------------------------------------------


class TestClassifyRateLimit:
    def test_is_retryable(self) -> None:
        r = default_classifier.classify(RateLimitError("429"))
        assert r.is_retryable is True

    def test_exponential_backoff_without_hint(self) -> None:
        r = default_classifier.classify(RateLimitError("429"))
        assert r.strategy == RetryStrategy.EXPONENTIAL_BACKOFF

    def test_fixed_wait_with_retry_after_hint(self) -> None:
        r = default_classifier.classify(RateLimitError("429", retry_after_seconds=45))
        assert r.strategy == RetryStrategy.FIXED_WAIT
        assert r.recommended_wait() == 45.0

    def test_user_message_mentions_rate_limit(self) -> None:
        r = default_classifier.classify(RateLimitError("429"))
        assert "rate" in r.user_message.lower() or "limit" in r.user_message.lower()


# ---------------------------------------------------------------------------
# ErrorClassifier — timeout errors
# ---------------------------------------------------------------------------


class TestClassifyTimeout:
    def test_is_retryable(self) -> None:
        r = default_classifier.classify(TimeoutError("timed out"))
        assert r.is_retryable is True

    def test_exponential_backoff_strategy(self) -> None:
        r = default_classifier.classify(TimeoutError("timed out"))
        assert r.strategy == RetryStrategy.EXPONENTIAL_BACKOFF

    def test_user_message_mentions_timeout(self) -> None:
        r = default_classifier.classify(TimeoutError("timed out"))
        assert "timed out" in r.user_message.lower() or "timeout" in r.user_message.lower()


# ---------------------------------------------------------------------------
# ErrorClassifier — API errors
# ---------------------------------------------------------------------------


class TestClassifyAPIError:
    def test_transient_api_error_is_retryable(self) -> None:
        r = default_classifier.classify(APIError("500 error", transient=True))
        assert r.is_retryable is True
        assert r.strategy == RetryStrategy.EXPONENTIAL_BACKOFF

    def test_permanent_api_error_not_retryable(self) -> None:
        r = default_classifier.classify(APIError("400 error", transient=False))
        assert r.is_retryable is False
        assert r.strategy == RetryStrategy.NO_RETRY

    def test_permanent_api_error_message_contains_error(self) -> None:
        r = default_classifier.classify(APIError("400 error", transient=False))
        assert "400 error" in r.user_message

    def test_transient_api_error_with_retry_after_upgrades_to_fixed_wait(self) -> None:
        r = default_classifier.classify(
            APIError("503 error", transient=True, retry_after_seconds=10)
        )
        assert r.strategy == RetryStrategy.FIXED_WAIT
        assert r.recommended_wait() == 10.0


# ---------------------------------------------------------------------------
# ErrorClassifier — generic LLMError
# ---------------------------------------------------------------------------


class TestClassifyGenericLLMError:
    def test_transient_generic_is_retryable(self) -> None:
        err = LLMError("generic transient", transient=True)
        r = default_classifier.classify(err)
        assert r.is_retryable is True
        assert r.strategy == RetryStrategy.EXPONENTIAL_BACKOFF

    def test_permanent_generic_not_retryable(self) -> None:
        err = LLMError("generic permanent", transient=False)
        r = default_classifier.classify(err)
        assert r.is_retryable is False
        assert r.strategy == RetryStrategy.NO_RETRY

    def test_permanent_generic_message_contains_error(self) -> None:
        err = LLMError("something went wrong", transient=False)
        r = default_classifier.classify(err)
        assert "something went wrong" in r.user_message


# ---------------------------------------------------------------------------
# ErrorClassifier — retry_after_seconds refinement
# ---------------------------------------------------------------------------


class TestRetryAfterRefinement:
    def test_timeout_with_retry_after_uses_fixed_wait(self) -> None:
        err = TimeoutError("slow", retry_after_seconds=5)
        r = default_classifier.classify(err)
        assert r.strategy == RetryStrategy.FIXED_WAIT
        assert r.recommended_wait() == 5.0

    def test_non_retryable_error_retry_after_ignored(self) -> None:
        # AuthenticationError is non-retryable; retry_after_seconds should be ignored.
        err = AuthenticationError("denied", retry_after_seconds=60)
        r = default_classifier.classify(err)
        assert r.strategy == RetryStrategy.NO_RETRY
        assert r.is_retryable is False


# ---------------------------------------------------------------------------
# ErrorClassifier convenience methods
# ---------------------------------------------------------------------------


class TestErrorClassifierMethods:
    def test_is_retryable_method(self) -> None:
        ec = ErrorClassifier()
        assert ec.is_retryable(RateLimitError("429")) is True
        assert ec.is_retryable(AuthenticationError("denied")) is False

    def test_recommended_wait_method(self) -> None:
        ec = ErrorClassifier()
        wait = ec.recommended_wait(TimeoutError("slow"), attempt=2)
        assert wait == 4.0  # 2**2

    def test_user_message_method(self) -> None:
        ec = ErrorClassifier()
        msg = ec.user_message(ConfigError("bad"))
        assert isinstance(msg, str)
        assert len(msg) > 0


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------


class TestModuleFunctions:
    def test_classify_function(self) -> None:
        r = classify(AuthenticationError("denied"))
        assert r.is_retryable is False

    def test_is_retryable_function(self) -> None:
        assert is_retryable(RateLimitError("429")) is True
        assert is_retryable(ConfigError("bad")) is False

    def test_recommended_wait_function(self) -> None:
        wait = recommended_wait(TimeoutError("slow"), attempt=1)
        assert wait == 2.0

    def test_user_message_function(self) -> None:
        msg = user_message(ValidationError("empty"))
        assert "empty" in msg

    def test_default_classifier_is_error_classifier(self) -> None:
        assert isinstance(default_classifier, ErrorClassifier)
