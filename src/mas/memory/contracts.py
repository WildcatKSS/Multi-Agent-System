"""Memory layer data contracts and types."""

from dataclasses import dataclass, field
from enum import Enum


class MemoryType(str, Enum):
    """Type of memory entry."""

    WORKING = "working"
    """Short-lived working memory for in-flight task state."""

    EPISODIC = "episodic"
    """Long-term episodic memory storing past task executions."""


@dataclass(frozen=True)
class MemoryEntry:
    """A single entry in memory."""

    id: str
    """Unique identifier for this memory entry."""

    content: dict
    """The memory content (arbitrary dict)."""

    memory_type: MemoryType
    """Type of memory this entry belongs to."""

    task_id: str
    """ID of the task this memory relates to."""

    step_id: str
    """ID of the step this memory relates to."""

    timestamp: str
    """ISO 8601 timestamp when this entry was created."""

    metadata: dict = field(default_factory=dict)
    """Optional metadata about this entry."""

    def __post_init__(self) -> None:
        """Validate memory entry on creation."""
        if not self.id:
            raise ValueError("id cannot be empty")
        if not self.task_id:
            raise ValueError("task_id cannot be empty")
        if self.content is None:
            raise ValueError("content cannot be None")


@dataclass(frozen=True)
class EpisodicRecord:
    """Record of a completed task execution (episodic memory)."""

    id: str
    """Unique identifier for this episodic record."""

    task_id: str
    """ID of the task that was executed."""

    plan_id: str
    """ID of the plan that was executed."""

    steps_executed: int
    """Number of steps executed in the plan."""

    outcome: str
    """Overall outcome (e.g., 'success', 'failed', 'partial')."""

    score: float
    """Quality score of the execution (0-1)."""

    duration_seconds: float
    """How long the execution took in seconds."""

    lessons: list[str] = field(default_factory=list)
    """Key lessons learned from this execution."""

    timestamp: str = ""
    """ISO 8601 timestamp when this execution completed."""

    def __post_init__(self) -> None:
        """Validate episodic record on creation."""
        if not self.id:
            raise ValueError("id cannot be empty")
        if not self.task_id:
            raise ValueError("task_id cannot be empty")
        if not (0.0 <= self.score <= 1.0):
            raise ValueError("score must be between 0 and 1")
