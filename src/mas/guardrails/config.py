"""Guardrails configuration."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailsConfig:
    """Configuration for runtime guardrails enforcement.

    All limits must come from trusted sources (environment variables, code, or
    trusted configuration files). The configuration is designed to be instantiated
    by system administrators or the framework itself, not from untrusted input.

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
        """Validate all limits are positive and finite.

        Rejects NaN and infinity values to prevent silent guard bypasses.
        These special float values are never intentional configuration values.
        """
        for name, value in [
            ("max_cost", self.max_cost),
            ("max_duration_seconds", self.max_duration_seconds),
        ]:
            if math.isnan(value) or math.isinf(value):
                raise ValueError(f"{name} must be finite, got {value}")

        if self.max_cost <= 0:
            raise ValueError(f"max_cost must be positive, got {self.max_cost}")
        if self.max_duration_seconds <= 0:
            raise ValueError(f"max_duration_seconds must be positive, got {self.max_duration_seconds}")
        if self.max_retries_per_run <= 0:
            raise ValueError(f"max_retries_per_run must be positive, got {self.max_retries_per_run}")
        if self.max_plan_depth <= 0:
            raise ValueError(f"max_plan_depth must be positive, got {self.max_plan_depth}")
