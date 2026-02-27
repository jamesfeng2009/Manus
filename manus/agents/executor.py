"""ReActExecutor - P0: Stable ReAct Loop Implementation."""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any

from manus.models import get_adapter
from manus.tools import ToolRegistry, get_tool_registry
from manus.agents.callbacks import (
    ExecutorCallbacks,
    ExecutionState,
    ExecutionResult,
    ExecutionStatus,
    StepRecord,
)
from manus.core.types import Message, MessageRole


DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant. You can use tools to complete tasks.

Available tools:
- read_file: Read file contents
- write_file: Write content to files
- list_directory: List directory contents
- search: Search the web for information
- browser: Control a browser to navigate URLs
- execute_code: Execute Python code

When you need to use a tool, respond in the following format:
Thought: [your reasoning]
Action: [tool_name] [parameters]

If you want to respond directly without using tools, respond in this format:
Thought: [your reasoning]
Response: [your response]
"""


class TaskCancelledError(Exception):
    """Raised when task is cancelled."""
    pass


class TaskTimeoutError(Exception):
    """Raised when task times out."""
    pass


class ReActExecutor:
    """P0: Stable ReAct Loop Executor.
    
    Features:
    - ReAct loop (Thought -> Action -> Observation)
    - Callback system for real-time updates
    - State management and history
    - Task cancellation support
    - Timeout support
    - Streaming token output
    """

    def __init__(
        self,
        model_id: str = "openai/gpt-4o",
        max_steps: int = 50,
        timeout: int = 1800,
        system_prompt: str | None = None,
        tools: ToolRegistry | None = None,
    ):
        self.model_id = model_id
        self.adapter = get_adapter(model_id)
        self.tools = tools or get_tool_registry()
        self.max_steps = max_steps
        self.timeout = timeout
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

        self._cancelled_tasks: set[str] = set()

    def cancel_task(self, task_id: str):
        """Cancel a running task."""
        self._cancelled_tasks.add(task_id)

    def is_cancelled(self, task_id: str) -> bool:
        """Check if task is cancelled."""
        return task_id in self._cancelled_tasks

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        callbacks: ExecutorCallbacks | None = None,
        task_id: str | None = None,
    ) -> ExecutionResult:
        """Execute a task using ReAct loop.
        
        Args:
            task: The task description
            context: Optional context dict
            callbacks: Optional callbacks for real-time updates
            task_id: Optional task ID (generated if not provided)
            
        Returns:
            ExecutionResult with final result and history
        """
        task_id = task_id or f"task_{uuid.uuid4().hex[:12]}"
        callbacks = callbacks or ExecutorCallbacks()
        context = context or {}

        state = ExecutionState(
            task_id=task_id,
            task=task,
            max_steps=self.max_steps,
            context=context,
            status=ExecutionStatus.RUNNING,
        )

        callbacks.emit_status_change(ExecutionStatus.RUNNING)

        messages = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt)
        ]

        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            messages.append(
                Message(role=MessageRole.SYSTEM, content=f"Context:\n{context_str}")
            )

        messages.append(Message(role=MessageRole.USER, content=task))

        start_time = datetime.now()
        step_times = []

        try:
            for step in range(self.max_steps):
                if self.is_cancelled(task_id):
                    state.status = ExecutionStatus.CANCELLED
                    state.error = "Task was cancelled by user"
                    callbacks.emit_status_change(ExecutionStatus.CANCELLED)
                    break

                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > self.timeout:
                    state.status = ExecutionStatus.TIMEOUT
                    state.error = f"Task timed out after {elapsed:.0f} seconds"
                    callbacks.emit_status_change(ExecutionStatus.TIMEOUT)
                    break

                state.current_step = step + 1

                step_start = datetime.now()

                try:
                    response = await self.adapter.chat(
                        messages=messages,
                        temperature=0.7,
                        max_tokens=2048,
                    )
                except Exception as e:
                    state.error = str(e)
                    state.status = ExecutionStatus.FAILED
                    callbacks.emit_error(e)
                    callbacks.emit_status_change(ExecutionStatus.FAILED)
                    break

                content = response.get("content", "")
                tool_calls = response.get("tool_calls", [])

                if not content:
                    continue

                callbacks.emit_thinking(content)

                step_record = StepRecord(
                    step=step + 1,
                    thought=content,
                    action="",
                    action_params={},
                    observation="",
                )

                if not tool_calls:
                    state.final_result = content
                    state.status = ExecutionStatus.COMPLETED
                    callbacks.emit_status_change(ExecutionStatus.COMPLETED)
                    break

                for tool_call in tool_calls:
                    func = tool_call.get("function", {})
                    tool_name = func.get("name", "")
                    tool_args = func.get("arguments", {})

                    if isinstance(tool_args, str):
                        import json
                        try:
                            tool_args = json.loads(tool_args)
                        except:
                            tool_args = {}

                    step_record.action = tool_name
                    step_record.action_params = tool_args

                    callbacks.emit_action(tool_name, tool_args)

                    tool = self.tools.get(tool_name)
                    if not tool:
                        observation = f"Error: Tool '{tool_name}' not found"
                        step_record.error = observation
                    else:
                        try:
                            result = await tool.execute(**tool_args)
                            if hasattr(result, 'content'):
                                observation = result.content or "No output"
                            else:
                                observation = str(result)
                            step_record.tool_name = tool_name
                            step_record.tool_result = observation[:500]
                        except Exception as e:
                            observation = f"Error: {str(e)}"
                            step_record.error = str(e)

                    step_record.observation = observation[:500]
                    callbacks.emit_observation(observation[:500])

                    tool_call_msg = Message(
                        role=MessageRole.ASSISTANT,
                        content=content,
                    )
                    messages.append(tool_call_msg)
                    messages.append(
                        Message(
                            role=MessageRole.USER,
                            content=f"Observation: {observation}",
                        )
                    )

                step_duration = int((datetime.now() - step_start).total_seconds() * 1000)
                step_record.duration_ms = step_duration
                step_times.append(step_duration)

                state.history.append(step_record)
                callbacks.emit_step_complete(step_record)

                await asyncio.sleep(0.05)

            else:
                state.status = ExecutionStatus.FAILED
                state.error = f"Max steps ({self.max_steps}) reached without completion"
                callbacks.emit_status_change(ExecutionStatus.FAILED)

        except Exception as e:
            state.status = ExecutionStatus.FAILED
            state.error = str(e)
            callbacks.emit_error(e)
            callbacks.emit_status_change(ExecutionStatus.FAILED)

        state.completed_at = datetime.now()

        total_duration = int((state.completed_at - state.started_at).total_seconds() * 1000)

        result = ExecutionResult(
            task_id=task_id,
            status=state.status,
            final_result=state.final_result,
            error=state.error,
            total_steps=state.current_step,
            duration_ms=total_duration,
            history=state.history,
        )

        callbacks.emit_complete(result)

        return result

    async def execute_stream(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        callbacks: ExecutorCallbacks | None = None,
        task_id: str | None = None,
    ):
        """Execute task with streaming token output.
        
        Yields:
            dict with type 'chunk', 'step', 'error', or 'complete'
        """
        task_id = task_id or f"task_{uuid.uuid4().hex[:12]}"
        callbacks = callbacks or ExecutorCallbacks()

        messages = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt)
        ]

        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            messages.append(
                Message(role=MessageRole.SYSTEM, content=f"Context:\n{context_str}")
            )

        messages.append(Message(role=MessageRole.USER, content=task))

        accumulated = ""

        try:
            async for chunk in self.adapter.chat_stream(messages=messages):
                if self.is_cancelled(task_id):
                    yield {"type": "error", "error": "Task cancelled"}
                    return

                accumulated += chunk
                callbacks.emit_token(chunk)
                yield {"type": "chunk", "content": chunk}

            yield {"type": "complete", "content": accumulated}

        except Exception as e:
            yield {"type": "error", "error": str(e)}


def get_executor(
    model_id: str = "openai/gpt-4o",
    **kwargs,
) -> ReActExecutor:
    """Factory function to get a ReActExecutor instance."""
    return ReActExecutor(model_id=model_id, **kwargs)
