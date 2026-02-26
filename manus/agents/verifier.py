"""Verifier Agent for validating task execution results."""

from typing import Any

from manus.core.types import Message, MessageRole
from manus.memory import get_memory_manager
from manus.models import get_adapter


VERIFIER_SYSTEM_PROMPT = """You are a task verification expert. Your job is to verify that the execution results meet the user's requirements.

Guidelines:
1. Carefully review the user's original request
2. Check if the execution completed all required steps
3. Verify the quality of outputs
4. Identify any issues or missing parts
5. Provide clear feedback

Output format:
{
  "verified": true/false,
  "issues": ["issue1", "issue2"],
  "suggestions": ["suggestion1", "suggestion2"],
  "summary": "brief summary"
}
"""


class VerifierAgent:
    """Verifier Agent for validating task execution.

    Checks if task execution results meet requirements and provides feedback.
    """

    def __init__(
        self,
        model_id: str,
        system_prompt: str | None = None,
    ):
        self.model_id = model_id
        self.adapter = get_adapter(model_id)
        self.system_prompt = system_prompt or VERIFIER_SYSTEM_PROMPT
        self.memory = get_memory_manager()

    async def verify(
        self,
        task_id: str,
        original_input: str,
        execution_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Verify task execution result."""
        prompt = f"""Verify the execution result:

Original task: {original_input}

Execution result:
{self._format_result(execution_result)}

Provide verification feedback in JSON format."""

        messages = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt),
            Message(role=MessageRole.USER, content=prompt),
        ]

        try:
            response = await self.adapter.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
            )

            content = response.get("content", "")
            return self._parse_verification(content)

        except Exception as e:
            return {
                "verified": False,
                "issues": [f"Verification failed: {str(e)}"],
                "suggestions": [],
                "summary": "Error during verification",
            }

    def _format_result(self, result: dict[str, Any]) -> str:
        """Format execution result for prompt."""
        lines = []
        
        if "final_response" in result:
            lines.append(f"Final response: {result['final_response']}")
        
        if "steps" in result:
            lines.append("\nExecution steps:")
            for step in result["steps"][-5:]:
                lines.append(f"  Step {step.get('step')}: {step.get('tool', 'N/A')}")
                lines.append(f"    Observation: {step.get('observation', '')[:200]}")
        
        if "error" in result:
            lines.append(f"\nError: {result['error']}")
        
        return "\n".join(lines)

    def _parse_verification(self, content: str) -> dict[str, Any]:
        """Parse verification from LLM response."""
        import json

        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            else:
                return {
                    "verified": "verified" in content.lower() and "true" in content.lower(),
                    "issues": [],
                    "suggestions": [],
                    "summary": content[:500],
                }

            data = json.loads(json_str.strip())
            return {
                "verified": data.get("verified", False),
                "issues": data.get("issues", []),
                "suggestions": data.get("suggestions", []),
                "summary": data.get("summary", ""),
            }

        except:
            return {
                "verified": "verified" in content.lower() and "true" in content.lower(),
                "issues": [],
                "suggestions": [],
                "summary": content[:500],
            }

    async def verify_step(
        self,
        step: dict[str, Any],
        expected_outcome: str,
    ) -> dict[str, Any]:
        """Verify a single execution step."""
        prompt = f"""Verify this step:

Expected: {expected_outcome}
Actual: {step.get('observation', 'No observation')}

Is this step completed correctly? Respond with yes or no and brief explanation."""

        messages = [
            Message(role=MessageRole.SYSTEM, content="You are a verification assistant."),
            Message(role=MessageRole.USER, content=prompt),
        ]

        try:
            response = await self.adapter.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=256,
            )

            content = response.get("content", "").lower()
            return {
                "verified": "yes" in content or "correct" in content,
                "feedback": content[:200],
            }

        except Exception as e:
            return {
                "verified": False,
                "feedback": f"Error: {str(e)}",
            }

    async def suggest_improvements(
        self,
        task_id: str,
        original_input: str,
        previous_result: dict[str, Any],
    ) -> list[str]:
        """Suggest improvements for failed or incomplete tasks."""
        prompt = f"""Analyze this failed task and suggest how to improve:

Original task: {original_input}

Previous result: {previous_result.get('final_response', '')}

What should be done differently? Provide 3-5 specific suggestions."""

        messages = [
            Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
            Message(role=MessageRole.USER, content=prompt),
        ]

        try:
            response = await self.adapter.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=512,
            )

            content = response.get("content", "")
            suggestions = [
                line.strip().lstrip("12345.- ").strip()
                for line in content.split("\n")
                if line.strip() and (line[0].isdigit() or line.startswith("-"))
            ][:5]

            return suggestions

        except Exception:
            return []
