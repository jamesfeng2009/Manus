"""ReflectorRetryExecutor - P1: Reflector retry mechanism."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from manus.agents.executor import ReActExecutor
from manus.agents.callbacks import (
    ExecutorCallbacks,
    ExecutionResult,
    ExecutionStatus,
    StepRecord,
)
from manus.agents.reflector import (
    Reflector,
    RetryDecision,
    ReflectionResult,
)
from manus.agents.state import SubTask, SubTaskStatus


@dataclass
class RetryConfig:
    max_attempts: int = 3
    wait_seconds: int = 1
    use_llm: bool = False
    reflector_model: str = "gpt-4o"


@dataclass
class RetryRecord:
    step: int
    attempt: int
    error: str
    decision: RetryDecision
    timestamp: datetime = field(default_factory=datetime.now)


class ReflectorRetryExecutor:
    """P1: ReAct Executor with Reflector retry mechanism.
    
    Features:
    - Post-step reflection using Reflector
    - Automatic retry for failed steps
    - Retry history tracking
    - Configurable retry strategies
    """

    def __init__(
        self,
        model_id: str = "gpt-4o",
        max_steps: int = 50,
        timeout: int = 1800,
        retry_config: RetryConfig | None = None,
        system_prompt: str | None = None,
    ):
        self.model_id = model_id
        self.max_steps = max_steps
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        self.system_prompt = system_prompt

        self._executor = ReActExecutor(
            model_id=model_id,
            max_steps=max_steps,
            timeout=timeout,
            system_prompt=system_prompt,
        )

        self._reflector = Reflector(
            model_name=self.retry_config.reflector_model,
        )

        self._retry_history: dict[str, list[RetryRecord]] = {}

    def _get_task_history(self, task_id: str) -> list[RetryRecord]:
        if task_id not in self._retry_history:
            self._retry_history[task_id] = []
        return self._retry_history[task_id]

    async def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        callbacks: ExecutorCallbacks | None = None,
        task_id: str | None = None,
    ) -> ExecutionResult:
        """Execute task with reflection and retry."""
        task_id = task_id or f"task_{uuid.uuid4().hex[:12]}"
        callbacks = callbacks or ExecutorCallbacks()

        result = await self._executor.execute(
            task=task,
            context=context,
            callbacks=callbacks,
            task_id=task_id,
        )

        if result.status == ExecutionStatus.COMPLETED:
            reflection = await self._reflect_on_result(
                task_id=task_id,
                task=task,
                result=result,
            )
            
            if not reflection.is_success:
                result.status = ExecutionStatus.FAILED
                result.error = f"Reflection failed: {reflection.thought}"

        return result

    async def _reflect_on_result(
        self,
        task_id: str,
        task: str,
        result: ExecutionResult,
    ) -> ReflectionResult:
        """Reflect on the execution result."""
        subtask = SubTask(
            id=task_id,
            description=task,
            status=SubTaskStatus.COMPLETED,
            result=result.final_result,
        )

        if self.retry_config.use_llm:
            reflection = await self._reflector.reflect(
                subtask=subtask,
                result=result.final_result,
                context={"history": [s.to_dict() for s in result.history]},
            )
        else:
            reflection = self._reflector.simple_reflect(
                subtask=subtask,
                result=result.final_result,
            )

        return reflection

    async def execute_with_retry(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        callbacks: ExecutorCallbacks | None = None,
        task_id: str | None = None,
    ) -> ExecutionResult:
        """Execute with retry mechanism for each step."""
        task_id = task_id or f"task_{uuid.uuid4().hex[:12]}"
        callbacks = callbacks or ExecutorCallbacks()

        from manus.agents.executor import ExecutionState
        from manus.core.types import Message, MessageRole
        
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
            Message(role=MessageRole.SYSTEM, content=self._executor.system_prompt)
        ]

        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            messages.append(
                Message(role=MessageRole.SYSTEM, content=f"Context:\n{context_str}")
            )

        messages.append(Message(role=MessageRole.USER, content=task))

        start_time = datetime.now()
        step_attempts = {}

        try:
            for step in range(self.max_steps):
                if self._executor.is_cancelled(task_id):
                    state.status = ExecutionStatus.CANCELLED
                    state.error = "Task was cancelled"
                    callbacks.emit_status_change(ExecutionStatus.CANCELLED)
                    break

                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > self.timeout:
                    state.status = ExecutionStatus.TIMEOUT
                    state.error = f"Task timed out after {elapsed:.0f}s"
                    callbacks.emit_status_change(ExecutionStatus.TIMEOUT)
                    break

                state.current_step = step + 1

                step_start = datetime.now()

                try:
                    response = await self._executor.adapter.chat(
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

                    tool = self._executor.tools.get(tool_name)
                    
                    step_key = f"{step}_{tool_name}"
                    attempt = step_attempts.get(step_key, 0)
                    observation = None

                    while attempt < self.retry_config.max_attempts:
                        attempt += 1
                        step_attempts[step_key] = attempt

                        if tool:
                            try:
                                result = await tool.execute(**tool_args)
                                if hasattr(result, 'content'):
                                    observation = result.content or "No output"
                                else:
                                    observation = str(result)
                                
                                step_record.tool_name = tool_name
                                step_record.tool_result = observation[:500]
                                step_record.error = None
                                
                                break
                            except Exception as e:
                                observation = f"Error: {str(e)}"
                                step_record.error = str(e)
                                
                                decision = await self._make_retry_decision(
                                    tool_name=tool_name,
                                    error=str(e),
                                    attempts=attempt,
                                    task_id=task_id,
                                )
                                
                                retry_record = RetryRecord(
                                    step=step + 1,
                                    attempt=attempt,
                                    error=str(e),
                                    decision=decision,
                                )
                                self._get_task_history(task_id).append(retry_record)
                                
                                callbacks.emit_error(e)
                                
                                if not decision.should_retry:
                                    break
                                
                                await asyncio.sleep(self.retry_config.wait_seconds)
                                callbacks.emit_status_change(ExecutionStatus.RUNNING)
                        else:
                            observation = f"Error: Tool '{tool_name}' not found"
                            break

                    step_record.observation = observation[:500] if observation else ""
                    callbacks.emit_observation(observation[:500] if observation else "")

                    messages.append(
                        Message(role=MessageRole.ASSISTANT, content=content)
                    )
                    messages.append(
                        Message(
                            role=MessageRole.USER,
                            content=f"Observation: {observation or 'No output'}",
                        )
                    )

                step_duration = int((datetime.now() - step_start).total_seconds() * 1000)
                step_record.duration_ms = step_duration

                state.history.append(step_record)
                callbacks.emit_step_complete(step_record)

                await asyncio.sleep(0.05)

            else:
                state.status = ExecutionStatus.FAILED
                state.error = f"Max steps ({self.max_steps}) reached"
                callbacks.emit_status_change(ExecutionStatus.FAILED)

        except Exception as e:
            state.status = ExecutionStatus.FAILED
            state.error = str(e)
            callbacks.emit_error(e)
            callbacks.emit_status_change(ExecutionStatus.FAILED)

        state.completed_at = datetime.now()
        total_duration = int((state.completed_at - state.started_at).total_seconds() * 1000)

        final_result = ExecutionResult(
            task_id=task_id,
            status=state.status,
            final_result=state.final_result,
            error=state.error,
            total_steps=state.current_step,
            duration_ms=total_duration,
            history=state.history,
        )

        callbacks.emit_complete(final_result)

        return final_result

    async def _make_retry_decision(
        self,
        tool_name: str,
        error: str,
        attempts: int,
        task_id: str,
    ) -> RetryDecision:
        """Make retry decision for a failed step."""
        subtask = SubTask(
            id=f"{task_id}_{tool_name}",
            description=f"Execute tool: {tool_name}",
            status=SubTaskStatus.FAILED,
            error=error,
            attempts=attempts,
        )

        if self.retry_config.use_llm:
            decision = await self._reflector.should_retry(
                subtask=subtask,
                error=error,
                attempts=attempts,
            )
        else:
            decision = self._reflector.simple_retry_decision(
                subtask=subtask,
                error=error,
                attempts=attempts,
            )

        return decision

    def get_retry_history(self, task_id: str) -> list[RetryRecord]:
        """Get retry history for a task."""
        return self._get_task_history(task_id)

    def cancel_task(self, task_id: str):
        """Cancel a running task."""
        self._executor.cancel_task(task_id)

    def is_cancelled(self, task_id: str) -> bool:
        """Check if task is cancelled."""
        return self._executor.is_cancelled(task_id)


def get_reflector_executor(
    model_id: str = "gpt-4o",
    **kwargs,
) -> ReflectorRetryExecutor:
    """Factory function to get a ReflectorRetryExecutor instance."""
    return ReflectorRetryExecutor(model_id=model_id, **kwargs)
