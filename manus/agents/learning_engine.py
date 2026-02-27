"""LearningEngine - P3: Self-learning and strategy optimization."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskComplexity(Enum):
    """Task complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class StrategyType(Enum):
    """Execution strategy types."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    PLANNED = "planned"
    ITERATIVE = "iterative"
    EXPLORATORY = "exploratory"


@dataclass
class TaskExample:
    """Example of a completed task."""
    id: str
    task_description: str
    complexity: TaskComplexity
    strategy_used: StrategyType
    success: bool
    steps: int
    duration_ms: int
    tools_used: list[str]
    errors: list[str]
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyPerformance:
    """Performance metrics for a strategy."""
    strategy: StrategyType
    total_attempts: int = 0
    success_count: int = 0
    avg_steps: float = 0.0
    avg_duration_ms: float = 0.0
    complexity_scores: dict[str, dict[str, float]] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.success_count / self.total_attempts


@dataclass
class LearningInsight:
    """Insight from learning analysis."""
    insight_type: str
    description: str
    confidence: float
    recommendation: str
    based_on_samples: int


@dataclass
class ExecutionStrategy:
    """Optimized execution strategy."""
    recommended_strategy: StrategyType
    estimated_steps: int
    estimated_duration_ms: int
    fallback_strategies: list[StrategyType]
    suggestions: list[str]


class LearningEngine:
    """P3: Self-learning and strategy optimization.
    
    Features:
    - Task pattern learning
    - Strategy performance tracking
    - Complexity estimation
    - Strategy optimization recommendations
    """

    COMPLEXITY_KEYWORDS = {
        TaskComplexity.SIMPLE: [
            "what is", "calculate", "convert", "define", "list",
            "simple", "basic", "just",
        ],
        TaskComplexity.MODERATE: [
            "compare", "analyze", "find", "search", "get",
            "create", "update", "manage",
        ],
        TaskComplexity.COMPLEX: [
            "build", "develop", "implement", "design", "create",
            "multiple", "several", "integrate",
        ],
        TaskComplexity.VERY_COMPLEX: [
            "architect", "research", "optimize", "refactor",
            "complex", "comprehensive", "end-to-end", "full-stack",
        ],
    }

    def __init__(self, max_examples: int = 1000):
        self.max_examples = max_examples
        
        self._examples: list[TaskExample] = []
        self._strategy_performance: dict[StrategyType, StrategyPerformance] = {
            s: StrategyPerformance(strategy=s) for s in StrategyType
        }
        self._complexity_patterns: dict[str, TaskComplexity] = {}
        self._insights: list[LearningInsight] = []

    def record_task(
        self,
        task_description: str,
        complexity: TaskComplexity,
        strategy: StrategyType,
        success: bool,
        steps: int,
        duration_ms: int,
        tools_used: list[str],
        errors: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> TaskExample:
        """Record a completed task for learning."""
        example = TaskExample(
            id=f"ex_{len(self._examples)}_{datetime.now().timestamp()}",
            task_description=task_description,
            complexity=complexity,
            strategy_used=strategy,
            success=success,
            steps=steps,
            duration_ms=duration_ms,
            tools_used=tools_used,
            errors=errors,
            metadata=metadata or {},
        )
        
        self._examples.append(example)
        self._update_strategy_performance(example)
        
        if len(self._examples) > self.max_examples:
            self._examples = self._examples[-self.max_examples:]
        
        self._generate_insights()
        
        return example

    def _update_strategy_performance(self, example: TaskExample):
        """Update strategy performance metrics."""
        perf = self._strategy_performance[example.strategy_used]
        
        prev_total = perf.total_attempts
        prev_success = perf.success_count
        
        perf.total_attempts += 1
        if example.success:
            perf.success_count += 1
        
        complexity_key = example.complexity.value
        
        if complexity_key not in perf.complexity_scores:
            perf.complexity_scores[complexity_key] = {
                "attempts": 0, "successes": 0, "avg_steps": 0, "avg_duration": 0
            }
        
        scores = perf.complexity_scores[complexity_key]
        
        new_attempts = scores["attempts"] + 1
        scores["attempts"] = new_attempts
        
        if example.success:
            scores["successes"] = scores["successes"] + 1
        
        scores["avg_steps"] = (
            (scores["avg_steps"] * (new_attempts - 1) + example.steps) / new_attempts
        )
        scores["avg_duration"] = (
            (scores["avg_duration"] * (new_attempts - 1) + example.duration_ms) / new_attempts
        )

    def estimate_complexity(self, task_description: str) -> TaskComplexity:
        """Estimate task complexity from description."""
        task_lower = task_description.lower()
        
        score_map = {
            TaskComplexity.VERY_COMPLEX: 0,
            TaskComplexity.COMPLEX: 0,
            TaskComplexity.MODERATE: 0,
            TaskComplexity.SIMPLE: 0,
        }
        
        for complexity, keywords in self.COMPLEXITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in task_lower:
                    score_map[complexity] += 1
        
        if not any(score_map.values()):
            return TaskComplexity.MODERATE
        
        return max(score_map, key=score_map.get)

    def recommend_strategy(
        self,
        task_description: str,
        complexity: TaskComplexity | None = None,
    ) -> ExecutionStrategy:
        """Recommend optimal execution strategy for a task."""
        if complexity is None:
            complexity = self.estimate_complexity(task_description)
        
        candidates = []
        
        for strategy, perf in self._strategy_performance.items():
            if perf.total_attempts == 0:
                continue
            
            complexity_scores = perf.complexity_scores.get(complexity.value)
            
            if complexity_scores and complexity_scores["attempts"] > 0:
                success_rate = complexity_scores["successes"] / complexity_scores["attempts"]
                avg_steps = complexity_scores["avg_steps"]
                avg_duration = complexity_scores["avg_duration"]
                
                score = success_rate * 0.5
                score += (1 / (1 + avg_steps)) * 0.25
                score += (1 / (1 + avg_duration / 1000)) * 0.25
                
                candidates.append((strategy, score, complexity_scores))
        
        if not candidates:
            candidates = self._get_default_strategies(complexity)
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        recommended = candidates[0][0]
        best_scores = candidates[0][2] if len(candidates) > 1 else {}
        
        estimated_steps = int(best_scores.get("avg_steps", self._estimate_steps(complexity)))
        estimated_duration = int(best_scores.get("avg_duration", self._estimate_duration(complexity)))
        
        fallback = [c[0] for c in candidates[1:3]] if len(candidates) > 1 else []
        
        suggestions = self._generate_suggestions(complexity, recommended)
        
        return ExecutionStrategy(
            recommended_strategy=recommended,
            estimated_steps=estimated_steps,
            estimated_duration_ms=estimated_duration,
            fallback_strategies=fallback,
            suggestions=suggestions,
        )

    def _get_default_strategies(self, complexity: TaskComplexity) -> list:
        """Get default strategy recommendations."""
        defaults = {
            TaskComplexity.SIMPLE: [(StrategyType.SEQUENTIAL, 0.8)],
            TaskComplexity.MODERATE: [(StrategyType.PLANNED, 0.7)],
            TaskComplexity.COMPLEX: [(StrategyType.ITERATIVE, 0.6)],
            TaskComplexity.VERY_COMPLEX: [(StrategyType.EXPLORATORY, 0.5)],
        }
        return defaults.get(complexity, [(StrategyType.SEQUENTIAL, 0.5)])

    def _estimate_steps(self, complexity: TaskComplexity) -> int:
        """Estimate steps based on complexity."""
        estimates = {
            TaskComplexity.SIMPLE: 3,
            TaskComplexity.MODERATE: 7,
            TaskComplexity.COMPLEX: 15,
            TaskComplexity.VERY_COMPLEX: 25,
        }
        return estimates.get(complexity, 5)

    def _estimate_duration(self, complexity: TaskComplexity) -> int:
        """Estimate duration based on complexity."""
        estimates = {
            TaskComplexity.SIMPLE: 5000,
            TaskComplexity.MODERATE: 15000,
            TaskComplexity.COMPLEX: 45000,
            TaskComplexity.VERY_COMPLEX: 90000,
        }
        return estimates.get(complexity, 10000)

    def _generate_suggestions(
        self,
        complexity: TaskComplexity,
        strategy: StrategyType,
    ) -> list[str]:
        """Generate execution suggestions."""
        suggestions = []
        
        if complexity == TaskComplexity.SIMPLE:
            suggestions.append("Use direct tool calls without extensive planning")
            suggestions.append("Limit to 3-5 tool invocations")
        
        elif complexity == TaskComplexity.MODERATE:
            suggestions.append("Break down into 2-3 subtasks")
            suggestions.append("Use planning phase before execution")
        
        elif complexity == TaskComplexity.COMPLEX:
            suggestions.append("Iterate with intermediate verification")
            suggestions.append("Consider using sub-planners for different aspects")
        
        else:
            suggestions.append("Use exploratory approach with frequent reflection")
            suggestions.append("Allow for backtracking and alternative paths")
            suggestions.append("Consider human-in-the-loop for critical decisions")
        
        return suggestions

    def _generate_insights(self):
        """Generate learning insights from accumulated data."""
        self._insights = []
        
        if len(self._examples) < 5:
            return
        
        for strategy in StrategyType:
            perf = self._strategy_performance[strategy]
            
            if perf.total_attempts >= 3:
                if perf.success_rate > 0.8:
                    self._insights.append(LearningInsight(
                        insight_type="strategy_success",
                        description=f"Strategy {strategy.value} has {perf.success_rate:.0%} success rate",
                        confidence=min(perf.total_attempts / 10, 1.0),
                        recommendation=f"Prefer {strategy.value} for similar tasks",
                        based_on_samples=perf.total_attempts,
                    ))
                
                worst_complexity = None
                worst_rate = 1.0
                
                for comp, scores in perf.complexity_scores.items():
                    if scores["attempts"] >= 2:
                        rate = scores["successes"] / scores["attempts"]
                        if rate < worst_rate:
                            worst_rate = rate
                            worst_complexity = comp
                
                if worst_complexity and worst_rate < 0.5:
                    self._insights.append(LearningInsight(
                        insight_type="strategy_weakness",
                        description=f"Strategy {strategy.value} struggles with {worst_complexity} tasks",
                        confidence=min(perf.total_attempts / 10, 1.0),
                        recommendation=f"Avoid using {strategy.value} for {worst_complexity} tasks",
                        based_on_samples=perf.total_attempts,
                    ))

    def get_insights(self) -> list[LearningInsight]:
        """Get generated insights."""
        return self._insights

    def get_strategy_performance(self, strategy: StrategyType) -> StrategyPerformance:
        """Get performance metrics for a strategy."""
        return self._strategy_performance.get(strategy)

    def get_all_performance(self) -> dict[StrategyType, StrategyPerformance]:
        """Get all strategy performance metrics."""
        return self._strategy_performance

    def get_task_history(
        self,
        limit: int = 10,
        success_only: bool = False,
    ) -> list[TaskExample]:
        """Get task history."""
        examples = self._examples[-limit:]
        
        if success_only:
            examples = [e for e in examples if e.success]
        
        return examples

    def analyze_failure_patterns(self) -> dict[str, Any]:
        """Analyze common failure patterns."""
        failures = [e for e in self._examples if not e.success]
        
        if not failures:
            return {"pattern": "none", "description": "No failures recorded"}
        
        error_counts = defaultdict(int)
        tool_failure_counts = defaultdict(int)
        
        for failure in failures:
            for error in failure.errors:
                error_counts[error] += 1
            
            for tool in failure.tools_used:
                tool_failure_counts[tool] += 1
        
        return {
            "total_failures": len(failures),
            "common_errors": dict(sorted(
                error_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5]),
            "problematic_tools": dict(sorted(
                tool_failure_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:3]),
        }

    def clear(self):
        """Clear all learning data."""
        self._examples.clear()
        self._insights.clear()
        for perf in self._strategy_performance.values():
            perf.total_attempts = 0
            perf.success_count = 0
            perf.complexity_scores.clear()


_global_engine: LearningEngine | None = None


def get_learning_engine() -> LearningEngine:
    """Get global learning engine instance."""
    global _global_engine
    if _global_engine is None:
        _global_engine = LearningEngine()
    return _global_engine
