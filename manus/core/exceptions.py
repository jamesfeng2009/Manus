"""Core exceptions for Manus."""

from typing import Any


class ManusError(Exception):
    """Base exception for Manus."""
    pass


class ModelError(ManusError):
    """Model-related errors."""
    pass


class ModelTimeoutError(ModelError):
    """Model request timeout."""
    pass


class ModelRateLimitError(ModelError):
    """Model rate limit exceeded."""
    pass


class ModelAuthenticationError(ModelError):
    """Model authentication failed."""
    pass


class ToolError(ManusError):
    """Tool-related errors."""
    pass


class ToolNotFoundError(ToolError):
    """Tool not found."""
    pass


class ToolExecutionError(ToolError):
    """Tool execution failed."""
    pass


class ToolPermissionError(ToolError):
    """Tool permission denied."""
    pass


class TaskError(ManusError):
    """Task-related errors."""
    pass


class TaskPlanningError(TaskError):
    """Task planning failed."""
    pass


class TaskExecutionError(TaskError):
    """Task execution failed."""
    pass


class TaskRetryExhaustedError(TaskError):
    """Task retries exhausted."""
    pass


class ConfigurationError(ManusError):
    """Configuration-related errors."""
    pass


class ValidationError(ManusError):
    """Validation errors."""
    pass
