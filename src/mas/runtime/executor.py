"""Step execution layer for the single-worker runtime.

The runtime delegates the actual work of a step to a ``StepExecutor``. This is
the extension point that future agents (planner, tool selection, self-healing)
will hook into. The baseline ships with ``EchoStepExecutor`` so the runtime is
fully testable before any agent exists.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from mas.domain.plan import Step


@dataclass
class StepResult:
    """Outcome of executing a single step."""

    step_id: str
    success: bool
    output: dict = field(default_factory=dict)
    error: str = ""


@runtime_checkable
class StepExecutor(Protocol):
    """Executes a single step and reports the outcome.

    Implementations must not mutate the step's status; the runtime owns all
    status transitions. An executor should signal failure by returning a
    ``StepResult`` with ``success=False`` (it may also raise, which the runtime
    treats as a failure).
    """

    def execute(self, step: Step) -> StepResult:
        """Execute ``step`` and return its result."""
        ...


class EchoStepExecutor:
    """Baseline executor that echoes the step back as a success.

    Used as the default executor so the runtime can be exercised end-to-end
    before real agents are implemented (PR-05+).
    """

    def execute(self, step: Step) -> StepResult:
        """Return a successful result echoing the step's action and inputs."""
        return StepResult(
            step_id=step.id,
            success=True,
            output={"action": step.action, "inputs": dict(step.inputs)},
        )
