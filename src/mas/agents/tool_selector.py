"""Tool Selection Agent: maps plan steps to tools."""

from mas.domain.plan import Plan
from mas.tools.registry import ToolRegistry
from mas.tools.contract import ToolSelection


class ToolSelector:
    """Agent that selects tools for plan steps.

    v1 characteristics:
    - Deterministic mapping: action name → tool name
    - Linear plans only (from Planner v1)
    - No capability matching (exact match on action)
    - No LLM reasoning (future versions will add this)
    """

    def __init__(self, registry: ToolRegistry) -> None:
        """Initialize tool selector with a registry.

        Args:
            registry: ToolRegistry with available tools
        """
        self.registry = registry

    def select_tools(self, plan: Plan) -> list[ToolSelection]:
        """Select tools for all steps in a plan.

        Args:
            plan: The plan to select tools for

        Returns:
            List of ToolSelection with tool assignments

        Raises:
            ValueError: If plan is invalid or tools not found
        """
        if not plan.steps:
            raise ValueError("Plan has no steps")

        selections: list[ToolSelection] = []

        for step in plan.steps:
            # MVP: Direct action-to-tool mapping
            # Future: Capability-aware selection
            tool_name = self._select_tool_for_action(step.action)

            selection = ToolSelection(
                step_id=step.id,
                tool_name=tool_name,
                tool_inputs=step.inputs,
                required_tools=step.depends_on,
            )
            selections.append(selection)

        return selections

    def _select_tool_for_action(self, action: str) -> str:
        """Map an action name to a tool name.

        MVP Baseline: Tool name = action name
        Future: Capability-aware selection from registry

        Args:
            action: The step action name

        Returns:
            The tool name to use

        Raises:
            ValueError: If no tool found for action
        """
        # MVP: action name should match a tool name
        # Example: action="retrieve_data" → tool_name="retrieve_data"
        if not self.registry.has(action):
            raise ValueError(
                f"No tool registered for action '{action}'. "
                f"Available tools: {self.registry.list_names()}"
            )

        return action
