"""Tool definitions, execution contracts, and tool registry."""

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ValidationError


class ToolCategory(StrEnum):
    READ = "read"  # Read-only query tools with zero side-effects
    PROPOSE = "propose"  # Prepares draft mutations requiring human confirmation
    TERMINAL = "terminal"  # Concludes the agent session (e.g. submit_recommendation)


class ToolDefinition:
    """Strongly typed tool declaration and execution wrapper."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters_schema: type[BaseModel],
        category: ToolCategory,
        handler: Callable[..., Any],
    ) -> None:
        self.name = name
        self.description = description
        self.parameters_schema = parameters_schema
        self.category = category
        self.handler = handler

    def to_declaration(self) -> dict[str, Any]:
        """Converts tool definition to standard model function declaration."""
        schema = self.parameters_schema.model_json_schema()
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", []),
            },
        }

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Validates arguments against parameters_schema and executes the handler."""
        try:
            validated_args = self.parameters_schema.model_validate(arguments)
        except ValidationError as exc:
            return {"error": f"Tool argument validation failed: {exc}"}

        try:
            result = self.handler(validated_args)
            if isinstance(result, BaseModel):
                return result.model_dump()
            if isinstance(result, dict):
                return result
            return {"result": result}
        except Exception as exc:
            return {"error": f"Tool execution failed: {exc}"}


class ToolRegistry:
    """Registry managing available tools for an agent."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def to_declarations(self) -> list[dict[str, Any]]:
        return [tool.to_declaration() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self.get(name)
        if not tool:
            return {"error": f"Tool '{name}' is not registered."}
        return tool.execute(arguments)
