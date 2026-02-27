from sqlalchemy import Column, String, Float, Integer, Boolean, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
from enum import Enum
import uuid


Base = declarative_base()


class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    AGENT_EXECUTE = "agent_execute"
    AGENT_PLAN = "agent_plan"
    TOOL_BROWSER = "tool_browser"
    TOOL_SEARCH = "tool_search"
    TOOL_CODE = "tool_code"
    MULTIMODAL_AUDIO = "multimodal_audio"
    MULTIMODAL_VIDEO = "multimodal_video"
    MULTIMODAL_PDF = "multimodal_pdf"
    FILE_PROCESS = "file_process"
    FILE_DOWNLOAD = "file_download"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(64), primary_key=True, default=lambda: f"task_{uuid.uuid4().hex[:12]}")
    user_id = Column(String(64), nullable=False, index=True)
    task_type = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default=TaskStatus.PENDING.value)
    progress = Column(Float, nullable=False, default=0.0)
    input_data = Column(JSON)
    result = Column(JSON)
    error = Column(Text)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    events = relationship("TaskEvent", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_created_at", "created_at"),
    )


class TaskEvent(Base):
    __tablename__ = "task_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(32), nullable=False)
    event_data = Column(JSON)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    task = relationship("Task", back_populates="events")


class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, default=lambda: f"user_{uuid.uuid4().hex[:12]}")
    email = Column(String(255), unique=True)
    username = Column(String(128))
    password_hash = Column(String(256))
    avatar_url = Column(String(512))
    provider = Column(String(32))
    provider_id = Column(String(128))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(String(32), default="user")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    tasks = relationship("Task", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")

    __table_args__ = (
        Index("idx_users_provider", "provider", "provider_id"),
    )


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(64), primary_key=True, default=lambda: f"key_{uuid.uuid4().hex[:12]}")
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key_hash = Column(String(256), nullable=False)
    name = Column(String(128))
    rate_limit = Column(Integer, default=60)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    expires_at = Column(DateTime)

    user = relationship("User", back_populates="api_keys")

    __table_args__ = (
        Index("idx_api_keys_key_hash", "key_hash"),
    )


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    depends_on_task_id = Column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(32), default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (
        Index("idx_task_deps_task_id", "task_id"),
        Index("idx_task_deps_depends_on", "depends_on_task_id"),
    )


class APIUsage(Base):
    __tablename__ = "api_usage"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"))
    provider = Column(String(32), nullable=False)
    model = Column(String(64), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer)
    status_code = Column(Integer)
    endpoint = Column(String(128))
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (
        Index("idx_api_usage_user_id", "user_id"),
        Index("idx_api_usage_created_at", "created_at"),
        Index("idx_api_usage_provider_model", "provider", "model"),
    )


class TaskUsage(Base):
    __tablename__ = "task_usage"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"))
    task_id = Column(String(64), nullable=True)
    tool_name = Column(String(64), nullable=False)
    duration_ms = Column(Integer)
    status = Column(String(32))
    input_size = Column(Integer, default=0)
    output_size = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    __table_args__ = (
        Index("idx_task_usage_user_id", "user_id"),
        Index("idx_task_usage_task_id", "task_id"),
        Index("idx_task_usage_tool_name", "tool_name"),
        Index("idx_task_usage_created_at", "created_at"),
    )
