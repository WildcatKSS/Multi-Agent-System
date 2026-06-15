"""Step executor registry: maps step actions to handler callables.

The registry decouples the runtime from concrete step implementations. In this
baseline there are no real agents yet (#5-#9); handlers are simple callables
that take a Step and return a StepResult. Unknown actions resolve to no handler
and are skipped by the runtime. This mirrors the future Tool Registry (#6).
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from mas.domain.plan import Step


@dataclass
class StepResult:
    """Outcome of executing a single step."""

    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str = ""


# A handler takes the step to execute and returns its result.
StepHandler = Callable[[Step], StepResult]


class StepExecutorRegistry:
    """Maps step action names to handler callables.

    Single-threaded only; no locking. Register handlers before running a plan.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._handlers: dict[str, StepHandler] = {}

    def register(self, action: str, handler: StepHandler) -> None:
        """Register a handler for an action name."""
        if not action:
            raise ValueError("action cannot be empty")
        self._handlers[action] = handler

    def get(self, action: str) -> StepHandler | None:
        """Return the handler for an action, or None if unregistered."""
        return self._handlers.get(action)

    def has(self, action: str) -> bool:
        """Check whether a handler is registered for an action."""
        return action in self._handlers
