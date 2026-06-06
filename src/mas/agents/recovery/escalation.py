"""Escalation logic for unrecoverable or exhausted failures."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class EscalationReason(str, Enum):
    """Reason for escalating a failure."""

    RETRIES_EXHAUSTED = "retries_exhausted"
    """Retry limit reached without success."""

    PERMANENT_ERROR = "permanent_error"
    """Unrecoverable error detected."""

    FALLBACK_FAILED = "fallback_failed"
    """Fallback handler was executed but also failed."""

    TIMEOUT = "timeout"
    """Execution timeout occurred."""

    UNKNOWN = "unknown"
    """Escalation reason could not be determined."""


@dataclass(frozen=True)
class EscalationOutcome:
    """Result of escalation when recovery is no longer possible."""

    reason: EscalationReason
    """Why escalation occurred."""

    should_fail: bool
    """True if step should fail (terminal), False if blocked for manual intervention."""

    message: str
    """Human-readable escalation message."""

    context: dict[str, Any] | None = None
    """Additional escalation context."""

    def __post_init__(self) -> None:
        """Validate escalation outcome on creation."""
        if not self.message:
            raise ValueError("message cannot be empty")

    @staticmethod
    def retries_exhausted(step_id: str, max_retries: int) -> "EscalationOutcome":
        """Create outcome for exhausted retries.

        Args:
            step_id: ID of step that exhausted retries
            max_retries: Maximum retries that were attempted

        Returns:
            EscalationOutcome indicating failure escalation
        """
        return EscalationOutcome(
            reason=EscalationReason.RETRIES_EXHAUSTED,
            should_fail=True,
            message=f"Step {step_id} exhausted {max_retries} retries",
            context={"step_id": step_id, "max_retries": max_retries},
        )

    @staticmethod
    def permanent_error(step_id: str, error_message: str) -> "EscalationOutcome":
        """Create outcome for permanent error.

        Args:
            step_id: ID of step with permanent error
            error_message: Description of the error

        Returns:
            EscalationOutcome indicating immediate failure
        """
        return EscalationOutcome(
            reason=EscalationReason.PERMANENT_ERROR,
            should_fail=True,
            message=f"Step {step_id} encountered unrecoverable error: {error_message}",
            context={"step_id": step_id, "error": error_message},
        )

    @staticmethod
    def fallback_failed(step_id: str, error_message: str) -> "EscalationOutcome":
        """Create outcome for failed fallback.

        Args:
            step_id: ID of step whose fallback failed
            error_message: Description of the fallback failure

        Returns:
            EscalationOutcome indicating escalation after fallback failure
        """
        return EscalationOutcome(
            reason=EscalationReason.FALLBACK_FAILED,
            should_fail=True,
            message=f"Step {step_id} fallback failed: {error_message}",
            context={"step_id": step_id, "error": error_message},
        )
