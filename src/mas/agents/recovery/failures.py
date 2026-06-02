"""Failure classification and taxonomy for recovery logic."""

from dataclasses import dataclass, field
from enum import Enum


class FailureType(str, Enum):
    """Classification of step failures."""

    TIMEOUT = "timeout"
    """Step exceeded execution timeout."""

    TOOL_UNAVAILABLE = "tool_unavailable"
    """Required tool or dependency not available."""

    HANDLER_ERROR = "handler_error"
    """Step handler raised an exception."""

    INVALID_INPUT = "invalid_input"
    """Step received invalid or malformed input."""

    RESOURCE_EXHAUSTED = "resource_exhausted"
    """System ran out of required resources (memory, connections, etc)."""

    EXTERNAL_SERVICE_ERROR = "external_service_error"
    """External service returned error (network, API, etc)."""

    UNKNOWN = "unknown"
    """Failure reason could not be determined."""

    def is_recoverable(self) -> bool:
        """Check if this failure type is typically recoverable.

        Recoverable failures can be retried.
        Permanent failures should escalate immediately.

        Returns:
            True if typically recoverable (transient), False if permanent.
        """
        recoverable = {
            FailureType.TIMEOUT,
            FailureType.TOOL_UNAVAILABLE,
            FailureType.RESOURCE_EXHAUSTED,
            FailureType.EXTERNAL_SERVICE_ERROR,
        }
        return self in recoverable


@dataclass(frozen=True)
class RecoverableError(Exception):
    """Error that can be recovered via retry or fallback."""

    failure_type: FailureType
    """Type of failure that occurred."""

    message: str
    """Human-readable error message."""

    context: dict | None = field(default=None)
    """Additional context about the failure (step_id, attempt, etc)."""

    def __post_init__(self) -> None:
        """Validate recoverable error on creation."""
        if not self.failure_type.is_recoverable():
            raise ValueError(
                f"FailureType {self.failure_type} is not recoverable"
            )
        if not self.message:
            raise ValueError("message cannot be empty")


@dataclass(frozen=True)
class PermanentError(Exception):
    """Error that cannot be recovered and should escalate immediately."""

    failure_type: FailureType
    """Type of failure that occurred."""

    message: str
    """Human-readable error message."""

    context: dict | None = field(default=None)
    """Additional context about the failure."""

    def __post_init__(self) -> None:
        """Validate permanent error on creation."""
        if self.failure_type.is_recoverable():
            raise ValueError(
                f"FailureType {self.failure_type} is recoverable, "
                f"use RecoverableError instead"
            )
        if not self.message:
            raise ValueError("message cannot be empty")


@dataclass(frozen=True)
class StepFailure:
    """Record of a step failure with classification and metadata."""

    step_id: str
    """ID of the step that failed."""

    failure_type: FailureType
    """Type of failure that occurred."""

    message: str
    """Error message from the failure."""

    attempt_number: int
    """Which attempt number this was (1-indexed)."""

    context: dict | None = field(default=None)
    """Additional failure context."""

    def __post_init__(self) -> None:
        """Validate step failure on creation."""
        if not self.step_id:
            raise ValueError("step_id cannot be empty")
        if not self.message:
            raise ValueError("message cannot be empty")
        if self.attempt_number < 1:
            raise ValueError("attempt_number must be >= 1")

    def is_recoverable(self) -> bool:
        """Check if this failure is recoverable.

        Returns:
            True if failure type is typically recoverable.
        """
        return self.failure_type.is_recoverable()
