"""LearningAgent - 组合模式封装 Agent + LearningEngine."""

import time
from typing import Any

from manus.agents.learning_engine import (
    LearningEngine,
    TaskComplexity,
    StrategyType,
    get_learning_engine,
)
from manus.core.types import Message


class LearningAgent:
    """组合 Agent，内部封装 Agent + LearningEngine。
    
    使用组合模式，在不修改原有 Agent 代码的情况下，为其添加学习能力。
    
    使用方式:
        agent = ReActAgent(model_id="openai/gpt-4o")
        learning_agent = LearningAgent(agent)
        
        result = await learning_agent.execute(task_id="1", user_input="帮我写一个排序算法")
    """

    def __init__(
        self,
        agent: Any,
        learning: LearningEngine | None = None,
        record_after_execute: bool = True,
        recommend_before_execute: bool = True,
    ):
        """初始化 LearningAgent。
        
        Args:
            agent: 被包装的 Agent 实例
            learning: LearningEngine 实例，默认为全局单例
            record_after_execute: 是否在执行完成后记录任务
            recommend_before_execute: 是否在执行前获取策略推荐
        """
        self._agent = agent
        self._learning = learning or get_learning_engine()
        self._record_after_execute = record_after_execute
        self._recommend_before_execute = recommend_before_execute

    @property
    def learning(self) -> LearningEngine:
        """获取 LearningEngine 实例。"""
        return self._learning

    @property
    def agent(self) -> Any:
        """获取被包装的 Agent 实例。"""
        return self._agent

    async def execute(
        self,
        task_id: str,
        user_input: str,
        context: list[Message] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """执行任务，并在执行前后记录学习数据。
        
        Args:
            task_id: 任务 ID
            user_input: 用户输入
            context: 消息上下文
            **kwargs: 其他参数
            
        Returns:
            执行结果
        """
        start_time = time.time()
        
        strategy_recommendation = None
        complexity = None
        
        if self._recommend_before_execute:
            complexity = self._learning.estimate_complexity(user_input)
            strategy_recommendation = self._learning.recommend_strategy(user_input, complexity)
        
        try:
            result = await self._agent.execute(
                task_id=task_id,
                user_input=user_input,
                context=context,
                **kwargs,
            )
        except Exception as e:
            if self._record_after_execute:
                self._record_task(
                    task_description=user_input,
                    complexity=complexity or TaskComplexity.MODERATE,
                    strategy=strategy_recommendation.recommended_strategy if strategy_recommendation else StrategyType.SEQUENTIAL,
                    success=False,
                    steps=0,
                    duration_ms=int((time.time() - start_time) * 1000),
                    tools_used=[],
                    errors=[str(e)],
                )
            raise

        if self._record_after_execute:
            duration_ms = result.get("duration_ms") or int((time.time() - start_time) * 1000)
            steps = result.get("total_steps", 0)
            success = result.get("status") == "completed"
            
            tools_used = []
            errors = []
            if "history" in result:
                for item in result.get("history", []):
                    tool = item.get("tool")
                    if tool and tool not in tools_used:
                        tools_used.append(tool)
                    error = item.get("observation", "")
                    if error and "error" in error.lower():
                        errors.append(error[:200])

            self._record_task(
                task_description=user_input,
                complexity=complexity or self._learning.estimate_complexity(user_input),
                strategy=strategy_recommendation.recommended_strategy if strategy_recommendation else StrategyType.SEQUENTIAL,
                success=success,
                steps=steps,
                duration_ms=duration_ms,
                tools_used=tools_used,
                errors=errors,
            )

        return result

    def _record_task(
        self,
        task_description: str,
        complexity: TaskComplexity,
        strategy: StrategyType,
        success: bool,
        steps: int,
        duration_ms: int,
        tools_used: list[str],
        errors: list[str],
    ):
        """记录任务到学习引擎。"""
        try:
            self._learning.record_task(
                task_description=task_description,
                complexity=complexity,
                strategy=strategy,
                success=success,
                steps=steps,
                duration_ms=duration_ms,
                tools_used=tools_used,
                errors=errors,
            )
        except Exception:
            pass

    def estimate_complexity(self, task_description: str) -> TaskComplexity:
        """估计任务复杂度。"""
        return self._learning.estimate_complexity(task_description)

    def recommend_strategy(
        self,
        task_description: str,
        complexity: TaskComplexity | None = None,
    ):
        """获取策略推荐。"""
        return self._learning.recommend_strategy(task_description, complexity)

    def get_insights(self):
        """获取学习洞察。"""
        return self._learning.get_insights()

    def get_strategy_performance(self, strategy: StrategyType):
        """获取指定策略的性能数据。"""
        return self._learning.get_strategy_performance(strategy)

    def get_task_history(self, limit: int = 100):
        """获取任务历史。"""
        return self._learning.get_task_history(limit)

    def __getattr__(self, name: str) -> Any:
        """代理未被覆盖的属性到被包装的 Agent。"""
        return getattr(self._agent, name)
