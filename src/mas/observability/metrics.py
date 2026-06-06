"""Metrics collection for execution monitoring."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ExecutionMetrics:
    """Metrics from a single execution run.

    Captures comprehensive execution statistics including step outcomes,
    cost accounting, timing, and guard violations for operational visibility
    and performance analysis.

    Attributes:
        run_id: Unique identifier for this run (correlates with logs/traces).
        task_id: Task being executed.
        workflow_id: Workflow state machine ID.
        plan_id: Plan being executed.
        total_steps: Number of steps in the plan.
        completed_steps: Count of successfully completed steps.
        failed_steps: Count of failed steps (did not succeed after retries).
        skipped_steps: Count of skipped steps (never attempted due to dependency/guard).
        total_retries: Total retry attempts across all steps.
        accumulated_cost: Total cost incurred during execution (sum of step costs).
        elapsed_seconds: Total wall-clock time in seconds.
        succeeded: Whether the execution succeeded (no failures or guards violated).
        guard_violation: Name of guard violation, if any (COST, TTL, RETRIES, PLAN_DEPTH).
    """

    run_id: str
    task_id: str
    workflow_id: str
    plan_id: str
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    skipped_steps: int = 0
    total_retries: int = 0
    accumulated_cost: float = 0.0
    elapsed_seconds: float = 0.0
    succeeded: bool = False
    guard_violation: str | None = None

    def __post_init__(self) -> None:
        """Validate metrics."""
        if not self.run_id:
            raise ValueError("run_id cannot be empty")
        if self.elapsed_seconds < 0:
            raise ValueError(f"elapsed_seconds cannot be negative, got {self.elapsed_seconds}")
        if self.accumulated_cost < 0:
            raise ValueError(f"accumulated_cost cannot be negative, got {self.accumulated_cost}")

    @property
    def total_attempted_steps(self) -> int:
        """Total steps attempted (completed + failed)."""
        return self.completed_steps + self.failed_steps

    @property
    def success_rate(self) -> float:
        """Success rate of executed steps (0.0 to 1.0).

        Returns:
            Fraction of attempted steps that succeeded, or 0.0 if no steps attempted.
        """
        total = self.total_attempted_steps
        if total == 0:
            return 0.0
        return self.completed_steps / total

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for logging/serialization.

        Returns:
            Dictionary representation of metrics.
        """
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "workflow_id": self.workflow_id,
            "plan_id": self.plan_id,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "total_attempted_steps": self.total_attempted_steps,
            "success_rate": self.success_rate,
            "total_retries": self.total_retries,
            "accumulated_cost": self.accumulated_cost,
            "elapsed_seconds": self.elapsed_seconds,
            "succeeded": self.succeeded,
            "guard_violation": self.guard_violation,
        }


class MetricsCollector:
    """Collects and aggregates execution metrics.

    Tracks step execution, cost accumulation, and timing across an execution run.
    """

    def __init__(self, run_id: str, task_id: str = "", workflow_id: str = "", plan_id: str = "") -> None:
        """Initialize metrics collector for a run.

        Args:
            run_id: Unique run identifier.
            task_id: Task being executed (optional).
            workflow_id: Workflow state machine ID (optional).
            plan_id: Plan being executed (optional).
        """
        self.metrics = ExecutionMetrics(
            run_id=run_id,
            task_id=task_id,
            workflow_id=workflow_id,
            plan_id=plan_id,
        )
        self._start_time: float | None = None
        self._end_time: float | None = None

    def set_plan_size(self, total_steps: int) -> None:
        """Set the total number of steps in the plan.

        Args:
            total_steps: Number of steps in the plan.
        """
        self.metrics.total_steps = total_steps

    def record_step_completion(self) -> None:
        """Record a step that completed successfully."""
        self.metrics.completed_steps += 1

    def record_step_failure(self) -> None:
        """Record a step that failed."""
        self.metrics.failed_steps += 1

    def record_step_skip(self) -> None:
        """Record a step that was skipped."""
        self.metrics.skipped_steps += 1

    def record_retry(self) -> None:
        """Record a retry attempt."""
        self.metrics.total_retries += 1

    def add_cost(self, cost: float) -> None:
        """Add to accumulated cost.

        Args:
            cost: Cost to add (must be >= 0).

        Raises:
            ValueError: If cost is negative.
        """
        if cost < 0:
            raise ValueError(
                f"cost must be non-negative, got {cost}. "
                f"Step costs accumulate—ensure each step's cost value is >= 0.0"
            )
        self.metrics.accumulated_cost += cost

    def set_start_time(self, timestamp: float) -> None:
        """Set execution start time.

        Args:
            timestamp: Start timestamp (e.g., from time.monotonic()).
        """
        self._start_time = timestamp

    def set_end_time(self, timestamp: float) -> None:
        """Set execution end time and compute elapsed seconds.

        Args:
            timestamp: End timestamp (e.g., from time.monotonic()).
        """
        self._end_time = timestamp
        if self._start_time is not None:
            self.metrics.elapsed_seconds = timestamp - self._start_time

    def set_succeeded(self, succeeded: bool) -> None:
        """Mark the execution as succeeded or failed.

        Args:
            succeeded: True if execution succeeded.
        """
        self.metrics.succeeded = succeeded

    def set_guard_violation(self, violation_type: str | None) -> None:
        """Record a guard violation that halted execution.

        Args:
            violation_type: Type of violation (COST, TTL, RETRIES, PLAN_DEPTH), or None.
        """
        self.metrics.guard_violation = violation_type

    def get_metrics(self) -> ExecutionMetrics:
        """Get the collected metrics.

        Returns:
            ExecutionMetrics snapshot.
        """
        return self.metrics
