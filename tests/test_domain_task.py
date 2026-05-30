"""Tests for Task domain contract."""

import pytest

from mas.domain.task import Task, TaskStatus


class TestTask:
    """Tests for Task dataclass."""

    def test_task_creation(self) -> None:
        """Can create a task with required fields."""
        task = Task(
            id="task-1",
            description="Analyze customer feedback",
            goal="Generate insights from feedback",
        )
        assert task.id == "task-1"
        assert task.description == "Analyze customer feedback"
        assert task.goal == "Generate insights from feedback"
        assert task.status == TaskStatus.PENDING

    def test_task_with_context(self) -> None:
        """Task can store execution context."""
        context = {"language": "en", "priority": "high"}
        task = Task(
            id="task-1",
            description="Translate document",
            goal="Translate to Spanish",
            context=context,
        )
        assert task.context == context

    def test_task_with_constraints(self) -> None:
        """Task can have execution constraints."""
        constraints = ["max_tokens: 2000", "temperature: 0.5"]
        task = Task(
            id="task-1",
            description="Generate text",
            goal="Generate creative story",
            constraints=constraints,
        )
        assert task.constraints == constraints

    def test_task_validation_empty_id(self) -> None:
        """Task creation fails with empty id."""
        with pytest.raises(ValueError, match="id cannot be empty"):
            Task(id="", description="Test", goal="Test goal")

    def test_task_validation_empty_description(self) -> None:
        """Task creation fails with empty description."""
        with pytest.raises(ValueError, match="description cannot be empty"):
            Task(id="task-1", description="", goal="Test goal")

    def test_task_validation_empty_goal(self) -> None:
        """Task creation fails with empty goal."""
        with pytest.raises(ValueError, match="goal cannot be empty"):
            Task(id="task-1", description="Test", goal="")

    def test_task_status_transitions(self) -> None:
        """Task status can be updated."""
        task = Task(
            id="task-1",
            description="Work",
            goal="Complete work",
            status=TaskStatus.PENDING,
        )
        assert task.status == TaskStatus.PENDING
        assert not task.is_complete()

        task.status = TaskStatus.IN_PROGRESS
        assert task.is_active()
        assert not task.is_complete()

        task.status = TaskStatus.COMPLETED
        assert task.is_complete()
        assert not task.is_active()

    def test_task_is_complete(self) -> None:
        """is_complete() returns True for terminal states."""
        terminal_states = [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]
        for state in terminal_states:
            task = Task(
                id="task-1",
                description="Work",
                goal="Complete",
                status=state,
            )
            assert task.is_complete()

    def test_task_is_active(self) -> None:
        """is_active() returns True only for IN_PROGRESS."""
        task = Task(
            id="task-1",
            description="Work",
            goal="Complete",
            status=TaskStatus.IN_PROGRESS,
        )
        assert task.is_active()

        task.status = TaskStatus.PENDING
        assert not task.is_active()

    def test_task_metadata(self) -> None:
        """Task can store arbitrary metadata."""
        metadata = {"user_id": "123", "campaign": "summer-sale"}
        task = Task(
            id="task-1",
            description="Process order",
            goal="Complete order",
            metadata=metadata,
        )
        assert task.metadata == metadata
