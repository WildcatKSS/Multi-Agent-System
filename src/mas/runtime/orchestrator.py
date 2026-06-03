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

import time
import uuid
from dataclasses import dataclass, field

from mas.domain.plan import Plan, Step, StepStatus
from mas.domain.task import Task, TaskStatus
from mas.guardrails import GuardrailsEngine
from mas.guardrails.violations import GuardViolation
from mas.runtime.executor import StepExecutorRegistry, StepResult
from mas.workflow.policy import PolicyEngine
from mas.workflow.state import WorkflowState


@dataclass
class _RunContext:
    """Mutable context tracking during a single runtime execution."""

    start_time: float
    accumulated_cost: float = 0.0
    total_retries: int = 0
    guard_violation: GuardViolation | None = None


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
    guard_violation: GuardViolation | None = None


class Runtime:
    """Single-worker orchestrator that runs a Task's Plan to a terminal state."""

    def __init__(
        self,
        policy: PolicyEngine | None = None,
        registry: StepExecutorRegistry | None = None,
        guardrails: GuardrailsEngine | None = None,
    ) -> None:
        """Initialize with an optional shared PolicyEngine, executor registry, and guardrails.

        Args:
            policy: PolicyEngine for workflow state management.
            registry: StepExecutorRegistry for step handlers.
            guardrails: GuardrailsEngine for runtime limits (optional; None = no enforcement).
        """
        self.policy = policy or PolicyEngine()
        self.registry = registry or StepExecutorRegistry()
        self.guardrails = guardrails

    def run(self, task: Task, plan: Plan) -> RunResult:
        """Execute the plan end-to-end, returning a RunResult."""
        # 0. Guard: reject empty / non-executable plans without starting a workflow.
        if not plan.is_executable():
            return RunResult(
                task_id=task.id,
                final_state=WorkflowState.FAILED,
                succeeded=False,
            )

        # 0b. Check guardrails on the plan (if enabled).
        if self.guardrails:
            result = self.guardrails.check_plan(plan)
            if not result.passed:
                return RunResult(
                    task_id=task.id,
                    final_state=WorkflowState.FAILED,
                    succeeded=False,
                    guard_violation=result.violation,
                )

        # 1. Register workflow. A unique id per run keeps the same Task/Plan
        #    re-runnable on a shared PolicyEngine (create_workflow rejects dupes).
        workflow_id = f"{task.id}:{plan.id}:{uuid.uuid4().hex[:8]}"
        self.policy.create_workflow(workflow_id)
        self.policy.transition_workflow(workflow_id, WorkflowState.QUEUED, reason="enqueued")
        self.policy.transition_workflow(workflow_id, WorkflowState.RUNNING, reason="started")
        task.status = TaskStatus.IN_PROGRESS

        # 2. Dependency-driven loop; workflow stays RUNNING throughout.
        ctx = _RunContext(start_time=time.monotonic())
        self._execute_steps(plan, ctx)

        # 3. Terminal transition based on step outcomes and guardrails violations.
        failed = plan.get_steps_by_status(StepStatus.FAILED)
        completed = plan.get_steps_by_status(StepStatus.COMPLETED)
        skipped = plan.get_steps_by_status(StepStatus.SKIPPED)
        unresolved = [
            s for s in plan.steps
            if s.status not in {StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED}
        ]

        # If a guardrail was violated during execution, mark all unresolved steps as SKIPPED.
        if ctx.guard_violation:
            for step in unresolved:
                step.status = StepStatus.SKIPPED
            skipped.extend(unresolved)
            unresolved = []

        succeeded = not failed and not unresolved and not ctx.guard_violation
        if succeeded:
            self.policy.transition_workflow(
                workflow_id, WorkflowState.COMPLETED, reason="all_steps_completed"
            )
            task.status = TaskStatus.COMPLETED
            final_state = WorkflowState.COMPLETED
        else:
            if ctx.guard_violation:
                reason = f"guardrail_violated:{ctx.guard_violation.guard_type.value}"
            elif failed:
                reason = "step_failed"
            else:
                reason = "unresolved_steps"
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
            guard_violation=ctx.guard_violation,
        )

    def _execute_steps(self, plan: Plan, ctx: _RunContext) -> None:
        """Run the dependency-driven scheduling loop until no progress is made."""
        by_id = {s.id: s for s in plan.steps}

        progress = True
        while progress:
            progress = False

            # Check guardrails budget at the start of each iteration (if enabled).
            if self.guardrails and not ctx.guard_violation:
                elapsed = time.monotonic() - ctx.start_time
                result = self.guardrails.check_budget(
                    ctx.accumulated_cost, elapsed, ctx.total_retries
                )
                if not result.passed:
                    ctx.guard_violation = result.violation
                    # Mark all non-terminal steps as SKIPPED.
                    for step in plan.steps:
                        if step.status in {StepStatus.PENDING, StepStatus.READY, StepStatus.EXECUTING}:
                            step.status = StepStatus.SKIPPED
                    break

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
                self._run_step(step, ctx)
                progress = True

    def _run_step(self, step: Step, ctx: _RunContext) -> None:
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
            ctx.accumulated_cost += step.metadata.get("cost", 1.0)
            return

        # Failure: mark FAILED, then retry in-place if budget remains.
        step.status = StepStatus.FAILED
        if step.can_retry():
            step.retry_count += 1
            ctx.total_retries += 1
            step.status = StepStatus.PENDING
