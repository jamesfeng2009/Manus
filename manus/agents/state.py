from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class SubTaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Phase(Enum):
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    DONE = "done"


@dataclass
class SubTask:
    id: str
    description: str
    status: SubTaskStatus = SubTaskStatus.PENDING
    result: Any = None
    error: str | None = None
    dependencies: list[str] = field(default_factory=list)
    attempts: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "dependencies": self.dependencies,
            "attempts": self.attempts,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class ReflectionRecord:
    timestamp: datetime = field(default_factory=datetime.now)
    phase: str = ""
    target_task_id: str | None = None
    thought: str = ""
    action: str = ""
    result: Any = None
    success: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "phase": self.phase,
            "target_task_id": self.target_task_id,
            "thought": self.thought,
            "action": self.action,
            "result": self.result,
            "success": self.success,
        }


@dataclass
class TaskState:
    task_id: str
    original_goal: str
    current_phase: Phase = Phase.PLANNING
    subtasks: list[SubTask] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    reflection_history: list[ReflectionRecord] = field(default_factory=list)
    max_iterations: int = 10
    current_iteration: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_subtask(self, description: str, dependencies: list[str] | None = None) -> SubTask:
        subtask = SubTask(
            id=f"subtask_{uuid.uuid4().hex[:8]}",
            description=description,
            dependencies=dependencies or [],
        )
        self.subtasks.append(subtask)
        return subtask

    def get_pending_subtasks(self) -> list[SubTask]:
        return [
            st for st in self.subtasks
            if st.status == SubTaskStatus.PENDING
            and all(
                dep_id in [s.id for s in self.get_completed_subtasks()]
                for dep_id in st.dependencies
            )
        ]

    def get_completed_subtasks(self) -> list[SubTask]:
        return [st for st in self.subtasks if st.status == SubTaskStatus.COMPLETED]

    def get_failed_subtasks(self) -> list[SubTask]:
        return [st for st in self.subtasks if st.status == SubTaskStatus.FAILED]

    def add_reflection(self, phase: str, thought: str, action: str = "", result: Any = None, success: bool = True):
        record = ReflectionRecord(
            phase=phase,
            target_task_id=self.subtasks[self.current_iteration - 1].id if self.subtasks else None,
            thought=thought,
            action=action,
            result=result,
            success=success,
        )
        self.reflection_history.append(record)

    def is_complete(self) -> bool:
        return all(st.status == SubTaskStatus.COMPLETED for st in self.subtasks)

    def has_failures(self) -> bool:
        return any(st.status == SubTaskStatus.FAILED for st in self.subtasks)

    def can_continue(self) -> bool:
        if self.current_iteration >= self.max_iterations:
            return False
        if self.is_complete():
            return False
        self.current_iteration += 1
        return True

    def get_progress(self) -> float:
        if not self.subtasks:
            return 0.0
        completed = len([st for st in self.subtasks if st.status == SubTaskStatus.COMPLETED])
        return completed / len(self.subtasks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "original_goal": self.original_goal,
            "current_phase": self.current_phase.value,
            "subtasks": [st.to_dict() for st in self.subtasks],
            "context": self.context,
            "reflection_history": [r.to_dict() for r in self.reflection_history],
            "max_iterations": self.max_iterations,
            "current_iteration": self.current_iteration,
            "progress": self.get_progress(),
            "is_complete": self.is_complete(),
            "has_failures": self.has_failures(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def plan(self, subtasks: list["SubTask"]):
        """设置子任务列表（由 Planner 调用）"""
        self.subtasks = subtasks
