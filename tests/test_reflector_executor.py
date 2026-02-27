"""Test script for ReflectorRetryExecutor (P1)."""

import asyncio
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from manus.agents import ReflectorRetryExecutor, get_reflector_executor, RetryConfig, ExecutorCallbacks


async def test_reflector_executor():
    """Test the ReflectorRetryExecutor."""
    print("Testing ReflectorRetryExecutor...")
    
    retry_config = RetryConfig(
        max_attempts=3,
        wait_seconds=1,
        use_llm=False,
    )
    
    executor = get_reflector_executor(
        model_id="gpt-4o",
        retry_config=retry_config,
    )
    
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
    
    def on_error(error):
        events.append(f"error: {str(error)}")
        print(f"[Error] {error}")
    
    callbacks.on_thinking = on_thinking
    callbacks.on_action = on_action
    callbacks.on_observation = on_observation
    callbacks.on_status_change = on_status
    callbacks.on_complete = on_complete
    callbacks.on_error = on_error
    
    print("\n--- Running task with retry ---")
    result = await executor.execute(
        task="What is 2 + 2?",
        callbacks=callbacks,
    )
    
    print(f"\n--- Result ---")
    print(f"Status: {result.status.value}")
    print(f"Total steps: {result.total_steps}")
    print(f"Final result: {result.final_result}")
    print(f"Error: {result.error}")
    
    print(f"\n--- Retry History ---")
    history = executor.get_retry_history(result.task_id)
    print(f"Retries: {len(history)}")
    
    return result


async def test_execute_with_retry():
    """Test execute_with_retry method."""
    print("\n\n--- Testing execute_with_retry ---")
    
    retry_config = RetryConfig(
        max_attempts=2,
        wait_seconds=0,
        use_llm=False,
    )
    
    executor = get_reflector_executor(
        model_id="gpt-4o",
        retry_config=retry_config,
    )
    
    print("Running task with retry mechanism...")
    result = await executor.execute_with_retry(
        task="List files in current directory",
    )
    
    print(f"\nStatus: {result.status.value}")
    print(f"Steps: {result.total_steps}")


if __name__ == "__main__":
    asyncio.run(test_reflector_executor())
