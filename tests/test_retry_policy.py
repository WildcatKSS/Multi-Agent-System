"""Tests for retry policy and configuration."""

import pytest

from mas.agents.recovery.retry_policy import RetryPolicy, RetryConfig


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_config(self) -> None:
        """RetryConfig has sensible defaults."""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.initial_delay_ms == 100
        assert config.backoff_factor == 2.0

    def test_custom_config(self) -> None:
        """Can create RetryConfig with custom values."""
        config = RetryConfig(
            max_retries=5,
            initial_delay_ms=500,
            backoff_factor=1.5,
        )

        assert config.max_retries == 5
        assert config.initial_delay_ms == 500
        assert config.backoff_factor == 1.5

    def test_reject_negative_max_retries(self) -> None:
        """Cannot create config with negative max_retries."""
        with pytest.raises(ValueError, match="max_retries cannot be negative"):
            RetryConfig(max_retries=-1)

    def test_reject_negative_delay(self) -> None:
        """Cannot create config with negative initial_delay_ms."""
        with pytest.raises(ValueError, match="initial_delay_ms cannot be negative"):
            RetryConfig(initial_delay_ms=-100)

    def test_reject_non_positive_backoff(self) -> None:
        """Cannot create config with non-positive backoff_factor."""
        with pytest.raises(ValueError, match="backoff_factor must be positive"):
            RetryConfig(backoff_factor=0.0)

        with pytest.raises(ValueError, match="backoff_factor must be positive"):
            RetryConfig(backoff_factor=-1.0)

    def test_immutable(self) -> None:
        """RetryConfig is immutable (frozen dataclass)."""
        config = RetryConfig()

        with pytest.raises(AttributeError):
            config.max_retries = 10  # type: ignore


class TestRetryPolicy:
    """Tests for RetryPolicy logic."""

    def test_default_policy(self) -> None:
        """RetryPolicy uses default config if none provided."""
        policy = RetryPolicy()

        assert policy.config.max_retries == 3

    def test_custom_policy(self) -> None:
        """RetryPolicy uses custom config if provided."""
        config = RetryConfig(max_retries=5)
        policy = RetryPolicy(config)

        assert policy.config.max_retries == 5

    def test_should_retry_within_limit(self) -> None:
        """should_retry returns True when within retry limit."""
        policy = RetryPolicy(RetryConfig(max_retries=3))

        # Attempt 1 = first try, should be able to retry
        assert policy.should_retry(1)
        assert policy.should_retry(2)
        assert policy.should_retry(3)

    def test_should_retry_at_limit(self) -> None:
        """should_retry returns False when at or beyond retry limit."""
        policy = RetryPolicy(RetryConfig(max_retries=3))

        # After 3 failed attempts, no more retries
        assert not policy.should_retry(4)
        assert not policy.should_retry(5)

    def test_is_exhausted_within_limit(self) -> None:
        """is_exhausted returns False when retries remain."""
        policy = RetryPolicy(RetryConfig(max_retries=3))

        assert not policy.is_exhausted(1)
        assert not policy.is_exhausted(2)
        assert not policy.is_exhausted(3)

    def test_is_exhausted_at_limit(self) -> None:
        """is_exhausted returns True when retries exhausted."""
        policy = RetryPolicy(RetryConfig(max_retries=3))

        assert policy.is_exhausted(4)
        assert policy.is_exhausted(5)

    def test_next_delay_ms(self) -> None:
        """next_delay_ms returns configured initial delay (MVP linear)."""
        config = RetryConfig(initial_delay_ms=500)
        policy = RetryPolicy(config)

        # MVP: Always returns initial_delay_ms
        # Future: Exponential backoff based on attempt_number
        assert policy.next_delay_ms(1) == 500
        assert policy.next_delay_ms(2) == 500
        assert policy.next_delay_ms(3) == 500

    def test_zero_retries_allowed(self) -> None:
        """Policy with max_retries=0 allows no retries."""
        policy = RetryPolicy(RetryConfig(max_retries=0))

        assert not policy.should_retry(1)
        assert policy.is_exhausted(1)

    def test_many_retries_allowed(self) -> None:
        """Policy with large max_retries allows many retries."""
        policy = RetryPolicy(RetryConfig(max_retries=100))

        for attempt in range(1, 101):
            assert policy.should_retry(attempt), (
                f"Attempt {attempt} should be allowed"
            )

        assert not policy.should_retry(101)
