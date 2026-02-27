import asyncio
import json
from typing import Any, AsyncGenerator
from dataclasses import dataclass


@dataclass
class TaskInfo:
    task_id: str
    status: str
    progress: float
    result: dict[str, Any] | None
    error: str | None


class TaskClient:
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._headers = {}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    async def submit_task(
        self,
        task_type: str,
        input_data: dict[str, Any],
        user_id: str = "default",
    ) -> TaskInfo:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/queue/submit",
                json={
                    "user_id": user_id,
                    "task_type": task_type,
                    "input_data": input_data,
                },
                headers=self._headers,
            ) as resp:
                data = await resp.json()
                return TaskInfo(
                    task_id=data["task_id"],
                    status=data["status"],
                    progress=0.0,
                    result=None,
                    error=None,
                )

    async def get_task(self, task_id: str) -> TaskInfo:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/queue/tasks/{task_id}",
                headers=self._headers,
            ) as resp:
                data = await resp.json()
                return TaskInfo(
                    task_id=data["id"],
                    status=data["status"],
                    progress=data.get("progress", 0.0),
                    result=data.get("result"),
                    error=data.get("error"),
                )

    async def list_tasks(self, user_id: str = "default") -> list[TaskInfo]:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/queue/tasks?user_id={user_id}",
                headers=self._headers,
            ) as resp:
                data = await resp.json()
                return [
                    TaskInfo(
                        task_id=t["id"],
                        status=t["status"],
                        progress=t.get("progress", 0.0),
                        result=t.get("result"),
                        error=t.get("error"),
                    )
                    for t in data
                ]

    async def cancel_task(self, task_id: str) -> bool:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{self.base_url}/api/queue/tasks/{task_id}",
                headers=self._headers,
            ) as resp:
                return resp.status == 200

    async def listen(self, task_id: str) -> AsyncGenerator[dict[str, Any], None]:
        import aiohttp

        ws_url = f"ws://{self.base_url.replace('http://', '')}/ws/queue?task_id={task_id}"

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        yield json.loads(msg.data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        break


class SyncTaskClient:
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str | None = None):
        self._client = TaskClient(base_url, api_key)

    def submit_task(self, task_type: str, input_data: dict[str, Any], user_id: str = "default") -> TaskInfo:
        return asyncio.run(self._client.submit_task(task_type, input_data, user_id))

    def get_task(self, task_id: str) -> TaskInfo:
        return asyncio.run(self._client.get_task(task_id))

    def list_tasks(self, user_id: str = "default") -> list[TaskInfo]:
        return asyncio.run(self._client.list_tasks(user_id))

    def cancel_task(self, task_id: str) -> bool:
        return asyncio.run(self._client.cancel_task(task_id))

    def wait_for_result(self, task_id: str, timeout: float = 300.0) -> TaskInfo:
        import time

        start = time.time()
        while time.time() - start < timeout:
            task = self.get_task(task_id)
            if task.status in ("completed", "failed", "cancelled"):
                return task
            time.sleep(1)

        return TaskInfo(
            task_id=task_id,
            status="timeout",
            progress=0.0,
            result=None,
            error="Timeout waiting for result",
        )
