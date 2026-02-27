"""Callback system for ReActExecutor."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class ExecutionStatus(Enum):
    """Execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class StepRecord:
    """Record of a single execution step."""
    step: int
    thought: str
    action: str
    action_params: dict
    observation: str
    tool_name: str | None = None
    tool_result: str | None = None
    error: str | None = None
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionState:
    """Current execution state."""
    task_id: str
    task: str
    current_step: int = 0
    max_steps: int = 50
    history: list[StepRecord] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    error: str | None = None
    final_result: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task": self.task,
            "current_step": self.current_step,
            "max_steps": self.max_steps,
            "status": self.status.value,
            "history": [
                {
                    "step": r.step,
                    "thought": r.thought,
                    "action": r.action,
                    "observation": r.observation[:500] if r.observation else None,
                    "tool_name": r.tool_name,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                }
                for r in self.history
            ],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "final_result": self.final_result,
        }


@dataclass
class ExecutionResult:
    """Result of execution."""
    task_id: str
    status: ExecutionStatus
    final_result: str | None = None
    error: str | None = None
    total_steps: int = 0
    duration_ms: int = 0
    history: list[StepRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "final_result": self.final_result,
            "error": self.error,
            "total_steps": self.total_steps,
            "duration_ms": self.duration_ms,
        }


class ExecutorCallbacks:
    """Callbacks for execution events."""

    def __init__(self):
        self.on_thinking: Callable[[str], None] | None = None
        self.on_action: Callable[[str, dict], None] | None = None
        self.on_observation: Callable[[str], None] | None = None
        self.on_error: Callable[[Exception], None] | None = None
        self.on_step_complete: Callable[[StepRecord], None] | None = None
        self.on_complete: Callable[[ExecutionResult], None] | None = None
        self.on_token: Callable[[str], None] | None = None
        self.on_status_change: Callable[[ExecutionStatus], None] | None = None

    def emit_thinking(self, thought: str):
        if self.on_thinking:
            try:
                self.on_thinking(thought)
            except Exception:
                pass

    def emit_action(self, action: str, params: dict):
        if self.on_action:
            try:
                self.on_action(action, params)
            except Exception:
                pass

    def emit_observation(self, observation: str):
        if self.on_observation:
            try:
                self.on_observation(observation)
            except Exception:
                pass

    def emit_error(self, error: Exception):
        if self.on_error:
            try:
                self.on_error(error)
            except Exception:
                pass

    def emit_step_complete(self, step: StepRecord):
        if self.on_step_complete:
            try:
                self.on_step_complete(step)
            except Exception:
                pass

    def emit_complete(self, result: ExecutionResult):
        if self.on_complete:
            try:
                self.on_complete(result)
            except Exception:
                pass

    def emit_token(self, token: str):
        if self.on_token:
            try:
                self.on_token(token)
            except Exception:
                pass

    def emit_status_change(self, status: ExecutionStatus):
        if self.on_status_change:
            try:
                self.on_status_change(status)
            except Exception:
                pass
