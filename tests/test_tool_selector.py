"""Tests for Tool Selector Agent."""

import pytest

from mas.agents.tool_selector import ToolSelector
from mas.domain.plan import Plan, Step
from mas.domain.task import Task
from mas.tools.registry import ToolRegistry
from mas.tools.contract import Tool


def _search_handler(*args, **kwargs):
    return {"results": []}


def _process_handler(*args, **kwargs):
    return {"processed": True}


class TestToolSelector:
    """Tests for ToolSelector agent."""

    def _registry_with_tools(self) -> ToolRegistry:
        """Create a registry with common tools."""
        registry = ToolRegistry()
        registry.register(
            Tool(name="retrieve_data", description="Retrieve data"),
            _search_handler,
        )
        registry.register(
            Tool(name="process", description="Process data"),
            _process_handler,
        )
        registry.register(
            Tool(name="output_result", description="Output results"),
            _process_handler,
        )
        return registry

    def test_selector_selects_tools(self) -> None:
        """ToolSelector maps steps to tools."""
        registry = self._registry_with_tools()
        selector = ToolSelector(registry=registry)

        task = Task(id="task-1", description="Find data", goal="Generate report")
        plan = Plan(
            id="plan-1",
            task_id="task-1",
            steps=[
                Step(id="step-01", action="retrieve_data"),
                Step(id="step-02", action="process", depends_on=["step-01"]),
            ],
        )

        selections = selector.select_tools(plan)

        assert len(selections) == 2
        assert selections[0].step_id == "step-01"
        assert selections[0].tool_name == "retrieve_data"
        assert selections[1].step_id == "step-02"
        assert selections[1].tool_name == "process"

    def test_selector_preserves_step_order(self) -> None:
        """Tool selections maintain step order."""
        registry = self._registry_with_tools()
        selector = ToolSelector(registry=registry)

        plan = Plan(
            id="plan-1",
            task_id="task-1",
            steps=[
                Step(id="step-01", action="retrieve_data"),
                Step(id="step-02", action="process", depends_on=["step-01"]),
                Step(id="step-03", action="output_result", depends_on=["step-02"]),
            ],
        )

        selections = selector.select_tools(plan)

        step_ids = [s.step_id for s in selections]
        assert step_ids == ["step-01", "step-02", "step-03"]

    def test_selector_handles_unknown_action(self) -> None:
        """Selector raises error for unregistered action."""
        registry = self._registry_with_tools()
        selector = ToolSelector(registry=registry)

        plan = Plan(
            id="plan-1",
            task_id="task-1",
            steps=[Step(id="step-01", action="unknown_action")],
        )

        with pytest.raises(ValueError, match="No tool registered"):
            selector.select_tools(plan)

    def test_selector_includes_tool_inputs(self) -> None:
        """Tool selections include step inputs."""
        registry = self._registry_with_tools()
        selector = ToolSelector(registry=registry)

        plan = Plan(
            id="plan-1",
            task_id="task-1",
            steps=[
                Step(
                    id="step-01",
                    action="retrieve_data",
                    inputs={"query": "find users"},
                ),
            ],
        )

        selections = selector.select_tools(plan)

        assert selections[0].tool_inputs == {"query": "find users"}

    def test_selector_includes_dependencies(self) -> None:
        """Tool selections preserve step dependencies."""
        registry = self._registry_with_tools()
        selector = ToolSelector(registry=registry)

        plan = Plan(
            id="plan-1",
            task_id="task-1",
            steps=[
                Step(id="step-01", action="retrieve_data"),
                Step(id="step-02", action="process", depends_on=["step-01"]),
            ],
        )

        selections = selector.select_tools(plan)

        assert selections[0].required_tools == []
        assert selections[1].required_tools == ["step-01"]

    def test_selector_rejects_empty_plan(self) -> None:
        """Selector rejects empty plans."""
        registry = self._registry_with_tools()
        selector = ToolSelector(registry=registry)

        plan = Plan(id="plan-1", task_id="task-1", steps=[])

        with pytest.raises(ValueError, match="no steps"):
            selector.select_tools(plan)
