"""Workflow state definitions and transitions."""

from enum import Enum


class WorkflowState(Enum):
    """Allowed states in workflow lifecycle."""

    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_RETRY = "waiting_for_retry"
    BLOCKED = "blocked"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    @classmethod
    def initial_state(cls) -> "WorkflowState":
        """Return the initial state when a workflow is created."""
        return cls.CREATED

    @classmethod
    def terminal_states(cls) -> set["WorkflowState"]:
        """Return states from which no further transitions are allowed."""
        return {cls.FAILED, cls.COMPLETED, cls.CANCELLED}

    def is_terminal(self) -> bool:
        """Check if this is a terminal state."""
        return self in {WorkflowState.FAILED, WorkflowState.COMPLETED, WorkflowState.CANCELLED}


# State transition rules: which states can transition to which
ALLOWED_TRANSITIONS = {
    WorkflowState.CREATED: {WorkflowState.QUEUED, WorkflowState.CANCELLED},
    WorkflowState.QUEUED: {WorkflowState.RUNNING, WorkflowState.CANCELLED},
    WorkflowState.RUNNING: {
        WorkflowState.COMPLETED,
        WorkflowState.FAILED,
        WorkflowState.WAITING_FOR_RETRY,
        WorkflowState.BLOCKED,
    },
    WorkflowState.WAITING_FOR_RETRY: {WorkflowState.RUNNING, WorkflowState.FAILED},
    WorkflowState.BLOCKED: {WorkflowState.RUNNING, WorkflowState.FAILED},
    WorkflowState.FAILED: set(),
    WorkflowState.COMPLETED: set(),
    WorkflowState.CANCELLED: set(),
}


def can_transition(from_state: WorkflowState, to_state: WorkflowState) -> bool:
    """Check if a transition from one state to another is allowed."""
    return to_state in ALLOWED_TRANSITIONS.get(from_state, set())
