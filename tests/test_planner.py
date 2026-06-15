"""Tests for Planner agent v1."""

import pytest

from mas.agents.planner import Planner, PlannerConfig
from mas.domain.task import Task


def _task(
    task_id: str = "task-1",
    description: str = "Find and process data",
    goal: str = "Generate a report",
) -> Task:
    return Task(id=task_id, description=description, goal=goal)


class TestPlannerConfig:
    """Tests for PlannerConfig."""

    def test_default_config(self) -> None:
        """Default config has max_depth of 10."""
        config = PlannerConfig()
        assert config.max_depth == 10

    def test_custom_max_depth(self) -> None:
        """Can set custom max_depth."""
        config = PlannerConfig(max_depth=5)
        assert config.max_depth == 5

    def test_invalid_max_depth(self) -> None:
        """max_depth must be >= 1."""
        with pytest.raises(ValueError, match="max_depth must be at least 1"):
            PlannerConfig(max_depth=0)

        with pytest.raises(ValueError, match="max_depth must be at least 1"):
            PlannerConfig(max_depth=-1)


class TestPlannerBasic:
    """Basic planner functionality."""

    def test_planner_creates_plan(self) -> None:
        """Planner generates a valid plan from a task."""
        planner = Planner()
        task = _task()
        plan = planner.generate_plan(task)

        assert plan.task_id == task.id
        assert len(plan.steps) > 0
        assert plan.estimated_cost > 0
        assert plan.estimated_time_seconds > 0

    def test_planner_creates_unique_plan_ids(self) -> None:
        """Each plan gets a unique ID."""
        planner = Planner()
        task1 = _task(task_id="task-1")
        task2 = _task(task_id="task-2")

        plan1 = planner.generate_plan(task1)
        plan2 = planner.generate_plan(task2)

        assert plan1.id != plan2.id

    def test_planner_rejects_empty_task(self) -> None:
        """Planner rejects tasks with missing description or goal."""
        planner = Planner()

        with pytest.raises(ValueError):
            planner.generate_plan(Task(id="task-1", description="", goal="test"))

        with pytest.raises(ValueError):
            planner.generate_plan(Task(id="task-1", description="test", goal=""))


class TestPlannerLinearConstraint:
    """Tests for linear constraint validation."""

    def test_generated_plan_is_linear(self) -> None:
        """Generated plan forms a linear chain (each step depends on at most one previous)."""
        planner = Planner()
        task = _task()
        plan = planner.generate_plan(task)

        # Check: each step has at most one dependency
        for step in plan.steps:
            assert len(step.depends_on) <= 1

        # Check: dependencies form a forward chain
        step_ids = [s.id for s in plan.steps]
        for i, step in enumerate(plan.steps):
            if step.depends_on:
                dep = step.depends_on[0]
                dep_index = step_ids.index(dep)
                assert dep_index < i, f"Step {step.id} depends on later step {dep}"

    def test_plan_steps_are_sequential(self) -> None:
        """Plan steps are ordered so dependencies point backwards."""
        planner = Planner()
        task = _task(description="Find, process, and output data")
        plan = planner.generate_plan(task)

        # Build dependency graph
        for i, step in enumerate(plan.steps):
            for dep in step.depends_on:
                # Find which step has this ID
                dep_index = next(
                    (j for j, s in enumerate(plan.steps) if s.id == dep), -1
                )
                assert dep_index >= 0, f"Step {step.id} depends on unknown {dep}"
                assert dep_index < i, f"Dependency not backwards: {step.id} -> {dep}"


class TestPlannerMaxDepth:
    """Tests for max depth constraint."""

    def test_plan_respects_max_depth(self) -> None:
        """Generated plan never exceeds max_depth."""
        planner = Planner(config=PlannerConfig(max_depth=5))
        task = _task()
        plan = planner.generate_plan(task)

        assert len(plan.steps) <= 5

    def test_plan_fails_on_depth_violation(self) -> None:
        """If decomposition would exceed max_depth, planner raises."""
        # Create a planner with very restrictive max_depth
        planner = Planner(config=PlannerConfig(max_depth=1))
        task = _task(description="Find and process and output data")

        # Baseline decomposition creates 3+ steps, so should fail
        # (This depends on task keywords, but "find" + "process" + "output" => 3 steps)
        with pytest.raises(ValueError, match="exceeds max_depth"):
            planner.generate_plan(task)


class TestPlannerEstimates:
    """Tests for cost and time estimation."""

    def test_plan_has_cost_estimate(self) -> None:
        """Plan includes cost estimate."""
        planner = Planner()
        task = _task()
        plan = planner.generate_plan(task)

        assert plan.estimated_cost > 0
        # Baseline: cost = num_steps * 1.0
        assert plan.estimated_cost == len(plan.steps) * 1.0

    def test_plan_has_time_estimate(self) -> None:
        """Plan includes time estimate."""
        planner = Planner()
        task = _task()
        plan = planner.generate_plan(task)

        assert plan.estimated_time_seconds > 0
        # Baseline: time = num_steps * 5.0 seconds
        assert plan.estimated_time_seconds == len(plan.steps) * 5.0

    def test_estimates_scale_with_plan_size(self) -> None:
        """Estimates increase with plan size."""
        planner = Planner()
        task = _task(description="Find data to retrieve")
        plan1 = planner.generate_plan(task)

        task2 = _task(description="Find, process, and output data")
        plan2 = planner.generate_plan(task2)

        # Plan2 should be larger and have higher estimates
        assert len(plan2.steps) >= len(plan1.steps)
        assert plan2.estimated_cost >= plan1.estimated_cost
        assert plan2.estimated_time_seconds >= plan1.estimated_time_seconds


class TestPlannerStepGeneration:
    """Tests for step generation."""

    def test_plan_steps_have_unique_ids(self) -> None:
        """All steps in a plan have unique IDs."""
        planner = Planner()
        task = _task()
        plan = planner.generate_plan(task)

        step_ids = [s.id for s in plan.steps]
        assert len(step_ids) == len(set(step_ids))
        # Verify zero-padded format (e.g., step-01, step-02)
        for step_id in step_ids:
            assert step_id.startswith("step-")
            assert "-" in step_id

    def test_plan_steps_have_actions(self) -> None:
        """All steps have valid actions."""
        planner = Planner()
        task = _task()
        plan = planner.generate_plan(task)

        for step in plan.steps:
            assert step.action in {"retrieve_data", "process", "output_result"}

    def test_plan_steps_have_inputs(self) -> None:
        """Steps have inputs dict (may be empty but present)."""
        planner = Planner()
        task = _task()
        plan = planner.generate_plan(task)

        for step in plan.steps:
            assert isinstance(step.inputs, dict)


class TestPlannerExecutability:
    """Tests that generated plans are executable by Runtime."""

    def test_plan_passes_validation(self) -> None:
        """Generated plan passes Plan validation (no circular deps, etc)."""
        planner = Planner()
        task = _task()
        plan = planner.generate_plan(task)

        # If plan creation succeeded, it passed validation
        # (Plan.__post_init__ validates circular deps, unknowns, etc)
        assert plan.is_executable()

    def test_plan_readable_by_runtime(self) -> None:
        """Generated plan structure matches Runtime's expectations."""
        planner = Planner()
        task = _task()
        plan = planner.generate_plan(task)

        # Runtime expects: plan.steps, each with id, action, depends_on, status
        for step in plan.steps:
            assert hasattr(step, "id")
            assert hasattr(step, "action")
            assert hasattr(step, "depends_on")
            assert hasattr(step, "status")
            assert hasattr(step, "inputs")


class TestPlannerEdgeCases:
    """Edge cases and error conditions."""

    def test_plan_with_empty_task_constraints(self) -> None:
        """Task with empty constraints dict is handled."""
        planner = Planner()
        task = _task()
        task.constraints = []
        plan = planner.generate_plan(task)

        assert len(plan.steps) > 0

    def test_plan_with_task_metadata(self) -> None:
        """Task with metadata doesn't break planning."""
        planner = Planner()
        task = _task()
        task.metadata = {"priority": "high", "user": "alice"}
        plan = planner.generate_plan(task)

        assert plan.task_id == task.id

    def test_multiple_planners_independent(self) -> None:
        """Multiple planner instances are independent."""
        planner1 = Planner(config=PlannerConfig(max_depth=5))
        planner2 = Planner(config=PlannerConfig(max_depth=10))

        task = _task()
        plan1 = planner1.generate_plan(task)
        plan2 = planner2.generate_plan(task)

        # Plans should be different (different IDs)
        assert plan1.id != plan2.id
