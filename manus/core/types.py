"""Core type definitions for Manus."""

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class AgentType(str, Enum):
    """Agent types in the system."""
    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"


class ToolPermission(str, Enum):
    """Tool execution permission levels."""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class MessageRole(str, Enum):
    """Message role in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """Chat message."""
    role: MessageRole
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class ToolCall(BaseModel):
    """Tool call from agent."""
    id: str
    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    """Result from tool execution."""
    tool_call_id: str
    output: str | dict[str, Any]
    error: str | None = None


class TaskStep(BaseModel):
    """A single step in a task plan."""
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    result: str | None = None
    error: str | None = None
    retry_count: int = 0


class TaskPlan(BaseModel):
    """Task execution plan."""
    task_id: str
    original_input: str
    steps: list[TaskStep]
    current_step_index: int = 0
    status: TaskStatus = TaskStatus.PENDING
    created_at: str | None = None
    updated_at: str | None = None


class ModelInfo(BaseModel):
    """Model information."""
    id: str
    name: str
    capabilities: list[str] = Field(default_factory=list)
    max_tokens: int = 4096
    supports_json: bool = False


class ProviderInfo(BaseModel):
    """LLM provider information."""
    provider: str
    name: str
    api_key_env: str
    base_url: str
    models: list[ModelInfo] = Field(default_factory=list)


class ConfigDefaults(BaseModel):
    """Default configuration."""
    default_model: str = "gpt-4o"
    planner_model: str = "gpt-4o"
    executor_model: str = "gpt-4o-mini"
    verifier_model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    max_tokens: int = 4096


class AppConfig(BaseModel):
    """Main application configuration."""
    models: list[ProviderInfo] = Field(default_factory=list)
    defaults: ConfigDefaults = Field(default_factory=ConfigDefaults)
