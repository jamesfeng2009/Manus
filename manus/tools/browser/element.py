"""Smart element matching for browser automation."""

from typing import Any


class ElementMatcher:
    """Smart element matching using multiple strategies."""

    def __init__(self, page: Any):
        self.page = page

    async def find_element(
        self,
        selector: str,
        by: str = "auto",
        timeout: int = 10,
    ):
        """Find element using specified strategy."""
        strategies = {
            "auto": self._find_auto,
            "css": self._find_css,
            "xpath": self._find_xpath,
            "text": self._find_by_text,
            "semantic": self._find_semantic,
        }

        finder = strategies.get(by, self._find_css)
        return await finder(selector, timeout)

    async def _find_auto(self, selector: str, timeout: int):
        """Auto-detect selector type."""
        if selector.startswith("//"):
            return await self._find_xpath(selector, timeout)
        elif selector.startswith("#") or selector.startswith("."):
            return await self._find_css(selector, timeout)
        else:
            return await self._find_by_text(selector, timeout)

    async def _find_css(self, selector: str, timeout: int):
        """Find element by CSS selector."""
        return await self.page.wait_for_selector(selector, timeout=timeout)

    async def _find_xpath(self, selector: str, timeout: int):
        """Find element by XPath."""
        return await self.page.wait_for_selector(f"xpath={selector}", timeout=timeout)

    async def _find_by_text(self, text: str, timeout: int):
        """Find element by text content."""
        selector = f"text={text}"
        return await self.page.wait_for_selector(selector, timeout=timeout)

    async def _find_semantic(self, semantic: str, timeout: int):
        """Find element by semantic description."""
        semantic_map = {
            "search_input": [
                "input[type='search']",
                "input[placeholder*='搜索']",
                "input[placeholder*='search']",
                "#search",
            ],
            "login_button": [
                "button:has-text('登录')",
                "button:has-text('Login')",
                "button:has-text('Sign in')",
                "[role='button'].primary",
            ],
            "submit_button": [
                "button[type='submit']",
                "button:has-text('提交')",
                "button:has-text('Submit')",
            ],
            "close_button": [
                "button[aria-label='关闭']",
                "button[aria-label='Close']",
                ".close",
                "[role='button'].close",
            ],
        }

        selectors = semantic_map.get(semantic, [semantic])
        for sel in selectors:
            try:
                element = await self.page.wait_for_selector(sel, timeout=timeout)
                if element:
                    return element
            except Exception:
                continue
        raise ValueError(f"Could not find element: {semantic}")

    async def click(self, selector: str, by: str = "auto") -> bool:
        """Click an element."""
        element = await self.find_element(selector, by)
        if element:
            await element.click()
            return True
        return False

    async def input_text(
        self,
        selector: str,
        text: str,
        by: str = "auto",
        clear: bool = True,
    ) -> bool:
        """Input text into an element."""
        element = await self.find_element(selector, by)
        if element:
            if clear:
                await element.clear()
            await element.fill(text)
            return True
        return False

    async def wait_for_element(
        self,
        selector: str,
        by: str = "auto",
        timeout: int = 10,
        state: str = "visible",
    ) -> bool:
        """Wait for element to reach a specific state."""
        strategies = {
            "css": lambda: self.page.wait_for_selector(selector, timeout=timeout, state=state),
            "xpath": lambda: self.page.wait_for_selector(f"xpath={selector}", timeout=timeout, state=state),
        }

        finder = strategies.get(by, strategies["css"])
        try:
            await finder()
            return True
        except Exception:
            return False

    async def get_element_info(self, selector: str, by: str = "auto") -> dict[str, Any]:
        """Get element information."""
        element = await self.find_element(selector, by)
        if not element:
            return {}

        try:
            return await element.evaluate("""el => ({
                tag: el.tagName,
                text: el.textContent,
                href: el.href,
                src: el.src,
                id: el.id,
                class: el.className,
                attributes: Array.from(el.attributes).reduce((acc, attr) => {
                    acc[attr.name] = attr.value;
                    return acc;
                }, {})
            })""")
        except Exception:
            return {}
