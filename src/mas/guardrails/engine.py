"""Guardrails Engine: stateless enforcement of runtime limits."""

import logging
import math

from mas.domain.plan import Plan
from mas.guardrails.config import GuardrailsConfig
from mas.guardrails.violations import GuardResult, GuardType, GuardViolation

logger = logging.getLogger(__name__)


class GuardrailsEngine:
    """Stateless engine that enforces cost, TTL, retries, and plan depth limits.

    The engine performs two types of checks:
    1. `check_plan()` — pre-run validation (plan depth, estimated cost)
    2. `check_budget()` — in-run budget tracking (accumulated cost, elapsed time, total retries)

    The engine itself is stateless; the Runtime tracks mutable counters via _RunContext.
    """

    def __init__(self, config: GuardrailsConfig | None = None) -> None:
        """Initialize with optional configuration.

        Args:
            config: GuardrailsConfig with limits (defaults to GuardrailsConfig()).
        """
        self.config = config or GuardrailsConfig()

    def check_plan(self, plan: Plan) -> GuardResult:
        """Validate a plan before execution.

        Checks plan depth, finiteness of estimates, and estimated cost against limits.
        Returns the first violation found (plan_depth → finite check → cost).

        Args:
            plan: Plan to validate.

        Returns:
            GuardResult with passed=True if no violations, False with violation details otherwise.
        """
        # Defensive: Reject plans with NaN or infinite estimates (should not reach here due to Plan.__post_init__,
        # but this provides additional security in case Plan is created via deserialization or other means).
        if math.isnan(plan.estimated_cost) or math.isinf(plan.estimated_cost):
            violation = GuardViolation(
                guard_type=GuardType.COST,
                message=f"Estimated cost must be finite, got {plan.estimated_cost}",
                limit=self.config.max_cost,
                actual=float('inf') if math.isinf(plan.estimated_cost) else 0.0,
            )
            logger.warning(f"Plan {plan.id}: {violation.message}")
            return GuardResult(passed=False, violation=violation)

        # Check plan depth first
        plan_depth = len(plan.steps)
        if plan_depth > self.config.max_plan_depth:
            violation = GuardViolation(
                guard_type=GuardType.PLAN_DEPTH,
                message=(
                    f"Plan depth {plan_depth} exceeds limit {self.config.max_plan_depth} "
                    "(reduce steps or increase max_plan_depth)"
                ),
                limit=self.config.max_plan_depth,
                actual=plan_depth,
            )
            logger.warning(f"Plan {plan.id}: {violation.message}")
            return GuardResult(passed=False, violation=violation)

        # Check estimated cost
        if plan.estimated_cost > self.config.max_cost:
            violation = GuardViolation(
                guard_type=GuardType.COST,
                message=(
                    f"Estimated cost {plan.estimated_cost} exceeds limit {self.config.max_cost} "
                    "(reduce step count or increase max_cost)"
                ),
                limit=self.config.max_cost,
                actual=plan.estimated_cost,
            )
            logger.warning(f"Plan {plan.id}: {violation.message}")
            return GuardResult(passed=False, violation=violation)

        return GuardResult(passed=True)

    def check_budget(
        self,
        accumulated_cost: float,
        elapsed_seconds: float,
        total_retries: int,
    ) -> GuardResult:
        """Check runtime budget during execution.

        Checks accumulated cost, elapsed time, and total retries against limits.
        Returns the first violation found (cost → ttl → retries).

        Args:
            accumulated_cost: Total cost accumulated so far in the run.
            elapsed_seconds: Wall-clock seconds elapsed since run start.
            total_retries: Total retry attempts so far in the run.

        Returns:
            GuardResult with passed=True if within budget, False with violation details otherwise.
        """
        # Check cost first
        if accumulated_cost > self.config.max_cost:
            violation = GuardViolation(
                guard_type=GuardType.COST,
                message=(
                    f"Accumulated cost {accumulated_cost} exceeds limit {self.config.max_cost} "
                    "(halting execution to prevent resource exhaustion)"
                ),
                limit=self.config.max_cost,
                actual=accumulated_cost,
            )
            logger.warning(f"Cost budget exceeded: {violation.message}")
            return GuardResult(passed=False, violation=violation)

        # Check elapsed time
        if elapsed_seconds > self.config.max_duration_seconds:
            violation = GuardViolation(
                guard_type=GuardType.TTL,
                message=(
                    f"Elapsed time {elapsed_seconds:.1f}s exceeds limit "
                    f"{self.config.max_duration_seconds}s (halting execution to meet deadline)"
                ),
                limit=self.config.max_duration_seconds,
                actual=elapsed_seconds,
            )
            logger.warning(f"TTL exceeded: {violation.message}")
            return GuardResult(passed=False, violation=violation)

        # Check total retries
        if total_retries > self.config.max_retries_per_run:
            violation = GuardViolation(
                guard_type=GuardType.RETRIES,
                message=(
                    f"Total retries {total_retries} exceeds limit {self.config.max_retries_per_run} "
                    "(halting to prevent infinite retry loops)"
                ),
                limit=self.config.max_retries_per_run,
                actual=total_retries,
            )
            logger.warning(f"Retry budget exceeded: {violation.message}")
            return GuardResult(passed=False, violation=violation)

        return GuardResult(passed=True)
