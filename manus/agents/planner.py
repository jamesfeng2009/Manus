"""Planner Agent for task planning and decomposition."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from manus.core.types import Message, MessageRole, TaskStep, TaskStatus
from manus.memory import get_memory_manager
from manus.models import get_adapter


PLANNER_SYSTEM_PROMPT = """You are a task planning expert. Your job is to break down complex user tasks into clear, executable steps.

Guidelines:
1. Analyze the user's request to understand the goal
2. Break down the task into numbered steps
3. Each step should be specific and actionable
4. Consider dependencies between steps
5. Identify required tools for each step
6. Estimate complexity (simple/medium/complex)

Output format should be a JSON array of steps:
[
  {
    "step": 1,
    "description": "Step description",
    "tool": "required tool name or null",
    "dependencies": [],
    "complexity": "simple|medium|complex"
  }
]
"""


@dataclass
class TaskPlan:
    """Task execution plan."""

    task_id: str
    original_input: str
    steps: list[TaskStep] = field(default_factory=list)
    current_step: int = 0
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class PlannerAgent:
    """Planner Agent for task decomposition and planning.

    Analyzes user requests and creates structured execution plans.
    """

    def __init__(
        self,
        model_id: str,
        system_prompt: str | None = None,
    ):
        self.model_id = model_id
        self.adapter = get_adapter(model_id)
        self.system_prompt = system_prompt or PLANNER_SYSTEM_PROMPT
        self.memory = get_memory_manager()

    async def plan(
        self,
        task_id: str,
        user_input: str,
        context: str | None = None,
    ) -> TaskPlan:
        """Create a task plan from user input."""
        plan = TaskPlan(
            task_id=task_id,
            original_input=user_input,
            status=TaskStatus.PLANNING,
        )

        prompt = user_input
        if context:
            prompt += f"\n\nContext:\n{context}"

        messages = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt),
            Message(role=MessageRole.USER, content=prompt),
        ]

        try:
            response = await self.adapter.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )

            content = response.get("content", "")

            steps = self._parse_steps(content)

            if steps:
                plan.steps = steps
                plan.status = TaskStatus.PENDING
            else:
                plan.steps = [
                    TaskStep(
                        step_id="1",
                        description=user_input,
                        tool=None,
                        status=TaskStatus.PENDING,
                    )
                ]
                plan.status = TaskStatus.PENDING

        except Exception as e:
            plan.steps = [
                TaskStep(
                    step_id="1",
                    description=f"Error in planning: {str(e)}",
                    tool=None,
                    status=TaskStatus.FAILED,
                )
            ]
            plan.status = TaskStatus.FAILED

        plan.updated_at = datetime.now()
        return plan

    def _parse_steps(self, content: str) -> list[TaskStep]:
        """Parse steps from LLM response."""
        steps = []

        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            else:
                json_str = content

            data = json.loads(json_str.strip())

            if isinstance(data, list):
                for item in data:
                    step = TaskStep(
                        step_id=str(item.get("step", len(steps) + 1)),
                        description=item.get("description", ""),
                        tool=item.get("tool"),
                        complexity=item.get("complexity", "medium"),
                        status=TaskStatus.PENDING,
                    )
                    steps.append(step)

        except json.JSONDecodeError:
            lines = content.strip().split("\n")
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    desc = line.lstrip("0123456789.- ").strip()
                    if desc:
                        steps.append(TaskStep(
                            step_id=str(i),
                            description=desc,
                            status=TaskStatus.PENDING,
                        ))

        return steps

    async def refine_plan(
        self,
        plan: TaskPlan,
        feedback: str,
    ) -> TaskPlan:
        """Refine an existing plan based on feedback."""
        prompt = f"""Refine the following plan based on feedback:

Original task: {plan.original_input}

Current plan:
{self._format_plan(plan)}

Feedback: {feedback}

Provide an improved plan in JSON format."""

        messages = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt),
            Message(role=MessageRole.USER, content=prompt),
        ]

        try:
            response = await self.adapter.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )

            new_steps = self._parse_steps(response.get("content", ""))
            if new_steps:
                plan.steps = new_steps
                plan.updated_at = datetime.now()

        except Exception:
            pass

        return plan

    def _format_plan(self, plan: TaskPlan) -> str:
        """Format plan for display."""
        lines = []
        for step in plan.steps:
            lines.append(f"{step.step_id}. {step.description}")
            if step.tool:
                lines.append(f"   Tool: {step.tool}")
        return "\n".join(lines)

    async def estimate_complexity(self, plan: TaskPlan) -> str:
        """Estimate overall task complexity."""
        simple_count = sum(1 for s in plan.steps if s.complexity == "simple")
        medium_count = sum(1 for s in plan.steps if s.complexity == "medium")
        complex_count = sum(1 for s in plan.steps if s.complexity == "complex")

        if complex_count > 0:
            return "complex"
        elif medium_count > 2:
            return "medium"
        else:
            return "simple"
