"""Browser state management for save/restore."""

import json
import uuid
from typing import Any


class BrowserState:
    """Manage browser state persistence."""

    def __init__(self, page: Any):
        self.page = page
        self._state_storage: dict[str, dict[str, Any]] = {}

    async def save_state(self, label: str | None = None) -> str:
        """Save current browser state."""
        state_id = label or f"state_{uuid.uuid4().hex[:8]}"

        state = {
            "url": self.page.url,
            "title": await self.page.title(),
            "cookies": await self.page.context.cookies(),
            "local_storage": await self.page.evaluate("() => JSON.stringify(localStorage)"),
            "session_storage": await self.page.evaluate("() => JSON.stringify(sessionStorage)"),
        }

        self._state_storage[state_id] = state
        return state_id

    async def restore_state(self, state_id: str) -> bool:
        """Restore browser state."""
        if state_id not in self._state_storage:
            return False

        state = self._state_storage[state_id]

        try:
            await self.page.goto(state["url"])

            await self.page.context.add_cookies(state["cookies"])

            local_storage = json.loads(state.get("local_storage", "{}"))
            await self.page.evaluate(f"""() => {{
                localStorage.clear();
                Object.entries({json.dumps(local_storage)}).forEach(([k, v]) => {{
                    localStorage.setItem(k, v);
                }});
            }}""")

            session_storage = json.loads(state.get("session_storage", "{}"))
            await self.page.evaluate(f"""() => {{
                sessionStorage.clear();
                Object.entries({json.dumps(session_storage)}).forEach(([k, v]) => {{
                    sessionStorage.setItem(k, v);
                }});
            }}""")

            return True
        except Exception:
            return False

    async def get_state(self) -> dict[str, Any]:
        """Get current state as dict."""
        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "cookies": len(await self.page.context.cookies()),
        }

    def list_states(self) -> list[str]:
        """List all saved state IDs."""
        return list(self._state_storage.keys())

    def delete_state(self, state_id: str) -> bool:
        """Delete a saved state."""
        if state_id in self._state_storage:
            del self._state_storage[state_id]
            return True
        return False

    async def serialize_state(self, state_id: str) -> str | None:
        """Serialize state to JSON string."""
        if state_id not in self._state_storage:
            return None
        return json.dumps(self._state_storage[state_id])

    async def deserialize_state(self, state_json: str) -> str:
        """Deserialize state from JSON string."""
        state = json.loads(state_json)
        state_id = f"state_{uuid.uuid4().hex[:8]}"
        self._state_storage[state_id] = state
        return state_id
