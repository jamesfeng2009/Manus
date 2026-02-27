from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(str, Enum):
    TASK_PROGRESS = "task.progress"
    TASK_STATUS = "task.status"
    TASK_RESULT = "task.result"
    TASK_ERROR = "task.error"
    TASK_LOG = "task.log"

    AGENT_THINKING = "agent.thinking"
    AGENT_ACTION = "agent.action"
    AGENT_TOOL_CALL = "agent.tool_call"
    AGENT_TOOL_RESULT = "agent.tool_result"
    AGENT_TOKEN = "agent.token"
    AGENT_COMPLETE = "agent.complete"

    CONNECT = "system.connect"
    DISCONNECT = "system.disconnect"
    PING = "system.ping"
    PONG = "system.pong"

    DISCORD_MESSAGE = "discord.message"
    DISCORD_READY = "discord.ready"


@dataclass
class WSMessage:
    event: EventType
    data: dict[str, Any]
    task_id: str | None = None
    user_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event.value,
            "data": self.data,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict())


@dataclass
class SSEMessage:
    event: str
    data: str
    id: str | None = None
    retry: int | None = None

    def to_sse(self) -> str:
        parts = []
        if self.id:
            parts.append(f"id: {self.id}")
        parts.append(f"event: {self.event}")
        parts.append(f"data: {self.data}")
        if self.retry:
            parts.append(f"retry: {self.retry}")
        return "\n".join(parts) + "\n\n"
