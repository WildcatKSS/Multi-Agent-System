"""Planner agent: generates execution plans for tasks.

The baseline Planner v1 generates linear execution plans with:
- Steps form a chain: step-1 -> step-2 -> step-3 (no diamonds)
- Max depth constraint (default: 10 steps)
- Estimated cost and duration
- Ready for LLM-based planning in future versions
"""

import uuid
from dataclasses import dataclass

from mas.domain.plan import Plan, Step
from mas.domain.task import Task


@dataclass
class PlannerConfig:
    """Configuration for the Planner agent."""

    max_depth: int = 10
    """Maximum number of steps in a plan."""

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.max_depth < 1:
            raise ValueError("max_depth must be at least 1")


class Planner:
    """Agent that generates execution plans for tasks.

    v1 characteristics:
    - Linear plans only (steps form a chain, no parallel execution)
    - Respects max_depth constraint
    - Generates step IDs and estimates cost/time
    - Deterministic (no LLM yet; future versions will integrate LLMs)
    """

    def __init__(self, config: PlannerConfig | None = None) -> None:
        """Initialize planner with optional configuration."""
        self.config = config or PlannerConfig()

    def generate_plan(self, task: Task) -> Plan:
        """Generate a linear execution plan for the task.

        The baseline implementation creates a simple linear plan:
        1. Parse task description for action keywords
        2. Create a chain of steps
        3. Estimate cost/time
        4. Return executable Plan

        Args:
            task: The task to plan for

        Returns:
            Plan: An executable plan with linear dependencies

        Raises:
            ValueError: If task is invalid or plan exceeds max_depth
        """
        if not task.description or not task.goal:
            raise ValueError("Task must have description and goal")

        # Baseline: decompose task into simple steps
        # Future: Replace with LLM-based planning
        steps = self._decompose_task(task)

        # Validate constraints
        if len(steps) > self.config.max_depth:
            raise ValueError(
                f"Plan depth {len(steps)} exceeds max_depth {self.config.max_depth}"
            )

        # Validate linearity
        self._validate_linear(steps)

        # Create plan with linearity
        # Cost/time estimation is intentionally simple for MVP.
        # Future versions will consider action type, task complexity, and historical data.
        plan = Plan(
            id=f"plan:{task.id}:{uuid.uuid4().hex[:8]}",
            task_id=task.id,
            steps=steps,
            estimated_cost=len(steps) * 1.0,  # MVP baseline: 1.0 unit per step
            estimated_time_seconds=len(steps) * 5.0,  # MVP baseline: 5s per step
            reasoning="Linear plan from task decomposition (MVP v1)",
        )

        return plan

    def _decompose_task(self, task: Task) -> list[Step]:
        """Decompose task into a linear chain of steps.

        MVP Baseline implementation uses simple keyword matching for action selection.
        Future versions will use LLM-based decomposition for more sophisticated planning.

        Steps:
        1. Optional retrieval step (if keywords suggest data gathering)
        2. Required process step (core task execution)
        3. Optional output step (if keywords suggest results generation)
        """
        steps: list[Step] = []
        step_counter = 0

        # Parse task for keywords (simple heuristics for MVP baseline)
        # Future: Replace with LLM-based action detection
        task_lower = task.description.lower()

        # Step 1: Retrieve/gather information
        if any(word in task_lower for word in ["find", "get", "retrieve", "search"]):
            step_counter += 1
            steps.append(
                Step(
                    id=f"step-{step_counter:02d}",
                    action="retrieve_data",
                    inputs={"query": task.description},
                    depends_on=[],
                    metadata={"source": "task_description"},
                )
            )

        # Step 2: Process/analyze (always present)
        step_counter += 1
        prev_step = f"step-{step_counter - 1:02d}" if steps else None
        steps.append(
            Step(
                id=f"step-{step_counter:02d}",
                action="process",
                inputs={"goal": task.goal},
                depends_on=[prev_step] if prev_step else [],
                metadata={"goal": task.goal},
            )
        )

        # Step 3: Output/return results (if task implies it)
        if any(
            word in task_lower
            for word in ["output", "return", "generate", "create", "write"]
        ):
            step_counter += 1
            steps.append(
                Step(
                    id=f"step-{step_counter:02d}",
                    action="output_result",
                    inputs={"format": "json"},
                    depends_on=[f"step-{step_counter - 1:02d}"],
                    metadata={"task_id": task.id},
                )
            )

        return steps

    def _validate_linear(self, steps: list[Step]) -> None:
        """Validate that steps form a linear chain (no diamonds, no parallel).

        In a linear plan, each step depends on at most one previous step,
        and steps are ordered sequentially.
        """
        if not steps:
            return

        # Check: each step has at most one dependency
        for step in steps:
            if len(step.depends_on) > 1:
                raise ValueError(
                    f"Step {step.id} has {len(step.depends_on)} dependencies; "
                    "linear plans allow at most 1"
                )

        # Check: dependencies form a valid chain
        step_ids = {step.id for step in steps}
        for i, step in enumerate(steps):
            if step.depends_on:
                # This step depends on a previous step
                dep = step.depends_on[0]
                if dep not in step_ids:
                    raise ValueError(
                        f"Step {step.id} depends on unknown step {dep}"
                    )
                # In a linear plan, dependent should be earlier in the chain
                dep_index = next(
                    (j for j, s in enumerate(steps) if s.id == dep), -1
                )
                if dep_index >= i:
                    raise ValueError(
                        f"Step {step.id} depends on later step {dep}; "
                        "linear plans must form a forward chain"
                    )
