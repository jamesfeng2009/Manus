import asyncio
import json
import logging
from dataclasses import dataclass
from litestar import WebSocket, Controller, get, websocket
from litestar.response import ServerSentEvent
from typing import AsyncGenerator

from manus.websocket.manager import get_ws_manager
from manus.websocket.events import WSMessage, EventType
from manus.websocket.stream import sse_event_stream, task_progress_stream

logger = logging.getLogger(__name__)


@dataclass
class DiscordState:
    session_id: str | None = None
    sequence: int | None = None
    heartbeat_interval: int | None = None
    last_heartbeat_ack: float = 0


class DiscordWebSocketController(Controller):
    path = "/ws/discord"

    @websocket()
    async def discord_ws(
        self,
        socket: WebSocket,
        token: str | None = None,
    ) -> None:
        await socket.accept()

        state = DiscordState()
        ws_manager = get_ws_manager()
        conn_id = f"discord_{id(socket)}"

        ws_manager.add_connection(
            conn_id,
            user_id="discord",
            websocket=socket,
            task_id="discord",
        )

        try:
            while True:
                data = await socket.receive_json()
                await self._handle_dispatch(
                    data, socket, state, ws_manager, conn_id, token
                )
        except Exception as e:
            logger.error(f"Discord WebSocket error: {e}")
        finally:
            ws_manager.remove_connection(conn_id)

    async def _handle_dispatch(
        self,
        data: dict,
        socket: WebSocket,
        state: DiscordState,
        ws_manager,
        conn_id: str,
        bot_token: str | None,
    ):
        op = data.get("op")
        payload = data.get("d", {})

        if op == 2:
            await self._handle_identify(socket, payload, state, bot_token, ws_manager, conn_id)
        elif op == 6:
            await self._handle_heartbeat(socket, state)
        elif op == 1:
            await socket.send_json({"op": 11, "d": None})

    async def _handle_identify(
        self,
        socket: WebSocket,
        payload: dict,
        state: DiscordState,
        bot_token: str | None,
        ws_manager,
        conn_id: str,
    ):
        await socket.send_json({
            "op": 10,
            "d": {
                "heartbeat_interval": 41250,
                "_trace": ["discord-ws"],
            }
        })

        await ws_manager.send(conn_id, WSMessage(
            event=EventType.DISCORD_READY,
            data={"status": "connected"},
            user_id="discord",
        ))

        asyncio.create_task(self._heartbeat_loop(socket, state))

    async def _handle_heartbeat(self, socket: WebSocket, state: DiscordState):
        await socket.send_json({"op": 1, "d": state.sequence})

    async def _heartbeat_loop(self, socket: WebSocket, state: DiscordState):
        interval = state.heartbeat_interval or 41250
        while True:
            await asyncio.sleep(interval / 1000)
            try:
                await socket.send_json({
                    "op": 1,
                    "d": state.sequence,
                })
            except Exception:
                break


class WebSocketController(Controller):
    path = "/ws"

    @get()
    async def ws_root(
        self,
        user_id: str | None = None,
        task_id: str | None = None,
    ) -> ServerSentEvent:
        return ServerSentEvent(task_progress_stream(task_id or "global"))

    @get("/tasks")
    async def ws_tasks(
        self,
        user_id: str | None = None,
        task_id: str | None = None,
    ) -> ServerSentEvent:
        return ServerSentEvent(task_progress_stream(task_id or "global"))


class SSEController(Controller):
    path = "/sse"

    @get("/stream/{task_id:str}")
    async def stream_agent(
        self,
        task_id: str,
        user_input: str | None = None,
    ) -> ServerSentEvent:
        return ServerSentEvent(sse_event_stream(task_id, user_input))

    @get("/tasks/{task_id:str}")
    async def task_progress(
        self,
        task_id: str,
    ) -> ServerSentEvent:
        return ServerSentEvent(task_progress_stream(task_id))
