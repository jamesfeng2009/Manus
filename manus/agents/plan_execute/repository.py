"""Plan Execute repository for database operations."""

from datetime import datetime
from typing import Any, TypedDict
from sqlalchemy.orm import Session

from manus.db.database import Database
from manus.db.models import (
    PlanExecution,
    PlanExecutionStatus,
    StepExecution,
    StepExecutionStatus,
    VerificationRecord,
)


class PlanDict(TypedDict):
    id: str
    task_id: str
    user_id: str
    original_input: str
    plan_json: dict | None
    mode: str
    max_iterations: int
    enable_verification: bool
    verify_each_step: bool
    status: str
    current_iteration: int
    progress: float
    final_result: str | None
    error: str | None
    created_at: datetime | None
    updated_at: datetime | None
    completed_at: datetime | None


class PlanExecuteRepository:
    """Repository for plan execution database operations."""

    def __init__(self, database: Database | None = None):
        self.db = database

    def _get_db(self) -> Database:
        if self.db is None:
            self.db = Database()
        return self.db

    def _to_dict(self, plan: PlanExecution) -> PlanDict:
        return PlanDict(
            id=plan.id,
            task_id=plan.task_id,
            user_id=plan.user_id,
            original_input=plan.original_input,
            plan_json=plan.plan_json,
            mode=plan.mode,
            max_iterations=plan.max_iterations,
            enable_verification=plan.enable_verification,
            verify_each_step=plan.verify_each_step,
            status=plan.status,
            current_iteration=plan.current_iteration,
            progress=plan.progress,
            final_result=plan.final_result,
            error=plan.error,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            completed_at=plan.completed_at,
        )
    
    def create_plan(
        self,
        task_id: str,
        user_id: str,
        original_input: str,
        plan_json: dict[str, Any],
        mode: str,
        max_iterations: int,
        enable_verification: bool,
    ) -> PlanExecution:
        """Create a new plan execution record."""
        db = self._get_db()
        with db.get_session() as session:
            plan = PlanExecution(
                task_id=task_id,
                user_id=user_id,
                original_input=original_input,
                plan_json=plan_json,
                mode=mode,
                max_iterations=max_iterations,
                enable_verification=enable_verification,
                status=PlanExecutionStatus.PENDING.value,
            )
            session.add(plan)
            session.commit()
            session.refresh(plan)
            return plan
    
    def get_plan(self, plan_id: str) -> PlanExecution | None:
        """Get plan by ID."""
        db = self._get_db()
        with db.get_session() as session:
            return session.query(PlanExecution).filter(
                PlanExecution.id == plan_id
            ).first()
    
    def get_plan_by_task_id(self, task_id: str) -> PlanDict | None:
        """Get plan by task ID."""
        db = self._get_db()
        with db.get_session() as session:
            plan = session.query(PlanExecution).filter(
                PlanExecution.task_id == task_id
            ).first()
            if plan:
                return self._to_dict(plan)
            return None
    
    def update_plan_status(
        self,
        plan_id: str,
        status: str,
        progress: float | None = None,
        current_iteration: int | None = None,
        final_result: str | None = None,
        error: str | None = None,
    ) -> PlanExecution | None:
        """Update plan status by plan id."""
        db = self._get_db()
        with db.get_session() as session:
            plan = session.query(PlanExecution).filter(
                PlanExecution.id == plan_id
            ).first()
            if plan:
                plan.status = status
                if progress is not None:
                    plan.progress = progress
                if current_iteration is not None:
                    plan.current_iteration = current_iteration
                if final_result is not None:
                    plan.final_result = final_result
                if error is not None:
                    plan.error = error
                if status in (PlanExecutionStatus.COMPLETED.value, 
                              PlanExecutionStatus.FAILED.value,
                              PlanExecutionStatus.CANCELLED.value):
                    plan.completed_at = datetime.now()
                plan.updated_at = datetime.now()
            return plan

    def update_plan_status_by_task_id(
        self,
        task_id: str,
        status: str,
        progress: float | None = None,
        current_iteration: int | None = None,
        final_result: str | None = None,
        error: str | None = None,
    ) -> PlanExecution | None:
        """Update plan status by task id."""
        db = self._get_db()
        with db.get_session() as session:
            plan = session.query(PlanExecution).filter(
                PlanExecution.task_id == task_id
            ).first()
            if plan:
                plan.status = status
                if progress is not None:
                    plan.progress = progress
                if current_iteration is not None:
                    plan.current_iteration = current_iteration
                if final_result is not None:
                    plan.final_result = final_result
                if error is not None:
                    plan.error = error
                if status in (PlanExecutionStatus.COMPLETED.value, 
                              PlanExecutionStatus.FAILED.value,
                              PlanExecutionStatus.CANCELLED.value):
                    plan.completed_at = datetime.now()
                plan.updated_at = datetime.now()
                session.commit()
            return plan
    
    def create_step(
        self,
        plan_id: str,
        step_index: int,
        step_id: str,
        description: str,
        tool_name: str | None = None,
        complexity: str | None = None,
        dependencies: list | None = None,
    ) -> StepExecution:
        """Create a new step execution record."""
        db = self._get_db()
        with db.get_session() as session:
            step = StepExecution(
                plan_id=plan_id,
                step_index=step_index,
                step_id=step_id,
                description=description,
                tool_name=tool_name,
                complexity=complexity,
                dependencies=dependencies,
                status=StepExecutionStatus.PENDING.value,
            )
            session.add(step)
            session.commit()
            session.refresh(step)
            return step
    
    def get_steps(self, plan_id: str) -> list[StepExecution]:
        """Get all steps for a plan."""
        db = self._get_db()
        with db.get_session() as session:
            return session.query(StepExecution).filter(
                StepExecution.plan_id == plan_id
            ).order_by(StepExecution.step_index).all()
    
    def update_step(
        self,
        step_id: str,
        status: str | None = None,
        result: str | None = None,
        error: str | None = None,
        tool_calls_json: list | None = None,
        retry_count: int | None = None,
    ) -> StepExecution | None:
        """Update step execution record."""
        db = self._get_db()
        with db.get_session() as session:
            step = session.query(StepExecution).filter(
                StepExecution.id == step_id
            ).first()
            if step:
                if status is not None:
                    step.status = status
                if result is not None:
                    step.result = result
                if error is not None:
                    step.error = error
                if tool_calls_json is not None:
                    step.tool_calls_json = tool_calls_json
                if retry_count is not None:
                    step.retry_count = retry_count
                if status == StepExecutionStatus.RUNNING.value and not step.started_at:
                    step.started_at = datetime.now()
                elif status in (StepExecutionStatus.COMPLETED.value,
                               StepExecutionStatus.FAILED.value,
                               StepExecutionStatus.SKIPPED.value):
                    step.completed_at = datetime.now()
                    if step.started_at:
                        step.duration_ms = int(
                            (step.completed_at - step.started_at).total_seconds() * 1000
                        )
                session.commit()
                session.refresh(step)
            return step
    
    def start_step(self, step_id: str) -> StepExecution | None:
        """Mark step as started."""
        return self.update_step(step_id, status=StepExecutionStatus.RUNNING.value)
    
    def complete_step(
        self,
        step_id: str,
        result: str,
        tool_calls_json: list | None = None,
    ) -> StepExecution | None:
        """Mark step as completed."""
        return self.update_step(
            step_id,
            status=StepExecutionStatus.COMPLETED.value,
            result=result,
            tool_calls_json=tool_calls_json,
        )
    
    def fail_step(
        self,
        step_id: str,
        error: str,
        retry_count: int = 0,
    ) -> StepExecution | None:
        """Mark step as failed."""
        return self.update_step(
            step_id,
            status=StepExecutionStatus.FAILED.value,
            error=error,
            retry_count=retry_count,
        )
    
    def create_verification(
        self,
        plan_id: str,
        step_id: str | None = None,
        iteration: int | None = None,
        verification_type: str | None = None,
        verified: bool = False,
        issues: list | None = None,
        suggestions: list | None = None,
        verification_prompt: str | None = None,
        verification_result: str | None = None,
        duration_ms: int | None = None,
    ) -> VerificationRecord:
        """Create a verification record."""
        db = self._get_db()
        with db.get_session() as session:
            record = VerificationRecord(
                plan_id=plan_id,
                step_id=step_id,
                iteration=iteration,
                verification_type=verification_type,
                verified=verified,
                issues=issues,
                suggestions=suggestions,
                verification_prompt=verification_prompt,
                verification_result=verification_result,
                duration_ms=duration_ms,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record
    
    def get_verifications(self, plan_id: str) -> list[VerificationRecord]:
        """Get all verifications for a plan."""
        db = self._get_db()
        with db.get_session() as session:
            return session.query(VerificationRecord).filter(
                VerificationRecord.plan_id == plan_id
            ).all()
    
    def get_plan_progress(self, plan_id: str) -> float:
        """Calculate plan execution progress."""
        db = self._get_db()
        with db.get_session() as session:
            total = session.query(StepExecution).filter(
                StepExecution.plan_id == plan_id
            ).count()
            if total == 0:
                return 0.0
            completed = session.query(StepExecution).filter(
                StepExecution.plan_id == plan_id,
                StepExecution.status.in_([
                    StepExecutionStatus.COMPLETED.value,
                    StepExecutionStatus.SKIPPED.value,
                ])
            ).count()
            return completed / total
    
    def list_plans(
        self,
        user_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[PlanExecution]:
        """List plans with filters."""
        db = self._get_db()
        with db.get_session() as session:
            query = session.query(PlanExecution)
            if user_id:
                query = query.filter(PlanExecution.user_id == user_id)
            if status:
                query = query.filter(PlanExecution.status == status)
            return query.order_by(PlanExecution.created_at.desc()).limit(limit).all()


_plan_execute_repo: PlanExecuteRepository | None = None


def get_plan_execute_repository() -> PlanExecuteRepository:
    """Get global plan execute repository instance."""
    global _plan_execute_repo
    if _plan_execute_repo is None:
        _plan_execute_repo = PlanExecuteRepository()
    return _plan_execute_repo


__all__ = [
    "PlanExecuteRepository",
    "get_plan_execute_repository",
]
