import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Any, Callable
import asyncio


@dataclass
class TaskEvent:
    event_type: str
    task_id: str
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "task_id": self.task_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class WSConnection:
    def __init__(self, connection_id: str, user_id: str, send_callback: Callable):
        self.connection_id = connection_id
        self.user_id = user_id
        self._send_callback = send_callback

    async def send(self, event: TaskEvent):
        await self._send_callback(event.to_json())


class WSManager:
    def __init__(self):
        self._connections: dict[str, WSConnection] = {}
        self._user_connections: dict[str, set[str]] = {}
        self._task_subscriptions: dict[str, set[str]] = {}

    def add_connection(self, connection_id: str, user_id: str, send_callback: Callable):
        conn = WSConnection(connection_id, user_id, send_callback)
        self._connections[connection_id] = conn

        if user_id not in self._user_connections:
            self._user_connections[user_id] = set()
        self._user_connections[user_id].add(connection_id)

    def remove_connection(self, connection_id: str):
        if connection_id in self._connections:
            conn = self._connections[connection_id]
            user_id = conn.user_id

            if user_id in self._user_connections:
                self._user_connections[user_id].discard(connection_id)

            del self._connections[connection_id]

    def subscribe_task(self, connection_id: str, task_id: str):
        if task_id not in self._task_subscriptions:
            self._task_subscriptions[task_id] = set()
        self._task_subscriptions[task_id].add(connection_id)

    def unsubscribe_task(self, connection_id: str, task_id: str):
        if task_id in self._task_subscriptions:
            self._task_subscriptions[task_id].discard(connection_id)

    async def send_to_connection(self, connection_id: str, event: TaskEvent):
        if connection_id in self._connections:
            try:
                await self._connections[connection_id].send(event)
            except Exception:
                pass

    async def send_to_user(self, user_id: str, event: TaskEvent):
        if user_id in self._user_connections:
            for conn_id in self._user_connections[user_id]:
                await self.send_to_connection(conn_id, event)

    async def send_to_task(self, task_id: str, event: TaskEvent):
        if task_id in self._task_subscriptions:
            for conn_id in self._task_subscriptions[task_id]:
                await self.send_to_connection(conn_id, event)

    async def broadcast(self, event: TaskEvent):
        for conn in self._connections.values():
            try:
                await conn.send(event)
            except Exception:
                pass


_ws_manager: WSManager | None = None


def get_ws_manager() -> WSManager:
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WSManager()
    return _ws_manager


async def broadcast_progress(task_id: str, progress: float, message: str = ""):
    event = TaskEvent(
        event_type="progress",
        task_id=task_id,
        data={"progress": progress, "message": message},
    )
    ws = get_ws_manager()
    await ws.send_to_task(task_id, event)


async def broadcast_status(task_id: str, status: str):
    event = TaskEvent(
        event_type="status",
        task_id=task_id,
        data={"status": status},
    )
    ws = get_ws_manager()
    await ws.send_to_task(task_id, event)


async def broadcast_result(task_id: str, result: dict[str, Any]):
    event = TaskEvent(
        event_type="result",
        task_id=task_id,
        data={"result": result},
    )
    ws = get_ws_manager()
    await ws.send_to_task(task_id, event)


async def broadcast_error(task_id: str, error: str):
    event = TaskEvent(
        event_type="error",
        task_id=task_id,
        data={"error": error},
    )
    ws = get_ws_manager()
    await ws.send_to_task(task_id, event)
