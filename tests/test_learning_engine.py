"""Test script for LearningEngine (P3)."""

from manus.agents import (
    LearningEngine, get_learning_engine,
    TaskComplexity, StrategyType,
)


def test_learning_engine():
    """Test the LearningEngine."""
    print("Testing LearningEngine...")
    
    engine = LearningEngine()
    
    tasks = [
        ("What is Python?", TaskComplexity.SIMPLE, StrategyType.SEQUENTIAL, True, 2, 1000, ["search"], []),
        ("List files in directory", TaskComplexity.SIMPLE, StrategyType.SEQUENTIAL, True, 1, 500, ["list_directory"], []),
        ("Compare Python and JavaScript", TaskComplexity.MODERATE, StrategyType.PLANNED, True, 5, 8000, ["search", "compare"], []),
        ("Build a web scraper", TaskComplexity.COMPLEX, StrategyType.ITERATIVE, True, 12, 25000, ["search", "code", "execute"], []),
        ("Create a full-stack app", TaskComplexity.VERY_COMPLEX, StrategyType.EXPLORATORY, False, 25, 120000, ["plan", "code", "test"], ["timeout"]),
        ("Calculate 2+2", TaskComplexity.SIMPLE, StrategyType.SEQUENTIAL, True, 1, 200, ["calculator"], []),
        ("Find files modified today", TaskComplexity.MODERATE, StrategyType.SEQUENTIAL, True, 3, 3000, ["search"], []),
    ]
    
    for task_desc, complexity, strategy, success, steps, duration, tools, errors in tasks:
        engine.record_task(
            task_description=task_desc,
            complexity=complexity,
            strategy=strategy,
            success=success,
            steps=steps,
            duration_ms=duration,
            tools_used=tools,
            errors=errors,
        )
    
    print(f"\nRecorded {len(engine._examples)} task examples")
    
    print("\n--- Strategy Performance ---")
    for strategy in StrategyType:
        perf = engine.get_strategy_performance(strategy)
        if perf.total_attempts > 0:
            print(f"  {strategy.value}: {perf.success_rate:.0%} ({perf.total_attempts} attempts)")
    
    print("\n--- Complexity Estimation ---")
    test_tasks = [
        "What is the weather?",
        "Build a REST API with authentication",
        "Research and compare machine learning frameworks",
    ]
    
    for task in test_tasks:
        complexity = engine.estimate_complexity(task)
        print(f"  '{task[:40]}...' -> {complexity.value}")
    
    print("\n--- Strategy Recommendations ---")
    for task in test_tasks:
        strategy = engine.recommend_strategy(task)
        print(f"  '{task[:30]}...'")
        print(f"    Strategy: {strategy.recommended_strategy.value}")
        print(f"    Est. steps: {strategy.estimated_steps}")
        print(f"    Suggestions: {strategy.suggestions[0] if strategy.suggestions else 'None'}")
    
    print("\n--- Insights ---")
    insights = engine.get_insights()
    if insights:
        for insight in insights:
            print(f"  [{insight.insight_type}] {insight.description}")
            print(f"    Confidence: {insight.confidence:.0%}, Based on: {insight.based_on_samples} samples")
    else:
        print("  (Need more samples to generate insights)")
    
    print("\n--- Failure Analysis ---")
    analysis = engine.analyze_failure_patterns()
    print(f"  Total failures: {analysis.get('total_failures', 0)}")
    
    print("\n✅ All tests passed!")


def test_complexity_estimation():
    """Test complexity estimation."""
    print("\nTesting complexity estimation...")
    
    engine = LearningEngine()
    
    test_cases = [
        ("What is 2+2?", TaskComplexity.SIMPLE),
        ("List all files", TaskComplexity.SIMPLE),
        ("Compare A and B", TaskComplexity.MODERATE),
        ("Build a web app", TaskComplexity.COMPLEX),
        ("Design a distributed system", TaskComplexity.VERY_COMPLEX),
    ]
    
    for task, expected in test_cases:
        result = engine.estimate_complexity(task)
        status = "✅" if result == expected else f"❌ (got {result.value})"
        print(f"  '{task}': {status}")


if __name__ == "__main__":
    test_learning_engine()
    test_complexity_estimation()
