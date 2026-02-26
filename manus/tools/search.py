"""Search tool for web and codebase search."""

import httpx
from typing import Any

from manus.tools.base import Tool, ToolResult, ToolStatus


class SearchTool(Tool):
    """Web and codebase search tool."""

    def __init__(self, timeout: int = 30):
        super().__init__(
            name="search",
            description="Search the web for information. Use this when you need to find current information or verify facts.",
            parameters={
                "query": {
                    "schema": {"type": "string", "description": "Search query"},
                    "required": True,
                },
                "max_results": {
                    "schema": {"type": "integer", "description": "Maximum number of results", "default": 5},
                    "required": False,
                },
            },
        )
        self.timeout = timeout

    async def execute(self, query: str, max_results: int = 5, **kwargs) -> ToolResult:
        """Execute search."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": "1",
                        "skip_disambig": "1",
                    },
                )
                data = response.json()

                results = []
                for item in data.get("RelatedTopics", [])[:max_results]:
                    if "Text" in item:
                        results.append({
                            "title": item.get("Text", "").split(" - ")[0] if " - " in item.get("Text", "") else item.get("Text", "")[:50],
                            "content": item.get("Text", ""),
                            "url": item.get("FirstURL", ""),
                        })

                content = f"Search results for '{query}':\n\n"
                for i, r in enumerate(results, 1):
                    content += f"{i}. {r['title']}\n"
                    content += f"   {r['content'][:200]}...\n"
                    content += f"   URL: {r['url']}\n\n"

                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.SUCCESS,
                    content=content,
                    metadata={"query": query, "result_count": len(results)},
                )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )
