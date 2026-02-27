"""Obsidian tool for Obsidian vault integration."""

import os
from pathlib import Path
from typing import Any

from manus.tools.base import Tool, ToolResult, ToolStatus


class ObsidianTool(Tool):
    """Obsidian vault operations."""

    name = "obsidian"
    description = "Read, write, search Obsidian notes"

    parameters = {
        "action": "Operation: read, write, delete, search, list",
        "vault": "Vault name",
        "path": "Note path (without extension)",
        "content": "Note content (Markdown)",
        "query": "Search query",
    }

    def __init__(
        self,
        vault_path: str | None = None,
        mode: str = "local",
        rest_api_url: str | None = None,
    ):
        self.vault_path = vault_path
        self.mode = mode
        self.rest_api_url = rest_api_url

        if not self.vault_path:
            from os import getenv

            self.vault_path = getenv("OBSIDIAN_VAULT_PATH")

    async def execute(
        self,
        action: str,
        vault: str | None = None,
        path: str | None = None,
        content: str | None = None,
        query: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        if not self.vault_path and self.mode == "local":
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Vault path not configured. Set OBSIDIAN_VAULT_PATH or vault_path.",
            )

        if self.mode == "rest_api":
            return await self._execute_rest_api(action, vault, path, content, query)
        else:
            return await self._execute_local(action, vault, path, content, query)

    async def _execute_local(
        self,
        action: str,
        vault: str | None,
        path: str | None,
        content: str | None,
        query: str | None,
    ) -> ToolResult:
        try:
            vault_path = Path(self.vault_path)

            if not vault_path.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Vault path does not exist: {self.vault_path}",
                )

            if action == "read":
                if not path:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="path is required for read action",
                    )

                note_path = vault_path / f"{path}.md"
                if not note_path.exists():
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error=f"Note not found: {path}.md",
                    )

                with open(note_path, "r", encoding="utf-8") as f:
                    note_content = f.read()

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"path": path, "content": note_content},
                )

            elif action == "write":
                if not path or content is None:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="path and content are required for write action",
                    )

                note_path = vault_path / f"{path}.md"
                note_path.parent.mkdir(parents=True, exist_ok=True)

                with open(note_path, "w", encoding="utf-8") as f:
                    f.write(content)

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"path": path, "written": True},
                )

            elif action == "delete":
                if not path:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="path is required for delete action",
                    )

                note_path = vault_path / f"{path}.md"
                if not note_path.exists():
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error=f"Note not found: {path}.md",
                    )

                note_path.unlink()

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"path": path, "deleted": True},
                )

            elif action == "list":
                notes = []
                for md_file in vault_path.rglob("*.md"):
                    relative_path = md_file.relative_to(vault_path)
                    notes.append(str(relative_path.with_suffix("")))

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"notes": notes, "count": len(notes)},
                )

            elif action == "search":
                if not query:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error="query is required for search action",
                    )

                results = []
                query_lower = query.lower()

                for md_file in vault_path.rglob("*.md"):
                    try:
                        with open(md_file, "r", encoding="utf-8") as f:
                            content = f.read()
                            if query_lower in content.lower():
                                relative_path = md_file.relative_to(vault_path)
                                results.append(str(relative_path.with_suffix("")))
                    except Exception:
                        continue

                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    data={"results": results, "count": len(results)},
                )

            else:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Action {action} not supported",
                )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Obsidian operation failed: {str(e)}",
            )

    async def _execute_rest_api(
        self,
        action: str,
        vault: str | None,
        path: str | None,
        content: str | None,
        query: str | None,
    ) -> ToolResult:
        try:
            import httpx

            base_url = self.rest_api_url or "http://localhost:8080"

            async with httpx.AsyncClient() as client:
                if action == "read":
                    if not path:
                        return ToolResult(
                            status=ToolStatus.ERROR,
                            error="path is required",
                        )

                    response = await client.get(f"{base_url}/notes/{vault}/{path}")
                    response.raise_for_status()

                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data=response.json(),
                    )

                elif action == "write":
                    if not path or not content:
                        return ToolResult(
                            status=ToolStatus.ERROR,
                            error="path and content are required",
                        )

                    response = await client.post(
                        f"{base_url}/notes/{vault}/{path}",
                        json={"content": content},
                    )
                    response.raise_for_status()

                    return ToolResult(
                        status=ToolStatus.SUCCESS,
                        data={"written": True},
                    )

                else:
                    return ToolResult(
                        status=ToolStatus.ERROR,
                        error=f"Action {action} not supported in REST API mode",
                    )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Obsidian REST API error: {str(e)}",
            )
