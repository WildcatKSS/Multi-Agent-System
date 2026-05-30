"""Policy engine for workflow state transitions and validation."""

from dataclasses import dataclass, field
from datetime import datetime

from mas.workflow.state import WorkflowState, can_transition


@dataclass
class StateTransitionEvent:
    """Record of a state transition."""

    timestamp: datetime
    from_state: WorkflowState
    to_state: WorkflowState
    reason: str = ""
    metadata: dict = field(default_factory=dict)


class WorkflowStateMachine:
    """Single-workflow state machine with audit trail."""

    def __init__(self, workflow_id: str):
        """Initialize a new workflow state machine."""
        self.workflow_id = workflow_id
        self._state = WorkflowState.initial_state()
        self._events: list[StateTransitionEvent] = []

        self._events.append(
            StateTransitionEvent(
                timestamp=datetime.now(),
                from_state=self._state,
                to_state=self._state,
                reason="workflow_initialized",
            )
        )

    @property
    def state(self) -> WorkflowState:
        """Get current state."""
        return self._state

    @property
    def events(self) -> list[StateTransitionEvent]:
        """Get immutable copy of event log."""
        return self._events.copy()

    def transition(
        self, new_state: WorkflowState, reason: str = "", metadata: dict | None = None
    ) -> bool:
        """Attempt a state transition."""
        if not can_transition(self._state, new_state):
            return False

        self._events.append(
            StateTransitionEvent(
                timestamp=datetime.now(),
                from_state=self._state,
                to_state=new_state,
                reason=reason,
                metadata=metadata or {},
            )
        )
        self._state = new_state
        return True


class PolicyEngine:
    """Global policy enforcement for workflow execution.

    Manages state machines for multiple workflows and enforces transition rules.
    Maintains immutable audit log of all state changes.

    NOTE: Single-threaded only. Add locking if used in async/multi-worker contexts.
    """

    def __init__(self):
        """Initialize policy engine."""
        self._workflows: dict[str, WorkflowStateMachine] = {}
        self._global_events: list[StateTransitionEvent] = []

    def create_workflow(self, workflow_id: str) -> WorkflowStateMachine:
        """Create a new workflow state machine."""
        if workflow_id in self._workflows:
            raise ValueError(f"Workflow {workflow_id} already exists")

        machine = WorkflowStateMachine(workflow_id)
        self._workflows[workflow_id] = machine
        self._global_events.append(
            StateTransitionEvent(
                timestamp=datetime.now(),
                from_state=machine.state,
                to_state=machine.state,
                reason="workflow_created",
                metadata={"workflow_id": workflow_id},
            )
        )
        return machine

    def get_workflow(self, workflow_id: str) -> WorkflowStateMachine | None:
        """Get an existing workflow state machine."""
        return self._workflows.get(workflow_id)

    def transition_workflow(
        self,
        workflow_id: str,
        new_state: WorkflowState,
        reason: str = "",
        metadata: dict | None = None,
    ) -> bool:
        """Transition a workflow through the policy layer."""
        machine = self.get_workflow(workflow_id)
        if machine is None:
            return False

        if machine.transition(new_state, reason, metadata):
            self._global_events.append(
                StateTransitionEvent(
                    timestamp=datetime.now(),
                    from_state=machine.events[-1].from_state,
                    to_state=new_state,
                    reason=reason,
                    metadata={**(metadata or {}), "workflow_id": workflow_id},
                )
            )
            return True

        return False

    @property
    def global_events(self) -> list[StateTransitionEvent]:
        """Get immutable copy of global event log."""
        return self._global_events.copy()

    def workflows(self) -> dict[str, WorkflowStateMachine]:
        """Get all workflows (shallow copy)."""
        return self._workflows.copy()
