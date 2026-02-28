"""Agent Teams for multi-agent collaboration."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from manus.agents.planner import PlannerAgent
from manus.agents.react import ReActAgent
from manus.agents.verifier import VerifierAgent
from manus.core.types import TaskStatus
from manus.memory import get_memory_manager
from manus.tools import get_tool_registry


class TeamRole(Enum):
    """Agent team roles."""
    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"


@dataclass
class TeamMember:
    """A member of the agent team."""

    name: str
    role: TeamRole
    agent: PlannerAgent | ReActAgent | VerifierAgent
    enabled: bool = True


@dataclass
class TeamResult:
    """Result of team execution."""

    task_id: str
    status: TaskStatus
    final_response: str = ""
    steps: list[dict[str, Any]] = field(default_factory=list)
    plan: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None
    error: str | None = None
    duration: float = 0.0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None


class AgentTeam:
    """Multi-agent team for complex task execution.

    Coordinates:
    - Planner: Creates task execution plan
    - Executor: Executes tasks using ReAct
    - Verifier: Validates execution results
    """

    def __init__(
        self,
        planner_model: str,
        executor_model: str,
        verifier_model: str,
        max_iterations: int = 3,
    ):
        self.max_iterations = max_iterations
        self.memory = get_memory_manager()
        self.tool_registry = get_tool_registry()

        self.planner = PlannerAgent(model_id=planner_model)
        self.executor = ReActAgent(
            model_id=executor_model,
            tools=self.tool_registry,
        )
        self.verifier = VerifierAgent(model_id=verifier_model)

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
    ) -> TeamResult:
        """Execute task using the agent team."""
        start_time = datetime.now()
        result = TeamResult(task_id=task_id, status=TaskStatus.EXECUTING)

        try:
            plan = await self.planner.plan(task_id=task_id, user_input=user_input)
            result.plan = {
                "steps": [
                    {"step_id": s.step_id, "description": s.description, "tool": s.tool}
                    for s in plan.steps
                ]
            }

            plan_text = "\n".join([f"{s.step_id}. {s.description}" for s in plan.steps])
            execution_prompt = f"""Execute the following plan:

{plan_text}

User original request: {user_input}"""

            execution_result = await self.executor.execute(
                task_id=task_id,
                user_input=execution_prompt,
            )

            result.steps = execution_result.get("steps", [])
            result.final_response = execution_result.get("final_response", "")

            if execution_result.get("status") == TaskStatus.FAILED.value:
                result.status = TaskStatus.FAILED
                result.error = execution_result.get("error")
                result.completed_at = datetime.now()
                result.duration = (result.completed_at - start_time).total_seconds()
                return result

            for iteration in range(self.max_iterations):
                verification = await self.verifier.verify(
                    task_id=task_id,
                    original_input=user_input,
                    execution_result=execution_result,
                )

                result.verification = verification

                if verification.get("verified"):
                    result.status = TaskStatus.COMPLETED
                    break

                issues = verification.get("issues", [])
                if not issues:
                    result.status = TaskStatus.COMPLETED
                    break

                feedback = f"Issues found: {', '.join(issues)}"
                suggestions = verification.get("suggestions", [])

                if suggestions and iteration < self.max_iterations - 1:
                    refinement_prompt = f"""Refine the plan based on feedback:

Original request: {user_input}
Current response: {result.final_response}

Feedback: {feedback}
Suggestions: {', '.join(suggestions)}

Please execute again with improvements."""

                    execution_result = await self.executor.execute(
                        task_id=task_id,
                        user_input=refinement_prompt,
                    )

                    result.steps.extend(execution_result.get("steps", []))
                    result.final_response = execution_result.get("final_response", "")
                else:
                    result.status = TaskStatus.PARTIAL
                    break

        except Exception as e:
            result.status = TaskStatus.FAILED
            result.error = str(e)

        result.completed_at = datetime.now()
        result.duration = (result.completed_at - start_time).total_seconds()

        return result

    async def execute_parallel(
        self,
        task_id: str,
        sub_tasks: list[str],
    ) -> list[TeamResult]:
        """Execute multiple sub-tasks in parallel."""
        import asyncio

        tasks = [
            self.execute(task_id=f"{task_id}_{i}", user_input=sub_task)
            for i, sub_task in enumerate(sub_tasks)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        team_results = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                team_results.append(TeamResult(
                    task_id=f"{task_id}_{i}",
                    status=TaskStatus.FAILED,
                    error=str(r),
                ))
            else:
                team_results.append(r)

        return team_results


class SimpleAgentTeam(AgentTeam):
    """Simplified agent team with default models."""

    def __init__(self):
        super().__init__(
            planner_model="openai/gpt-4o",
            executor_model="openai/gpt-4o",
            verifier_model="openai/gpt-4o",
            max_iterations=3,
        )
