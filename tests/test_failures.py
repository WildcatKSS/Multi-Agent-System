"""Tests for failure classification and taxonomy."""

import pytest

from mas.agents.recovery.failures import (
    FailureType,
    RecoverableError,
    PermanentError,
    StepFailure,
)


class TestFailureType:
    """Tests for FailureType enum."""

    def test_recoverable_failures(self) -> None:
        """Verify recoverable failure types are classified correctly."""
        recoverable = {
            FailureType.TIMEOUT,
            FailureType.TOOL_UNAVAILABLE,
            FailureType.RESOURCE_EXHAUSTED,
            FailureType.EXTERNAL_SERVICE_ERROR,
        }

        for failure_type in recoverable:
            assert failure_type.is_recoverable(), (
                f"{failure_type} should be recoverable"
            )

    def test_permanent_failures(self) -> None:
        """Verify permanent failure types are classified correctly."""
        permanent = {
            FailureType.HANDLER_ERROR,
            FailureType.INVALID_INPUT,
            FailureType.UNKNOWN,
        }

        for failure_type in permanent:
            assert not failure_type.is_recoverable(), (
                f"{failure_type} should be permanent"
            )


class TestRecoverableError:
    """Tests for RecoverableError exception."""

    def test_create_recoverable_error(self) -> None:
        """Can create a recoverable error with valid data."""
        error = RecoverableError(
            failure_type=FailureType.TIMEOUT,
            message="Step timed out after 60 seconds",
            context={"step_id": "step-01", "timeout_ms": 60000},
        )

        assert error.failure_type == FailureType.TIMEOUT
        assert error.message == "Step timed out after 60 seconds"
        assert error.context["step_id"] == "step-01"

    def test_reject_permanent_failure_type(self) -> None:
        """Cannot create recoverable error with permanent failure type."""
        with pytest.raises(ValueError, match="not recoverable"):
            RecoverableError(
                failure_type=FailureType.HANDLER_ERROR,
                message="Invalid error type",
            )

    def test_reject_empty_message(self) -> None:
        """Cannot create recoverable error with empty message."""
        with pytest.raises(ValueError, match="message cannot be empty"):
            RecoverableError(
                failure_type=FailureType.TIMEOUT,
                message="",
            )

    def test_immutable(self) -> None:
        """RecoverableError is immutable (frozen dataclass)."""
        error = RecoverableError(
            failure_type=FailureType.TIMEOUT,
            message="Timeout",
        )

        with pytest.raises(AttributeError):
            error.message = "Modified"  # type: ignore


class TestPermanentError:
    """Tests for PermanentError exception."""

    def test_create_permanent_error(self) -> None:
        """Can create a permanent error with valid data."""
        error = PermanentError(
            failure_type=FailureType.INVALID_INPUT,
            message="Step received malformed input",
            context={"step_id": "step-02", "input": "invalid"},
        )

        assert error.failure_type == FailureType.INVALID_INPUT
        assert error.message == "Step received malformed input"

    def test_reject_recoverable_failure_type(self) -> None:
        """Cannot create permanent error with recoverable failure type."""
        with pytest.raises(ValueError, match="is recoverable"):
            PermanentError(
                failure_type=FailureType.TIMEOUT,
                message="Invalid error type",
            )

    def test_reject_empty_message(self) -> None:
        """Cannot create permanent error with empty message."""
        with pytest.raises(ValueError, match="message cannot be empty"):
            PermanentError(
                failure_type=FailureType.INVALID_INPUT,
                message="",
            )

    def test_immutable(self) -> None:
        """PermanentError is immutable (frozen dataclass)."""
        error = PermanentError(
            failure_type=FailureType.INVALID_INPUT,
            message="Invalid input",
        )

        with pytest.raises(AttributeError):
            error.message = "Modified"  # type: ignore


class TestStepFailure:
    """Tests for StepFailure record."""

    def test_create_step_failure(self) -> None:
        """Can create a step failure with valid data."""
        failure = StepFailure(
            step_id="step-01",
            failure_type=FailureType.TIMEOUT,
            message="Step timed out",
            attempt_number=1,
            context={"timeout_ms": 60000},
        )

        assert failure.step_id == "step-01"
        assert failure.failure_type == FailureType.TIMEOUT
        assert failure.attempt_number == 1

    def test_is_recoverable(self) -> None:
        """StepFailure.is_recoverable() delegates to FailureType."""
        recoverable = StepFailure(
            step_id="step-01",
            failure_type=FailureType.TIMEOUT,
            message="Timeout",
            attempt_number=1,
        )
        assert recoverable.is_recoverable()

        permanent = StepFailure(
            step_id="step-02",
            failure_type=FailureType.INVALID_INPUT,
            message="Invalid input",
            attempt_number=1,
        )
        assert not permanent.is_recoverable()

    def test_reject_empty_step_id(self) -> None:
        """Cannot create step failure with empty step_id."""
        with pytest.raises(ValueError, match="step_id cannot be empty"):
            StepFailure(
                step_id="",
                failure_type=FailureType.TIMEOUT,
                message="Timeout",
                attempt_number=1,
            )

    def test_reject_empty_message(self) -> None:
        """Cannot create step failure with empty message."""
        with pytest.raises(ValueError, match="message cannot be empty"):
            StepFailure(
                step_id="step-01",
                failure_type=FailureType.TIMEOUT,
                message="",
                attempt_number=1,
            )

    def test_reject_invalid_attempt_number(self) -> None:
        """Cannot create step failure with invalid attempt number."""
        with pytest.raises(ValueError, match="attempt_number must be >= 1"):
            StepFailure(
                step_id="step-01",
                failure_type=FailureType.TIMEOUT,
                message="Timeout",
                attempt_number=0,
            )

    def test_immutable(self) -> None:
        """StepFailure is immutable (frozen dataclass)."""
        failure = StepFailure(
            step_id="step-01",
            failure_type=FailureType.TIMEOUT,
            message="Timeout",
            attempt_number=1,
        )

        with pytest.raises(AttributeError):
            failure.message = "Modified"  # type: ignore
