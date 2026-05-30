"""Tests for policy engine and workflow state machine."""

import pytest

from mas.workflow.policy import PolicyEngine, WorkflowStateMachine
from mas.workflow.state import WorkflowState


class TestWorkflowStateMachine:
    """Tests for single workflow state machine."""

    def test_initial_state(self) -> None:
        """Workflow starts in CREATED state."""
        machine = WorkflowStateMachine("test-workflow")
        assert machine.state == WorkflowState.CREATED

    def test_workflow_id(self) -> None:
        """Workflow ID is stored."""
        machine = WorkflowStateMachine("my-workflow-123")
        assert machine.workflow_id == "my-workflow-123"

    def test_initial_event_recorded(self) -> None:
        """Creation event is logged."""
        machine = WorkflowStateMachine("test")
        assert len(machine.events) == 1
        assert machine.events[0].reason == "workflow_initialized"

    def test_valid_transition(self) -> None:
        """Can transition to allowed state."""
        machine = WorkflowStateMachine("test")
        result = machine.transition(WorkflowState.QUEUED, reason="enqueued")
        assert result is True
        assert machine.state == WorkflowState.QUEUED

    def test_invalid_transition(self) -> None:
        """Cannot transition to disallowed state."""
        machine = WorkflowStateMachine("test")
        result = machine.transition(WorkflowState.RUNNING, reason="invalid")
        assert result is False
        assert machine.state == WorkflowState.CREATED

    def test_transition_with_metadata(self) -> None:
        """Transition events record metadata."""
        machine = WorkflowStateMachine("test")
        machine.transition(
            WorkflowState.QUEUED,
            reason="enqueued",
            metadata={"priority": "high"},
        )
        event = machine.events[-1]
        assert event.metadata == {"priority": "high"}

    def test_event_log_immutable(self) -> None:
        """Event log returned is a copy."""
        machine = WorkflowStateMachine("test")
        events1 = machine.events
        machine.transition(WorkflowState.QUEUED)
        events2 = machine.events
        assert len(events1) < len(events2)

    def test_state_machine_happy_path(self) -> None:
        """Follow typical workflow: created -> queued -> running -> completed."""
        machine = WorkflowStateMachine("test")
        assert machine.transition(WorkflowState.QUEUED, reason="enqueued")
        assert machine.transition(WorkflowState.RUNNING, reason="started")
        assert machine.transition(WorkflowState.COMPLETED, reason="success")
        assert machine.state == WorkflowState.COMPLETED


class TestPolicyEngine:
    """Tests for global policy engine."""

    def test_create_workflow(self) -> None:
        """Can create a new workflow."""
        engine = PolicyEngine()
        machine = engine.create_workflow("wf-1")
        assert machine.workflow_id == "wf-1"
        assert machine.state == WorkflowState.CREATED

    def test_get_workflow(self) -> None:
        """Can retrieve a created workflow."""
        engine = PolicyEngine()
        engine.create_workflow("wf-1")
        machine = engine.get_workflow("wf-1")
        assert machine is not None
        assert machine.workflow_id == "wf-1"

    def test_get_nonexistent_workflow(self) -> None:
        """Getting nonexistent workflow returns None."""
        engine = PolicyEngine()
        assert engine.get_workflow("missing") is None

    def test_duplicate_workflow_id(self) -> None:
        """Cannot create workflow with duplicate ID."""
        engine = PolicyEngine()
        engine.create_workflow("wf-1")
        with pytest.raises(ValueError, match="already exists"):
            engine.create_workflow("wf-1")

    def test_transition_workflow(self) -> None:
        """Can transition workflow through policy engine."""
        engine = PolicyEngine()
        engine.create_workflow("wf-1")
        result = engine.transition_workflow(
            "wf-1", WorkflowState.QUEUED, reason="enqueued"
        )
        assert result is True
        machine = engine.get_workflow("wf-1")
        assert machine.state == WorkflowState.QUEUED

    def test_transition_nonexistent_workflow(self) -> None:
        """Transitioning nonexistent workflow returns False."""
        engine = PolicyEngine()
        result = engine.transition_workflow(
            "missing", WorkflowState.QUEUED, reason="test"
        )
        assert result is False

    def test_global_event_log(self) -> None:
        """Policy engine logs all transitions globally."""
        engine = PolicyEngine()
        engine.create_workflow("wf-1")
        engine.transition_workflow("wf-1", WorkflowState.QUEUED, reason="test")

        events = engine.global_events
        assert len(events) >= 2
        assert events[0].reason == "workflow_created"

    def test_global_events_immutable(self) -> None:
        """Global event log returned is a copy."""
        engine = PolicyEngine()
        events1 = engine.global_events
        engine.create_workflow("wf-1")
        events2 = engine.global_events
        assert len(events1) < len(events2)

    def test_multiple_workflows(self) -> None:
        """Can manage multiple independent workflows."""
        engine = PolicyEngine()
        engine.create_workflow("wf-1")
        engine.create_workflow("wf-2")

        engine.transition_workflow("wf-1", WorkflowState.QUEUED)
        engine.transition_workflow("wf-2", WorkflowState.QUEUED)
        engine.transition_workflow("wf-2", WorkflowState.RUNNING)

        assert engine.get_workflow("wf-1").state == WorkflowState.QUEUED
        assert engine.get_workflow("wf-2").state == WorkflowState.RUNNING

    def test_workflows_dict(self) -> None:
        """Can retrieve all workflows."""
        engine = PolicyEngine()
        engine.create_workflow("wf-1")
        engine.create_workflow("wf-2")

        workflows = engine.workflows()
        assert "wf-1" in workflows
        assert "wf-2" in workflows
        assert len(workflows) == 2
