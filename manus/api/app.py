"""LiteStar API application for Manus."""

from datetime import datetime
from typing import Any

from litestar import Litestar, get, post, put, delete
from litestar.controller import Controller
from litestar.params import Parameter
from litestar.exceptions import HTTPException
from pydantic import BaseModel

from manus.agents import SimpleAgentTeam
from manus.config import get_config
from manus.tasks import TaskManager, TaskStatus, get_task_manager
from manus.websocket.handler import SSEController, WebSocketController, DiscordWebSocketController
from manus.auth.routes import AuthController, APIKeyController
from manus.auth.oauth import OAuthController


class TaskCreate(BaseModel):
    """Create task request."""
    user_input: str
    user_id: str | None = None
    model_id: str | None = None


class TaskUpdate(BaseModel):
    """Update task request."""
    status: str | None = None
    result: dict[str, Any] | None = None


class TaskResponse(BaseModel):
    """Task response."""
    task_id: str
    user_input: str
    status: str
    created_at: str
    updated_at: str


class ExecuteRequest(BaseModel):
    """Execute task request."""
    user_input: str
    user_id: str | None = None
    model_id: str | None = None


class ExecuteResponse(BaseModel):
    """Execute response."""
    task_id: str
    status: str
    result: dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str


class TaskController(Controller):
    """Task management endpoints."""

    path = "/tasks"

    @post("")
    async def create_task(
        self,
        data: TaskCreate,
        task_manager: TaskManager = get_task_manager,
    ) -> TaskResponse:
        """Create a new task."""
        task = task_manager.create_task(
            user_input=data.user_input,
            user_id=data.user_id,
            model_id=data.model_id,
        )
        return TaskResponse(
            task_id=task.task_id,
            user_input=task.user_input,
            status=task.status.value,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
        )

    @get("")
    async def list_tasks(
        self,
        user_id: str | None = Parameter(default=None),
        status: str | None = Parameter(default=None),
        limit: int = Parameter(default=50),
        task_manager: TaskManager = get_task_manager,
    ) -> list[TaskResponse]:
        """List tasks."""
        task_status = TaskStatus(status) if status else None
        tasks = task_manager.list_tasks(user_id=user_id, status=task_status, limit=limit)
        return [
            TaskResponse(
                task_id=t.task_id,
                user_input=t.user_input,
                status=t.status.value,
                created_at=t.created_at.isoformat(),
                updated_at=t.updated_at.isoformat(),
            )
            for t in tasks
        ]

    @get("/{task_id:str}")
    async def get_task(
        self,
        task_id: str,
        task_manager: TaskManager = get_task_manager,
    ) -> TaskResponse | None:
        """Get task by ID."""
        task = task_manager.get_task(task_id)
        if not task:
            return None
        return TaskResponse(
            task_id=task.task_id,
            user_input=task.user_input,
            status=task.status.value,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
        )

    @put("/{task_id:str}")
    async def update_task(
        self,
        task_id: str,
        data: TaskUpdate,
        task_manager: TaskManager = get_task_manager,
    ) -> TaskResponse | None:
        """Update task."""
        update_data = {}
        if data.status:
            update_data["status"] = data.status
        if data.result:
            update_data["result"] = data.result

        task = task_manager.update_task(task_id, **update_data)
        if not task:
            return None
        return TaskResponse(
            task_id=task.task_id,
            user_input=task.user_input,
            status=task.status.value,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
        )

    @delete("/{task_id:str}", status_code=200)
    async def delete_task(
        self,
        task_id: str,
        task_manager: TaskManager = get_task_manager,
    ) -> dict[str, str]:
        """Delete task."""
        success = task_manager.delete_task(task_id)
        return {"success": str(success)}

    @post("/{task_id:str}/cancel", status_code=200)
    async def cancel_task(
        self,
        task_id: str,
        task_manager: TaskManager = get_task_manager,
    ) -> dict[str, str]:
        """Cancel a running task."""
        success = task_manager.cancel_task(task_id)
        return {"success": str(success)}

    @post("/{task_id:str}/dependencies")
    async def add_dependency(
        self,
        task_id: str,
        depends_on: str = Parameter(default=None),
        task_manager: TaskManager = get_task_manager,
    ) -> dict[str, str]:
        """Add task dependency."""
        success = task_manager.add_dependency(task_id, depends_on)
        return {"success": str(success)}

    @get("/{task_id:str}/dependencies")
    async def get_dependencies(
        self,
        task_id: str,
        task_manager: TaskManager = get_task_manager,
    ) -> dict[str, list[str]]:
        """Get task dependencies."""
        deps = task_manager.get_dependencies(task_id)
        return {"dependencies": deps}


class ExecuteController(Controller):
    """Task execution endpoints."""

    path = "/execute"

    @post("")
    async def execute_task(
        self,
        data: ExecuteRequest,
        task_manager: TaskManager = get_task_manager,
    ) -> ExecuteResponse:
        """Execute a task using the agent team."""
        task = task_manager.create_task(
            user_input=data.user_input,
            user_id=data.user_id,
            model_id=data.model_id,
        )

        task_manager.update_task(task.task_id, status="running")

        team = SimpleAgentTeam()

        try:
            result = await team.execute(task.task_id, data.user_input)

            task_manager.update_task(
                task.task_id,
                status="completed" if result.status.value == "completed" else "failed",
                result=result.final_response,
            )

            return ExecuteResponse(
                task_id=task.task_id,
                status=result.status.value,
                result={"response": result.final_response, "duration": result.duration},
            )

        except Exception as e:
            task_manager.update_task(task.task_id, status="failed", error=str(e))
            return ExecuteResponse(
                task_id=task.task_id,
                status="failed",
                result={"error": str(e)},
            )


class ModelController(Controller):
    """Model configuration endpoints."""

    path = "/models"

    @get("")
    async def list_models(self) -> dict[str, Any]:
        """List available models."""
        from manus.models import get_model_factory

        factory = get_model_factory()
        config = get_config()

        return {
            "default_model": config.defaults.default_model,
            "available_models": factory.list_available_models(),
            "providers": [
                {
                    "name": p.provider,
                    "models": [m.id for m in p.models],
                }
                for p in config.models
            ],
        }


class HealthController(Controller):
    """Health check endpoints."""

    path = "/health"

    @get("")
    async def health_check(self) -> HealthResponse:
        """Health check."""
        return HealthResponse(
            status="healthy",
            version="0.1.0",
            timestamp=datetime.now().isoformat(),
        )


class ImageController(Controller):
    """Image generation endpoints."""

    path = "/images"

    @post("/generate")
    async def generate_image(
        self,
        prompt: str = Parameter(default=None),
        provider: str = Parameter(default="dalle"),
        size: str = Parameter(default="1024x1024"),
        quality: str = Parameter(default="standard"),
        style: str = Parameter(default="natural"),
    ) -> dict[str, Any]:
        """Generate an image."""
        from manus.models.adapters.image import ImageGenFactory

        try:
            adapter = ImageGenFactory.create(provider)
            result = await adapter.generate(
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
            )
            return {
                "image_url": result.image_url,
                "provider": result.provider,
                "model": result.model,
                "revised_prompt": result.revised_prompt,
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


app = Litestar(
    route_handlers=[
        TaskController,
        ExecuteController,
        ModelController,
        HealthController,
        ImageController,
        SSEController,
        WebSocketController,
        DiscordWebSocketController,
        AuthController,
        APIKeyController,
        OAuthController,
    ],
)
