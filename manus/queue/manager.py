import uuid
import os
from typing import Any
from manus.db import Task, TaskStatus, TaskType, get_database, Database
from manus.queue.repository import TaskRepository
from manus.queue.websocket import get_ws_manager, TaskEvent


class TaskQueueManager:
    def __init__(self, database: Database | None = None, redis_url: str | None = None):
        self.db = database or get_database()
        self.repository = TaskRepository(self.db)
        self.ws_manager = get_ws_manager()
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._queue = None

    @property
    def queue(self):
        if self._queue is None:
            try:
                from redis import Redis
                from rq import Queue
                self._queue = Queue("manus-tasks", connection=Redis.from_url(self._redis_url))
            except ImportError:
                self._queue = None
        return self._queue

    def submit_task(
        self,
        user_id: str,
        task_type: str,
        input_data: dict[str, Any],
        priority: int = 0,
    ) -> Task:
        task = Task(
            id=f"task_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            task_type=task_type,
            input_data=input_data,
            priority=priority,
            status=TaskStatus.PENDING.value,
        )

        task = self.repository.create(task)

        self.repository.add_event(task.id, "created", {"task_type": task_type})

        if self.queue:
            from rq.job import Job
            job = self.queue.enqueue(
                "manus.queue.worker.process_task",
                task.id,
                task_type,
                input_data,
                job_timeout=3600,
                result_ttl=86400,
            )
            task.status = TaskStatus.QUEUED.value
            task = self.repository.update(task)
            self.repository.add_event(task.id, "queued", {"job_id": job.id})

        return task

    def get_task(self, task_id: str) -> Task | None:
        return self.repository.get_by_id(task_id)

    def get_user_tasks(self, user_id: str, limit: int = 50) -> list[Task]:
        return self.repository.get_by_user(user_id, limit)

    def list_tasks(self, status: TaskStatus | None = None, limit: int = 100) -> list[Task]:
        return self.repository.list_all(status, limit)

    def cancel_task(self, task_id: str) -> bool:
        task = self.repository.get_by_id(task_id)
        if not task:
            return False

        if task.status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value):
            return False

        if self.queue:
            from rq.job import Job
            jobs = self.queue.get_job_ids()
            for job_id in jobs:
                if task_id in str(job_id):
                    job = self.queue.fetch_job(job_id)
                    if job:
                        job.cancel()
                    break

        task.status = TaskStatus.CANCELLED.value
        self.repository.update(task)
        self.repository.add_event(task.id, "cancelled", {})
        return True

    def delete_task(self, task_id: str) -> bool:
        return self.repository.delete(task_id)

    def get_task_events(self, task_id: str) -> list:
        return self.repository.get_events(task_id)

    def add_dependency(self, task_id: str, depends_on_task_id: str) -> bool:
        from manus.db.models import TaskDependency
        if task_id == depends_on_task_id:
            return False
        dep = TaskDependency(
            task_id=task_id,
            depends_on_task_id=depends_on_task_id,
            status="pending",
        )
        with self.db.get_session() as session:
            session.add(dep)
            session.commit()
        return True

    def get_dependencies(self, task_id: str) -> list[str]:
        from manus.db.models import TaskDependency
        with self.db.get_session() as session:
            deps = session.query(TaskDependency).filter(
                TaskDependency.task_id == task_id
            ).all()
            return [d.depends_on_task_id for d in deps]

    def check_dependencies_met(self, task_id: str) -> bool:
        from manus.db.models import TaskDependency
        with self.db.get_session() as session:
            deps = session.query(TaskDependency).filter(
                TaskDependency.task_id == task_id,
                TaskDependency.status != "completed",
            ).all()
            for dep in deps:
                parent = session.query(Task).filter(Task.id == dep.depends_on_task_id).first()
                if not parent or parent.status != TaskStatus.COMPLETED.value:
                    return False
            return True

    def wait_for_dependencies(self, task_id: str, timeout: int = 300) -> bool:
        import time
        start = time.time()
        while time.time() - start < timeout:
            if self.check_dependencies_met(task_id):
                return True
            time.sleep(1)
        return False


_manager: TaskQueueManager | None = None


def get_queue_manager() -> TaskQueueManager:
    global _manager
    if _manager is None:
        _manager = TaskQueueManager()
    return _manager
