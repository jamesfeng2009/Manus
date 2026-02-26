"""Vision tool for image analysis."""

import base64
from pathlib import Path

from manus.tools.base import Tool, ToolResult, ToolStatus


class VisionTool(Tool):
    """Analyze images using vision models."""

    def __init__(self):
        super().__init__(
            name="analyze_image",
            description="Analyze an image and describe its contents. Use this to understand images, screenshots, diagrams, or photos.",
            parameters={
                "image_path": {
                    "schema": {"type": "string", "description": "Path to the image file"},
                    "required": True,
                },
                "question": {
                    "schema": {"type": "string", "description": "Specific question about the image"},
                    "required": False,
                },
            },
        )

    async def execute(self, image_path: str, question: str | None = None, **kwargs) -> ToolResult:
        """Execute image analysis."""
        try:
            p = Path(image_path)
            if not p.exists():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"Image not found: {image_path}",
                )

            image_data = base64.b64encode(p.read_bytes()).decode("utf-8")

            prompt = question or "Describe this image in detail."

            from manus.models import get_adapter
            adapter = get_adapter("gpt-4o")

            from manus.core.types import Message, MessageRole
            messages = [
                Message(
                    role=MessageRole.USER,
                    content=[
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}",
                                "detail": "high",
                            },
                        },
                    ],
                )
            ]

            try:
                response = await adapter.chat(messages=messages, max_tokens=1024)
                content = response.get("content", "No analysis available")
            except Exception as e:
                content = f"Note: Vision analysis requires a vision-capable model. Error: {str(e)}"

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=content,
                metadata={"image_path": str(p), "question": question},
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )
