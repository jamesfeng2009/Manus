"""Test script for ReActExecutor (P0)."""

import asyncio
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from manus.agents.executor import ReActExecutor, get_executor
from manus.agents.callbacks import ExecutorCallbacks, ExecutionStatus


async def test_executor():
    """Test the ReActExecutor."""
    print("Testing ReActExecutor...")
    
    executor = get_executor(model_id="gpt-4o")
    
    callbacks = ExecutorCallbacks()
    
    events = []
    
    def on_thinking(thought):
        events.append(f"thinking: {thought[:50]}...")
        print(f"[Thinking] {thought[:50]}...")
    
    def on_action(action, params):
        events.append(f"action: {action}")
        print(f"[Action] {action} {params}")
    
    def on_observation(obs):
        events.append(f"observation: {obs[:50]}...")
        print(f"[Observation] {obs[:50]}...")
    
    def on_status(status):
        events.append(f"status: {status.value}")
        print(f"[Status] {status.value}")
    
    def on_complete(result):
        events.append(f"complete: {result.status.value}")
        print(f"[Complete] {result.status.value}, steps: {result.total_steps}")
    
    callbacks.on_thinking = on_thinking
    callbacks.on_action = on_action
    callbacks.on_observation = on_observation
    callbacks.on_status_change = on_status
    callbacks.on_complete = on_complete
    
    print("\n--- Running task ---")
    result = await executor.execute(
        task="What is 2 + 2?",
        callbacks=callbacks,
    )
    
    print(f"\n--- Result ---")
    print(f"Status: {result.status.value}")
    print(f"Total steps: {result.total_steps}")
    print(f"Final result: {result.final_result}")
    print(f"Error: {result.error}")
    
    return result


async def test_cancel():
    """Test task cancellation."""
    print("\n\n--- Testing cancellation ---")
    
    executor = get_executor(model_id="gpt-4o")
    
    task_id = "test_cancel_001"
    
    executor.cancel_task(task_id)
    
    result = await executor.execute(
        task="Count to 100",
        task_id=task_id,
    )
    
    print(f"Status after cancel: {result.status.value}")
    print(f"Is cancelled: {executor.is_cancelled(task_id)}")


if __name__ == "__main__":
    asyncio.run(test_executor())
