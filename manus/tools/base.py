"""Base tool class for Manus agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ToolStatus(Enum):
    """Tool execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ToolResult:
    """Result of tool execution."""
    tool_name: str
    status: ToolStatus
    content: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    duration: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "status": self.status.value,
            "content": self.content,
            "error": self.error,
            "metadata": self.metadata,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
        }


class Tool(ABC):
    """Base class for all tools."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any] | None = None,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters or {}

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def get_schema(self) -> dict[str, Any]:
        """Get tool schema for LLM function calling."""
        schema = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }

        if self.parameters:
            schema["function"]["parameters"]["properties"] = {
                k: v.get("schema", {}) for k, v in self.parameters.items()
            }
            schema["function"]["parameters"]["required"] = [
                k for k, v in self.parameters.items() if v.get("required", False)
            ]

        return schema

    async def execute_with_timing(self, **kwargs) -> ToolResult:
        """Execute tool with timing."""
        start = datetime.now()
        try:
            result = await self.execute(**kwargs)
            result.duration = (datetime.now() - start).total_seconds()
            result.completed_at = datetime.now()
            return result
        except Exception as e:
            result = ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )
            result.duration = (datetime.now() - start).total_seconds()
            result.completed_at = datetime.now()
            return result
