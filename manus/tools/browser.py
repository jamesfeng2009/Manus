"""Browser tool for web automation."""

import asyncio
from typing import Any

from manus.tools.base import Tool, ToolResult, ToolStatus


class BrowserTool(Tool):
    """Browser automation tool using Playwright."""

    def __init__(self, timeout: int = 30):
        super().__init__(
            name="browser",
            description="Control a browser to navigate to URLs, take screenshots, and extract content from web pages.",
            parameters={
                "action": {
                    "schema": {"type": "string", "enum": ["goto", "screenshot", "extract", "click", "type"]},
                    "required": True,
                },
                "url": {
                    "schema": {"type": "string", "description": "URL to navigate to"},
                    "required": False,
                },
                "selector": {
                    "schema": {"type": "string", "description": "CSS selector for element"},
                    "required": False,
                },
                "text": {
                    "schema": {"type": "string", "description": "Text to type"},
                    "required": False,
                },
            },
        )
        self.timeout = timeout
        self._page = None

    async def _get_page(self):
        """Get or create browser page."""
        if self._page is None:
            try:
                from playwright.async_api import async_playwright
                playwright = await async_playwright().start()
                browser = await playwright.chromium.launch(headless=True)
                self._page = await browser.new_page()
            except ImportError:
                raise ImportError("Playwright is not installed. Run: pip install playwright && playwright install chromium")
        return self._page

    async def execute(self, action: str, **kwargs) -> ToolResult:
        """Execute browser action."""
        try:
            page = await self._get_page()

            if action == "goto":
                url = kwargs.get("url")
                if not url:
                    return ToolResult(
                        tool_name=self.name,
                        status=ToolStatus.FAILED,
                        error="URL is required for goto action",
                    )
                await page.goto(url, timeout=self.timeout * 1000)
                title = await page.title()
                content = f"Navigated to {url}\nTitle: {title}"
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.SUCCESS,
                    content=content,
                    metadata={"url": url, "title": title},
                )

            elif action == "screenshot":
                if not self._page:
                    return ToolResult(
                        tool_name=self.name,
                        status=ToolStatus.FAILED,
                        error="No page available. Use goto first.",
                    )
                screenshot_bytes = await self._page.screenshot()
                import base64
                b64 = base64.b64encode(screenshot_bytes).decode()
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.SUCCESS,
                    content=f"Screenshot taken (base64 length: {len(b64)})",
                    metadata={"screenshot": b64[:100] + "..."},
                )

            elif action == "extract":
                if not self._page:
                    return ToolResult(
                        tool_name=self.name,
                        status=ToolStatus.FAILED,
                        error="No page available. Use goto first.",
                    )
                content = await page.content()
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.SUCCESS,
                    content=content[:5000],
                    metadata={"length": len(content)},
                )

            elif action == "click":
                selector = kwargs.get("selector")
                if not selector:
                    return ToolResult(
                        tool_name=self.name,
                        status=ToolStatus.FAILED,
                        error="Selector is required for click action",
                    )
                await page.click(selector, timeout=self.timeout * 1000)
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.SUCCESS,
                    content=f"Clicked element: {selector}",
                )

            elif action == "type":
                selector = kwargs.get("selector")
                text = kwargs.get("text")
                if not selector or not text:
                    return ToolResult(
                        tool_name=self.name,
                        status=ToolStatus.FAILED,
                        error="Selector and text are required for type action",
                    )
                await page.fill(selector, text)
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.SUCCESS,
                    content=f"Typed text into: {selector}",
                )

            else:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"Unknown action: {action}",
                )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )

    async def close(self):
        """Close browser."""
        if self._page:
            await self._page.context.browser.close()
            self._page = None
