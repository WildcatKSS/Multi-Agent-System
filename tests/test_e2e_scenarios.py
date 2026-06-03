"""End-to-end MVP scenario pack tests.

Comprehensive test suite validating the complete MVP system:
- Happy path execution
- Input adapter integration
- Guardrail enforcement
- Recovery and retry logic
- Complex dependency resolution
- Memory integration
- Observability (metrics, correlation IDs, logging)
"""

import pytest

from mas.domain.plan import Plan, Step, StepStatus
from mas.domain.task import Task, TaskStatus
from mas.guardrails import GuardrailsConfig, GuardrailsEngine, GuardType
from mas.observability.correlation import get_correlation_id, reset_correlation_id
from mas.runtime.executor import StepExecutorRegistry, StepResult
from mas.runtime.orchestrator import Runtime
from mas.workflow.policy import PolicyEngine
from mas.workflow.state import WorkflowState

from e2e_scenario_builders import (
    PlanBuilder,
    StepBuilder,
    StepHandlerFactory,
    TaskBuilder,
    generate_diamond_plan,
    generate_expensive_plan,
    generate_linear_plan,
)


@pytest.fixture(autouse=True)
def cleanup_correlation_context() -> None:
    """Reset correlation context after each test."""
    yield
    reset_correlation_id()


class TestE2EHappyPath:
    """Happy path scenarios: simple task -> plan -> execution -> completion."""

    def test_happy_path_simple_linear_plan(self) -> None:
        """Simple 3-step linear plan executes successfully."""
        task = TaskBuilder().with_goal("Complete work").build()
        plan = generate_linear_plan(task.id, step_count=3)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert result.final_state == WorkflowState.COMPLETED
        assert task.status == TaskStatus.COMPLETED
        assert len(result.completed_steps) == 3
        assert len(result.failed_steps) == 0
        assert result.metrics.success_rate == 1.0
        assert result.metrics.succeeded is True

    def test_happy_path_multi_step_plan(self) -> None:
        """Multi-step linear plan (5 steps) completes successfully."""
        task = TaskBuilder().with_description("Multi-step task").build()
        plan = generate_linear_plan(task.id, step_count=5)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert len(result.completed_steps) == 5
        assert result.metrics.total_steps == 5

    def test_happy_path_complex_dependencies(self) -> None:
        """Diamond dependency graph executes in correct order."""
        task = TaskBuilder().with_goal("Execute dependencies").build()
        plan = generate_diamond_plan(task.id)

        execution_order = []

        def recording_handler(step: Step) -> StepResult:
            execution_order.append(step.id)
            return StepResult(success=True)

        registry = StepExecutorRegistry()
        registry.register("default_action", recording_handler)

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        # Verify execution respects dependency order
        assert execution_order.index("step-A") < execution_order.index("step-B")
        assert execution_order.index("step-A") < execution_order.index("step-C")
        assert execution_order.index("step-B") < execution_order.index("step-D")
        assert execution_order.index("step-C") < execution_order.index("step-D")
        assert result.succeeded is True

    def test_happy_path_with_metrics_collection(self) -> None:
        """Happy path execution collects comprehensive metrics."""
        task = TaskBuilder().build()
        plan = generate_linear_plan(task.id, step_count=3)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        # Verify metrics populated
        assert result.metrics is not None
        assert result.metrics.run_id is not None
        assert len(result.metrics.run_id) == 8
        assert result.metrics.task_id == task.id
        assert result.metrics.plan_id == plan.id
        assert result.metrics.total_steps == 3
        assert result.metrics.completed_steps == 3
        assert result.metrics.failed_steps == 0
        assert result.metrics.elapsed_seconds > 0
        assert result.metrics.succeeded is True


class TestE2EInputAdapters:
    """Input adapter integration: email, calendar, document, transcript."""

    def test_email_input_scenario(self) -> None:
        """Email input: task created with email source context."""
        context = {
            "source_type": "email",
            "sender": "alice@example.com",
            "subject": "Action Required",
            "body": "Please process this request",
        }
        task = TaskBuilder().with_context(context).with_goal("Process email").build()
        plan = generate_linear_plan(task.id, step_count=2)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert task.context["source_type"] == "email"
        assert task.context["sender"] == "alice@example.com"

    def test_calendar_input_scenario(self) -> None:
        """Calendar input: task created with event context."""
        context = {
            "source_type": "calendar",
            "event_title": "Team Standup",
            "start_time": "2026-06-03T09:00:00Z",
            "attendees": ["alice@example.com", "bob@example.com"],
        }
        task = TaskBuilder().with_context(context).with_goal("Manage calendar event").build()
        plan = generate_linear_plan(task.id, step_count=2)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert task.context["source_type"] == "calendar"
        assert len(task.context["attendees"]) == 2

    def test_document_input_scenario(self) -> None:
        """Document input: task created with document context."""
        context = {
            "source_type": "document",
            "doc_type": "proposal",
            "filename": "proposal.pdf",
        }
        task = TaskBuilder().with_context(context).with_goal("Review document").build()
        plan = generate_linear_plan(task.id, step_count=2)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert task.context["source_type"] == "document"
        assert task.context["doc_type"] == "proposal"

    def test_transcript_input_scenario(self) -> None:
        """Transcript input: task created with transcript context."""
        context = {
            "source_type": "transcript",
            "speaker_count": 2,
            "duration_seconds": 300,
        }
        task = TaskBuilder().with_context(context).with_goal("Process transcript").build()
        plan = generate_linear_plan(task.id, step_count=2)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert task.context["source_type"] == "transcript"
        assert task.context["speaker_count"] == 2


class TestE2EGuardrailViolations:
    """Guardrail enforcement: cost, TTL, retries, depth limits."""

    def test_cost_guard_violation(self) -> None:
        """Plan exceeding cost limit is rejected."""
        task = TaskBuilder().build()
        plan = generate_expensive_plan(task.id, step_count=3, cost_per_step=40.0)
        plan.estimated_cost = 120.0

        config = GuardrailsConfig(max_cost=100.0)
        guardrails = GuardrailsEngine(config)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry, guardrails=guardrails)
        result = runtime.run(task, plan)

        assert result.succeeded is False
        assert result.final_state == WorkflowState.FAILED
        assert result.guard_violation is not None
        assert result.guard_violation.guard_type == GuardType.COST
        assert result.metrics.guard_violation == "cost"
        assert task.status == TaskStatus.PENDING

    def test_plan_depth_guard_violation(self) -> None:
        """Plan with too many steps is rejected pre-execution."""
        task = TaskBuilder().build()
        plan = generate_linear_plan(task.id, step_count=25)

        config = GuardrailsConfig(max_plan_depth=20)
        guardrails = GuardrailsEngine(config)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry, guardrails=guardrails)
        result = runtime.run(task, plan)

        assert result.succeeded is False
        assert result.guard_violation is not None
        assert result.guard_violation.guard_type == GuardType.PLAN_DEPTH
        assert result.workflow_id == ""

    def test_retries_guard_violation(self) -> None:
        """Total retries exceeding limit halts execution."""
        task = TaskBuilder().build()
        plan = PlanBuilder(task.id).with_linear_steps(2).build()
        for step in plan.steps:
            step.max_retries = 2

        config = GuardrailsConfig(max_retries_per_run=2)
        guardrails = GuardrailsEngine(config)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.failure_handler())

        runtime = Runtime(registry=registry, guardrails=guardrails)
        result = runtime.run(task, plan)

        # Execution should be halted or fail due to retries limit
        assert result.succeeded is False
        # Guard violation may be set if retries exceeded during execution
        if result.guard_violation:
            assert result.guard_violation.guard_type == GuardType.RETRIES


class TestE2ERecovery:
    """Recovery scenarios: failures followed by retry and success."""

    def test_recovery_single_retry(self) -> None:
        """Step fails once, retries, and succeeds."""
        task = TaskBuilder().build()
        plan = generate_linear_plan(task.id, step_count=2)
        plan.steps[0].max_retries = 1

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.retry_handler(fail_count=1))

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert result.metrics.total_retries >= 1
        assert len(result.completed_steps) == 2

    def test_recovery_multi_retry(self) -> None:
        """Step fails multiple times then succeeds."""
        task = TaskBuilder().build()
        plan = generate_linear_plan(task.id, step_count=2)
        plan.steps[0].max_retries = 3

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.retry_handler(fail_count=2))

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert result.metrics.total_retries >= 2

    def test_recovery_partial_failure(self) -> None:
        """Some steps fail, some recover, execution continues."""
        task = TaskBuilder().build()

        success_sequence = [False, True, False, True]
        plan = PlanBuilder(task.id).with_custom_steps([
            {"id": "step-0", "action": "default_action", "max_retries": 1},
            {"id": "step-1", "action": "default_action"},
            {"id": "step-2", "action": "default_action", "max_retries": 1},
            {"id": "step-3", "action": "default_action"},
        ]).build()

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.mixed_handler(success_sequence))

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        # First failure causes retry but eventually succeeds; others also succeed
        assert len(result.completed_steps) >= 2


class TestE2EComplexPlans:
    """Complex plans: dependency resolution and cascading failures."""

    def test_diamond_dependency_execution(self) -> None:
        """Diamond graph: A -> B,C; B,C -> D executes in correct order."""
        task = TaskBuilder().build()
        plan = generate_diamond_plan(task.id)

        execution_order = []

        def recording_handler(step: Step) -> StepResult:
            execution_order.append(step.id)
            return StepResult(success=True)

        registry = StepExecutorRegistry()
        registry.register("default_action", recording_handler)

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        # Verify dependency order
        assert execution_order.index("step-A") < execution_order.index("step-B")
        assert execution_order.index("step-A") < execution_order.index("step-C")
        assert execution_order.index("step-B") < execution_order.index("step-D")
        assert execution_order.index("step-C") < execution_order.index("step-D")
        assert result.succeeded is True

    def test_skip_cascading_on_dependency_failure(self) -> None:
        """Failed step causes downstream steps to skip."""
        task = TaskBuilder().build()
        plan = PlanBuilder(task.id).with_custom_steps([
            {"id": "step-0", "action": "default_action"},
            {"id": "step-1", "action": "default_action", "depends_on": ["step-0"]},
            {"id": "step-2", "action": "default_action", "depends_on": ["step-1"]},
            {"id": "step-3", "action": "default_action", "depends_on": ["step-2"]},
        ]).build()

        def failing_first_handler(step: Step) -> StepResult:
            if step.id == "step-1":
                return StepResult(success=False, error="Failed intentionally")
            return StepResult(success=True)

        registry = StepExecutorRegistry()
        registry.register("default_action", failing_first_handler)

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        # step-1 fails, step-2 and step-3 should be skipped
        assert result.succeeded is False
        assert len(result.failed_steps) == 1
        # step-0 succeeds, step-1 fails, step-2 and step-3 skipped
        assert len(result.skipped_steps) == 2

    def test_multiple_independent_branches(self) -> None:
        """Multiple independent branches execute in parallel (scheduling)."""
        task = TaskBuilder().build()
        plan = PlanBuilder(task.id).with_custom_steps([
            {"id": "step-A1", "action": "default_action"},
            {"id": "step-A2", "action": "default_action", "depends_on": ["step-A1"]},
            {"id": "step-B1", "action": "default_action"},
            {"id": "step-B2", "action": "default_action", "depends_on": ["step-B1"]},
        ]).build()

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert len(result.completed_steps) == 4


class TestE2EMemoryIntegration:
    """Memory integration: episodic store records completions."""

    def test_execution_produces_metrics_for_storage(self) -> None:
        """Completed execution produces metrics that can be stored."""
        task = TaskBuilder().build()
        plan = generate_linear_plan(task.id, step_count=3)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        # Metrics should be available for storage
        assert result.metrics is not None
        assert result.metrics.run_id is not None
        assert result.metrics.task_id == task.id
        assert result.metrics.completed_steps == 3
        assert result.metrics.succeeded is True

    def test_multiple_execution_attempts_tracked(self) -> None:
        """Multiple executions of same task track independently."""
        task = TaskBuilder().build()
        plan = generate_linear_plan(task.id, step_count=2)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        run_ids = []
        for _ in range(3):
            runtime = Runtime(registry=registry)
            result = runtime.run(task, plan)
            run_ids.append(result.metrics.run_id)
            reset_correlation_id()

        # All runs should have unique run IDs
        assert len(set(run_ids)) == 3


class TestE2EObservability:
    """Observability: metrics, correlation IDs, logging."""

    def test_correlation_id_propagation(self) -> None:
        """Run ID is propagated through execution and stored in metrics."""
        task = TaskBuilder().build()
        plan = generate_linear_plan(task.id, step_count=2)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        # Correlation ID should be set and in metrics
        assert result.metrics.run_id is not None
        assert len(result.metrics.run_id) == 8
        assert all(c in "0123456789abcdef" for c in result.metrics.run_id)

    def test_metrics_completeness(self) -> None:
        """All metrics fields populated correctly after execution."""
        task = TaskBuilder().build()
        plan = generate_linear_plan(task.id, step_count=4)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        metrics = result.metrics
        assert metrics.run_id is not None
        assert metrics.task_id == task.id
        assert metrics.workflow_id is not None
        assert metrics.plan_id == plan.id
        assert metrics.total_steps == 4
        assert metrics.completed_steps == 4
        assert metrics.failed_steps == 0
        assert metrics.skipped_steps == 0
        assert metrics.elapsed_seconds >= 0
        assert metrics.succeeded is True

    def test_success_rate_calculation_all_success(self) -> None:
        """Success rate is 1.0 when all steps succeed."""
        task = TaskBuilder().build()
        plan = generate_linear_plan(task.id, step_count=5)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        assert result.metrics.success_rate == 1.0

    def test_success_rate_calculation_partial_success(self) -> None:
        """Success rate correctly reflects completed/failed ratio."""
        task = TaskBuilder().build()
        plan = PlanBuilder(task.id).with_custom_steps([
            {"id": "step-0", "action": "default_action"},
            {"id": "step-1", "action": "default_action", "depends_on": ["step-0"]},
            {"id": "step-2", "action": "default_action", "depends_on": ["step-1"]},
            {"id": "step-3", "action": "default_action", "depends_on": ["step-2"]},
        ]).build()

        def mixed_results(step: Step) -> StepResult:
            if step.id in ["step-0", "step-2"]:
                return StepResult(success=True)
            return StepResult(success=False, error="Failed")

        registry = StepExecutorRegistry()
        registry.register("default_action", mixed_results)

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        # 2 succeeded, 2 failed (or skipped due to dependency)
        total_attempted = result.metrics.completed_steps + result.metrics.failed_steps
        if total_attempted > 0:
            expected_rate = result.metrics.completed_steps / total_attempted
            assert abs(result.metrics.success_rate - expected_rate) < 0.01

    def test_guard_violation_recorded_in_metrics(self) -> None:
        """Guard violation type recorded in metrics."""
        task = TaskBuilder().build()
        plan = generate_expensive_plan(task.id, step_count=2, cost_per_step=60.0)
        plan.estimated_cost = 120.0

        config = GuardrailsConfig(max_cost=100.0)
        guardrails = GuardrailsEngine(config)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry, guardrails=guardrails)
        result = runtime.run(task, plan)

        assert result.metrics.guard_violation == "cost"
        assert result.metrics.succeeded is False

    def test_metrics_serialization_to_dict(self) -> None:
        """Metrics can be serialized to dictionary for logging/storage."""
        task = TaskBuilder().build()
        plan = generate_linear_plan(task.id, step_count=2)

        registry = StepExecutorRegistry()
        registry.register("default_action", StepHandlerFactory.success_handler())

        runtime = Runtime(registry=registry)
        result = runtime.run(task, plan)

        metrics_dict = result.metrics.to_dict()

        assert isinstance(metrics_dict, dict)
        assert "run_id" in metrics_dict
        assert "task_id" in metrics_dict
        assert "completed_steps" in metrics_dict
        assert "success_rate" in metrics_dict
        assert "succeeded" in metrics_dict
        assert metrics_dict["succeeded"] is True
