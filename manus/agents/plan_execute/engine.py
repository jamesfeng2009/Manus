"""Plan Execute Engine - Core execution engine."""

import asyncio
import uuid
from datetime import datetime
from typing import Any

from manus.agents.planner import PlannerAgent
from manus.agents.executor import ReActExecutor, ExecutorCallbacks
from manus.agents.callbacks import ExecutionStatus
from manus.agents.plan_execute.config import (
    PlanExecuteConfig,
    PlanExecuteResult,
    StepResult,
    PlanExecuteCallbacks,
    ExecuteMode,
)
from manus.db import (
    PlanExecution,
    PlanExecutionStatus,
    StepExecution,
    StepExecutionStatus,
    VerificationRecord,
)
from manus.agents.plan_execute.repository import PlanExecuteRepository


class PlanExecuteEngine:
    """Plan->Execute Engine.
    
    Core flow:
    1. Receive user input
    2. Planner generates execution plan (TaskPlan)
    3. Execute each step according to mode:
       - SEQUENTIAL: Execute steps in order
       - PARALLEL: Execute independent steps in parallel
       - ADAPTIVE: Dynamically orchestrate based on dependencies
    4. Optional verification step
    5. Return complete execution result
    """
    
    def __init__(
        self,
        config: PlanExecuteConfig | None = None,
        planner: PlannerAgent | None = None,
        executor: ReActExecutor | None = None,
        repository: PlanExecuteRepository | None = None,
    ):
        self.config = config or PlanExecuteConfig()
        
        self.planner = planner or PlannerAgent(model_id=self.config.planner_model)
        self.executor = executor or ReActExecutor(
            model_id=self.config.executor_model,
            max_steps=self.config.max_steps_per_phase,
            timeout=self.config.timeout,
        )
        self.repository = repository or PlanExecuteRepository()
        
        self.callbacks = PlanExecuteCallbacks()
        
        self._cancelled_tasks: set[str] = set()
    
    async def execute(
        self,
        user_input: str,
        task_id: str | None = None,
        user_id: str = "default",
        context: dict[str, Any] | None = None,
    ) -> PlanExecuteResult:
        """Execute complete plan->execute flow.
        
        Args:
            user_input: User input / task description
            task_id: Task ID (auto-generated if not provided)
            user_id: User ID for tracking
            context: Additional context information
            
        Returns:
            PlanExecuteResult: Complete execution result
        """
        task_id = task_id or f"task_{uuid.uuid4().hex[:12]}"
        context = context or {}
        
        result = PlanExecuteResult(
            task_id=task_id,
            original_input=user_input,
            status=PlanExecutionStatus.PENDING.value,
        )
        
        start_time = datetime.now()
        result.started_at = start_time.isoformat()
        
        plan_db = None
        
        try:
            if self.config.enable_db_record:
                plan_db = self.repository.create_plan(
                    task_id=task_id,
                    user_id=user_id,
                    original_input=user_input,
                    plan_json={},
                    mode=self.config.mode,
                    max_iterations=self.config.max_iterations,
                    enable_verification=self.config.enable_verification,
                )
            
            plan = await self._planning_phase(
                task_id, user_input, context, plan_db
            )
            
            if plan is None:
                result.status = PlanExecutionStatus.FAILED.value
                result.error = "Failed to create plan"
                return result
            
            result.plan = {
                "task_id": plan.task_id,
                "steps": [
                    {
                        "step_id": s.step_id,
                        "description": s.description,
                        "tool": s.tool,
                        "complexity": getattr(s, 'complexity', 'medium'),
                    }
                    for s in plan.steps
                ]
            }
            
            if plan_db:
                self.repository.update_plan_status(
                    plan_db.id,
                    status=PlanExecutionStatus.RUNNING.value,
                    progress=0.0,
                )
            
            result.status = PlanExecutionStatus.RUNNING.value
            self.callbacks.emit_plan_started()
            self.callbacks.emit_status_change(result.status)
            
            await self._execution_phase(task_id, user_input, plan, result, context, plan_db)
            
            if result.status == PlanExecutionStatus.RUNNING.value:
                if result.failed_steps > 0:
                    result.status = PlanExecutionStatus.PARTIAL.value
                else:
                    result.status = PlanExecutionStatus.COMPLETED.value
            
            if self.config.enable_verification and result.status in (
                PlanExecutionStatus.COMPLETED.value,
                PlanExecutionStatus.PARTIAL.value,
            ):
                verification = await self._verification_phase(
                    task_id, user_input, result, plan_db
                )
                result.verification = verification
                
                if not verification.get("verified", True):
                    result.status = PlanExecutionStatus.PARTIAL.value
            
            if plan_db:
                self.repository.update_plan_status(
                    plan_db.id,
                    status=result.status,
                    progress=1.0,
                    final_result=result.final_result,
                )
                
        except Exception as e:
            result.status = PlanExecutionStatus.FAILED.value
            result.error = str(e)
            
            if plan_db:
                self.repository.update_plan_status(
                    plan_db.id,
                    status=PlanExecutionStatus.FAILED.value,
                    error=str(e),
                )
        
        end_time = datetime.now()
        result.completed_at = end_time.isoformat()
        result.duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return result
    
    async def _planning_phase(
        self,
        task_id: str,
        user_input: str,
        context: dict[str, Any],
        plan_db,
    ) -> Any:
        """Planning phase - generate execution plan."""
        try:
            self.callbacks.emit_status_change(PlanExecutionStatus.PLANNING.value)
            
            plan = await self.planner.plan(
                task_id=task_id,
                user_input=user_input,
                context=str(context) if context else None,
            )
            
            plan_json = {
                "task_id": plan.task_id,
                "original_input": plan.original_input,
                "steps": [
                    {
                        "step_id": s.step_id,
                        "description": s.description,
                        "tool": s.tool,
                        "complexity": getattr(s, 'complexity', 'medium'),
                    }
                    for s in plan.steps
                ]
            }
            
            self.callbacks.emit_plan_created(plan_json)
            
            if plan_db:
                self.repository.update_plan_status(
                    plan_db.id,
                    status=PlanExecutionStatus.PENDING.value,
                )
                
                for idx, step in enumerate(plan.steps):
                    self.repository.create_step(
                        plan_id=plan_db.id,
                        step_index=idx,
                        step_id=step.step_id,
                        description=step.description,
                        tool_name=step.tool,
                        complexity=getattr(step, 'complexity', 'medium'),
                    )
            
            return plan
            
        except Exception as e:
            self.callbacks.emit_status_change(PlanExecutionStatus.FAILED.value)
            raise
    
    async def _execution_phase(
        self,
        task_id: str,
        original_input: str,
        plan,
        result: PlanExecuteResult,
        context: dict[str, Any],
        plan_db,
    ):
        """Execution phase - execute plan steps."""
        if self.config.mode == ExecuteMode.SEQUENTIAL.value:
            await self._execute_sequential(task_id, original_input, plan, result, context, plan_db)
        elif self.config.mode == ExecuteMode.PARALLEL.value:
            await self._execute_parallel(task_id, original_input, plan, result, context, plan_db)
        elif self.config.mode == ExecuteMode.ADAPTIVE.value:
            await self._execute_adaptive(task_id, original_input, plan, result, context, plan_db)
    
    async def _execute_sequential(
        self,
        task_id: str,
        original_input: str,
        plan,
        result: PlanExecuteResult,
        context: dict[str, Any],
        plan_db,
    ):
        """Sequential execution - execute plan steps in order."""
        for iteration in range(self.config.max_iterations):
            result.iterations = iteration + 1
            
            self.callbacks.emit_iteration(iteration + 1, self.config.max_iterations)
            
            if plan_db:
                self.repository.update_plan_status(
                    plan_db.id,
                    current_iteration=iteration + 1,
                )
            
            all_completed = True
            has_failures = False
            
            for step in plan.steps:
                if task_id in self._cancelled_tasks:
                    result.status = PlanExecutionStatus.CANCELLED.value
                    return
                
                step_result = await self._execute_step(
                    task_id, step, original_input, context, plan_db
                )
                result.steps.append(step_result)
                result.total_steps += 1
                
                if step_result.status == StepExecutionStatus.COMPLETED.value:
                    result.completed_steps += 1
                else:
                    all_completed = False
                    has_failures = True
                    
                    if not self.config.retry_on_error:
                        break
                
                progress = result.completed_steps / len(plan.steps)
                result.progress = progress
                self.callbacks.emit_progress(progress)
                
                if plan_db:
                    self.repository.update_plan_status(
                        plan_db.id,
                        progress=progress,
                    )
            
            if all_completed:
                result.status = PlanExecutionStatus.COMPLETED.value
                result.final_result = self._aggregate_results(result.steps)
                break
            
            if has_failures and iteration < self.config.max_iterations - 1:
                if self.config.retry_on_error:
                    context["failed_steps"] = [
                        s.to_dict() for s in result.steps 
                        if s.status == StepExecutionStatus.FAILED.value
                    ]
    
    async def _execute_parallel(
        self,
        task_id: str,
        original_input: str,
        plan,
        result: PlanExecuteResult,
        context: dict[str, Any],
        plan_db,
    ):
        """Parallel execution - execute independent steps in parallel."""
        independent_steps = self._identify_independent_steps(plan.steps)
        
        for batch in self._batch_steps(independent_steps, self.config.max_concurrent_steps):
            if task_id in self._cancelled_tasks:
                result.status = PlanExecutionStatus.CANCELLED.value
                return
            
            tasks = [
                self._execute_step(task_id, step, original_input, context, plan_db)
                for step in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for step_result in batch_results:
                if isinstance(step_result, Exception):
                    error_step = StepResult(
                        step_id="unknown",
                        description="Parallel execution error",
                        status=StepExecutionStatus.FAILED.value,
                        error=str(step_result),
                    )
                    result.steps.append(error_step)
                    result.failed_steps += 1
                else:
                    result.steps.append(step_result)
                    if step_result.status == StepExecutionStatus.COMPLETED.value:
                        result.completed_steps += 1
                    else:
                        result.failed_steps += 1
        
        result.total_steps = len(result.steps)
        progress = result.completed_steps / result.total_steps if result.total_steps > 0 else 0
        result.progress = progress
        self.callbacks.emit_progress(progress)
        
        if result.failed_steps > 0 and not self.config.retry_on_error:
            result.status = PlanExecutionStatus.PARTIAL.value
        else:
            result.status = PlanExecutionStatus.COMPLETED.value
            result.final_result = self._aggregate_results(result.steps)
    
    async def _execute_adaptive(
        self,
        task_id: str,
        original_input: str,
        plan,
        result: PlanExecuteResult,
        context: dict[str, Any],
        plan_db,
    ):
        """Adaptive execution - dynamically adjust based on step results."""
        remaining_steps = list(plan.steps)
        completed_step_ids = set()
        
        while remaining_steps:
            next_step = self._select_next_step(remaining_steps, completed_step_ids)
            
            if next_step is None:
                break
            
            step_result = await self._execute_step(
                task_id, next_step, original_input, context, plan_db
            )
            result.steps.append(step_result)
            result.total_steps += 1
            
            if step_result.status == StepExecutionStatus.COMPLETED.value:
                result.completed_steps += 1
                completed_step_ids.add(next_step.step_id)
            else:
                result.failed_steps += 1
            
            remaining_steps.remove(next_step)
            
            progress = result.completed_steps / len(plan.steps)
            result.progress = progress
            self.callbacks.emit_progress(progress)
            
            if step_result.status == StepExecutionStatus.FAILED.value:
                if self.config.retry_on_error and step_result.retry_count < self.config.max_retries:
                    continue
        
        result.status = (
            PlanExecutionStatus.COMPLETED.value 
            if result.failed_steps == 0 
            else PlanExecutionStatus.PARTIAL.value
        )
        result.final_result = self._aggregate_results(result.steps)
    
    async def _execute_step(
        self,
        task_id: str,
        step,
        original_input: str,
        context: dict[str, Any],
        plan_db,
    ) -> StepResult:
        """Execute a single step."""
        step_db = None
        if plan_db:
            steps = self.repository.get_steps(plan_db.id)
            for s in steps:
                if s.step_id == step.step_id:
                    step_db = s
                    break
        
        step_result = StepResult(
            step_id=step.step_id,
            description=step.description,
            status=StepExecutionStatus.PENDING.value,
        )
        
        start_time = datetime.now()
        step_result.start_time = start_time.isoformat()
        
        self.callbacks.emit_step_start(step_result)
        
        if step_db:
            self.repository.start_step(step_db.id)
        
        retry_count = 0
        
        try:
            step_prompt = self._build_step_prompt(step, original_input, context)
            
            step_callbacks = ExecutorCallbacks()
            step_callbacks.on_token = self.callbacks.on_token
            step_callbacks.on_thinking = self.callbacks.emit_thinking
            
            exec_result = await self.executor.execute(
                task=f"Step {step.step_id}: {step.description}\n\n{step_prompt}",
                context=context,
                callbacks=step_callbacks,
                task_id=f"{task_id}_step_{step.step_id}",
            )
            
            step_result.status = (
                StepExecutionStatus.COMPLETED.value
                if exec_result.status == ExecutionStatus.COMPLETED
                else StepExecutionStatus.FAILED.value
            )
            step_result.result = exec_result.final_result
            step_result.error = exec_result.error
            step_result.tool_calls = [
                {
                    "step": r.step,
                    "action": r.action,
                    "observation": r.observation[:500] if r.observation else None,
                }
                for r in exec_result.history
            ]
            
            if step_db:
                if step_result.status == StepExecutionStatus.COMPLETED.value:
                    self.repository.complete_step(
                        step_db.id,
                        step_result.result or "",
                        step_result.tool_calls,
                    )
                else:
                    self.repository.fail_step(
                        step_db.id,
                        step_result.error or "Unknown error",
                    )
            
        except Exception as e:
            step_result.status = StepExecutionStatus.FAILED.value
            step_result.error = str(e)
            
            if step_db:
                self.repository.fail_step(step_db.id, str(e))
            
            self.callbacks.emit_step_error(step_result, e)
        
        end_time = datetime.now()
        step_result.end_time = end_time.isoformat()
        step_result.duration_ms = int((end_time - start_time).total_seconds() * 1000)
        step_result.retry_count = retry_count
        
        self.callbacks.emit_step_complete(step_result)
        
        return step_result
    
    async def _verification_phase(
        self,
        task_id: str,
        user_input: str,
        result: PlanExecuteResult,
        plan_db,
    ) -> dict[str, Any]:
        """Verification phase - verify execution results."""
        self.callbacks.emit_status_change("verifying")
        
        verification = {
            "verified": result.status == PlanExecutionStatus.COMPLETED.value,
            "checks": [],
            "issues": [],
            "suggestions": [],
        }
        
        if result.failed_steps > 0:
            verification["issues"].append(f"{result.failed_steps} steps failed")
            verification["verified"] = False
        
        if plan_db:
            self.repository.create_verification(
                plan_id=plan_db.id,
                iteration=result.iterations,
                verification_type="final",
                verified=verification["verified"],
                issues=verification["issues"],
                suggestions=verification["suggestions"],
            )
        
        self.callbacks.emit_verification(verification)
        
        return verification
    
    def _identify_independent_steps(self, steps: list) -> list:
        """Identify steps that can be executed in parallel."""
        return [s for s in steps if not getattr(s, 'dependencies', None) or not s.dependencies]
    
    def _batch_steps(self, steps: list, batch_size: int) -> list[list]:
        """Batch steps for parallel execution."""
        return [steps[i:i+batch_size] for i in range(0, len(steps), batch_size)]
    
    def _select_next_step(self, remaining_steps: list, completed_step_ids: set) -> Any | None:
        """Intelligently select next step to execute."""
        for step in remaining_steps:
            deps = getattr(step, 'dependencies', None) or []
            if not deps or all(dep in completed_step_ids for dep in deps):
                return step
        return remaining_steps[0] if remaining_steps else None
    
    def _build_step_prompt(self, step, original_input: str, context: dict) -> str:
        """Build step execution prompt."""
        prompt = f"""Execute this specific step from the overall task:

Original Task: {original_input}

Current Step: {step.description}

"""
        if step.tool:
            prompt += f"Recommended Tool: {step.tool}\n"
        
        if context:
            prompt += f"\nContext: {context}\n"
        
        return prompt
    
    def _aggregate_results(self, steps: list[StepResult]) -> str:
        """Aggregate results from all steps."""
        results = []
        for step in steps:
            if step.result:
                results.append(f"Step {step.step_id}: {step.result}")
        
        return "\n\n".join(results) if results else "No results"
    
    def cancel_task(self, task_id: str):
        """Cancel a running task."""
        self._cancelled_tasks.add(task_id)
        self.executor.cancel_task(task_id)
    
    def is_cancelled(self, task_id: str) -> bool:
        """Check if task is cancelled."""
        return task_id in self._cancelled_tasks


_plan_execute_engine: PlanExecuteEngine | None = None


def get_plan_execute_engine(config: PlanExecuteConfig | None = None) -> PlanExecuteEngine:
    """Get global PlanExecuteEngine instance."""
    global _plan_execute_engine
    if _plan_execute_engine is None:
        _plan_execute_engine = PlanExecuteEngine(config=config)
    return _plan_execute_engine


__all__ = [
    "PlanExecuteEngine",
    "get_plan_execute_engine",
]
