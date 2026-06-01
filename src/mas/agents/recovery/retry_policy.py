"""Retry policy and logic for recoverable failures."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    """Maximum number of retries for recoverable failures."""

    initial_delay_ms: int = 100
    """Initial delay between retries in milliseconds (future: exponential backoff)."""

    backoff_factor: float = 2.0
    """Multiplier for delay between retries (future: implement exponential backoff)."""

    def __post_init__(self) -> None:
        """Validate retry config on creation."""
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if self.initial_delay_ms < 0:
            raise ValueError("initial_delay_ms cannot be negative")
        if self.backoff_factor <= 0:
            raise ValueError("backoff_factor must be positive")


class RetryPolicy:
    """Policy engine for retry decisions.

    v1 characteristics:
    - Deterministic: no randomization
    - Simple: max_retries count, no exponential backoff yet
    - Configurable: per-step or global retry config
    """

    def __init__(self, config: RetryConfig | None = None) -> None:
        """Initialize retry policy with optional configuration.

        Args:
            config: RetryConfig to use (defaults to RetryConfig() if None)
        """
        self.config = config or RetryConfig()

    def should_retry(self, attempt_number: int) -> bool:
        """Determine if a failure should be retried.

        Args:
            attempt_number: Which attempt this was (1-indexed)

        Returns:
            True if retry should be attempted, False if retries exhausted
        """
        # attempt_number 1 = first try, so we can retry up to max_retries times
        # After max_retries failed attempts, we've exhausted retries
        return attempt_number <= self.config.max_retries

    def is_exhausted(self, attempt_number: int) -> bool:
        """Check if retries have been exhausted.

        Args:
            attempt_number: Number of attempts made so far

        Returns:
            True if retries are exhausted, False otherwise
        """
        return not self.should_retry(attempt_number)

    def next_delay_ms(self, attempt_number: int) -> int:
        """Calculate delay before next retry in milliseconds.

        Args:
            attempt_number: Which attempt this is (1-indexed)

        Returns:
            Delay in milliseconds before next retry
        """
        # MVP: Simple linear delays
        # Future: Exponential backoff with backoff_factor
        return self.config.initial_delay_ms
