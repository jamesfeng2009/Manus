"""Cross-task context manager for managing user profiles, task history, and tool experience."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from manus.core.constants import MEMORY_DIR


@dataclass
class UserProfile:
    """User profile with preferences and context."""

    user_id: str
    name: str | None = None
    preferences: dict[str, Any] = field(default_factory=dict)
    default_model: str | None = None
    default_tools: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "preferences": self.preferences,
            "default_model": self.default_model,
            "default_tools": self.default_tools,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserProfile":
        return cls(
            user_id=data["user_id"],
            name=data.get("name"),
            preferences=data.get("preferences", {}),
            default_model=data.get("default_model"),
            default_tools=data.get("default_tools", []),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now().isoformat())),
            last_active=datetime.fromisoformat(data.get("last_active", datetime.now().isoformat())),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TaskSummary:
    """Summary of a completed task."""

    task_id: str
    user_id: str
    original_input: str
    status: str
    model_used: str | None
    tools_used: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    success: bool = False
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "original_input": self.original_input,
            "status": self.status,
            "model_used": self.model_used,
            "tools_used": self.tools_used,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskSummary":
        return cls(
            task_id=data["task_id"],
            user_id=data["user_id"],
            original_input=data.get("original_input", ""),
            status=data.get("status", "unknown"),
            model_used=data.get("model_used"),
            tools_used=data.get("tools_used", []),
            started_at=datetime.fromisoformat(data.get("started_at", datetime.now().isoformat())),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            duration_seconds=data.get("duration_seconds"),
            success=data.get("success", False),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ToolExperience:
    """Tool usage experience and statistics."""

    tool_name: str
    user_id: str
    success_count: int = 0
    failure_count: int = 0
    total_duration: float = 0.0
    last_used: datetime | None = None
    last_success: datetime | None = None
    last_failure: datetime | None = None
    avg_satisfaction: float = 0.0
    user_preferences: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "user_id": self.user_id,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_duration": self.total_duration,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "avg_satisfaction": self.avg_satisfaction,
            "user_preferences": self.user_preferences,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolExperience":
        return cls(
            tool_name=data["tool_name"],
            user_id=data["user_id"],
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            total_duration=data.get("total_duration", 0.0),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            last_success=datetime.fromisoformat(data["last_success"]) if data.get("last_success") else None,
            last_failure=datetime.fromisoformat(data["last_failure"]) if data.get("last_failure") else None,
            avg_satisfaction=data.get("avg_satisfaction", 0.0),
            user_preferences=data.get("user_preferences", {}),
        )


class CrossTaskContext:
    """Manages cross-task context including user profiles, task history, and tool experience."""

    USER_FILE = "users.json"
    TASK_FILE = "task_history.json"
    TOOL_FILE = "tool_experience.json"

    MAX_TASK_HISTORY = 1000

    def __init__(self, memory_dir: Path | None = None):
        self._memory_dir = memory_dir or MEMORY_DIR
        self._users: dict[str, UserProfile] = {}
        self._tasks: dict[str, TaskSummary] = {}
        self._tool_exp: dict[tuple[str, str], ToolExperience] = {}
        self._load_data()

    def _load_data(self) -> None:
        self._memory_dir.mkdir(parents=True, exist_ok=True)

        user_file = self._memory_dir / self.USER_FILE
        if user_file.exists():
            try:
                with open(user_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_data in data.get("users", []):
                        user = UserProfile.from_dict(user_data)
                        self._users[user.user_id] = user
            except Exception:
                pass

        task_file = self._memory_dir / self.TASK_FILE
        if task_file.exists():
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for task_data in data.get("tasks", []):
                        task = TaskSummary.from_dict(task_data)
                        self._tasks[task.task_id] = task
            except Exception:
                pass

        tool_file = self._memory_dir / self.TOOL_FILE
        if tool_file.exists():
            try:
                with open(tool_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for tool_data in data.get("tools", []):
                        exp = ToolExperience.from_dict(tool_data)
                        key = (exp.tool_name, exp.user_id)
                        self._tool_exp[key] = exp
            except Exception:
                pass

    def _save_users(self) -> None:
        user_file = self._memory_dir / self.USER_FILE
        data = {"users": [u.to_dict() for u in self._users.values()]}
        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_tasks(self) -> None:
        task_file = self._memory_dir / self.TASK_FILE
        data = {"tasks": [t.to_dict() for t in self._tasks.values()]}
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_tools(self) -> None:
        tool_file = self._memory_dir / self.TOOL_FILE
        data = {"tools": [t.to_dict() for t in self._tool_exp.values()]}
        with open(tool_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_or_create_user(self, user_id: str) -> UserProfile:
        """Get existing user or create new one."""
        if user_id not in self._users:
            self._users[user_id] = UserProfile(user_id=user_id)
            self._save_users()
        user = self._users[user_id]
        user.last_active = datetime.now()
        self._save_users()
        return user

    def update_user(self, user_id: str, **kwargs) -> UserProfile | None:
        """Update user profile."""
        if user_id not in self._users:
            return None

        user = self._users[user_id]
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        self._save_users()
        return user

    def get_user(self, user_id: str) -> UserProfile | None:
        """Get user profile."""
        return self._users.get(user_id)

    def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        """Get user preferences."""
        user = self._users.get(user_id)
        return user.preferences if user else {}

    def set_user_preference(self, user_id: str, key: str, value: Any) -> None:
        """Set user preference."""
        user = self.get_or_create_user(user_id)
        user.preferences[key] = value
        self._save_users()

    def record_task_start(
        self,
        task_id: str,
        user_id: str,
        original_input: str,
        model_used: str | None = None,
    ) -> TaskSummary:
        """Record task start."""
        task = TaskSummary(
            task_id=task_id,
            user_id=user_id,
            original_input=original_input,
            status="running",
            model_used=model_used,
        )
        self._tasks[task_id] = task
        self._save_tasks()
        return task

    def record_task_complete(
        self,
        task_id: str,
        success: bool,
        error_message: str | None = None,
    ) -> TaskSummary | None:
        """Record task completion."""
        if task_id not in self._tasks:
            return None

        task = self._tasks[task_id]
        task.status = "completed" if success else "failed"
        task.completed_at = datetime.now()
        task.duration_seconds = (task.completed_at - task.started_at).total_seconds()
        task.success = success
        task.error_message = error_message

        self._save_tasks()
        return task

    def add_tool_usage(
        self,
        task_id: str,
        tool_name: str,
        success: bool,
        duration: float,
        user_id: str,
    ) -> None:
        """Record tool usage for a task."""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            if tool_name not in task.tools_used:
                task.tools_used.append(tool_name)
            self._save_tasks()

        key = (tool_name, user_id)
        if key not in self._tool_exp:
            self._tool_exp[key] = ToolExperience(tool_name=tool_name, user_id=user_id)

        exp = self._tool_exp[key]
        exp.total_duration += duration
        exp.last_used = datetime.now()

        if success:
            exp.success_count += 1
            exp.last_success = datetime.now()
        else:
            exp.failure_count += 1
            exp.last_failure = datetime.now()

        self._save_tools()

    def get_tool_experience(self, tool_name: str, user_id: str) -> ToolExperience | None:
        """Get tool experience for a user."""
        key = (tool_name, user_id)
        return self._tool_exp.get(key)

    def get_recent_tasks(self, user_id: str, limit: int = 10) -> list[TaskSummary]:
        """Get recent tasks for a user."""
        user_tasks = [
            t for t in self._tasks.values() if t.user_id == user_id
        ]
        return sorted(user_tasks, key=lambda t: t.started_at, reverse=True)[:limit]

    def get_task_stats(self, user_id: str) -> dict[str, Any]:
        """Get task statistics for a user."""
        user_tasks = [t for t in self._tasks.values() if t.user_id == user_id]
        
        completed = [t for t in user_tasks if t.status == "completed"]
        failed = [t for t in user_tasks if t.status == "failed"]
        
        durations = [t.duration_seconds for t in completed if t.duration_seconds]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "total_tasks": len(user_tasks),
            "completed": len(completed),
            "failed": len(failed),
            "success_rate": len(completed) / len(user_tasks) if user_tasks else 0,
            "avg_duration": avg_duration,
        }

    def get_recommended_tools(self, user_id: str) -> list[tuple[str, float]]:
        """Get recommended tools based on user history."""
        user_tools = [
            exp for exp in self._tool_exp.values() if exp.user_id == user_id
        ]
        
        recommendations = []
        for exp in user_tools:
            score = exp.success_rate * 0.7 + (1.0 / (1.0 + exp.total_duration)) * 0.3
            recommendations.append((exp.tool_name, score))
        
        return sorted(recommendations, key=lambda x: x[1], reverse=True)


_cross_task_context: CrossTaskContext | None = None


def get_cross_task_context() -> CrossTaskContext:
    """Get global cross-task context instance."""
    global _cross_task_context
    if _cross_task_context is None:
        _cross_task_context = CrossTaskContext()
    return _cross_task_context
