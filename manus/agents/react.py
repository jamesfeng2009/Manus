"""ReAct Agent for executing tasks with reasoning and action loop."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from manus.context import get_cross_task_context
from manus.core.types import Message, MessageRole, TaskStep, TaskStatus
from manus.memory import get_memory_manager
from manus.models import get_adapter
from manus.tools import ToolRegistry, get_tool_registry


@dataclass
class AgentState:
    """Agent execution state."""

    task_id: str
    current_step: int = 0
    max_steps: int = 50
    reasoning: str = ""
    action: str = ""
    observation: str = ""
    history: list[dict[str, str]] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


class ReActAgent:
    """ReAct (Reasoning + Acting) Agent.

    Executes tasks using the ReAct loop:
    1. Thought: Reason about the current state
    2. Action: Execute a tool or respond
    3. Observation: Get the result
    4. Repeat until task is complete
    """

    DEFAULT_SYSTEM_PROMPT = """You are a helpful AI assistant. You can use tools to complete tasks.

Available tools:
- search: Search the web for information
- browser: Control a browser to navigate URLs
- execute_code: Execute Python code
- read_file: Read file contents
- write_file: Write content to files
- list_directory: List directory contents

When you need to use a tool, respond in the following format:
Thought: [your reasoning]
Action: [tool_name] [parameters]
"""

    def __init__(
        self,
        model_id: str,
        tools: ToolRegistry | None = None,
        system_prompt: str | None = None,
        max_steps: int = 50,
    ):
        self.model_id = model_id
        self.adapter = get_adapter(model_id)
        self.tools = tools or get_tool_registry()
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.max_steps = max_steps
        self.memory = get_memory_manager()
        self.context = get_cross_task_context()

        self.on_token: callable | None = None
        self.on_thinking: callable | None = None
        self.on_tool_call: callable | None = None
        self.on_tool_result: callable | None = None

    def _emit_token(self, token: str):
        if self.on_token:
            try:
                self.on_token(token)
            except Exception:
                pass

    def _emit_thinking(self, reasoning: str):
        if self.on_thinking:
            try:
                self.on_thinking(reasoning)
            except Exception:
                pass

    def _emit_tool_call(self, tool_name: str, args: dict):
        if self.on_tool_call:
            try:
                self.on_tool_call(tool_name, args)
            except Exception:
                pass

    def _emit_tool_result(self, tool_name: str, result: str):
        if self.on_tool_result:
            try:
                self.on_tool_result(tool_name, result)
            except Exception:
                pass

    async def execute(
        self,
        task_id: str,
        user_input: str,
        context: list[Message] | None = None,
    ) -> dict[str, Any]:
        """Execute a task using ReAct loop."""
        state = AgentState(task_id=task_id, max_steps=self.max_steps)

        messages = []
        if self.system_prompt:
            messages.append(Message(role=MessageRole.SYSTEM, content=self.system_prompt))

        if context:
            messages.extend(context)

        messages.append(Message(role=MessageRole.USER, content=user_input))

        result = {
            "task_id": task_id,
            "status": TaskStatus.EXECUTING.value,
            "steps": [],
            "final_response": "",
        }

        for step in range(self.max_steps):
            state.current_step = step + 1

            try:
                response = await self.adapter.chat(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2048,
                )
                content = response.get("content", "")
                tool_calls = response.get("tool_calls", [])
                self._emit_thinking(content)
            except Exception as e:
                result["status"] = TaskStatus.FAILED.value
                result["error"] = str(e)
                break

            if not tool_calls and content:
                result["final_response"] = content
                result["status"] = TaskStatus.COMPLETED.value
                messages.append(Message(role=MessageRole.ASSISTANT, content=content))
                break

            if tool_calls:
                for tool_call in tool_calls:
                    tool_name = tool_call.get("function", {}).get("name")
                    tool_args = tool_call.get("function", {}).get("arguments", {})

                    if isinstance(tool_args, str):
                        import json
                        try:
                            tool_args = json.loads(tool_args)
                        except:
                            tool_args = {}

                    state.history.append({
                        "thought": content,
                        "action": f"{tool_name}({tool_args})",
                    })

                    tool = self.tools.get(tool_name)
                    if not tool:
                        observation = f"Error: Tool '{tool_name}' not found"
                    else:
                        self._emit_tool_call(tool_name, tool_args)
                        tool_result = await tool.execute_with_timing(**tool_args)
                        observation = tool_result.content or tool_result.error or "No output"
                        self._emit_tool_result(tool_name, observation[:500])

                        if tool_result.status.value == "success":
                            self.context.add_tool_usage(
                                task_id=task_id,
                                tool_name=tool_name,
                                success=True,
                                duration=tool_result.duration,
                                user_id="default",
                            )
                        else:
                            self.context.add_tool_usage(
                                task_id=task_id,
                                tool_name=tool_name,
                                success=False,
                                duration=tool_result.duration,
                                user_id="default",
                            )

                    state.history[-1]["observation"] = observation

                    messages.append(Message(
                        role=MessageRole.ASSISTANT,
                        content=content,
                        tool_calls=[tool_call],
                    ))
                    messages.append(Message(
                        role=MessageRole.USER,
                        content=f"Observation: {observation}",
                    ))

                    result["steps"].append({
                        "step": step + 1,
                        "thought": content,
                        "tool": tool_name,
                        "observation": observation[:500],
                    })

            await asyncio.sleep(0.1)

        if state.current_step >= self.max_steps:
            result["status"] = TaskStatus.PENDING.value
            result["error"] = "Max steps reached"

        result["history"] = state.history
        result["total_steps"] = state.current_step

        return result

    async def execute_stream(
        self,
        task_id: str,
        user_input: str,
        context: list[Message] | None = None,
    ):
        """Execute task with streaming response."""
        messages = []
        if self.system_prompt:
            messages.append(Message(role=MessageRole.SYSTEM, content=self.system_prompt))
        if context:
            messages.extend(context)
        messages.append(Message(role=MessageRole.USER, content=user_input))

        accumulated_content = ""

        async for chunk in self.adapter.chat_stream(messages=messages):
            accumulated_content += chunk
            self._emit_token(chunk)
            yield {"type": "chunk", "content": chunk}

        yield {"type": "complete", "content": accumulated_content}


class ReActAgentWithReflection(ReActAgent):
    """ReAct Agent with reflection for improved reasoning."""

    def __init__(self, *args, reflection_enabled: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.reflection_enabled = reflection_enabled

    async def execute(self, task_id: str, user_input: str, context: list[Message] | None = None) -> dict[str, Any]:
        """Execute with reflection."""
        result = await super().execute(task_id, user_input, context)

        if self.reflection_enabled and result.get("status") == TaskStatus.COMPLETED.value:
            reflection_prompt = f"""Review your previous response for the task: {user_input}

Your response: {result.get('final_response')}

Is this response correct and complete? If not, provide improvements."""

            messages = [
                Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
                Message(role=MessageRole.USER, content=reflection_prompt),
            ]

            try:
                reflection = await self.adapter.chat(messages=messages, temperature=0.7)
                reflection_content = reflection.get("content", "")

                if "improve" in reflection_content.lower() or "incorrect" in reflection_content.lower():
                    result["final_response"] = reflection_content
                    result["was_reflected"] = True
            except:
                pass

        return result
