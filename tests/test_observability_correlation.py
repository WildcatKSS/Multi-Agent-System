"""Tests for observability correlation ID management."""

import pytest

from mas.observability.correlation import (
    CorrelationContext,
    generate_run_id,
    get_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)


class TestRunIdGeneration:
    """Tests for run ID generation."""

    def test_generate_run_id_format(self) -> None:
        """Generated run ID is 8 hex characters."""
        run_id = generate_run_id()

        assert isinstance(run_id, str)
        assert len(run_id) == 8
        assert all(c in "0123456789abcdef" for c in run_id)

    def test_generate_run_id_unique(self) -> None:
        """Generated run IDs are unique."""
        ids = {generate_run_id() for _ in range(100)}

        assert len(ids) == 100


class TestCorrelationContext:
    """Tests for CorrelationContext dataclass."""

    def test_context_creation(self) -> None:
        """Can create correlation context with required fields."""
        ctx = CorrelationContext(run_id="abc12345", task_id="task-1", workflow_id="wf-1")

        assert ctx.run_id == "abc12345"
        assert ctx.task_id == "task-1"
        assert ctx.workflow_id == "wf-1"

    def test_context_validation_empty_run_id(self) -> None:
        """Context creation fails with empty run_id."""
        with pytest.raises(ValueError, match="run_id cannot be empty"):
            CorrelationContext(run_id="")

    def test_context_immutable(self) -> None:
        """Context is immutable (frozen)."""
        ctx = CorrelationContext(run_id="abc12345")

        with pytest.raises(AttributeError):
            ctx.run_id = "xyz"  # type: ignore


class TestCorrelationIDManagement:
    """Tests for correlation ID context variable management."""

    def setup_method(self) -> None:
        """Clear correlation ID before each test."""
        reset_correlation_id()

    def teardown_method(self) -> None:
        """Clear correlation ID after each test."""
        reset_correlation_id()

    def test_set_and_get_correlation_id(self) -> None:
        """Can set and retrieve correlation ID."""
        run_id = generate_run_id()
        ctx = set_correlation_id(run_id, task_id="task-1")

        assert ctx.run_id == run_id
        assert ctx.task_id == "task-1"
        assert get_correlation_id() == run_id

    def test_get_correlation_id_when_not_set(self) -> None:
        """get_correlation_id returns None when not set."""
        reset_correlation_id()

        assert get_correlation_id() is None

    def test_reset_correlation_id(self) -> None:
        """reset_correlation_id clears the context."""
        set_correlation_id("test-id")
        assert get_correlation_id() == "test-id"

        reset_correlation_id()
        assert get_correlation_id() is None

    def test_set_correlation_id_overwrites(self) -> None:
        """set_correlation_id overwrites previous value."""
        set_correlation_id("id-1")
        assert get_correlation_id() == "id-1"

        set_correlation_id("id-2")
        assert get_correlation_id() == "id-2"
