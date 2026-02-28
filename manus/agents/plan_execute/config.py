"""Plan Execute configuration and types."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class ExecuteMode(str, Enum):
    """Execution mode."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"


class StepExecutionMode(str, Enum):
    """Single step execution mode."""
    REACT = "react"
    DIRECT = "direct"
    AGENT = "agent"


@dataclass
class PlanExecuteConfig:
    """Plan->Execute configuration."""
    planner_model: str = "gpt-4o"
    executor_model: str = "gpt-4o-mini"
    verifier_model: str = "claude-3-5-sonnet-20241022"
    
    mode: ExecuteMode = ExecuteMode.SEQUENTIAL
    max_iterations: int = 3
    max_steps_per_phase: int = 50
    timeout: int = 1800
    
    enable_retry: bool = True
    max_retries: int = 2
    retry_on_error: bool = True
    
    enable_verification: bool = True
    verify_each_step: bool = False
    
    max_concurrent_steps: int = 5
    
    enable_db_record: bool = True


@dataclass
class StepResult:
    """Single step execution result."""
    step_id: str
    description: str
    status: str
    result: str | None = None
    error: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    duration_ms: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    retry_count: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "tool_calls": self.tool_calls,
            "retry_count": self.retry_count,
        }


@dataclass
class PlanExecuteResult:
    """Complete plan->execute result."""
    task_id: str
    original_input: str
    status: str
    
    plan: dict[str, Any] | None = None
    steps: list[StepResult] = field(default_factory=list)
    
    final_result: str | None = None
    error: str | None = None
    
    iterations: int = 0
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int = 0
    
    verification: dict[str, Any] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "original_input": self.original_input,
            "status": self.status,
            "plan": self.plan,
            "steps": [s.to_dict() for s in self.steps],
            "final_result": self.final_result,
            "error": self.error,
            "iterations": self.iterations,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "verification": self.verification,
        }


class PlanExecuteCallbacks:
    """Plan->Execute execution callbacks."""
    
    def __init__(self):
        self.on_plan_created: Callable[[dict], None] | None = None
        self.on_plan_started: Callable[[], None] | None = None
        self.on_step_start: Callable[[StepResult], None] | None = None
        self.on_step_complete: Callable[[StepResult], None] | None = None
        self.on_step_error: Callable[[StepResult, Exception], None] | None = None
        self.on_step_retry: Callable[[StepResult, int], None] | None = None
        self.on_iteration: Callable[[int, int], None] | None = None
        self.on_verification: Callable[[dict], None] | None = None
        self.on_token: Callable[[str], None] | None = None
        self.on_thinking: Callable[[str], None] | None = None
        self.on_status_change: Callable[[str], None] | None = None
        self.on_progress: Callable[[float], None] | None = None
    
    def emit_plan_created(self, plan: dict):
        if self.on_plan_created:
            try:
                self.on_plan_created(plan)
            except Exception:
                pass
    
    def emit_plan_started(self):
        if self.on_plan_started:
            try:
                self.on_plan_started()
            except Exception:
                pass
    
    def emit_step_start(self, step: StepResult):
        if self.on_step_start:
            try:
                self.on_step_start(step)
            except Exception:
                pass
    
    def emit_step_complete(self, step: StepResult):
        if self.on_step_complete:
            try:
                self.on_step_complete(step)
            except Exception:
                pass
    
    def emit_step_error(self, step: StepResult, error: Exception):
        if self.on_step_error:
            try:
                self.on_step_error(step, error)
            except Exception:
                pass
    
    def emit_step_retry(self, step: StepResult, attempt: int):
        if self.on_step_retry:
            try:
                self.on_step_retry(step, attempt)
            except Exception:
                pass
    
    def emit_iteration(self, current: int, total: int):
        if self.on_iteration:
            try:
                self.on_iteration(current, total)
            except Exception:
                pass
    
    def emit_verification(self, verification: dict):
        if self.on_verification:
            try:
                self.on_verification(verification)
            except Exception:
                pass
    
    def emit_token(self, token: str):
        if self.on_token:
            try:
                self.on_token(token)
            except Exception:
                pass
    
    def emit_thinking(self, reasoning: str):
        if self.on_thinking:
            try:
                self.on_thinking(reasoning)
            except Exception:
                pass
    
    def emit_status_change(self, status: str):
        if self.on_status_change:
            try:
                self.on_status_change(status)
            except Exception:
                pass
    
    def emit_progress(self, progress: float):
        if self.on_progress:
            try:
                self.on_progress(progress)
            except Exception:
                pass


__all__ = [
    "ExecuteMode",
    "StepExecutionMode",
    "PlanExecuteConfig",
    "StepResult",
    "PlanExecuteResult",
    "PlanExecuteCallbacks",
]
