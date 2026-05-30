"""Tests for workflow state machine."""

import pytest

from mas.workflow.state import WorkflowState, can_transition


class TestWorkflowState:
    """Tests for WorkflowState enum."""

    def test_initial_state_is_created(self) -> None:
        """Workflow starts in CREATED state."""
        assert WorkflowState.initial_state() == WorkflowState.CREATED

    def test_terminal_states(self) -> None:
        """Terminal states are those with no outgoing transitions."""
        terminal = WorkflowState.terminal_states()
        assert WorkflowState.FAILED in terminal
        assert WorkflowState.COMPLETED in terminal
        assert WorkflowState.CANCELLED in terminal
        assert len(terminal) == 3

    def test_is_terminal(self) -> None:
        """States correctly identify as terminal or not."""
        assert WorkflowState.COMPLETED.is_terminal()
        assert WorkflowState.FAILED.is_terminal()
        assert WorkflowState.CANCELLED.is_terminal()

        assert not WorkflowState.CREATED.is_terminal()
        assert not WorkflowState.RUNNING.is_terminal()
        assert not WorkflowState.QUEUED.is_terminal()


class TestStateTransitions:
    """Tests for allowed state transitions."""

    def test_created_to_queued(self) -> None:
        """Can transition from CREATED to QUEUED."""
        assert can_transition(WorkflowState.CREATED, WorkflowState.QUEUED)

    def test_created_to_cancelled(self) -> None:
        """Can transition from CREATED to CANCELLED."""
        assert can_transition(WorkflowState.CREATED, WorkflowState.CANCELLED)

    def test_queued_to_running(self) -> None:
        """Can transition from QUEUED to RUNNING."""
        assert can_transition(WorkflowState.QUEUED, WorkflowState.RUNNING)

    def test_running_to_completed(self) -> None:
        """Can transition from RUNNING to COMPLETED."""
        assert can_transition(WorkflowState.RUNNING, WorkflowState.COMPLETED)

    def test_running_to_failed(self) -> None:
        """Can transition from RUNNING to FAILED."""
        assert can_transition(WorkflowState.RUNNING, WorkflowState.FAILED)

    def test_running_to_waiting_for_retry(self) -> None:
        """Can transition from RUNNING to WAITING_FOR_RETRY."""
        assert can_transition(WorkflowState.RUNNING, WorkflowState.WAITING_FOR_RETRY)

    def test_running_to_blocked(self) -> None:
        """Can transition from RUNNING to BLOCKED."""
        assert can_transition(WorkflowState.RUNNING, WorkflowState.BLOCKED)

    def test_waiting_for_retry_to_running(self) -> None:
        """Can transition from WAITING_FOR_RETRY back to RUNNING."""
        assert can_transition(WorkflowState.WAITING_FOR_RETRY, WorkflowState.RUNNING)

    def test_blocked_to_running(self) -> None:
        """Can transition from BLOCKED back to RUNNING."""
        assert can_transition(WorkflowState.BLOCKED, WorkflowState.RUNNING)

    def test_invalid_transition_created_to_running(self) -> None:
        """Cannot skip QUEUED when transitioning from CREATED."""
        assert not can_transition(WorkflowState.CREATED, WorkflowState.RUNNING)

    def test_invalid_transition_from_completed(self) -> None:
        """Cannot transition from terminal state COMPLETED."""
        assert not can_transition(WorkflowState.COMPLETED, WorkflowState.RUNNING)
        assert not can_transition(WorkflowState.COMPLETED, WorkflowState.QUEUED)

    def test_invalid_transition_from_failed(self) -> None:
        """Cannot transition from terminal state FAILED."""
        assert not can_transition(WorkflowState.FAILED, WorkflowState.RUNNING)

    def test_invalid_transition_from_cancelled(self) -> None:
        """Cannot transition from terminal state CANCELLED."""
        assert not can_transition(WorkflowState.CANCELLED, WorkflowState.RUNNING)
