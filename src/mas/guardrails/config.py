"""Guardrails configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailsConfig:
    """Configuration for runtime guardrails enforcement.

    Attributes:
        max_cost: Maximum accumulated cost per run (default 100.0).
        max_duration_seconds: Maximum wall-clock seconds per run (default 300.0).
        max_retries_per_run: Maximum total retries across all steps (default 10).
        max_plan_depth: Maximum number of steps in a plan (default 20).
    """

    max_cost: float = 100.0
    max_duration_seconds: float = 300.0
    max_retries_per_run: int = 10
    max_plan_depth: int = 20

    def __post_init__(self) -> None:
        """Validate all limits are positive."""
        if self.max_cost <= 0:
            raise ValueError(f"max_cost must be positive, got {self.max_cost}")
        if self.max_duration_seconds <= 0:
            raise ValueError(f"max_duration_seconds must be positive, got {self.max_duration_seconds}")
        if self.max_retries_per_run <= 0:
            raise ValueError(f"max_retries_per_run must be positive, got {self.max_retries_per_run}")
        if self.max_plan_depth <= 0:
            raise ValueError(f"max_plan_depth must be positive, got {self.max_plan_depth}")
