"""Tests for the single-worker runtime orchestrator."""

from mas.domain.plan import Plan, Step, StepStatus
from mas.runtime import EchoStepExecutor, Runtime, StepResult
from mas.workflow import PolicyEngine, WorkflowState


def _plan(steps: list[Step], task_id: str = "task-1") -> Plan:
    return Plan(id=f"plan-{task_id}", task_id=task_id, steps=steps)


class FailingExecutor:
    """Executor that always fails."""

    def execute(self, step: Step) -> StepResult:
        return StepResult(step_id=step.id, success=False, error="boom")


class FlakyExecutor:
    """Executor that fails a fixed number of times before succeeding."""

    def __init__(self, failures_before_success: int):
        self.remaining_failures = failures_before_success

    def execute(self, step: Step) -> StepResult:
        if self.remaining_failures > 0:
            self.remaining_failures -= 1
            return StepResult(step_id=step.id, success=False, error="transient")
        return StepResult(step_id=step.id, success=True, output={"ok": True})


class RaisingExecutor:
    """Executor that raises instead of returning a failed result."""

    def execute(self, step: Step) -> StepResult:
        raise RuntimeError("kaboom")


class TestEchoStepExecutor:
    def test_echoes_action_and_inputs(self) -> None:
        executor = EchoStepExecutor()
        result = executor.execute(Step(id="s1", action="do_thing", inputs={"k": "v"}))
        assert result.success is True
        assert result.output == {"action": "do_thing", "inputs": {"k": "v"}}


class TestRuntimeHappyPath:
    def test_linear_plan_completes(self) -> None:
        plan = _plan(
            [
                Step(id="a", action="step_a"),
                Step(id="b", action="step_b"),
            ]
        )
        result = Runtime(PolicyEngine()).run(plan)

        assert result.final_state == WorkflowState.COMPLETED
        assert result.completed is True
        assert all(r.success for r in result.step_results)
        assert all(s.status == StepStatus.COMPLETED for s in plan.steps)

    def test_dependency_order(self) -> None:
        order: list[str] = []

        class RecordingExecutor:
            def execute(self, step: Step) -> StepResult:
                order.append(step.id)
                return StepResult(step_id=step.id, success=True)

        plan = _plan(
            [
                Step(id="b", action="b", depends_on=["a"]),
                Step(id="a", action="a"),
            ]
        )
        Runtime(PolicyEngine(), RecordingExecutor()).run(plan)
        assert order == ["a", "b"]


class TestRuntimeFailure:
    def test_failing_step_exhausts_retries(self) -> None:
        step = Step(id="a", action="a", max_retries=3)
        plan = _plan([step])
        result = Runtime(PolicyEngine(), FailingExecutor()).run(plan)

        assert result.final_state == WorkflowState.FAILED
        assert result.completed is False
        assert step.status == StepStatus.FAILED
        assert step.retry_count == 3
        assert step.has_failed() is True

    def test_retry_recovers(self) -> None:
        step = Step(id="a", action="a", max_retries=3)
        plan = _plan([step])
        result = Runtime(PolicyEngine(), FlakyExecutor(2)).run(plan)

        assert result.final_state == WorkflowState.COMPLETED
        assert step.status == StepStatus.COMPLETED
        assert step.retry_count == 2

    def test_raised_exception_is_treated_as_failure(self) -> None:
        plan = _plan([Step(id="a", action="a", max_retries=0)])
        result = Runtime(PolicyEngine(), RaisingExecutor()).run(plan)

        assert result.final_state == WorkflowState.FAILED
        assert result.step_results[0].error == "kaboom"

    def test_dependent_step_skipped_after_failure(self) -> None:
        a = Step(id="a", action="a", max_retries=0)
        b = Step(id="b", action="b", depends_on=["a"])
        plan = _plan([a, b])
        result = Runtime(PolicyEngine(), FailingExecutor()).run(plan)

        assert result.final_state == WorkflowState.FAILED
        assert a.status == StepStatus.FAILED
        assert b.status == StepStatus.SKIPPED

    def test_empty_plan_fails(self) -> None:
        result = Runtime(PolicyEngine()).run(_plan([]))
        assert result.final_state == WorkflowState.FAILED
        assert result.completed is False


class TestRuntimeStateTransitions:
    def test_state_chain_is_logged(self) -> None:
        policy = PolicyEngine()
        plan = _plan([Step(id="a", action="a")])
        Runtime(policy).run(plan)

        reasons = [e.reason for e in policy.global_events]
        assert "workflow_created" in reasons
        assert "runtime_enqueued" in reasons
        assert "runtime_started" in reasons
        assert "all_steps_completed" in reasons

    def test_machine_reaches_completed(self) -> None:
        policy = PolicyEngine()
        plan = _plan([Step(id="a", action="a")], task_id="wf-x")
        Runtime(policy).run(plan)

        machine = policy.get_workflow("wf-x")
        assert machine is not None
        assert machine.state == WorkflowState.COMPLETED
