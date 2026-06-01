"""Tool registry: maps tool names to tool implementations."""

from dataclasses import dataclass

from mas.tools.contract import Tool


@dataclass
class RegisteredTool:
    """A tool registered in the registry."""

    tool: Tool
    handler: callable
    """The function or callable that implements this tool."""


class ToolRegistry:
    """Registry mapping tool names to tool definitions and handlers.

    Single-threaded only; no locking. Register tools before running plans.
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, tool: Tool, handler: callable) -> None:
        """Register a tool with its handler.

        Args:
            tool: Tool definition with metadata
            handler: Callable that implements the tool

        Raises:
            ValueError: If tool name is empty or already registered
        """
        if not tool.name:
            raise ValueError("tool name cannot be empty")
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name} is already registered")

        self._tools[tool.name] = RegisteredTool(tool=tool, handler=handler)

    def get(self, tool_name: str) -> Tool | None:
        """Get a tool by name.

        Args:
            tool_name: Name of the tool to retrieve

        Returns:
            Tool definition if found, None otherwise
        """
        registered = self._tools.get(tool_name)
        return registered.tool if registered else None

    def get_handler(self, tool_name: str) -> callable | None:
        """Get the handler function for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Handler callable if found, None otherwise
        """
        registered = self._tools.get(tool_name)
        return registered.handler if registered else None

    def has(self, tool_name: str) -> bool:
        """Check if a tool is registered.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if tool is registered, False otherwise
        """
        return tool_name in self._tools

    def list(self) -> list[Tool]:
        """List all registered tools.

        Returns:
            List of Tool definitions (shallow copy)
        """
        return [registered.tool for registered in self._tools.values()]

    def list_names(self) -> list[str]:
        """List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())
