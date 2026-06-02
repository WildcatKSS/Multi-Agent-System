"""Tests for Tool Registry."""

import pytest

from mas.tools.registry import ToolRegistry
from mas.tools.contract import Tool


def _dummy_handler(*args, **kwargs):
    """Dummy handler for testing."""
    return {"result": "ok"}


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_register_and_get(self) -> None:
        """Can register and retrieve a tool."""
        registry = ToolRegistry()
        tool = Tool(name="search", description="Search tool")
        registry.register(tool, _dummy_handler)

        retrieved = registry.get("search")
        assert retrieved is not None
        assert retrieved.name == "search"

    def test_get_handler(self) -> None:
        """Can retrieve the handler for a tool."""
        registry = ToolRegistry()
        tool = Tool(name="search", description="Search tool")
        registry.register(tool, _dummy_handler)

        handler = registry.get_handler("search")
        assert handler is _dummy_handler

    def test_has(self) -> None:
        """Can check if tool exists."""
        registry = ToolRegistry()
        tool = Tool(name="search", description="Search tool")
        registry.register(tool, _dummy_handler)

        assert registry.has("search") is True
        assert registry.has("missing") is False

    def test_unknown_tool_returns_none(self) -> None:
        """Getting unknown tool returns None."""
        registry = ToolRegistry()
        assert registry.get("missing") is None
        assert registry.get_handler("missing") is None

    def test_list_tools(self) -> None:
        """Can list all registered tools."""
        registry = ToolRegistry()
        tool1 = Tool(name="search", description="Search tool")
        tool2 = Tool(name="parse", description="Parse tool")

        registry.register(tool1, _dummy_handler)
        registry.register(tool2, _dummy_handler)

        tools = registry.all_tools()
        assert len(tools) == 2
        assert tools[0].name in ["search", "parse"]
        assert tools[1].name in ["search", "parse"]

    def test_list_names(self) -> None:
        """Can list all tool names."""
        registry = ToolRegistry()
        registry.register(Tool(name="search", description="Search"), _dummy_handler)
        registry.register(Tool(name="parse", description="Parse"), _dummy_handler)

        names = registry.list_names()
        assert set(names) == {"search", "parse"}

    def test_empty_name_rejected_by_tool(self) -> None:
        """Cannot create tool with empty name."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            Tool(name="", description="Tool")

    def test_duplicate_registration_rejected(self) -> None:
        """Cannot register same tool twice."""
        registry = ToolRegistry()
        tool = Tool(name="search", description="Search")

        registry.register(tool, _dummy_handler)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool, _dummy_handler)

    def test_tool_is_immutable(self) -> None:
        """Tool objects are frozen and cannot be mutated."""
        tool = Tool(name="search", description="Search tool")

        with pytest.raises(AttributeError):
            tool.name = "modified"  # type: ignore
