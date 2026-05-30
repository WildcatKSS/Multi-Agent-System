"""Tests for Plan and Step domain contracts."""

import pytest

from mas.domain.plan import Plan, Step, StepStatus


class TestStep:
    """Tests for Step dataclass."""

    def test_step_creation(self) -> None:
        """Can create a step with required fields."""
        step = Step(
            id="step-1",
            action="retrieve_data",
            inputs={"source": "database"},
        )
        assert step.id == "step-1"
        assert step.action == "retrieve_data"
        assert step.inputs == {"source": "database"}
        assert step.status == StepStatus.PENDING

    def test_step_with_dependencies(self) -> None:
        """Step can depend on other steps."""
        step = Step(
            id="step-2",
            action="process",
            depends_on=["step-1"],
        )
        assert step.depends_on == ["step-1"]

    def test_step_validation_empty_id(self) -> None:
        """Step creation fails with empty id."""
        with pytest.raises(ValueError, match="id cannot be empty"):
            Step(id="", action="work")

    def test_step_validation_empty_action(self) -> None:
        """Step creation fails with empty action."""
        with pytest.raises(ValueError, match="action cannot be empty"):
            Step(id="step-1", action="")

    def test_step_validation_negative_retries(self) -> None:
        """Step creation fails with negative max_retries."""
        with pytest.raises(ValueError, match="max_retries cannot be negative"):
            Step(id="step-1", action="work", max_retries=-1)

    def test_step_can_execute(self) -> None:
        """can_execute() is True only for READY status."""
        step = Step(id="step-1", action="work", status=StepStatus.READY)
        assert step.can_execute()

        step.status = StepStatus.PENDING
        assert not step.can_execute()

    def test_step_retry_logic(self) -> None:
        """Retry logic works correctly."""
        step = Step(
            id="step-1",
            action="work",
            status=StepStatus.FAILED,
            retry_count=1,
            max_retries=3,
        )
        assert step.can_retry()
        assert not step.has_failed()

        step.retry_count = 3
        assert not step.can_retry()
        assert step.has_failed()


class TestPlan:
    """Tests for Plan dataclass."""

    def test_plan_creation(self) -> None:
        """Can create a plan with required fields."""
        step = Step(id="step-1", action="work")
        plan = Plan(id="plan-1", task_id="task-1", steps=[step])
        assert plan.id == "plan-1"
        assert plan.task_id == "task-1"
        assert len(plan.steps) == 1

    def test_plan_validation_empty_id(self) -> None:
        """Plan creation fails with empty id."""
        with pytest.raises(ValueError, match="id cannot be empty"):
            Plan(id="", task_id="task-1")

    def test_plan_validation_empty_task_id(self) -> None:
        """Plan creation fails with empty task_id."""
        with pytest.raises(ValueError, match="task_id cannot be empty"):
            Plan(id="plan-1", task_id="")

    def test_plan_validation_negative_cost(self) -> None:
        """Plan creation fails with negative cost."""
        with pytest.raises(ValueError, match="estimated_cost cannot be negative"):
            Plan(id="plan-1", task_id="task-1", estimated_cost=-1.0)

    def test_plan_validation_negative_time(self) -> None:
        """Plan creation fails with negative time."""
        with pytest.raises(ValueError, match="estimated_time_seconds cannot be negative"):
            Plan(id="plan-1", task_id="task-1", estimated_time_seconds=-1.0)

    def test_plan_validation_unknown_dependency(self) -> None:
        """Plan creation fails if step depends on unknown step."""
        step = Step(id="step-1", action="work", depends_on=["unknown-step"])
        with pytest.raises(ValueError, match="depends on unknown step"):
            Plan(id="plan-1", task_id="task-1", steps=[step])

    def test_plan_get_steps_by_status(self) -> None:
        """Can retrieve steps by status."""
        steps = [
            Step(id="step-1", action="work", status=StepStatus.PENDING),
            Step(id="step-2", action="work", status=StepStatus.READY),
            Step(id="step-3", action="work", status=StepStatus.PENDING),
        ]
        plan = Plan(id="plan-1", task_id="task-1", steps=steps)

        pending = plan.get_steps_by_status(StepStatus.PENDING)
        assert len(pending) == 2
        assert pending[0].id == "step-1"

    def test_plan_is_executable(self) -> None:
        """Plan is executable if it has steps with valid IDs."""
        plan_empty = Plan(id="plan-1", task_id="task-1")
        assert not plan_empty.is_executable()

        step = Step(id="step-1", action="work")
        plan_with_steps = Plan(id="plan-1", task_id="task-1", steps=[step])
        assert plan_with_steps.is_executable()

    def test_plan_get_ready_steps(self) -> None:
        """get_ready_steps() returns only READY steps."""
        steps = [
            Step(id="step-1", action="work", status=StepStatus.READY),
            Step(id="step-2", action="work", status=StepStatus.PENDING),
            Step(id="step-3", action="work", status=StepStatus.READY),
        ]
        plan = Plan(id="plan-1", task_id="task-1", steps=steps)

        ready = plan.get_ready_steps()
        assert len(ready) == 2
        assert ready[0].id == "step-1"
        assert ready[1].id == "step-3"

    def test_plan_all_steps_completed(self) -> None:
        """all_steps_completed() checks if all steps are terminal."""
        plan_empty = Plan(id="plan-1", task_id="task-1")
        assert not plan_empty.all_steps_completed()

        steps = [
            Step(id="step-1", action="work", status=StepStatus.COMPLETED),
            Step(id="step-2", action="work", status=StepStatus.FAILED),
            Step(id="step-3", action="work", status=StepStatus.SKIPPED),
        ]
        plan = Plan(id="plan-1", task_id="task-1", steps=steps)
        assert plan.all_steps_completed()

        # Add a non-terminal step
        steps.append(Step(id="step-4", action="work", status=StepStatus.PENDING))
        plan_incomplete = Plan(id="plan-1", task_id="task-1", steps=steps)
        assert not plan_incomplete.all_steps_completed()
