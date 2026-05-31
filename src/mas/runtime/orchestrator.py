"""Single-worker runtime orchestrator (baseline).

Executes a :class:`~mas.domain.plan.Plan` linearly, driving the workflow state
machine **exclusively** through the :class:`~mas.workflow.policy.PolicyEngine`
(no hidden orchestration, no direct state mutation). Steps run in dependency
order; failures are retried up to the step's ``max_retries`` before the step —
and the workflow — is marked failed.

Out of scope for the baseline: parallel/recursive execution, distributed
runtime, memory and guardrails. See ``docs/roadmap.md``.
"""

from dataclasses import dataclass, field

from mas.domain.plan import Plan, Step, StepStatus
from mas.runtime.executor import EchoStepExecutor, StepExecutor, StepResult
from mas.workflow.policy import PolicyEngine
from mas.workflow.state import WorkflowState


@dataclass
class RuntimeResult:
    """Outcome of running a plan through the runtime."""

    workflow_id: str
    final_state: WorkflowState
    step_results: list[StepResult] = field(default_factory=list)
    completed: bool = False


class Runtime:
    """Linear single-worker plan executor."""

    def __init__(self, policy: PolicyEngine, executor: StepExecutor | None = None):
        """Create a runtime bound to a policy engine and a step executor."""
        self._policy = policy
        self._executor: StepExecutor = executor or EchoStepExecutor()

    def run(self, plan: Plan) -> RuntimeResult:
        """Execute ``plan`` and return the aggregated result."""
        workflow_id = plan.task_id
        self._policy.create_workflow(workflow_id)
        self._policy.transition_workflow(
            workflow_id, WorkflowState.QUEUED, reason="runtime_enqueued"
        )
        self._policy.transition_workflow(
            workflow_id, WorkflowState.RUNNING, reason="runtime_started"
        )

        step_results: list[StepResult] = []

        if not plan.is_executable():
            self._policy.transition_workflow(
                workflow_id, WorkflowState.FAILED, reason="plan_not_executable"
            )
            return RuntimeResult(
                workflow_id=workflow_id,
                final_state=WorkflowState.FAILED,
                step_results=step_results,
                completed=False,
            )

        failed = False
        while True:
            ready = self._mark_ready_steps(plan)
            if not ready:
                break
            for step in ready:
                result = self._execute_with_retries(workflow_id, step)
                step_results.append(result)
                if not result.success:
                    failed = True
            if failed:
                break

        # Any step we never reached (blocked by a failed/unmet dependency) is skipped.
        self._skip_unreached_steps(plan)

        completed = not failed and all(
            step.status == StepStatus.COMPLETED for step in plan.steps
        )
        final_state = WorkflowState.COMPLETED if completed else WorkflowState.FAILED
        self._policy.transition_workflow(
            workflow_id,
            final_state,
            reason="all_steps_completed" if completed else "step_failed",
        )

        return RuntimeResult(
            workflow_id=workflow_id,
            final_state=final_state,
            step_results=step_results,
            completed=completed,
        )

    def _mark_ready_steps(self, plan: Plan) -> list[Step]:
        """Promote PENDING steps whose dependencies are all COMPLETED to READY."""
        completed_ids = {
            step.id for step in plan.steps if step.status == StepStatus.COMPLETED
        }
        ready: list[Step] = []
        for step in plan.steps:
            if step.status == StepStatus.PENDING and all(
                dep in completed_ids for dep in step.depends_on
            ):
                step.status = StepStatus.READY
                ready.append(step)
        return ready

    def _execute_with_retries(self, workflow_id: str, step: Step) -> StepResult:
        """Execute a single step, retrying up to ``step.max_retries`` times."""
        while True:
            step.status = StepStatus.EXECUTING
            result = self._safe_execute(step)
            if result.success:
                step.status = StepStatus.COMPLETED
                return result

            step.status = StepStatus.FAILED
            if not step.can_retry():
                return result

            step.retry_count += 1
            self._policy.transition_workflow(
                workflow_id,
                WorkflowState.WAITING_FOR_RETRY,
                reason=f"step_{step.id}_retry_{step.retry_count}",
            )
            self._policy.transition_workflow(
                workflow_id,
                WorkflowState.RUNNING,
                reason=f"step_{step.id}_retrying",
            )

    def _safe_execute(self, step: Step) -> StepResult:
        """Run the executor, converting raised exceptions into a failed result."""
        try:
            return self._executor.execute(step)
        except Exception as exc:  # noqa: BLE001 — runtime must not crash on step errors
            return StepResult(step_id=step.id, success=False, error=str(exc))

    def _skip_unreached_steps(self, plan: Plan) -> None:
        """Mark any steps that were never executed as SKIPPED."""
        for step in plan.steps:
            if step.status in {StepStatus.PENDING, StepStatus.READY}:
                step.status = StepStatus.SKIPPED
