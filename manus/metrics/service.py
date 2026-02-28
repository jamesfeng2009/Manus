"""Usage statistics service."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from manus.db.models import APIUsage, TaskUsage
from manus.db.database import get_db
from manus.metrics.cost import CostCalculator


class UsageService:
    """Service for querying usage statistics."""

    def __init__(self, db_session: Session | None = None):
        self._db = db_session

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = next(get_db())
        return self._db

    def get_user_usage(
        self,
        user_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        days: int | None = None,
    ) -> dict[str, Any]:
        """Get usage statistics for a user."""
        if days is not None:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

        query = self.db.query(APIUsage)

        if user_id:
            query = query.filter(APIUsage.user_id == user_id)

        if start_date:
            query = query.filter(APIUsage.created_at >= start_date)
        if end_date:
            query = query.filter(APIUsage.created_at <= end_date)

        records = query.all()

        total_calls = len(records)
        total_prompt = sum(r.prompt_tokens for r in records)
        total_completion = sum(r.completion_tokens for r in records)
        total_tokens = total_prompt + total_completion

        by_provider = {}
        for r in records:
            key = f"{r.provider}/{r.model}"
            if key not in by_provider:
                by_provider[key] = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}
            by_provider[key]["calls"] += 1
            by_provider[key]["prompt_tokens"] += r.prompt_tokens
            by_provider[key]["completion_tokens"] += r.completion_tokens

        total_cost = 0.0
        for r in records:
            cost = CostCalculator.calculate_cost(
                r.provider, r.model, r.prompt_tokens, r.completion_tokens
            )
            total_cost += cost

        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "total_cost_usd": round(total_cost, 4),
            "by_provider": by_provider,
        }

    def get_usage_trend(
        self,
        user_id: str | None = None,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Get daily usage trend."""
        start_date = datetime.now() - timedelta(days=days)

        query = self.db.query(
            func.date(APIUsage.created_at).label("date"),
            func.count(APIUsage.id).label("calls"),
            func.sum(APIUsage.prompt_tokens).label("prompt_tokens"),
            func.sum(APIUsage.completion_tokens).label("completion_tokens"),
            func.sum(APIUsage.total_tokens).label("total_tokens"),
        ).filter(APIUsage.created_at >= start_date)

        if user_id:
            query = query.filter(APIUsage.user_id == user_id)

        query = query.group_by(func.date(APIUsage.created_at)).order_by("date")

        results = query.all()

        trend = []
        for r in results:
            trend.append({
                "date": str(r.date),
                "calls": r.calls,
                "prompt_tokens": r.prompt_tokens or 0,
                "completion_tokens": r.completion_tokens or 0,
                "total_tokens": r.total_tokens or 0,
            })

        return trend

    def get_top_users(self, days: int = 30, limit: int = 10) -> list[dict[str, Any]]:
        """Get top users by usage."""
        start_date = datetime.now() - timedelta(days=days)

        query = self.db.query(
            APIUsage.user_id,
            func.count(APIUsage.id).label("calls"),
            func.sum(APIUsage.total_tokens).label("total_tokens"),
        ).filter(APIUsage.created_at >= start_date)

        query = query.group_by(APIUsage.user_id).order_by(
            func.sum(APIUsage.total_tokens).desc()
        ).limit(limit)

        results = query.all()

        return [
            {
                "user_id": r.user_id,
                "calls": r.calls,
                "total_tokens": r.total_tokens or 0,
            }
            for r in results
        ]

    def get_task_usage(
        self,
        user_id: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get task/tool usage statistics."""
        start_date = datetime.now() - timedelta(days=days)

        query = self.db.query(
            TaskUsage.tool_name,
            func.count(TaskUsage.id).label("executions"),
            func.avg(TaskUsage.duration_ms).label("avg_duration_ms"),
            func.sum(TaskUsage.duration_ms).label("total_duration_ms"),
        ).filter(TaskUsage.created_at >= start_date)

        if user_id:
            query = query.filter(TaskUsage.user_id == user_id)

        query = query.group_by(TaskUsage.tool_name).order_by(
            func.count(TaskUsage.id).desc()
        )

        results = query.all()

        return {
            "tools": [
                {
                    "name": r.tool_name,
                    "executions": r.executions,
                    "avg_duration_ms": round(r.avg_duration_ms or 0, 2),
                    "total_duration_ms": r.total_duration_ms or 0,
                }
                for r in results
            ]
        }


_service_instance: UsageService | None = None


def get_usage_service() -> UsageService:
    global _service_instance
    if _service_instance is None:
        _service_instance = UsageService()
    return _service_instance
