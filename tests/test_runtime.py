"""Tests for the single-worker runtime orchestrator and executor registry."""

import pytest

from mas.domain.plan import Plan, Step, StepStatus
from mas.domain.task import Task, TaskStatus
from mas.runtime import Runtime, StepExecutorRegistry, StepResult
from mas.workflow.state import WorkflowState


def _task(task_id: str = "task-1") -> Task:
    return Task(id=task_id, description="do work", goal="be done")


def _ok_handler(_step: Step) -> StepResult:
    return StepResult(success=True)


def _fail_handler(_step: Step) -> StepResult:
    return StepResult(success=False, error="boom")


class TestStepExecutorRegistry:
    """Tests for the action -> handler registry."""

    def test_register_and_get(self) -> None:
        registry = StepExecutorRegistry()
        registry.register("noop", _ok_handler)
        assert registry.get("noop") is _ok_handler

    def test_has(self) -> None:
        registry = StepExecutorRegistry()
        registry.register("noop", _ok_handler)
        assert registry.has("noop") is True
        assert registry.has("missing") is False

    def test_unknown_action_returns_none(self) -> None:
        registry = StepExecutorRegistry()
        assert registry.get("missing") is None

    def test_empty_action_rejected(self) -> None:
        registry = StepExecutorRegistry()
        with pytest.raises(ValueError, match="action cannot be empty"):
            registry.register("", _ok_handler)


class TestRuntimeHappyPath:
    """A simple linear plan runs to completion."""

    def test_linear_plan_completes(self) -> None:
        registry = StepExecutorRegistry()
        registry.register("work", _ok_handler)
        runtime = Runtime(registry=registry)
        task = _task()
        plan = Plan(
            id="plan-1",
            task_id=task.id,
            steps=[
                Step(id="s1", action="work"),
                Step(id="s2", action="work", depends_on=["s1"]),
                Step(id="s3", action="work", depends_on=["s2"]),
            ],
        )

        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert result.final_state == WorkflowState.COMPLETED
        assert task.status == TaskStatus.COMPLETED
        assert result.completed_steps == ["s1", "s2", "s3"]
        assert all(s.status == StepStatus.COMPLETED for s in plan.steps)


class TestRuntimeDependencies:
    """Steps execute in dependency order."""

    def test_execution_order_respects_dependencies(self) -> None:
        order: list[str] = []
        registry = StepExecutorRegistry()

        def recording(step: Step) -> StepResult:
            order.append(step.id)
            return StepResult(success=True)

        registry.register("work", recording)
        runtime = Runtime(registry=registry)
        task = _task()
        plan = Plan(
            id="plan-1",
            task_id=task.id,
            steps=[
                Step(id="b", action="work", depends_on=["a"]),
                Step(id="a", action="work"),
            ],
        )

        runtime.run(task, plan)

        assert order == ["a", "b"]

    def test_diamond_dependencies(self) -> None:
        order: list[str] = []
        registry = StepExecutorRegistry()

        def recording(step: Step) -> StepResult:
            order.append(step.id)
            return StepResult(success=True)

        registry.register("work", recording)
        runtime = Runtime(registry=registry)
        task = _task()
        plan = Plan(
            id="plan-1",
            task_id=task.id,
            steps=[
                Step(id="a", action="work"),
                Step(id="b", action="work", depends_on=["a"]),
                Step(id="c", action="work", depends_on=["a"]),
                Step(id="d", action="work", depends_on=["b", "c"]),
            ],
        )

        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert order[0] == "a"
        assert order[-1] == "d"
        assert set(order) == {"a", "b", "c", "d"}


class TestRuntimeFailure:
    """A failing step with no retries fails the workflow."""

    def test_failure_fails_workflow(self) -> None:
        registry = StepExecutorRegistry()
        registry.register("work", _fail_handler)
        runtime = Runtime(registry=registry)
        task = _task()
        plan = Plan(
            id="plan-1",
            task_id=task.id,
            steps=[Step(id="s1", action="work", max_retries=0)],
        )

        result = runtime.run(task, plan)

        assert result.succeeded is False
        assert result.final_state == WorkflowState.FAILED
        assert task.status == TaskStatus.FAILED
        assert result.failed_steps == ["s1"]


class TestRuntimeRetry:
    """A step that fails then succeeds is retried."""

    def test_retry_then_success(self) -> None:
        attempts = {"n": 0}
        registry = StepExecutorRegistry()

        def flaky(_step: Step) -> StepResult:
            attempts["n"] += 1
            return StepResult(success=attempts["n"] >= 2)

        registry.register("work", flaky)
        runtime = Runtime(registry=registry)
        task = _task()
        step = Step(id="s1", action="work", max_retries=3)
        plan = Plan(id="plan-1", task_id=task.id, steps=[step])

        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert step.status == StepStatus.COMPLETED
        assert step.retry_count == 1
        assert attempts["n"] == 2


class TestRuntimeSkip:
    """A step with no registered handler is skipped; independent steps still run."""

    def test_unregistered_action_is_skipped(self) -> None:
        registry = StepExecutorRegistry()
        registry.register("work", _ok_handler)
        runtime = Runtime(registry=registry)
        task = _task()
        plan = Plan(
            id="plan-1",
            task_id=task.id,
            steps=[
                Step(id="s1", action="unregistered"),
                Step(id="s2", action="work"),
            ],
        )

        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert result.skipped_steps == ["s1"]
        assert result.completed_steps == ["s2"]


class TestRuntimeExceptionSafe:
    """A handler that raises is treated as a step failure, not a crash."""

    def test_raising_handler_fails_step(self) -> None:
        registry = StepExecutorRegistry()

        def boom(_step: Step) -> StepResult:
            raise RuntimeError("kaboom")

        registry.register("work", boom)
        runtime = Runtime(registry=registry)
        task = _task()
        plan = Plan(
            id="plan-1",
            task_id=task.id,
            steps=[Step(id="s1", action="work", max_retries=0)],
        )

        result = runtime.run(task, plan)

        assert result.succeeded is False
        assert result.failed_steps == ["s1"]


class TestRuntimeFailedDependencySkips:
    """A failed step causes its dependents to be skipped and the workflow to fail."""

    def test_failed_dependency_skips_downstream(self) -> None:
        registry = StepExecutorRegistry()
        registry.register("fail", _fail_handler)
        registry.register("work", _ok_handler)
        runtime = Runtime(registry=registry)
        task = _task()
        plan = Plan(
            id="plan-1",
            task_id=task.id,
            steps=[
                Step(id="a", action="fail", max_retries=0),
                Step(id="b", action="work", depends_on=["a"]),
            ],
        )

        result = runtime.run(task, plan)

        assert result.succeeded is False
        assert result.failed_steps == ["a"]
        assert result.skipped_steps == ["b"]


class TestRuntimeEmptyPlan:
    """An empty / non-executable plan fails fast without creating a workflow."""

    def test_empty_plan(self) -> None:
        runtime = Runtime()
        task = _task()
        plan = Plan(id="plan-1", task_id=task.id, steps=[])

        result = runtime.run(task, plan)

        assert result.succeeded is False
        assert result.final_state == WorkflowState.FAILED
        assert result.workflow_id == ""
        assert runtime.policy.workflows() == {}


class TestRuntimeRerun:
    """Running the same Task/Plan twice on one Runtime does not raise."""

    def test_rerun_uses_unique_workflow_ids(self) -> None:
        registry = StepExecutorRegistry()
        registry.register("work", _ok_handler)
        runtime = Runtime(registry=registry)

        def fresh_plan() -> Plan:
            return Plan(id="plan-1", task_id="task-1", steps=[Step(id="s1", action="work")])

        first = runtime.run(_task(), fresh_plan())
        second = runtime.run(_task(), fresh_plan())

        assert first.succeeded is True
        assert second.succeeded is True
        assert first.workflow_id != second.workflow_id


class TestRuntimeAudit:
    """The PolicyEngine records the expected transitions for a run."""

    def test_transition_reasons_in_order(self) -> None:
        registry = StepExecutorRegistry()
        registry.register("work", _ok_handler)
        runtime = Runtime(registry=registry)
        task = _task()
        plan = Plan(id="plan-1", task_id=task.id, steps=[Step(id="s1", action="work")])

        result = runtime.run(task, plan)

        machine = runtime.policy.get_workflow(result.workflow_id)
        states = [e.to_state for e in machine.events]
        assert states == [
            WorkflowState.CREATED,
            WorkflowState.QUEUED,
            WorkflowState.RUNNING,
            WorkflowState.COMPLETED,
        ]
