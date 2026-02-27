from dataclasses import dataclass
from enum import Enum
from typing import Any
import json

from manus.models import get_adapter
from manus.agents.state import SubTask, SubTaskStatus


class RetryStrategy(Enum):
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"


@dataclass
class ReflectionResult:
    is_success: bool
    thought: str
    suggestion: str | None = None
    retry_strategy: RetryStrategy = RetryStrategy.ABORT
    confidence: float = 0.0


@dataclass
class RetryDecision:
    should_retry: bool
    strategy: RetryStrategy
    reason: str
    max_attempts: int = 3
    wait_seconds: int = 1


REFLECTOR_SYSTEM_PROMPT = """You are a self-reflection expert. Your job is to analyze task execution results and determine if the task was successful.

## Guidelines:
1. Carefully analyze the subtask description and its result
2. Check if the result meets the success criteria
3. Identify any errors or issues
4. Provide constructive feedback for improvement

## Output Format:
Return a JSON object with:
- is_success: boolean - did the task achieve its goal?
- thought: string - your analysis and reasoning
- suggestion: string (optional) - how to fix issues if failed
- retry_strategy: one of "retry", "skip", or "abort"
- confidence: float 0-1 - how confident are you in this assessment?
"""

RETRY_DECISION_PROMPT = """You are a retry decision expert. Based on the error and attempt count, determine if the task should be retried.

## Guidelines:
1. Consider the type of error
2. Consider how many attempts have been made
3. Some errors are retryable (network, timeout), others are not (syntax, logic)
4. Be conservative with retries to avoid infinite loops

## Input:
- Subtask: {subtask_description}
- Error: {error_message}
- Attempts: {attempts}

## Output Format:
Return a JSON object with:
- should_retry: boolean
- strategy: "retry", "skip", or "abort"
- reason: string explaining your decision
- max_attempts: maximum retries allowed (default 3)
- wait_seconds: seconds to wait before retry (default 1)
"""


class Reflector:
    """自我反思器 - 验证结果、修正错误"""

    def __init__(
        self,
        model_provider: str = "openai",
        model_name: str = "gpt-4o",
        default_max_attempts: int = 3,
    ):
        self.model_provider = model_provider
        self.model_name = model_name
        self.default_max_attempts = default_max_attempts

    async def reflect(
        self,
        subtask: SubTask,
        result: Any,
        context: dict[str, Any] | None = None,
    ) -> ReflectionResult:
        """反思执行结果"""
        adapter = get_adapter(self.model_provider, self.model_name)

        result_str = self._format_result(result)
        context_str = json.dumps(context, ensure_ascii=False) if context else "None"

        prompt = f"""{REFLECTOR_SYSTEM_PROMPT}

## Subtask:
{subtask.description}

## Result:
{result_str}

## Context:
{context_str}

Analyze and provide your reflection."""

        response = await adapter.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        content = response.get("content", "")
        return self._parse_reflection(content)

    async def should_retry(
        self,
        subtask: SubTask,
        error: str,
        attempts: int,
    ) -> RetryDecision:
        """判断是否重试"""
        adapter = get_adapter(self.model_provider, self.model_name)

        prompt = RETRY_DECISION_PROMPT.format(
            subtask_description=subtask.description,
            error_message=error,
            attempts=attempts,
        )

        response = await adapter.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        content = response.get("content", "")
        return self._parse_retry_decision(content, attempts)

    def simple_reflect(
        self,
        subtask: SubTask,
        result: Any,
    ) -> ReflectionResult:
        """简单的同步反思（无需 LLM）"""
        if result is None:
            return ReflectionResult(
                is_success=False,
                thought="Result is None, task may have failed",
                retry_strategy=RetryStrategy.RETRY,
                confidence=0.8,
            )

        if isinstance(result, dict):
            if result.get("error"):
                return ReflectionResult(
                    is_success=False,
                    thought=f"Error in result: {result.get('error')}",
                    retry_strategy=RetryStrategy.RETRY,
                    confidence=0.9,
                )

            if result.get("success") is False:
                return ReflectionResult(
                    is_success=False,
                    thought=f"Task reported failure: {result.get('message', 'Unknown')}",
                    retry_strategy=RetryStrategy.RETRY,
                    confidence=0.8,
                )

        return ReflectionResult(
            is_success=True,
            thought="Task completed successfully",
            retry_strategy=RetryStrategy.ABORT,
            confidence=0.9,
        )

    def simple_retry_decision(
        self,
        subtask: SubTask,
        error: str,
        attempts: int,
    ) -> RetryDecision:
        """简单的重试决策（无需 LLM）"""
        retryable_errors = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "rate limit",
            "429",
            "503",
            "500",
        ]

        error_lower = error.lower()
        is_retryable = any(e in error_lower for e in retryable_errors)

        if attempts >= self.default_max_attempts:
            return RetryDecision(
                should_retry=False,
                strategy=RetryStrategy.ABORT,
                reason=f"Max attempts ({self.default_max_attempts}) reached",
                max_attempts=self.default_max_attempts,
            )

        if is_retryable:
            return RetryDecision(
                should_retry=True,
                strategy=RetryStrategy.RETRY,
                reason="Retryable error detected",
                max_attempts=self.default_max_attempts,
            )

        if "syntax" in error_lower or "indentation" in error_lower:
            return RetryDecision(
                should_retry=False,
                strategy=RetryStrategy.ABORT,
                reason="Syntax error - will not fix by retrying",
                max_attempts=self.default_max_attempts,
            )

        if "permission" in error_lower or "unauthorized" in error_lower:
            return RetryDecision(
                should_retry=False,
                strategy=RetryStrategy.ABORT,
                reason="Permission error - will not fix by retrying",
                max_attempts=self.default_max_attempts,
            )

        return RetryDecision(
            should_retry=attempts < 2,
            strategy=RetryStrategy.RETRY if attempts < 2 else RetryStrategy.ABORT,
            reason="Unknown error, giving one more try",
            max_attempts=self.default_max_attempts,
        )

    def _format_result(self, result: Any) -> str:
        """格式化结果为字符串"""
        if result is None:
            return "No result (None)"

        if isinstance(result, str):
            return result[:2000]

        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, indent=2)[:2000]

        return str(result)[:2000]

    def _parse_reflection(self, content: str) -> ReflectionResult:
        """解析反思结果"""
        import re

        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            data = json.loads(content)
            strategy_str = data.get("retry_strategy", "abort")
            strategy = RetryStrategy(strategy_str)

            return ReflectionResult(
                is_success=data.get("is_success", False),
                thought=data.get("thought", ""),
                suggestion=data.get("suggestion"),
                retry_strategy=strategy,
                confidence=data.get("confidence", 0.5),
            )
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    strategy_str = data.get("retry_strategy", "abort")
                    strategy = RetryStrategy(strategy_str)

                    return ReflectionResult(
                        is_success=data.get("is_success", False),
                        thought=data.get("thought", ""),
                        suggestion=data.get("suggestion"),
                        retry_strategy=strategy,
                        confidence=data.get("confidence", 0.5),
                    )
                except json.JSONDecodeError:
                    pass

        return ReflectionResult(
            is_success=False,
            thought="Failed to parse reflection",
            retry_strategy=RetryStrategy.ABORT,
            confidence=0.0,
        )

    def _parse_retry_decision(self, content: str, attempts: int) -> RetryDecision:
        """解析重试决策"""
        import re

        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            data = json.loads(content)
            strategy_str = data.get("strategy", "abort")
            strategy = RetryStrategy(strategy_str)

            return RetryDecision(
                should_retry=data.get("should_retry", False),
                strategy=strategy,
                reason=data.get("reason", ""),
                max_attempts=data.get("max_attempts", self.default_max_attempts),
                wait_seconds=data.get("wait_seconds", 1),
            )
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    strategy_str = data.get("strategy", "abort")
                    strategy = RetryStrategy(strategy_str)

                    return RetryDecision(
                        should_retry=data.get("should_retry", False),
                        strategy=strategy,
                        reason=data.get("reason", ""),
                        max_attempts=data.get("max_attempts", self.default_max_attempts),
                        wait_seconds=data.get("wait_seconds", 1),
                    )
                except json.JSONDecodeError:
                    pass

        return RetryDecision(
            should_retry=attempts < self.default_max_attempts,
            strategy=RetryStrategy.RETRY if attempts < self.default_max_attempts else RetryStrategy.ABORT,
            reason="Failed to parse decision, defaulting",
            max_attempts=self.default_max_attempts,
        )
