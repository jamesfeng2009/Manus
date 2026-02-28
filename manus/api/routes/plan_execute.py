import uuid
import time
from typing import Any

from litestar import post, get, delete
from litestar.controller import Controller
from litestar.params import Parameter
from litestar.exceptions import HTTPException
from pydantic import BaseModel, Field

from manus.agents.plan_execute.messaging import get_rabbitmq_client
from manus.agents.plan_execute.repository import PlanExecuteRepository


class SubmitPlanRequest(BaseModel):
    user_id: str = Field(default="default")
    original_input: str
    plan_json: dict[str, Any] | None = None
    mode: str = Field(default="sequential")
    max_iterations: int = Field(default=3)
    enable_verification: bool = Field(default=True)


class SubmitPlanResponse(BaseModel):
    task_id: str
    status: str
    message: str


class PlanStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    current_iteration: int
    final_result: str | None = None
    error: str | None = None
    created_at: str
    updated_at: str
    completed_at: str | None = None


class CancelPlanRequest(BaseModel):
    reason: str | None = None


class CancelPlanResponse(BaseModel):
    task_id: str
    status: str
    message: str


class QueueStatusResponse(BaseModel):
    message_count: int
    consumer_count: int


class PlanExecuteController(Controller):
    path = "/api/plan-execute"

    @post("")
    async def submit_plan(self, data: SubmitPlanRequest) -> SubmitPlanResponse:
        task_id = f"plan_{uuid.uuid4().hex[:12]}"

        message = {
            "message_id": f"msg_{time.time()}_{uuid.uuid4().hex[:8]}",
            "message_type": "plan_execute",
            "task_id": task_id,
            "user_id": data.user_id,
            "timestamp": str(time.time()),
            "payload": {
                "original_input": data.original_input,
                "plan_json": data.plan_json,
                "config": {
                    "mode": data.mode,
                    "max_iterations": data.max_iterations,
                    "enable_verification": data.enable_verification,
                }
            },
            "retry_count": 0,
        }

        try:
            repository = PlanExecuteRepository()
            repository.create_plan(
                task_id=task_id,
                user_id=data.user_id,
                original_input=data.original_input,
                plan_json=data.plan_json,
                mode=data.mode,
                max_iterations=data.max_iterations,
                enable_verification=data.enable_verification,
            )

            client = get_rabbitmq_client()
            result = client.publish(message)

            if not result.success:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to submit task: {result.error}"
                )

            return SubmitPlanResponse(
                task_id=task_id,
                status="submitted",
                message="Plan execution task submitted successfully"
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @get("/{task_id:str}")
    async def get_plan_status(
        self,
        task_id: str = Parameter(description="Task ID")
    ) -> PlanStatusResponse:
        repository = PlanExecuteRepository()

        try:
            plan = repository.get_plan_by_task_id(task_id)

            if not plan:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

            return PlanStatusResponse(
                task_id=plan["task_id"],
                status=plan["status"],
                progress=plan.get("progress") or 0.0,
                current_iteration=plan.get("current_iteration") or 0,
                final_result=plan.get("final_result"),
                error=plan.get("error"),
                created_at=plan["created_at"].isoformat() if plan.get("created_at") else "",
                updated_at=plan["updated_at"].isoformat() if plan.get("updated_at") else "",
                completed_at=plan["completed_at"].isoformat() if plan.get("completed_at") else None,
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @delete("/{task_id:str}", status_code=200)
    async def cancel_plan(
        self,
        task_id: str = Parameter(description="Task ID")
    ) -> CancelPlanResponse:
        repository = PlanExecuteRepository()

        try:
            plan = repository.get_plan(task_id)

            if not plan:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

            if plan.status in ["completed", "failed", "cancelled"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Task is already {plan.status}"
                )

            repository.update_plan_status(
                task_id,
                status="cancelled"
            )

            return CancelPlanResponse(
                task_id=task_id,
                status="cancelled",
                message="Task cancelled successfully"
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @get("/queue/status")
    async def get_queue_status(self) -> QueueStatusResponse:
        try:
            client = get_rabbitmq_client()
            status = client.get_queue_status()

            if "error" in status:
                raise HTTPException(status_code=500, detail=status["error"])

            return QueueStatusResponse(
                message_count=status.get("message_count", 0),
                consumer_count=status.get("consumer_count", 0),
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
