"""Plan Execute WebSocket integration."""

from typing import Any

from manus.websocket.events import EventType, WSMessage
from manus.websocket.manager import WSManager


class PlanExecuteWebSocketHandler:
    """Handle Plan->Execute WebSocket events."""
    
    def __init__(self, ws_manager: WSManager | None = None):
        self.ws_manager = ws_manager
    
    def _get_ws_manager(self) -> WSManager:
        if self.ws_manager is None:
            from manus.websocket.manager import get_ws_manager
            return get_ws_manager()
        return self.ws_manager
    
    async def emit_plan_created(self, task_id: str, user_id: str, plan: dict):
        """Emit plan created event."""
        ws_manager = self._get_ws_manager()
        message = WSMessage(
            event=EventType("plan_execute.plan_created"),
            data={"plan": plan},
            task_id=task_id,
            user_id=user_id,
        )
        await ws_manager.send_to_user(user_id, message.to_json())
    
    async def emit_plan_started(self, task_id: str, user_id: str):
        """Emit plan started event."""
        ws_manager = self._get_ws_manager()
        message = WSMessage(
            event=EventType("plan_execute.plan_started"),
            data={},
            task_id=task_id,
            user_id=user_id,
        )
        await ws_manager.send_to_user(user_id, message.to_json())
    
    async def emit_step_start(
        self, 
        task_id: str, 
        user_id: str, 
        step_data: dict[str, Any]
    ):
        """Emit step started event."""
        ws_manager = self._get_ws_manager()
        message = WSMessage(
            event=EventType("plan_execute.step_start"),
            data=step_data,
            task_id=task_id,
            user_id=user_id,
        )
        await ws_manager.send_to_user(user_id, message.to_json())
    
    async def emit_step_complete(
        self,
        task_id: str,
        user_id: str,
        step_data: dict[str, Any],
    ):
        """Emit step completed event."""
        ws_manager = self._get_ws_manager()
        message = WSMessage(
            event=EventType("plan_execute.step_complete"),
            data=step_data,
            task_id=task_id,
            user_id=user_id,
        )
        await ws_manager.send_to_user(user_id, message.to_json())
    
    async def emit_step_error(
        self,
        task_id: str,
        user_id: str,
        step_data: dict[str, Any],
        error: str,
    ):
        """Emit step error event."""
        ws_manager = self._get_ws_manager()
        message = WSMessage(
            event=EventType("plan_execute.step_error"),
            data={**step_data, "error": error},
            task_id=task_id,
            user_id=user_id,
        )
        await ws_manager.send_to_user(user_id, message.to_json())
    
    async def emit_iteration(
        self,
        task_id: str,
        user_id: str,
        current: int,
        total: int,
    ):
        """Emit iteration event."""
        ws_manager = self._get_ws_manager()
        message = WSMessage(
            event=EventType("plan_execute.iteration"),
            data={"current": current, "total": total},
            task_id=task_id,
            user_id=user_id,
        )
        await ws_manager.send_to_user(user_id, message.to_json())
    
    async def emit_progress(
        self,
        task_id: str,
        user_id: str,
        progress: float,
    ):
        """Emit progress event."""
        ws_manager = self._get_ws_manager()
        message = WSMessage(
            event=EventType("plan_execute.progress"),
            data={"progress": progress},
            task_id=task_id,
            user_id=user_id,
        )
        await ws_manager.send_to_user(user_id, message.to_json())
    
    async def emit_verification(
        self,
        task_id: str,
        user_id: str,
        verification: dict[str, Any],
    ):
        """Emit verification event."""
        ws_manager = self._get_ws_manager()
        message = WSMessage(
            event=EventType("plan_execute.verification"),
            data=verification,
            task_id=task_id,
            user_id=user_id,
        )
        await ws_manager.send_to_user(user_id, message.to_json())
    
    async def emit_plan_complete(
        self,
        task_id: str,
        user_id: str,
        result: dict[str, Any],
    ):
        """Emit plan completed event."""
        ws_manager = self._get_ws_manager()
        message = WSMessage(
            event=EventType("plan_execute.plan_complete"),
            data=result,
            task_id=task_id,
            user_id=user_id,
        )
        await ws_manager.send_to_user(user_id, message.to_json())
    
    async def emit_plan_error(
        self,
        task_id: str,
        user_id: str,
        error: str,
    ):
        """Emit plan error event."""
        ws_manager = self._get_ws_manager()
        message = WSMessage(
            event=EventType("plan_execute.plan_error"),
            data={"error": error},
            task_id=task_id,
            user_id=user_id,
        )
        await ws_manager.send_to_user(user_id, message.to_json())
    
    async def emit_token(
        self,
        task_id: str,
        user_id: str,
        token: str,
    ):
        """Emit token event for streaming."""
        ws_manager = self._get_ws_manager()
        message = WSMessage(
            event=EventType.AGENT_TOKEN,
            data={"token": token},
            task_id=task_id,
            user_id=user_id,
        )
        await ws_manager.send_to_user(user_id, message.to_json())


_plan_execute_ws_handler: PlanExecuteWebSocketHandler | None = None


def get_plan_execute_ws_handler() -> PlanExecuteWebSocketHandler:
    """Get global PlanExecuteWebSocketHandler instance."""
    global _plan_execute_ws_handler
    if _plan_execute_ws_handler is None:
        _plan_execute_ws_handler = PlanExecuteWebSocketHandler()
    return _plan_execute_ws_handler


__all__ = [
    "PlanExecuteWebSocketHandler",
    "get_plan_execute_ws_handler",
]
