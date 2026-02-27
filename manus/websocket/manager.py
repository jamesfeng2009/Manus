import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from typing import Callable, Awaitable

from manus.websocket.events import WSMessage, EventType


@dataclass
class Connection:
    id: str
    user_id: str
    task_id: str | None = None
    websocket = None
    connected_at: datetime = field(default_factory=datetime.now)


class WSManager:
    def __init__(self):
        self._connections: dict[str, Connection] = {}
        self._user_connections: dict[str, set[str]] = defaultdict(set)
        self._task_connections: dict[str, set[str]] = defaultdict(set)
        self._callbacks: dict[str, list[Callable]] = defaultdict(list)

    def add_connection(
        self,
        conn_id: str,
        user_id: str,
        websocket,
        task_id: str | None = None,
    ):
        conn = Connection(
            id=conn_id,
            user_id=user_id,
            task_id=task_id,
            websocket=websocket,
        )
        self._connections[conn_id] = conn
        self._user_connections[user_id].add(conn_id)
        if task_id:
            self._task_connections[task_id].add(conn_id)

    def remove_connection(self, conn_id: str):
        if conn_id in self._connections:
            conn = self._connections[conn_id]
            self._user_connections[conn.user_id].discard(conn_id)
            if conn.task_id:
                self._task_connections[conn.task_id].discard(conn_id)
            del self._connections[conn_id]

    async def send(self, conn_id: str, message: WSMessage):
        if conn_id in self._connections:
            conn = self._connections[conn_id]
            if conn.websocket:
                try:
                    await conn.websocket.send(message.to_json())
                except Exception:
                    pass

    async def send_to_user(self, user_id: str, message: WSMessage):
        for conn_id in self._user_connections.get(user_id, []):
            await self.send(conn_id, message)

    async def send_to_task(self, task_id: str, message: WSMessage):
        for conn_id in self._task_connections.get(task_id, []):
            await self.send(conn_id, message)

    async def broadcast(self, message: WSMessage):
        for conn_id in self._connections:
            await self.send(conn_id, message)

    def subscribe(self, event: str, callback: Callable[[WSMessage], Awaitable[None]]):
        self._callbacks[event].append(callback)

    async def notify(self, event: str, message: WSMessage):
        for callback in self._callbacks.get(event, []):
            try:
                await callback(message)
            except Exception:
                pass

    def get_user_tasks(self, user_id: str) -> list[str]:
        return list(self._user_connections.get(user_id, set()))

    def get_connection_count(self) -> int:
        return len(self._connections)


_ws_manager: WSManager | None = None


def get_ws_manager() -> WSManager:
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WSManager()
    return _ws_manager
