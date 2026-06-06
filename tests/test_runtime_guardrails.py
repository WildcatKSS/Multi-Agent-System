"""Tests for Runtime with guardrails enforcement."""


from mas.domain.plan import Plan, Step
from mas.domain.task import Task, TaskStatus
from mas.guardrails import GuardrailsConfig, GuardrailsEngine, GuardType
from mas.runtime.executor import StepExecutorRegistry, StepResult
from mas.runtime.orchestrator import Runtime
from mas.workflow.policy import PolicyEngine


def _task(task_id: str = "task-1") -> Task:
    return Task(id=task_id, description="test", goal="test")


def _step(step_id: str = "step-1", cost: float = 1.0, action: str = "test") -> Step:
    return Step(
        id=step_id,
        action=action,
        inputs={},
        depends_on=[],
        metadata={"cost": cost},
        max_retries=0,
    )


def _plan(task_id: str = "task-1", steps: list[Step] | None = None) -> Plan:
    if steps is None:
        steps = [_step()]
    return Plan(
        id="plan-1",
        task_id=task_id,
        steps=steps,
        estimated_cost=sum(s.metadata.get("cost", 1.0) for s in steps),
        estimated_time_seconds=10.0,
        reasoning="test",
    )


class TestRuntimeGuardrailsDisabled:
    """Verify runtime behaves identically when guardrails are disabled."""

    def test_run_without_guardrails(self) -> None:
        """Runtime with guardrails=None executes normally."""
        task = _task()
        plan = _plan()

        registry = StepExecutorRegistry()
        registry.register("test", lambda s: StepResult(success=True))

        runtime = Runtime(
            policy=PolicyEngine(),
            registry=registry,
            guardrails=None,  # explicitly disabled
        )
        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert result.guard_violation is None


class TestRuntimeGuardrailsPlanDepth:
    """Verify plan depth validation before execution."""

    def test_plan_depth_within_limit(self) -> None:
        """Plan with steps <= max_plan_depth executes normally."""
        config = GuardrailsConfig(max_plan_depth=5)
        engine = GuardrailsEngine(config)
        task = _task()
        plan = _plan(steps=[_step(f"step-{i}") for i in range(3)])

        registry = StepExecutorRegistry()
        registry.register("test", lambda s: StepResult(success=True))

        runtime = Runtime(registry=registry, guardrails=engine)
        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert result.guard_violation is None

    def test_plan_depth_exceeds_limit(self) -> None:
        """Plan with steps > max_plan_depth fails before workflow registration."""
        config = GuardrailsConfig(max_plan_depth=3)
        engine = GuardrailsEngine(config)
        task = _task()
        plan = _plan(steps=[_step(f"step-{i}") for i in range(5)])

        registry = StepExecutorRegistry()
        registry.register("test", lambda s: StepResult(success=True))

        runtime = Runtime(registry=registry, guardrails=engine)
        result = runtime.run(task, plan)

        assert result.succeeded is False
        assert result.guard_violation is not None
        assert result.guard_violation.guard_type == GuardType.PLAN_DEPTH
        assert result.workflow_id == ""  # no workflow registered
        assert task.status == TaskStatus.PENDING  # task never started


class TestRuntimeGuardrailsCost:
    """Verify accumulated cost tracking and enforcement."""

    def test_cost_within_limit(self) -> None:
        """Plan accumulates cost; stays within limit."""
        config = GuardrailsConfig(max_cost=10.0)
        engine = GuardrailsEngine(config)
        task = _task()
        plan = _plan(steps=[_step(f"step-{i}", cost=2.0) for i in range(3)])

        registry = StepExecutorRegistry()
        registry.register("test", lambda s: StepResult(success=True))

        runtime = Runtime(registry=registry, guardrails=engine)
        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert result.guard_violation is None

    def test_cost_estimated_exceeds_limit_rejected_pre_run(self) -> None:
        """Plan with estimated_cost > max_cost is rejected before execution."""
        config = GuardrailsConfig(max_cost=5.0)
        engine = GuardrailsEngine(config)
        task = _task()
        # Two steps: 3.0 cost + 3.0 cost = 6.0 estimated total > 5.0 limit.
        steps = [_step(f"step-{i}", cost=3.0) for i in range(2)]
        plan = Plan(
            id="plan-1",
            task_id="task-1",
            steps=steps,
            estimated_cost=6.0,
            estimated_time_seconds=10.0,
            reasoning="test",
        )

        registry = StepExecutorRegistry()
        registry.register("test", lambda s: StepResult(success=True))

        runtime = Runtime(registry=registry, guardrails=engine)
        result = runtime.run(task, plan)

        assert result.succeeded is False
        assert result.guard_violation is not None
        assert result.guard_violation.guard_type == GuardType.COST
        assert result.workflow_id == ""  # no workflow registered

    def test_cost_default_per_step(self) -> None:
        """Steps default to cost=1.0 if not specified in metadata."""
        config = GuardrailsConfig(max_cost=5.0)
        engine = GuardrailsEngine(config)
        task = _task()
        # Three steps with no explicit cost -> 1.0 each = 3.0 total.
        steps = [Step(id=f"step-{i}", action="test", inputs={}, depends_on=[]) for i in range(3)]
        plan = _plan(steps=steps)

        registry = StepExecutorRegistry()
        registry.register("test", lambda s: StepResult(success=True))

        runtime = Runtime(registry=registry, guardrails=engine)
        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert result.guard_violation is None


class TestRuntimeGuardrailsTTL:
    """Verify elapsed time tracking and enforcement."""

    def test_ttl_within_limit(self) -> None:
        """Plan completes within TTL."""
        config = GuardrailsConfig(max_duration_seconds=10.0)
        engine = GuardrailsEngine(config)
        task = _task()
        plan = _plan()

        registry = StepExecutorRegistry()
        registry.register("test", lambda s: StepResult(success=True))

        runtime = Runtime(registry=registry, guardrails=engine)
        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert result.guard_violation is None


class TestRuntimeGuardrailsRetries:
    """Verify total retry tracking and enforcement."""

    def test_retries_within_limit(self) -> None:
        """Total retries stay within limit."""
        config = GuardrailsConfig(max_retries_per_run=5)
        engine = GuardrailsEngine(config)
        task = _task()
        # One step that retries once.
        plan = _plan(steps=[_step("step-0", action="flaky")])
        plan.steps[0].max_retries = 1

        registry = StepExecutorRegistry()

        call_count = 0

        def flaky_handler(s: Step) -> StepResult:
            nonlocal call_count
            call_count += 1
            # Fail on first call, succeed on retry.
            if call_count == 1:
                return StepResult(success=False, error="fail once")
            return StepResult(success=True)

        registry.register("flaky", flaky_handler)

        runtime = Runtime(registry=registry, guardrails=engine)
        result = runtime.run(task, plan)

        assert result.succeeded is True
        assert result.guard_violation is None

    def test_retries_exceed_limit(self) -> None:
        """Total retries exceeding limit halts execution."""
        config = GuardrailsConfig(max_retries_per_run=2)
        engine = GuardrailsEngine(config)
        task = _task()
        # Three steps that each retry twice = 6 total retries > 2 limit.
        plan = _plan(steps=[_step(f"step-{i}", action="flaky") for i in range(3)])
        for step in plan.steps:
            step.max_retries = 2

        registry = StepExecutorRegistry()
        # Always fail.
        registry.register("flaky", lambda s: StepResult(success=False, error="always fails"))

        runtime = Runtime(registry=registry, guardrails=engine)
        result = runtime.run(task, plan)

        assert result.succeeded is False
        assert result.guard_violation is not None
        assert result.guard_violation.guard_type == GuardType.RETRIES


class TestRuntimeCostValidation:
    """Verify runtime validates step cost metadata."""

    def test_reject_infinity_cost(self) -> None:
        """Step with infinite cost is rejected at runtime."""
        import pytest

        task = _task()
        step = Step(id="step-0", action="test", inputs={}, depends_on=[], metadata={"cost": float('inf')})
        plan = Plan(
            id="plan-1",
            task_id="task-1",
            steps=[step],
            estimated_cost=1.0,
            estimated_time_seconds=10.0,
            reasoning="test",
        )

        registry = StepExecutorRegistry()
        registry.register("test", lambda s: StepResult(success=True))

        runtime = Runtime(registry=registry)
        with pytest.raises(ValueError, match="must be finite"):
            runtime.run(task, plan)

    def test_reject_nan_cost(self) -> None:
        """Step with NaN cost is rejected at runtime."""
        import pytest

        task = _task()
        step = Step(id="step-0", action="test", inputs={}, depends_on=[], metadata={"cost": float('nan')})
        plan = Plan(
            id="plan-1",
            task_id="task-1",
            steps=[step],
            estimated_cost=1.0,
            estimated_time_seconds=10.0,
            reasoning="test",
        )

        registry = StepExecutorRegistry()
        registry.register("test", lambda s: StepResult(success=True))

        runtime = Runtime(registry=registry)
        with pytest.raises(ValueError, match="must be finite"):
            runtime.run(task, plan)

    def test_reject_negative_cost(self) -> None:
        """Step with negative cost is rejected at runtime."""
        import pytest

        task = _task()
        step = Step(id="step-0", action="test", inputs={}, depends_on=[], metadata={"cost": -5.0})
        plan = Plan(
            id="plan-1",
            task_id="task-1",
            steps=[step],
            estimated_cost=1.0,
            estimated_time_seconds=10.0,
            reasoning="test",
        )

        registry = StepExecutorRegistry()
        registry.register("test", lambda s: StepResult(success=True))

        runtime = Runtime(registry=registry)
        with pytest.raises(ValueError, match="must be non-negative"):
            runtime.run(task, plan)

    def test_reject_non_numeric_cost(self) -> None:
        """Step with non-numeric cost is rejected at runtime."""
        import pytest

        task = _task()
        step = Step(id="step-0", action="test", inputs={}, depends_on=[], metadata={"cost": "not a number"})
        plan = Plan(
            id="plan-1",
            task_id="task-1",
            steps=[step],
            estimated_cost=1.0,
            estimated_time_seconds=10.0,
            reasoning="test",
        )

        registry = StepExecutorRegistry()
        registry.register("test", lambda s: StepResult(success=True))

        runtime = Runtime(registry=registry)
        with pytest.raises(ValueError, match="must be numeric"):
            runtime.run(task, plan)


class TestRuntimeGuardrailsInteraction:
    """Verify guardrails interact correctly with runtime."""

    def test_violation_reason_in_transition(self) -> None:
        """Guard violation is recorded in workflow transition reason."""
        config = GuardrailsConfig(max_plan_depth=1)
        engine = GuardrailsEngine(config)
        task = _task()
        plan = _plan(steps=[_step(f"step-{i}") for i in range(2)])

        runtime = Runtime(guardrails=engine)
        result = runtime.run(task, plan)

        assert result.succeeded is False
        assert result.guard_violation is not None
        # Workflow reason should reference the guard type.
        assert "guardrail_violated" in result.final_state.value or result.final_state.value == "failed"

    def test_unresolved_steps_skipped_on_violation(self) -> None:
        """Unresolved steps are marked SKIPPED when guardrail is violated at plan level."""
        config = GuardrailsConfig(max_plan_depth=1)
        engine = GuardrailsEngine(config)
        task = _task()
        plan = _plan(steps=[_step(f"step-{i}") for i in range(2)])

        registry = StepExecutorRegistry()
        registry.register("test", lambda s: StepResult(success=True))

        runtime = Runtime(registry=registry, guardrails=engine)
        result = runtime.run(task, plan)

        assert result.succeeded is False
        assert result.guard_violation is not None
        assert result.guard_violation.guard_type == GuardType.PLAN_DEPTH
        assert task.status == TaskStatus.PENDING  # task never started
