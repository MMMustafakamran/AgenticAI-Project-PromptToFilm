from __future__ import annotations

from typing import Any

from mcp.tool_registry import ToolRegistry


class ToolExecutor:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(self, tool_name: str, **kwargs: Any) -> Any:
        tool = self.registry.get(tool_name)
        return tool.execute(**kwargs)
