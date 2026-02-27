from typing import AsyncGenerator, Callable, Any
import asyncio

from litestar.response import ServerSentEvent


class SSECollection:
    _events: dict[str, asyncio.Queue] = {}

    @classmethod
    def subscribe(cls, task_id: str) -> asyncio.Queue:
        if task_id not in cls._events:
            cls._events[task_id] = asyncio.Queue()
        return cls._events[task_id]

    @classmethod
    def unsubscribe(cls, task_id: str):
        if task_id in cls._events:
            del cls._events[task_id]

    @classmethod
    async def publish(cls, task_id: str, event: str, data: str):
        if task_id in cls._events:
            await cls._events[task_id].put({"event": event, "data": data})


async def sse_event_stream(
    task_id: str,
    user_input: str | None = None,
) -> AsyncGenerator[ServerSentEvent, None]:
    queue = SSECollection.subscribe(task_id)

    try:
        if user_input:
            from manus.agents.react import ReActAgent

            agent = ReActAgent(model_id="gpt-4o")
            buffer = ""

            async def on_token(token: str):
                nonlocal buffer
                buffer += token
                await SSECollection.publish(task_id, "agent.token", token)

            async def on_thinking(reasoning: str):
                await SSECollection.publish(task_id, "agent.thinking", reasoning)

            async def on_tool_call(tool_name: str, args: dict):
                import json
                await SSECollection.publish(
                    task_id,
                    "agent.tool_call",
                    json.dumps({"tool": tool_name, "args": args}),
                )

            async def on_tool_result(tool_name: str, result: str):
                await SSECollection.publish(
                    task_id,
                    "agent.tool_result",
                    result,
                )

            agent.on_token = on_token
            agent.on_thinking = on_thinking
            agent.on_tool_call = on_tool_call
            agent.on_tool_result = on_tool_result

            try:
                result = await agent.execute(task_id, user_input)
                final_response = result.get("final_response", "")
                await SSECollection.publish(task_id, "agent.complete", final_response)
                await SSECollection.publish(task_id, "task.result", str(final_response))
            except Exception as e:
                await SSECollection.publish(task_id, "task.error", str(e))

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                yield ServerSentEvent(
                    data=event["data"],
                    event=event["event"],
                )
            except asyncio.TimeoutError:
                yield ServerSentEvent(data="", event="ping")
    finally:
        SSECollection.unsubscribe(task_id)


async def task_progress_stream(
    task_id: str,
) -> AsyncGenerator[ServerSentEvent, None]:
    from manus.db import get_database
    from manus.db.models import Task

    db = get_database()

    with db.get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if task:
            yield ServerSentEvent(
                data=str(task.progress),
                event="task.progress",
            )
            yield ServerSentEvent(
                data=task.status,
                event="task.status",
            )


class StreamHandler:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.buffer = ""

    async def on_token(self, token: str):
        self.buffer += token
        await SSECollection.publish(self.task_id, "agent.token", token)

    async def on_thinking(self, reasoning: str):
        await SSECollection.publish(self.task_id, "agent.thinking", reasoning)

    async def on_tool_call(self, tool_name: str, args: dict):
        import json
        await SSECollection.publish(
            self.task_id,
            "agent.tool_call",
            json.dumps({"tool": tool_name, "args": args}),
        )

    async def on_complete(self):
        await SSECollection.publish(self.task_id, "agent.complete", self.buffer)

    async def on_error(self, error: str):
        await SSECollection.publish(self.task_id, "task.error", error)

    async def on_progress(self, progress: float, message: str):
        await SSECollection.publish(
            self.task_id,
            "task.progress",
            f"{progress}:{message}",
        )
