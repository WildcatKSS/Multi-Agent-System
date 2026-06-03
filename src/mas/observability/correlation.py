"""Correlation ID and execution context management."""

import contextvars
import uuid
from dataclasses import dataclass
from typing import Optional


_correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)


@dataclass(frozen=True)
class CorrelationContext:
    """Execution context for distributed tracing.

    Provides end-to-end tracing across multiple execution scopes by threading
    a unique run ID alongside task and workflow identifiers. Used to correlate
    logs, metrics, and debugging information across async execution boundaries.

    Attributes:
        run_id: Unique identifier for this execution run (8-char hex from UUID4).
        task_id: Identifier of the task being executed (optional).
        workflow_id: Identifier of the workflow state machine (optional).
    """

    run_id: str
    task_id: str = ""
    workflow_id: str = ""

    def __post_init__(self) -> None:
        """Validate context on creation."""
        if not self.run_id:
            raise ValueError(
                "run_id cannot be empty. Use generate_run_id() to create one."
            )


def generate_run_id() -> str:
    """Generate a unique run ID for this execution.

    Returns:
        A unique run ID (UUID4 hex, 8 characters).
    """
    return uuid.uuid4().hex[:8]


def set_correlation_id(run_id: str, task_id: str = "", workflow_id: str = "") -> CorrelationContext:
    """Set the correlation context for this execution.

    Args:
        run_id: Unique run identifier.
        task_id: Task identifier (optional).
        workflow_id: Workflow identifier (optional).

    Returns:
        The set CorrelationContext.

    Raises:
        ValueError: If run_id is empty.
    """
    context = CorrelationContext(run_id=run_id, task_id=task_id, workflow_id=workflow_id)
    _correlation_id_var.set(run_id)
    return context


def get_correlation_id() -> Optional[str]:
    """Get the current correlation run ID.

    Returns:
        The current run ID, or None if not set.
    """
    return _correlation_id_var.get()


def reset_correlation_id() -> None:
    """Clear the current correlation context.

    Used for cleanup between test runs or when a run completes.
    """
    _correlation_id_var.set(None)
