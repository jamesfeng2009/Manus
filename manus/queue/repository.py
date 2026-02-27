from manus.db import Database, Task, TaskEvent, TaskStatus
from datetime import datetime
from typing import Any


class TaskRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self, task: Task) -> Task:
        with self.db.get_session() as session:
            session.add(task)
            session.flush()
            session.refresh(task)
            return task

    def get_by_id(self, task_id: str) -> Task | None:
        with self.db.get_session() as session:
            return session.query(Task).filter(Task.id == task_id).first()

    def get_by_user(self, user_id: str, limit: int = 50) -> list[Task]:
        with self.db.get_session() as session:
            return (
                session.query(Task)
                .filter(Task.user_id == user_id)
                .order_by(Task.created_at.desc())
                .limit(limit)
                .all()
            )

    def list_all(self, status: TaskStatus | None = None, limit: int = 100) -> list[Task]:
        with self.db.get_session() as session:
            query = session.query(Task)
            if status:
                query = query.filter(Task.status == status.value)
            return query.order_by(Task.created_at.desc()).limit(limit).all()

    def update(self, task: Task) -> Task:
        with self.db.get_session() as session:
            session.merge(task)
            session.flush()
            session.refresh(task)
            return task

    def update_progress(self, task_id: str, progress: float):
        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.progress = progress
                task.updated_at = datetime.now()

    def update_status(self, task_id: str, status: TaskStatus):
        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = status.value
                task.updated_at = datetime.now()
                if status == TaskStatus.RUNNING:
                    task.started_at = datetime.now()
                elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    task.completed_at = datetime.now()

    def update_result(self, task_id: str, result: dict[str, Any] | None, error: str | None = None):
        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.result = result
                task.error = error
                task.updated_at = datetime.now()

    def delete(self, task_id: str) -> bool:
        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                session.delete(task)
                return True
            return False

    def add_event(self, task_id: str, event_type: str, event_data: dict[str, Any] | None = None):
        with self.db.get_session() as session:
            event = TaskEvent(
                task_id=task_id,
                event_type=event_type,
                event_data=event_data,
            )
            session.add(event)

    def get_events(self, task_id: str) -> list[TaskEvent]:
        with self.db.get_session() as session:
            return (
                session.query(TaskEvent)
                .filter(TaskEvent.task_id == task_id)
                .order_by(TaskEvent.created_at.asc())
                .all()
            )
