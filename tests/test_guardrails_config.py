"""Tests for GuardrailsConfig."""

import pytest

from mas.guardrails import GuardrailsConfig


class TestGuardrailsConfigDefaults:
    """Verify default configuration values."""

    def test_default_limits(self) -> None:
        """Config has sensible defaults for all limits."""
        config = GuardrailsConfig()

        assert config.max_cost == 100.0
        assert config.max_duration_seconds == 300.0
        assert config.max_retries_per_run == 10
        assert config.max_plan_depth == 20

    def test_custom_limits(self) -> None:
        """Config accepts custom limits."""
        config = GuardrailsConfig(
            max_cost=50.0,
            max_duration_seconds=120.0,
            max_retries_per_run=5,
            max_plan_depth=10,
        )

        assert config.max_cost == 50.0
        assert config.max_duration_seconds == 120.0
        assert config.max_retries_per_run == 5
        assert config.max_plan_depth == 10

    def test_partial_custom(self) -> None:
        """Config allows overriding individual limits."""
        config = GuardrailsConfig(max_cost=50.0)

        assert config.max_cost == 50.0
        assert config.max_duration_seconds == 300.0  # default
        assert config.max_retries_per_run == 10  # default
        assert config.max_plan_depth == 20  # default


class TestGuardrailsConfigValidation:
    """Verify configuration validation."""

    def test_reject_zero_cost(self) -> None:
        """Config rejects zero max_cost."""
        with pytest.raises(ValueError, match="max_cost must be positive"):
            GuardrailsConfig(max_cost=0.0)

    def test_reject_negative_cost(self) -> None:
        """Config rejects negative max_cost."""
        with pytest.raises(ValueError, match="max_cost must be positive"):
            GuardrailsConfig(max_cost=-1.0)

    def test_reject_zero_duration(self) -> None:
        """Config rejects zero max_duration_seconds."""
        with pytest.raises(ValueError, match="max_duration_seconds must be positive"):
            GuardrailsConfig(max_duration_seconds=0.0)

    def test_reject_negative_duration(self) -> None:
        """Config rejects negative max_duration_seconds."""
        with pytest.raises(ValueError, match="max_duration_seconds must be positive"):
            GuardrailsConfig(max_duration_seconds=-1.0)

    def test_reject_zero_retries(self) -> None:
        """Config rejects zero max_retries_per_run."""
        with pytest.raises(ValueError, match="max_retries_per_run must be positive"):
            GuardrailsConfig(max_retries_per_run=0)

    def test_reject_negative_retries(self) -> None:
        """Config rejects negative max_retries_per_run."""
        with pytest.raises(ValueError, match="max_retries_per_run must be positive"):
            GuardrailsConfig(max_retries_per_run=-1)

    def test_reject_zero_depth(self) -> None:
        """Config rejects zero max_plan_depth."""
        with pytest.raises(ValueError, match="max_plan_depth must be positive"):
            GuardrailsConfig(max_plan_depth=0)

    def test_reject_negative_depth(self) -> None:
        """Config rejects negative max_plan_depth."""
        with pytest.raises(ValueError, match="max_plan_depth must be positive"):
            GuardrailsConfig(max_plan_depth=-1)

    def test_frozen_config(self) -> None:
        """Config is immutable after creation."""
        config = GuardrailsConfig()

        with pytest.raises(AttributeError):
            config.max_cost = 200.0  # type: ignore

    def test_reject_infinity_cost(self) -> None:
        """Config rejects infinity as max_cost."""
        with pytest.raises(ValueError, match="max_cost must be finite"):
            GuardrailsConfig(max_cost=float('inf'))

    def test_reject_negative_infinity_cost(self) -> None:
        """Config rejects negative infinity as max_cost."""
        with pytest.raises(ValueError, match="max_cost must be finite"):
            GuardrailsConfig(max_cost=float('-inf'))

    def test_reject_nan_cost(self) -> None:
        """Config rejects NaN as max_cost."""
        with pytest.raises(ValueError, match="max_cost must be finite"):
            GuardrailsConfig(max_cost=float('nan'))

    def test_reject_infinity_duration(self) -> None:
        """Config rejects infinity as max_duration_seconds."""
        with pytest.raises(ValueError, match="max_duration_seconds must be finite"):
            GuardrailsConfig(max_duration_seconds=float('inf'))

    def test_reject_nan_duration(self) -> None:
        """Config rejects NaN as max_duration_seconds."""
        with pytest.raises(ValueError, match="max_duration_seconds must be finite"):
            GuardrailsConfig(max_duration_seconds=float('nan'))
