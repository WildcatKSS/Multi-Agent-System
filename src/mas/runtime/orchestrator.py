"""Single-worker runtime orchestrator (baseline).

Executes a Plan's steps in dependency order while driving the workflow through
its lifecycle via the PolicyEngine (the source of truth for state transitions).
Single-threaded; no concurrency, cancellation, or distributed execution yet.

Readiness / skip rules:
- A PENDING step becomes READY once all of its dependencies are COMPLETED.
- A PENDING step is SKIPPED if any dependency is FAILED or SKIPPED (failure and
  skips cascade transitively to downstream steps). Independent steps are
  unaffected.
- A step whose action has no registered handler is SKIPPED (no-op baseline).
"""

import uuid
from dataclasses import dataclass, field

from mas.domain.plan import Plan, Step, StepStatus
from mas.domain.task import Task, TaskStatus
from mas.runtime.executor import StepExecutorRegistry, StepResult
from mas.workflow.policy import PolicyEngine
from mas.workflow.state import WorkflowState


@dataclass
class RunResult:
    """Summary of a single runtime execution."""

    task_id: str
    final_state: WorkflowState
    succeeded: bool
    workflow_id: str = ""
    completed_steps: list[str] = field(default_factory=list)
    failed_steps: list[str] = field(default_factory=list)
    skipped_steps: list[str] = field(default_factory=list)


class Runtime:
    """Single-worker orchestrator that runs a Task's Plan to a terminal state."""

    def __init__(
        self,
        policy: PolicyEngine | None = None,
        registry: StepExecutorRegistry | None = None,
    ) -> None:
        """Initialize with an optional shared PolicyEngine and executor registry."""
        self.policy = policy or PolicyEngine()
        self.registry = registry or StepExecutorRegistry()

    def run(self, task: Task, plan: Plan) -> RunResult:
        """Execute the plan end-to-end, returning a RunResult."""
        # 0. Guard: reject empty / non-executable plans without starting a workflow.
        if not plan.is_executable():
            return RunResult(
                task_id=task.id,
                final_state=WorkflowState.FAILED,
                succeeded=False,
            )

        # 1. Register workflow. A unique id per run keeps the same Task/Plan
        #    re-runnable on a shared PolicyEngine (create_workflow rejects dupes).
        workflow_id = f"{task.id}:{plan.id}:{uuid.uuid4().hex[:8]}"
        self.policy.create_workflow(workflow_id)
        self.policy.transition_workflow(workflow_id, WorkflowState.QUEUED, reason="enqueued")
        self.policy.transition_workflow(workflow_id, WorkflowState.RUNNING, reason="started")
        task.status = TaskStatus.IN_PROGRESS

        # 2. Dependency-driven loop; workflow stays RUNNING throughout.
        self._execute_steps(plan)

        # 3. Terminal transition based on step outcomes.
        failed = plan.get_steps_by_status(StepStatus.FAILED)
        completed = plan.get_steps_by_status(StepStatus.COMPLETED)
        skipped = plan.get_steps_by_status(StepStatus.SKIPPED)
        unresolved = [
            s for s in plan.steps
            if s.status not in {StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED}
        ]

        succeeded = not failed and not unresolved
        if succeeded:
            self.policy.transition_workflow(
                workflow_id, WorkflowState.COMPLETED, reason="all_steps_completed"
            )
            task.status = TaskStatus.COMPLETED
            final_state = WorkflowState.COMPLETED
        else:
            reason = "step_failed" if failed else "unresolved_steps"
            self.policy.transition_workflow(workflow_id, WorkflowState.FAILED, reason=reason)
            task.status = TaskStatus.FAILED
            final_state = WorkflowState.FAILED

        return RunResult(
            task_id=task.id,
            final_state=final_state,
            succeeded=succeeded,
            workflow_id=workflow_id,
            completed_steps=[s.id for s in completed],
            failed_steps=[s.id for s in failed],
            skipped_steps=[s.id for s in skipped],
        )

    def _execute_steps(self, plan: Plan) -> None:
        """Run the dependency-driven scheduling loop until no progress is made."""
        by_id = {s.id: s for s in plan.steps}

        progress = True
        while progress:
            progress = False

            # Resolve readiness / skips for PENDING steps.
            for step in plan.steps:
                if step.status != StepStatus.PENDING:
                    continue
                dep_states = [by_id[d].status for d in step.depends_on]
                if any(st in {StepStatus.FAILED, StepStatus.SKIPPED} for st in dep_states):
                    step.status = StepStatus.SKIPPED
                    progress = True
                elif all(st == StepStatus.COMPLETED for st in dep_states):
                    step.status = StepStatus.READY
                    progress = True

            # Execute every ready step.
            for step in plan.steps:
                if step.status != StepStatus.READY:
                    continue
                self._run_step(step)
                progress = True

    def _run_step(self, step: Step) -> None:
        """Execute one ready step, applying retry semantics on failure."""
        handler = self.registry.get(step.action)
        if handler is None:
            step.status = StepStatus.SKIPPED
            return

        step.status = StepStatus.EXECUTING
        try:
            result = handler(step)
        except Exception as exc:  # noqa: BLE001 - any handler failure is a step failure
            result = StepResult(success=False, error=str(exc))

        if result.success:
            step.status = StepStatus.COMPLETED
            return

        # Failure: mark FAILED, then retry in-place if budget remains.
        step.status = StepStatus.FAILED
        if step.can_retry():
            step.retry_count += 1
            step.status = StepStatus.PENDING
