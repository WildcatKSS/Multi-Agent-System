"""Tests for GuardrailsEngine."""

from mas.domain.plan import Plan, Step
from mas.domain.task import Task
from mas.guardrails import GuardrailsConfig, GuardrailsEngine, GuardType


def _task(task_id: str = "task-1") -> Task:
    return Task(id=task_id, description="test", goal="test")


def _step(step_id: str = "step-1", cost: float = 1.0) -> Step:
    return Step(id=step_id, action="test", inputs={}, depends_on=[], metadata={"cost": cost})


def _plan(task_id: str = "task-1", step_count: int = 3, total_cost: float = 3.0) -> Plan:
    steps = [_step(f"step-{i}", cost=total_cost / step_count) for i in range(step_count)]
    return Plan(
        id="plan-1",
        task_id=task_id,
        steps=steps,
        estimated_cost=total_cost,
        estimated_time_seconds=10.0,
        reasoning="test",
    )


class TestCheckPlanDepth:
    """Verify plan depth validation."""

    def test_plan_depth_within_limit(self) -> None:
        """Plan with steps <= max_plan_depth passes."""
        config = GuardrailsConfig(max_plan_depth=5)
        engine = GuardrailsEngine(config)
        plan = _plan(step_count=3)

        result = engine.check_plan(plan)

        assert result.passed is True
        assert result.violation is None

    def test_plan_depth_exactly_at_limit(self) -> None:
        """Plan with steps == max_plan_depth passes."""
        config = GuardrailsConfig(max_plan_depth=5)
        engine = GuardrailsEngine(config)
        plan = _plan(step_count=5)

        result = engine.check_plan(plan)

        assert result.passed is True
        assert result.violation is None

    def test_plan_depth_exceeds_limit(self) -> None:
        """Plan with steps > max_plan_depth fails."""
        config = GuardrailsConfig(max_plan_depth=5)
        engine = GuardrailsEngine(config)
        plan = _plan(step_count=6)

        result = engine.check_plan(plan)

        assert result.passed is False
        assert result.violation is not None
        assert result.violation.guard_type == GuardType.PLAN_DEPTH
        assert result.violation.actual == 6
        assert result.violation.limit == 5

    def test_plan_depth_violation_message(self) -> None:
        """Depth violation has clear message."""
        config = GuardrailsConfig(max_plan_depth=3)
        engine = GuardrailsEngine(config)
        plan = _plan(step_count=5)

        result = engine.check_plan(plan)

        assert "5" in result.violation.message
        assert "3" in result.violation.message


class TestCheckPlanCost:
    """Verify plan cost validation."""

    def test_plan_cost_within_limit(self) -> None:
        """Plan with estimated_cost <= max_cost passes."""
        config = GuardrailsConfig(max_cost=100.0)
        engine = GuardrailsEngine(config)
        plan = _plan(total_cost=50.0)

        result = engine.check_plan(plan)

        assert result.passed is True
        assert result.violation is None

    def test_plan_cost_exactly_at_limit(self) -> None:
        """Plan with estimated_cost == max_cost passes."""
        config = GuardrailsConfig(max_cost=100.0)
        engine = GuardrailsEngine(config)
        plan = _plan(total_cost=100.0)

        result = engine.check_plan(plan)

        assert result.passed is True
        assert result.violation is None

    def test_plan_cost_exceeds_limit(self) -> None:
        """Plan with estimated_cost > max_cost fails."""
        config = GuardrailsConfig(max_cost=50.0)
        engine = GuardrailsEngine(config)
        plan = _plan(total_cost=75.0)

        result = engine.check_plan(plan)

        assert result.passed is False
        assert result.violation is not None
        assert result.violation.guard_type == GuardType.COST
        assert result.violation.actual == 75.0
        assert result.violation.limit == 50.0

    def test_depth_checked_before_cost(self) -> None:
        """Depth violation is returned before cost violation."""
        config = GuardrailsConfig(max_plan_depth=2, max_cost=50.0)
        engine = GuardrailsEngine(config)
        # Plan with 5 steps (violates depth) and cost 100 (violates cost).
        plan = _plan(step_count=5, total_cost=100.0)

        result = engine.check_plan(plan)

        assert result.passed is False
        assert result.violation.guard_type == GuardType.PLAN_DEPTH


class TestCheckBudget:
    """Verify runtime budget checks."""

    def test_budget_within_all_limits(self) -> None:
        """Budget within cost, TTL, and retries passes."""
        config = GuardrailsConfig(max_cost=100.0, max_duration_seconds=300.0, max_retries_per_run=10)
        engine = GuardrailsEngine(config)

        result = engine.check_budget(accumulated_cost=50.0, elapsed_seconds=100.0, total_retries=3)

        assert result.passed is True
        assert result.violation is None

    def test_budget_cost_violation(self) -> None:
        """Accumulated cost exceeding limit fails."""
        config = GuardrailsConfig(max_cost=100.0)
        engine = GuardrailsEngine(config)

        result = engine.check_budget(accumulated_cost=101.0, elapsed_seconds=50.0, total_retries=0)

        assert result.passed is False
        assert result.violation.guard_type == GuardType.COST
        assert result.violation.actual == 101.0
        assert result.violation.limit == 100.0

    def test_budget_ttl_violation(self) -> None:
        """Elapsed time exceeding limit fails."""
        config = GuardrailsConfig(max_duration_seconds=300.0)
        engine = GuardrailsEngine(config)

        result = engine.check_budget(accumulated_cost=50.0, elapsed_seconds=301.0, total_retries=0)

        assert result.passed is False
        assert result.violation.guard_type == GuardType.TTL
        assert result.violation.actual == 301.0
        assert result.violation.limit == 300.0

    def test_budget_retries_violation(self) -> None:
        """Total retries exceeding limit fails."""
        config = GuardrailsConfig(max_retries_per_run=10)
        engine = GuardrailsEngine(config)

        result = engine.check_budget(accumulated_cost=50.0, elapsed_seconds=100.0, total_retries=11)

        assert result.passed is False
        assert result.violation.guard_type == GuardType.RETRIES
        assert result.violation.actual == 11
        assert result.violation.limit == 10

    def test_cost_checked_before_ttl(self) -> None:
        """Cost violation is returned before TTL violation."""
        config = GuardrailsConfig(max_cost=100.0, max_duration_seconds=300.0)
        engine = GuardrailsEngine(config)

        result = engine.check_budget(accumulated_cost=101.0, elapsed_seconds=301.0, total_retries=0)

        assert result.passed is False
        assert result.violation.guard_type == GuardType.COST

    def test_ttl_checked_before_retries(self) -> None:
        """TTL violation is returned before retries violation."""
        config = GuardrailsConfig(max_duration_seconds=300.0, max_retries_per_run=10)
        engine = GuardrailsEngine(config)

        result = engine.check_budget(accumulated_cost=50.0, elapsed_seconds=301.0, total_retries=11)

        assert result.passed is False
        assert result.violation.guard_type == GuardType.TTL

    def test_default_config(self) -> None:
        """Engine with default config works."""
        engine = GuardrailsEngine()

        result = engine.check_budget(accumulated_cost=50.0, elapsed_seconds=100.0, total_retries=3)

        assert result.passed is True
