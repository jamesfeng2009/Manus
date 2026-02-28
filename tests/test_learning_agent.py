"""Test script for LearningAgent."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from manus.agents import (
    LearningAgent,
    LearningEngine,
    TaskComplexity,
    StrategyType,
)


class MockAgent:
    """Mock Agent for testing."""
    
    def __init__(self):
        self.execute_called = False
        self.execute_args = None
    
    async def execute(self, task_id: str, user_input: str, context=None, **kwargs):
        self.execute_called = True
        self.execute_args = (task_id, user_input, context, kwargs)
        
        return {
            "task_id": task_id,
            "status": "completed",
            "final_response": f"Result for: {user_input}",
            "total_steps": 5,
            "history": [
                {"tool": "search", "observation": "Found results"},
                {"tool": "code", "observation": "Code executed"},
            ],
        }


def test_learning_agent_init():
    """Test LearningAgent initialization."""
    print("Testing LearningAgent init...")
    
    mock_agent = MockAgent()
    learning = LearningEngine()
    
    agent = LearningAgent(
        agent=mock_agent,
        learning=learning,
        record_after_execute=True,
        recommend_before_execute=True,
    )
    
    assert agent.agent is mock_agent
    assert agent.learning is learning
    assert agent._record_after_execute is True
    assert agent._recommend_before_execute is True
    
    print("  ✓ Initialization works")


def test_learning_agent_with_default_learning():
    """Test LearningAgent with default learning engine."""
    print("Testing LearningAgent with default learning...")
    
    mock_agent = MockAgent()
    agent = LearningAgent(agent=mock_agent)
    
    assert agent.learning is not None
    assert agent.agent is mock_agent
    
    print("  ✓ Default learning engine works")


def test_proxy_attributes():
    """Test that LearningAgent proxies attributes to wrapped agent."""
    print("Testing attribute proxying...")
    
    mock_agent = MockAgent()
    mock_agent.some_attr = "test_value"
    
    agent = LearningAgent(agent=mock_agent)
    
    assert agent.some_attr == "test_value"
    
    print("  ✓ Attribute proxying works")


async def test_execute_with_learning():
    """Test execute method with learning."""
    print("Testing execute with learning...")
    
    mock_agent = MockAgent()
    learning = LearningEngine()
    
    agent = LearningAgent(
        agent=mock_agent,
        learning=learning,
        record_after_execute=True,
        recommend_before_execute=True,
    )
    
    result = await agent.execute(
        task_id="test_1",
        user_input="帮我写一个排序算法",
    )
    
    assert mock_agent.execute_called is True
    assert result["status"] == "completed"
    assert len(learning._examples) == 1
    
    example = learning._examples[0]
    assert example.task_description == "帮我写一个排序算法"
    assert example.steps == 5
    assert example.success is True
    assert "search" in example.tools_used
    
    print("  ✓ Execute with learning records task")


async def test_execute_without_recording():
    """Test execute without recording."""
    print("Testing execute without recording...")
    
    mock_agent = MockAgent()
    learning = LearningEngine()
    
    agent = LearningAgent(
        agent=mock_agent,
        learning=learning,
        record_after_execute=False,
        recommend_before_execute=True,
    )
    
    result = await agent.execute(
        task_id="test_2",
        user_input="简单任务",
    )
    
    assert len(learning._examples) == 0
    
    print("  ✓ Execute without recording works")


async def test_execute_failure():
    """Test execute with failure."""
    print("Testing execute with failure...")
    
    class FailingAgent:
        async def execute(self, task_id: str, user_input: str, context=None, **kwargs):
            raise RuntimeError("Task failed")
    
    mock_agent = FailingAgent()
    learning = LearningEngine()
    
    agent = LearningAgent(
        agent=mock_agent,
        learning=learning,
        record_after_execute=True,
        recommend_before_execute=True,
    )
    
    try:
        await agent.execute(task_id="test_3", user_input="失败任务")
    except RuntimeError:
        pass
    
    assert len(learning._examples) == 1
    example = learning._examples[0]
    assert example.success is False
    assert "Task failed" in str(example.errors)
    
    print("  ✓ Execute failure records error")


async def test_complexity_estimation():
    """Test complexity estimation."""
    print("Testing complexity estimation...")
    
    mock_agent = MockAgent()
    learning = LearningEngine()
    
    agent = LearningAgent(agent=mock_agent, learning=learning)
    
    simple_task = "What is Python?"
    complex_task = "Build a comprehensive full-stack application with authentication"
    
    simple_complexity = agent.estimate_complexity(simple_task)
    complex_complexity = agent.estimate_complexity(complex_task)
    
    assert simple_complexity in TaskComplexity
    assert complex_complexity in TaskComplexity
    
    print(f"  Simple task: {simple_complexity.value}")
    print(f"  Complex task: {complex_complexity.value}")
    print("  ✓ Complexity estimation works")


async def test_strategy_recommendation():
    """Test strategy recommendation."""
    print("Testing strategy recommendation...")
    
    mock_agent = MockAgent()
    learning = LearningEngine()
    
    agent = LearningAgent(agent=mock_agent, learning=learning)
    
    learning.record_task(
        task_description="Test task",
        complexity=TaskComplexity.SIMPLE,
        strategy=StrategyType.SEQUENTIAL,
        success=True,
        steps=2,
        duration_ms=1000,
        tools_used=["search"],
        errors=[],
    )
    
    strategy = agent.recommend_strategy("Another test task")
    
    assert strategy is not None
    assert hasattr(strategy, "recommended_strategy")
    assert hasattr(strategy, "estimated_steps")
    
    print("  ✓ Strategy recommendation works")


def test_get_insights():
    """Test getting insights."""
    print("Testing get_insights...")
    
    mock_agent = MockAgent()
    learning = LearningEngine()
    
    agent = LearningAgent(agent=mock_agent, learning=learning)
    
    learning.record_task(
        task_description="Test",
        complexity=TaskComplexity.MODERATE,
        strategy=StrategyType.PLANNED,
        success=True,
        steps=5,
        duration_ms=5000,
        tools_used=[],
        errors=[],
    )
    
    insights = agent.get_insights()
    
    assert isinstance(insights, list)
    
    print("  ✓ Get insights works")


def test_get_task_history():
    """Test getting task history."""
    print("Testing get_task_history...")
    
    mock_agent = MockAgent()
    learning = LearningEngine()
    
    agent = LearningAgent(agent=mock_agent, learning=learning)
    
    learning.record_task(
        task_description="Task 1",
        complexity=TaskComplexity.SIMPLE,
        strategy=StrategyType.SEQUENTIAL,
        success=True,
        steps=1,
        duration_ms=100,
        tools_used=[],
        errors=[],
    )
    
    history = agent.get_task_history(limit=10)
    
    assert len(history) == 1
    assert history[0].task_description == "Task 1"
    
    print("  ✓ Get task history works")


async def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 50)
    print("Running LearningAgent Tests")
    print("=" * 50 + "\n")
    
    test_learning_agent_init()
    test_learning_agent_with_default_learning()
    test_proxy_attributes()
    
    await test_execute_with_learning()
    await test_execute_without_recording()
    await test_execute_failure()
    await test_complexity_estimation()
    await test_strategy_recommendation()
    
    test_get_insights()
    test_get_task_history()
    
    print("\n" + "=" * 50)
    print("All tests passed!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
