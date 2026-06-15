"""Task contract: unit of work to be executed."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    """Status of a task execution."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """A unit of work to be executed by the system.

    Tasks are the primary input to workflows. Each task contains:
    - A description of what needs to be done
    - Success criteria (goals)
    - Constraints on execution
    - Optional context for the execution environment
    """

    id: str
    description: str
    goal: str
    status: TaskStatus = TaskStatus.PENDING
    context: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate task on creation."""
        if not self.id:
            raise ValueError("Task id cannot be empty")
        if not self.description:
            raise ValueError("Task description cannot be empty")
        if not self.goal:
            raise ValueError("Task goal cannot be empty")

    def is_complete(self) -> bool:
        """Check if task has reached a terminal state."""
        return self.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}

    def is_active(self) -> bool:
        """Check if task is currently being executed."""
        return self.status == TaskStatus.IN_PROGRESS
