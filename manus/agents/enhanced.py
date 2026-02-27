from typing import Any, Callable
import asyncio
import json
import uuid

from manus.agents.state import TaskState, SubTask, SubTaskStatus, Phase
from manus.agents.reflector import Reflector, RetryStrategy
from manus.tools import get_tool_registry
from manus.models import get_adapter


PLANNER_PROMPT = """You are a task decomposition expert. Break down the goal into subtasks.

Output JSON array:
[{"description": "subtask 1", "dependencies": []}, ...]

Goal: {goal}"""


ProgressCallback = Callable[[float, str], None]


class EnhancedAgent:
    """增强版 Agent - 整合 Planner/Executor/Reflector"""

    def __init__(
        self,
        model_provider: str = "openai",
        model_name: str = "gpt-4o",
        max_iterations: int = 10,
        enable_reflection: bool = True,
    ):
        self.model_provider = model_provider
        self.model_name = model_name
        self.reflector = Reflector(model_provider, model_name)
        self.max_iterations = max_iterations
        self.enable_reflection = enable_reflection
        self.tool_registry = get_tool_registry()

    async def _plan(self, goal: str, context: dict[str, Any] | None = None) -> list[SubTask]:
        """简单任务分解"""
        adapter = get_adapter(self.model_provider, self.model_name)
        
        prompt = PLANNER_PROMPT.format(goal=goal)
        
        response = await adapter.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        
        content = response.get("content", "")
        try:
            data = json.loads(content.strip())
            subtasks = []
            for i, item in enumerate(data):
                deps = item.get("dependencies", [])
                actual_deps = []
                for dep_idx in deps:
                    if dep_idx < len(subtasks):
                        actual_deps.append(subtasks[dep_idx].id)
                subtask = SubTask(
                    id=f"subtask_{uuid.uuid4().hex[:8]}",
                    description=item.get("description", ""),
                    dependencies=actual_deps,
                )
                subtasks.append(subtask)
            return subtasks
        except json.JSONDecodeError:
            return [SubTask(id=f"subtask_{uuid.uuid4().hex[:8]}", description=goal)]

    async def run(
        self,
        goal: str,
        context: dict[str, Any] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """执行任务的主流程"""
        task_state = TaskState(
            task_id=f"task_{uuid.uuid4().hex[:12]}",
            original_goal=goal,
            max_iterations=self.max_iterations,
            context=context or {},
        )

        await self._report_progress(progress_callback, 0.0, "开始任务分解...")

        task_state = await self._planning_phase(task_state, progress_callback)
        if task_state.has_failures():
            return self._create_failure_result(task_state, "Planning failed")

        await self._report_progress(
            progress_callback,
            task_state.get_progress() * 0.1,
            f"生成了 {len(task_state.subtasks)} 个子任务",
        )

        task_state = await self._execution_phase(task_state, progress_callback)
        if task_state.has_failures():
            return self._create_failure_result(task_state, "Execution failed")

        await self._report_progress(progress_callback, 1.0, "任务完成")

        return {
            "success": True,
            "task_id": task_state.task_id,
            "goal": goal,
            "subtasks": [st.to_dict() for st in task_state.subtasks],
            "state": task_state.to_dict(),
        }

    async def _planning_phase(
        self,
        task_state: TaskState,
        progress_callback: ProgressCallback | None,
    ) -> TaskState:
        """计划阶段 - 分解任务"""
        task_state.current_phase = Phase.PLANNING

        subtasks = await self._plan(
            goal=task_state.original_goal,
            context=task_state.context,
        )

        task_state.subtasks = subtasks
        task_state.add_reflection(
            phase="planning",
            thought=f"Generated {len(subtasks)} subtasks",
            action="plan",
            success=True,
        )

        return task_state

    async def _execution_phase(
        self,
        task_state: TaskState,
        progress_callback: ProgressCallback | None,
    ) -> TaskState:
        """执行阶段 - 依次执行子任务"""
        task_state.current_phase = Phase.EXECUTING

        while task_state.can_continue():
            pending = task_state.get_pending_subtasks()
            if not pending:
                break

            subtask = pending[0]
            task_state = await self._execute_subtask(task_state, subtask, progress_callback)

            if task_state.has_failures():
                task_state.current_phase = Phase.REFLECTING
                task_state = await self._reflection_phase(task_state, progress_callback)

        return task_state

    async def _execute_subtask(
        self,
        task_state: TaskState,
        subtask: SubTask,
        progress_callback: ProgressCallback | None,
    ) -> TaskState:
        """执行单个子任务"""
        subtask.status = SubTaskStatus.RUNNING
        subtask.attempts += 1

        await self._report_progress(
            progress_callback,
            task_state.get_progress(),
            f"执行: {subtask.description}",
        )

        try:
            result = await self._call_tools(subtask)

            if self.enable_reflection:
                reflection = await self.reflector.reflect(
                    subtask=subtask,
                    result=result,
                    context=task_state.context,
                )

                task_state.add_reflection(
                    phase="executing",
                    thought=reflection.thought,
                    action="reflect",
                    result=result,
                    success=reflection.is_success,
                )

                if reflection.is_success:
                    subtask.status = SubTaskStatus.COMPLETED
                    subtask.result = result
                else:
                    subtask.status = SubTaskStatus.FAILED
                    subtask.error = reflection.thought

                    retry_decision = await self.reflector.should_retry(
                        subtask=subtask,
                        error=reflection.thought,
                        attempts=subtask.attempts,
                    )

                    if retry_decision.should_retry and retry_decision.strategy == RetryStrategy.RETRY:
                        subtask.status = SubTaskStatus.PENDING
                        await asyncio.sleep(retry_decision.wait_seconds)
            else:
                subtask.status = SubTaskStatus.COMPLETED
                subtask.result = result

        except Exception as e:
            subtask.error = str(e)
            subtask.status = SubTaskStatus.FAILED

            if self.enable_reflection:
                retry_decision = await self.reflector.simple_retry_decision(
                    subtask=subtask,
                    error=str(e),
                    attempts=subtask.attempts,
                )

                if retry_decision.should_retry:
                    subtask.status = SubTaskStatus.PENDING

        return task_state

    async def _reflection_phase(
        self,
        task_state: TaskState,
        progress_callback: ProgressCallback | None,
    ) -> TaskState:
        """反思阶段 - 分析失败并尝试修复"""
        await self._report_progress(
            progress_callback,
            task_state.get_progress(),
            "分析失败原因...",
        )

        failed = task_state.get_failed_subtasks()
        if not failed:
            return task_state

        feedback = "\n".join([
            f"- {st.description}: {st.error}"
            for st in failed
        ])

        task_state.add_reflection(
            phase="reflecting",
            thought=f"Failed subtasks: {feedback}",
            action="retry",
            success=False,
        )

        for st in task_state.subtasks:
            if st.status == SubTaskStatus.FAILED:
                st.status = SubTaskStatus.PENDING

        return task_state

    async def _call_tools(self, subtask: SubTask) -> Any:
        """调用工具执行子任务"""
        available_tools = self.tool_registry.list_tools()

        if not available_tools:
            return {"error": "No tools available"}

        tool = self.tool_registry.get(available_tools[0])
        if not tool:
            return {"error": f"Tool {available_tools[0]} not found"}

        result = await tool.execute(
            task=subtask.description,
            context={"subtask_id": subtask.id},
        )

        return result.to_dict() if hasattr(result, "to_dict") else result

    async def _report_progress(
        self,
        callback: ProgressCallback | None,
        progress: float,
        message: str,
    ):
        if callback:
            try:
                await callback(progress, message)
            except Exception:
                pass

    def _create_failure_result(
        self,
        task_state: TaskState,
        error: str,
    ) -> dict[str, Any]:
        return {
            "success": False,
            "error": error,
            "task_id": task_state.task_id,
            "goal": task_state.original_goal,
            "subtasks": [st.to_dict() for st in task_state.subtasks],
            "state": task_state.to_dict(),
        }
