"""Usage statistics API routes."""

from datetime import datetime
from typing import Any

from litestar import get, post
from litestar.controller import Controller
from litestar.params import Parameter
from pydantic import BaseModel

from manus.metrics.service import UsageService
from manus.metrics.recorder import UsageRecorder


class UsageQuery(BaseModel):
    user_id: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    days: int = 30


class UsageController(Controller):
    """Usage statistics API"""

    path = "/api/v1/usage"

    @get()
    async def get_usage(
        self,
        user_id: str | None = Parameter(default=None),
        days: int = Parameter(default=30),
    ) -> dict[str, Any]:
        """Get user usage statistics"""
        service = UsageService()

        usage = service.get_user_usage(
            user_id=user_id,
            days=days,
        )

        return usage

    @get("/trend")
    async def get_usage_trend(
        self,
        user_id: str | None = Parameter(default=None),
        days: int = Parameter(default=30),
    ) -> list[dict[str, Any]]:
        """Get usage trend"""
        service = UsageService()
        return service.get_usage_trend(user_id=user_id, days=days)

    @get("/top-users")
    async def get_top_users(
        self,
        days: int = Parameter(default=30),
        limit: int = Parameter(default=10),
    ) -> list[dict[str, Any]]:
        """Get top users by usage"""
        service = UsageService()
        return service.get_top_users(days=days, limit=limit)

    @get("/tasks")
    async def get_task_usage(
        self,
        user_id: str | None = Parameter(default=None),
        days: int = Parameter(default=30),
    ) -> dict[str, Any]:
        """Get task/tool usage statistics"""
        service = UsageService()
        return service.get_task_usage(user_id=user_id, days=days)


class RecordController(Controller):
    """Record usage data"""

    path = "/api/v1/record"

    @post("/api-call")
    async def record_api_call(
        self,
        provider: str,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: int = 0,
        status_code: int = 200,
        endpoint: str = "",
        error: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Record an API call"""
        recorder = UsageRecorder()
        record_id = recorder.record_api_call(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            status_code=status_code,
            endpoint=endpoint,
            error=error,
            user_id=user_id,
        )
        return {"id": record_id, "success": True}

    @post("/task-execution")
    async def record_task_execution(
        self,
        tool_name: str,
        duration_ms: int = 0,
        status: str = "success",
        task_id: str | None = None,
        user_id: str | None = None,
        input_size: int = 0,
        output_size: int = 0,
    ) -> dict[str, Any]:
        """Record a task execution"""
        recorder = UsageRecorder()
        record_id = recorder.record_task_execution(
            tool_name=tool_name,
            duration_ms=duration_ms,
            status=status,
            task_id=task_id,
            user_id=user_id,
            input_size=input_size,
            output_size=output_size,
        )
        return {"id": record_id, "success": True}
