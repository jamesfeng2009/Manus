"""Tools system for Manus agents."""

from manus.tools.base import Tool, ToolResult, ToolStatus
from manus.tools.browser.tool import BrowserTool
from manus.tools.code_execution import CodeExecutionTool
from manus.tools.file_manager import ReadFileTool, WriteFileTool, ListDirectoryTool
from manus.tools.registry import ToolRegistry, get_tool_registry
from manus.tools.search import SearchTool
from manus.tools.image_generation import ImageGenerationTool
from manus.tools.email import EmailTool, GmailTool
from manus.tools.calendar import CalendarTool, OutlookCalendarTool
from manus.tools.notion import NotionTool
from manus.tools.obsidian import ObsidianTool
from manus.tools.github import GitHubTool


def _register_tools():
    registry = get_tool_registry()
    registry.register(EmailTool())
    registry.register(GmailTool())
    registry.register(CalendarTool())
    registry.register(OutlookCalendarTool())
    registry.register(NotionTool())
    registry.register(ObsidianTool())
    registry.register(GitHubTool())


_register_tools()

__all__ = [
    "Tool",
    "ToolResult",
    "ToolStatus",
    "ToolRegistry",
    "get_tool_registry",
    "SearchTool",
    "BrowserTool",
    "CodeExecutionTool",
    "ReadFileTool",
    "WriteFileTool",
    "ListDirectoryTool",
    "ImageGenerationTool",
    "EmailTool",
    "GmailTool",
    "CalendarTool",
    "OutlookCalendarTool",
    "NotionTool",
    "ObsidianTool",
    "GitHubTool",
]
