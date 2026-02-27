"""Browser manager for multi-tab management."""

import asyncio
import uuid
from typing import Any


class BrowserTab:
    """Represents a browser tab."""

    def __init__(self, tab_id: str, page: Any):
        self.id = tab_id
        self.page = page
        self.url = ""
        self.title = ""
        self.created_at = asyncio.get_event_loop().time()


class BrowserManager:
    """Manage multiple browser tabs."""

    def __init__(self):
        self.tabs: dict[str, BrowserTab] = {}
        self.active_tab_id: str | None = None
        self._playwright = None
        self._browser = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self):
        """Ensure browser is initialized."""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=True)
            except ImportError:
                raise ImportError("Playwright is not installed")

    async def create_tab(self, url: str = "about:blank") -> str:
        """Create a new browser tab."""
        async with self._lock:
            await self._ensure_browser()

            page = await self._browser.new_page()
            if url != "about:blank":
                await page.goto(url)

            tab_id = f"tab_{uuid.uuid4().hex[:8]}"
            tab = BrowserTab(tab_id, page)
            self.tabs[tab_id] = tab
            self.active_tab_id = tab_id

            self._update_tab_info(tab)
            return tab_id

    async def switch_tab(self, tab_id: str) -> bool:
        """Switch to a different tab."""
        async with self._lock:
            if tab_id not in self.tabs:
                return False
            self.active_tab_id = tab_id
            return True

    async def close_tab(self, tab_id: str) -> bool:
        """Close a browser tab."""
        async with self._lock:
            if tab_id not in self.tabs:
                return False

            tab = self.tabs[tab_id]
            await tab.page.close()
            del self.tabs[tab_id]

            if self.active_tab_id == tab_id:
                self.active_tab_id = next(iter(self.tabs.keys())) if self.tabs else None

            return True

    async def get_tabs(self) -> list[dict[str, Any]]:
        """Get list of all tabs."""
        result = []
        for tab_id, tab in self.tabs.items():
            self._update_tab_info(tab)
            result.append({
                "id": tab_id,
                "url": tab.url,
                "title": tab.title,
                "is_active": tab_id == self.active_tab_id,
            })
        return result

    async def get_active_tab(self) -> str | None:
        """Get active tab ID."""
        return self.active_tab_id

    async def take_screenshot(self, tab_id: str | None = None, full_page: bool = False) -> bytes:
        """Take a screenshot of a tab."""
        target_id = tab_id or self.active_tab_id
        if target_id is None or target_id not in self.tabs:
            raise ValueError("No active tab")

        tab = self.tabs[target_id]
        return await tab.page.screenshot(full_page=full_page)

    async def record_video(self, tab_id: str | None = None, duration: int = 10) -> bytes:
        """Record a video of a tab (simplified - captures screenshots)."""
        target_id = tab_id or self.active_tab_id
        if target_id is None or target_id not in self.tabs:
            raise ValueError("No active tab")

        tab = self.tabs[target_id]
        frames = []
        interval = 0.1
        steps = int(duration / interval)

        for _ in range(steps):
            frame = await tab.page.screenshot()
            frames.append(frame)
            await asyncio.sleep(interval)

        return b"".join(frames)

    def _update_tab_info(self, tab: BrowserTab):
        """Update tab URL and title."""
        try:
            tab.url = tab.page.url
            tab.title = tab.page.title()
        except Exception:
            pass

    async def close(self):
        """Close all tabs and browser."""
        async with self._lock:
            for tab in self.tabs.values():
                await tab.page.close()
            self.tabs.clear()

            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()


_manager_instance: BrowserManager | None = None


def get_browser_manager() -> BrowserManager:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = BrowserManager()
    return _manager_instance
