"""Tests for observability metrics collection."""

import pytest

from mas.observability.metrics import ExecutionMetrics, MetricsCollector


class TestExecutionMetrics:
    """Tests for ExecutionMetrics dataclass."""

    def test_metrics_creation(self) -> None:
        """Can create metrics with required fields."""
        metrics = ExecutionMetrics(run_id="abc12345", task_id="task-1", workflow_id="wf-1", plan_id="plan-1")

        assert metrics.run_id == "abc12345"
        assert metrics.task_id == "task-1"
        assert metrics.workflow_id == "wf-1"
        assert metrics.plan_id == "plan-1"

    def test_metrics_validation_empty_run_id(self) -> None:
        """Metrics creation fails with empty run_id."""
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            ExecutionMetrics(run_id="", task_id="task-1", workflow_id="", plan_id="")

    def test_metrics_validation_negative_elapsed(self) -> None:
        """Metrics creation fails with negative elapsed_seconds."""
        with pytest.raises(ValueError, match="elapsed_seconds cannot be negative"):
            ExecutionMetrics(
                run_id="abc12345",
                task_id="task-1",
                workflow_id="",
                plan_id="",
                elapsed_seconds=-1.0,
            )

    def test_metrics_validation_negative_cost(self) -> None:
        """Metrics creation fails with negative accumulated_cost."""
        with pytest.raises(ValueError, match="accumulated_cost cannot be negative"):
            ExecutionMetrics(
                run_id="abc12345",
                task_id="task-1",
                workflow_id="",
                plan_id="",
                accumulated_cost=-1.0,
            )

    def test_total_attempted_steps(self) -> None:
        """total_attempted_steps is completed + failed."""
        metrics = ExecutionMetrics(
            run_id="abc",
            task_id="task",
            workflow_id="",
            plan_id="",
            completed_steps=5,
            failed_steps=2,
            skipped_steps=3,
        )

        assert metrics.total_attempted_steps == 7

    def test_success_rate_with_no_attempts(self) -> None:
        """success_rate is 0.0 when no steps attempted."""
        metrics = ExecutionMetrics(run_id="abc", task_id="task", workflow_id="", plan_id="")

        assert metrics.success_rate == 0.0

    def test_success_rate_with_attempts(self) -> None:
        """success_rate is completed / (completed + failed)."""
        metrics = ExecutionMetrics(
            run_id="abc",
            task_id="task",
            workflow_id="",
            plan_id="",
            completed_steps=8,
            failed_steps=2,
        )

        assert metrics.success_rate == 0.8

    def test_metrics_to_dict(self) -> None:
        """to_dict() includes all metrics fields."""
        metrics = ExecutionMetrics(
            run_id="abc",
            task_id="task-1",
            workflow_id="wf-1",
            plan_id="plan-1",
            completed_steps=5,
            accumulated_cost=25.5,
            succeeded=True,
        )

        data = metrics.to_dict()

        assert data["run_id"] == "abc"
        assert data["task_id"] == "task-1"
        assert data["completed_steps"] == 5
        assert data["accumulated_cost"] == 25.5
        assert data["success_rate"] == 1.0
        assert data["succeeded"] is True


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_collector_initialization(self) -> None:
        """Can create metrics collector."""
        collector = MetricsCollector("run-1", task_id="task-1", workflow_id="wf-1", plan_id="plan-1")

        metrics = collector.get_metrics()
        assert metrics.run_id == "run-1"
        assert metrics.task_id == "task-1"
        assert metrics.workflow_id == "wf-1"
        assert metrics.plan_id == "plan-1"

    def test_collector_set_plan_size(self) -> None:
        """set_plan_size() sets total_steps."""
        collector = MetricsCollector("run-1", task_id="task-1", workflow_id="", plan_id="")
        collector.set_plan_size(10)

        assert collector.get_metrics().total_steps == 10

    def test_collector_record_completions(self) -> None:
        """record_step_completion() increments completed_steps."""
        collector = MetricsCollector("run-1", task_id="task-1", workflow_id="", plan_id="")

        collector.record_step_completion()
        collector.record_step_completion()

        assert collector.get_metrics().completed_steps == 2

    def test_collector_record_failures(self) -> None:
        """record_step_failure() increments failed_steps."""
        collector = MetricsCollector("run-1", task_id="task-1", workflow_id="", plan_id="")

        collector.record_step_failure()
        collector.record_step_failure()

        assert collector.get_metrics().failed_steps == 2

    def test_collector_record_skips(self) -> None:
        """record_step_skip() increments skipped_steps."""
        collector = MetricsCollector("run-1", task_id="task-1", workflow_id="", plan_id="")

        collector.record_step_skip()
        collector.record_step_skip()
        collector.record_step_skip()

        assert collector.get_metrics().skipped_steps == 3

    def test_collector_record_retries(self) -> None:
        """record_retry() increments total_retries."""
        collector = MetricsCollector("run-1", task_id="task-1", workflow_id="", plan_id="")

        collector.record_retry()
        collector.record_retry()

        assert collector.get_metrics().total_retries == 2

    def test_collector_add_cost(self) -> None:
        """add_cost() accumulates cost."""
        collector = MetricsCollector("run-1", task_id="task-1", workflow_id="", plan_id="")

        collector.add_cost(10.0)
        collector.add_cost(5.5)

        assert collector.get_metrics().accumulated_cost == 15.5

    def test_collector_add_cost_negative_rejected(self) -> None:
        """add_cost() rejects negative values."""
        collector = MetricsCollector("run-1", task_id="task-1", workflow_id="", plan_id="")

        with pytest.raises(ValueError, match="cost must be non-negative"):
            collector.add_cost(-1.0)

    def test_collector_set_timing(self) -> None:
        """set_start_time() and set_end_time() compute elapsed_seconds."""
        collector = MetricsCollector("run-1", task_id="task-1", workflow_id="", plan_id="")

        collector.set_start_time(100.0)
        collector.set_end_time(105.5)

        assert collector.get_metrics().elapsed_seconds == 5.5

    def test_collector_set_succeeded(self) -> None:
        """set_succeeded() marks execution outcome."""
        collector = MetricsCollector("run-1", task_id="task-1", workflow_id="", plan_id="")

        collector.set_succeeded(True)

        assert collector.get_metrics().succeeded is True

    def test_collector_set_guard_violation(self) -> None:
        """set_guard_violation() records violation type."""
        collector = MetricsCollector("run-1", task_id="task-1", workflow_id="", plan_id="")

        collector.set_guard_violation("COST")

        assert collector.get_metrics().guard_violation == "COST"

    def test_collector_integration(self) -> None:
        """Metrics collector tracks complete execution."""
        collector = MetricsCollector("run-1", task_id="task-1", workflow_id="wf-1", plan_id="plan-1")

        collector.set_plan_size(5)
        collector.set_start_time(0.0)

        # Execute some steps
        collector.record_step_completion()
        collector.add_cost(10.0)
        collector.record_step_completion()
        collector.add_cost(5.0)
        collector.record_step_failure()
        collector.record_step_skip()
        collector.record_retry()

        collector.set_end_time(10.0)
        collector.set_succeeded(False)

        metrics = collector.get_metrics()

        assert metrics.total_steps == 5
        assert metrics.completed_steps == 2
        assert metrics.failed_steps == 1
        assert metrics.skipped_steps == 1
        assert metrics.total_retries == 1
        assert metrics.accumulated_cost == 15.0
        assert metrics.elapsed_seconds == 10.0
        assert metrics.succeeded is False
        assert metrics.success_rate == 2 / 3

    def test_collector_zero_elapsed_time(self) -> None:
        """Metrics handles zero elapsed time (instant execution)."""
        collector = MetricsCollector("run-1", task_id="task-1", workflow_id="", plan_id="")

        collector.set_start_time(5.0)
        collector.set_end_time(5.0)

        assert collector.get_metrics().elapsed_seconds == 0.0

    def test_collector_multiple_retries_same_step(self) -> None:
        """Metrics accumulates multiple retry attempts correctly."""
        collector = MetricsCollector("run-1", task_id="task-1", workflow_id="", plan_id="")

        for _ in range(5):
            collector.record_retry()

        assert collector.get_metrics().total_retries == 5

    def test_collector_large_cost_accumulation(self) -> None:
        """Metrics handles large cost values without precision loss."""
        collector = MetricsCollector("run-1", task_id="task-1", workflow_id="", plan_id="")

        costs = [1000.5, 2000.75, 3000.25, 4000.0]
        for cost in costs:
            collector.add_cost(cost)

        assert collector.get_metrics().accumulated_cost == sum(costs)
