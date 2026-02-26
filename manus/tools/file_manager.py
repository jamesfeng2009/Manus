"""File management tool for reading and writing files."""

from pathlib import Path
from typing import Any

from manus.tools.base import Tool, ToolResult, ToolStatus


class ReadFileTool(Tool):
    """Read file contents."""

    def __init__(self, base_path: str | None = None):
        super().__init__(
            name="read_file",
            description="Read the contents of a file from the filesystem.",
            parameters={
                "path": {
                    "schema": {"type": "string", "description": "Path to the file to read"},
                    "required": True,
                },
                "offset": {
                    "schema": {"type": "integer", "description": "Line offset to start reading from"},
                    "required": False,
                },
                "limit": {
                    "schema": {"type": "integer", "description": "Number of lines to read"},
                    "required": False,
                },
            },
        )
        self.base_path = Path(base_path) if base_path else None

    async def execute(self, path: str, offset: int = 0, limit: int | None = None, **kwargs) -> ToolResult:
        """Read file."""
        try:
            file_path = Path(path)
            if self.base_path and not file_path.is_absolute():
                file_path = self.base_path / file_path

            if not file_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"File not found: {file_path}",
                )

            if not file_path.is_file():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"Not a file: {file_path}",
                )

            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            if offset > 0:
                lines = lines[offset:]

            if limit:
                lines = lines[:limit]

            display_content = "\n".join(lines)

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=display_content,
                metadata={
                    "path": str(file_path),
                    "total_lines": len(content.split("\n")),
                    "read_lines": len(lines),
                },
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )


class WriteFileTool(Tool):
    """Write content to file."""

    def __init__(self, base_path: str | None = None):
        super().__init__(
            name="write_file",
            description="Write content to a file. Creates the file if it doesn't exist.",
            parameters={
                "path": {
                    "schema": {"type": "string", "description": "Path to the file to write"},
                    "required": True,
                },
                "content": {
                    "schema": {"type": "string", "description": "Content to write to the file"},
                    "required": True,
                },
                "append": {
                    "schema": {"type": "boolean", "description": "Append to existing file instead of overwriting"},
                    "required": False,
                },
            },
        )
        self.base_path = Path(base_path) if base_path else None

    async def execute(self, path: str, content: str, append: bool = False, **kwargs) -> ToolResult:
        """Write file."""
        try:
            file_path = Path(path)
            if self.base_path and not file_path.is_absolute():
                file_path = self.base_path / file_path

            file_path.parent.mkdir(parents=True, exist_ok=True)

            mode = "a" if append else "w"
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(content)

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=f"Successfully wrote {len(content)} characters to {file_path}",
                metadata={
                    "path": str(file_path),
                    "bytes_written": len(content.encode("utf-8")),
                    "append": append,
                },
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )


class ListDirectoryTool(Tool):
    """List directory contents."""

    def __init__(self, base_path: str | None = None):
        super().__init__(
            name="list_directory",
            description="List files and directories in a given path.",
            parameters={
                "path": {
                    "schema": {"type": "string", "description": "Path to the directory to list"},
                    "required": False,
                },
            },
        )
        self.base_path = Path(base_path) if base_path else None

    async def execute(self, path: str = ".", **kwargs) -> ToolResult:
        """List directory."""
        try:
            dir_path = Path(path)
            if self.base_path and not dir_path.is_absolute():
                dir_path = self.base_path / dir_path

            if not dir_path.exists():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"Directory not found: {dir_path}",
                )

            if not dir_path.is_dir():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"Not a directory: {dir_path}",
                )

            items = []
            for item in sorted(dir_path.iterdir()):
                items.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })

            content = f"Contents of {dir_path}:\n"
            for item in items:
                suffix = "/" if item["type"] == "dir" else f" ({item['size']} bytes)"
                content += f"  {item['name']}{suffix}\n"

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=content,
                metadata={"path": str(dir_path), "item_count": len(items)},
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )
