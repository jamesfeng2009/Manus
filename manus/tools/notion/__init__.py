"""Notion tool for Notion integration."""

from typing import Any

from manus.tools.base import Tool, ToolResult, ToolStatus


class NotionTool(Tool):
    """Notion integration for pages and databases."""

    name = "notion"
    description = "Create and manage Notion pages and databases"

    parameters = {
        "action": "Operation: create_page, update_page, query_database, create_database, search",
        "page_id": "Page ID (required for update_page)",
        "database_id": "Database ID (required for query_database, create_database)",
        "title": "Page title",
        "content": "Page content (Markdown)",
        "properties": "Database properties (JSON)",
        "query": "Search query",
    }

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        if not self.api_key:
            from os import getenv

            self.api_key = getenv("NOTION_API_KEY")

        if not self.api_key:
            raise RuntimeError("Notion API key not configured")

        try:
            from notion_client import Client

            self._client = Client(auth=self.api_key)
            return self._client

        except ImportError:
            raise RuntimeError("notion-client not installed. Run: pip install notion-client")

    async def execute(
        self,
        action: str,
        page_id: str | None = None,
        database_id: str | None = None,
        title: str | None = None,
        content: str | None = None,
        properties: dict | None = None,
        query: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            client = self._get_client()

            if action == "create_page":
                if not title:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="title is required",
                    )

                parent = {"database_id": database_id} if database_id else {"page_id": page_id}

                blocks = self._markdown_to_blocks(content) if content else []

                result = client.pages.create(
                    parent=parent,
                    properties={"title": {"title": [{"text": {"content": title}}]}},
                    children=blocks,
                )

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"page_id": result.get("id"), "created": True},
                )

            elif action == "update_page":
                if not page_id:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="page_id is required",
                    )

                properties = properties or {}
                if title:
                    properties["title"] = {"title": [{"text": {"content": title}}]}

                client.pages.update(page_id=page_id, properties=properties)

                if content:
                    blocks = self._markdown_to_blocks(content)
                    client.blocks.children.append(block_id=page_id, children=blocks)

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"page_id": page_id, "updated": True},
                )

            elif action == "query_database":
                if not database_id:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="database_id is required",
                    )

                result = client.databases.query(database_id=database_id)

                pages = [
                    {"id": p.get("id"), "properties": p.get("properties")}
                    for p in result.get("results", [])
                ]

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"pages": pages, "count": len(pages)},
                )

            elif action == "create_database":
                if not database_id or not title:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="database_id and title are required",
                    )

                result = client.databases.create(
                    parent={"page_id": page_id},
                    title=[{"text": {"content": title}}],
                    properties=properties
                    or {
                        "Name": {"title": {}},
                        "Tags": {"multi_select": {"options": []}},
                    },
                )

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"database_id": result.get("id"), "created": True},
                )

            elif action == "search":
                result = client.search(query=query, filter={"value": "page", "property": "object"})

                pages = [
                    {"id": p.get("id"), "title": self._get_title(p)}
                    for p in result.get("results", [])
                ]

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"results": pages, "count": len(pages)},
                )

            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Action {action} not supported",
                )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Notion operation failed: {str(e)}",
            )

    def _markdown_to_blocks(self, markdown: str) -> list[dict]:
        blocks = []
        lines = markdown.split("\n")

        for line in lines:
            if line.strip():
                blocks.append(
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": line}}]
                        },
                    }
                )

        return blocks

    def _get_title(self, page: dict) -> str:
        props = page.get("properties", {})
        for key, val in props.items():
            if val.get("type") == "title":
                title_list = val.get("title", [])
                if title_list:
                    return title_list[0].get("text", {}).get("content", "")
        return "Untitled"
