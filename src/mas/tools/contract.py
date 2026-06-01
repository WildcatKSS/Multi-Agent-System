"""Tool contracts for the multi-agent system."""

from dataclasses import dataclass, field


@dataclass
class Tool:
    """Definition of an available tool."""

    name: str
    description: str
    inputs: dict = field(default_factory=dict)
    """Input schema/documentation for the tool."""

    outputs: dict = field(default_factory=dict)
    """Output schema/documentation for the tool."""

    prerequisites: list[str] = field(default_factory=list)
    """Tools that must be run before this one.
    Note: Validation and resolution in v2 (capability-aware selection phase)."""

    cost_estimate: float = 1.0
    """Estimated cost units for this tool."""

    def __post_init__(self) -> None:
        """Validate tool on creation."""
        if not self.name:
            raise ValueError("Tool name cannot be empty")
        if not self.description:
            raise ValueError("Tool description cannot be empty")
        if self.cost_estimate < 0:
            raise ValueError("cost_estimate cannot be negative")


@dataclass
class ToolSelection:
    """Selection of a tool for a plan step."""

    step_id: str
    tool_name: str
    tool_inputs: dict = field(default_factory=dict)
    """Inputs to pass to the tool."""

    required_tools: list[str] = field(default_factory=list)
    """Tools that must run before this one."""

    def __post_init__(self) -> None:
        """Validate selection on creation."""
        if not self.step_id:
            raise ValueError("step_id cannot be empty")
        if not self.tool_name:
            raise ValueError("tool_name cannot be empty")
