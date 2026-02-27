import os
import asyncio
from typing import Any
from datetime import datetime

from manus.db import get_database, TaskStatus, TaskType
from manus.queue.repository import TaskRepository
from manus.queue.websocket import broadcast_progress, broadcast_status, broadcast_result, broadcast_error
from manus.queue.manager import get_queue_manager


TASK_HANDLERS = {}


def register_handler(task_type: str):
    def decorator(func):
        TASK_HANDLERS[task_type] = func
        return func
    return decorator


@register_handler(TaskType.AGENT_EXECUTE.value)
def handle_agent_execute(task_id: str, input_data: dict[str, Any], check_cancelled=None):
    from manus.agents import AgentTeam

    async def run():
        agent = AgentTeam()

        async def progress_callback(progress: float, message: str):
            if check_cancelled and check_cancelled():
                raise asyncio.CancelledError("Task cancelled")
            await broadcast_progress(task_id, progress, message)

        result = await agent.execute(
            user_input=input_data.get("user_input", ""),
            progress_callback=progress_callback,
        )
        return result

    return asyncio.run(run())


@register_handler(TaskType.TOOL_CODE.value)
def handle_code_task(task_id: str, input_data: dict[str, Any]):
    from manus.sandbox import get_sandbox, SandboxType

    async def run():
        sandbox = get_sandbox(SandboxType.SUBPROCESS)

        result = await sandbox.execute(
            code=input_data.get("code", ""),
            language=input_data.get("language", "python"),
            timeout=input_data.get("timeout", 30),
        )

        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "execution_time": result.execution_time,
        }

    return asyncio.run(run())


@register_handler(TaskType.TOOL_SEARCH.value)
def handle_search_task(task_id: str, input_data: dict[str, Any]):
    from manus.tools import SearchTool

    async def run():
        tool = SearchTool()
        result = await tool.execute(
            query=input_data.get("query", ""),
            max_results=input_data.get("max_results", 10),
        )
        return result

    return asyncio.run(run())


@register_handler(TaskType.TOOL_BROWSER.value)
def handle_browser_task(task_id: str, input_data: dict[str, Any]):
    from manus.tools import BrowserTool

    async def run():
        tool = BrowserTool()

        action = input_data.get("action", "navigate")
        params = input_data.get("params", {})

        if action == "navigate":
            result = await tool.execute(
                url=params.get("url", ""),
            )
        elif action == "screenshot":
            result = await tool.execute(
                action="screenshot",
            )
        else:
            result = await tool.execute(action=action, **params)

        return result

    return asyncio.run(run())


@register_handler(TaskType.MULTIMODAL_AUDIO.value)
def handle_audio_task(task_id: str, input_data: dict[str, Any]):
    from manus.multimodal import AudioTool

    async def run():
        tool = AudioTool()
        result = await tool.execute(
            file_path=input_data.get("file_path", ""),
            operation=input_data.get("operation", "transcribe"),
        )
        return result

    return asyncio.run(run())


@register_handler(TaskType.MULTIMODAL_VIDEO.value)
def handle_video_task(task_id: str, input_data: dict[str, Any]):
    from manus.multimodal import VideoTool

    async def run():
        tool = VideoTool()
        result = await tool.execute(
            file_path=input_data.get("file_path", ""),
            operation=input_data.get("operation", "extract_frames"),
        )
        return result

    return asyncio.run(run())


@register_handler(TaskType.MULTIMODAL_PDF.value)
def handle_pdf_task(task_id: str, input_data: dict[str, Any]):
    from manus.multimodal import PDFTool

    async def run():
        tool = PDFTool()
        result = await tool.execute(
            file_path=input_data.get("file_path", ""),
            operation=input_data.get("operation", "extract_text"),
        )
        return result

    return asyncio.run(run())


@register_handler(TaskType.FILE_PROCESS.value)
def handle_file_task(task_id: str, input_data: dict[str, Any]):
    from manus.tools import FileManager

    async def run():
        tool = FileManager()

        operation = input_data.get("operation", "read")
        file_path = input_data.get("file_path", "")

        if operation == "read":
            result = await tool.read_file(file_path)
        elif operation == "write":
            content = input_data.get("content", "")
            result = await tool.write_file(file_path, content)
        elif operation == "list":
            directory = input_data.get("directory", ".")
            result = await tool.list_directory(directory)
        else:
            result = {"error": f"Unknown operation: {operation}"}

        return result

    return asyncio.run(run())


def process_task(task_id: str, task_type: str, input_data: dict[str, Any]) -> dict[str, Any]:
    db = get_database()
    repository = TaskRepository(db)
    queue_manager = get_queue_manager()

    task = repository.get_by_id(task_id)
    if not task:
        return {"error": f"Task {task_id} not found"}

    if not queue_manager.check_dependencies_met(task_id):
        repository.update_status(task_id, TaskStatus.PENDING)
        asyncio.run(broadcast_status(task_id, "waiting_for_dependencies"))
        if not queue_manager.wait_for_dependencies(task_id, timeout=300):
            return {"error": "Dependencies timeout"}

    repository.update_status(task_id, TaskStatus.RUNNING)
    asyncio.run(broadcast_status(task_id, "running"))

    def check_cancelled():
        task = repository.get_by_id(task_id)
        return task and task.status == TaskStatus.CANCELLED.value

    try:
        if task_type in TASK_HANDLERS:
            result = TASK_HANDLERS[task_type](task_id, input_data, check_cancelled)
        else:
            result = _default_handler(task_id, task_type, input_data)

        if check_cancelled():
            return {"cancelled": True}

        repository.update_status(task_id, TaskStatus.COMPLETED)
        repository.update_result(task_id, result, None)
        asyncio.run(broadcast_result(task_id, result))

        repository.add_event(task_id, "completed", {"result": result})

        return result

    except asyncio.CancelledError:
        repository.update_status(task_id, TaskStatus.CANCELLED)
        repository.add_event(task_id, "cancelled", {"reason": "Task was cancelled"})
        return {"cancelled": True}

    except Exception as e:
        error_msg = str(e)
        repository.update_status(task_id, TaskStatus.FAILED)
        repository.update_result(task_id, None, error_msg)
        asyncio.run(broadcast_error(task_id, error_msg))

        repository.add_event(task_id, "failed", {"error": error_msg})

        return {"error": error_msg}


def _default_handler(task_id: str, task_type: str, input_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "task_type": task_type,
        "message": "Task processed",
        "input": input_data,
    }
