"""Usage recorder for tracking API and task usage."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from manus.db.models import APIUsage, TaskUsage
from manus.db.database import get_db


class UsageRecorder:
    """Record API and task usage statistics."""

    def __init__(self, db_session: Session | None = None):
        self._db = db_session

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = next(get_db())
        return self._db

    def record_api_call(
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
    ) -> str:
        """Record an API call."""
        record = APIUsage(
            id=f"api_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            status_code=status_code,
            endpoint=endpoint,
            error=error,
            created_at=datetime.now(),
        )
        self.db.add(record)
        self.db.commit()
        return record.id

    def record_task_execution(
        self,
        tool_name: str,
        duration_ms: int = 0,
        status: str = "success",
        task_id: str | None = None,
        user_id: str | None = None,
        input_size: int = 0,
        output_size: int = 0,
    ) -> str:
        """Record a task/tool execution."""
        record = TaskUsage(
            id=f"task_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            task_id=task_id,
            tool_name=tool_name,
            duration_ms=duration_ms,
            status=status,
            input_size=input_size,
            output_size=output_size,
            created_at=datetime.now(),
        )
        self.db.add(record)
        self.db.commit()
        return record.id


_recorder_instance: UsageRecorder | None = None


def get_recorder() -> UsageRecorder:
    global _recorder_instance
    if _recorder_instance is None:
        _recorder_instance = UsageRecorder()
    return _recorder_instance
