"""Screen capture and analysis tools."""

import base64
import platform
from pathlib import Path

from manus.tools.base import Tool, ToolResult, ToolStatus


class ScreenCaptureTool(Tool):
    """Screen capture tool for screenshots and analysis."""

    def __init__(self):
        super().__init__(
            name="screen",
            description="Capture screen or specific region, analyze screenshots with vision model.",
            parameters={
                "mode": {
                    "schema": {
                        "type": "string",
                        "enum": ["capture", "analyze"],
                        "description": "Mode: 'capture' (take screenshot) or 'analyze' (analyze existing image)",
                    },
                    "required": True,
                },
                "output_path": {
                    "schema": {"type": "string", "description": "Path to save screenshot"},
                    "required": False,
                },
                "region": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer"},
                            "y": {"type": "integer"},
                            "width": {"type": "integer"},
                            "height": {"type": "integer"},
                        },
                    },
                    "description": "Region to capture: {x, y, width, height}",
                    "required": False,
                },
                "image_path": {
                    "schema": {"type": "string", "description": "Path to image for analyze mode"},
                    "required": False,
                },
                "question": {
                    "schema": {"type": "string", "description": "Question for analyze mode"},
                    "required": False,
                },
            },
        )

    async def execute(
        self,
        mode: str,
        output_path: str | None = None,
        region: dict | None = None,
        image_path: str | None = None,
        question: str | None = None,
        **kwargs,
    ) -> ToolResult:
        """Execute screen capture or analysis."""
        try:
            if mode == "capture":
                return await self._capture_screen(output_path, region)
            elif mode == "analyze":
                return await self._analyze_screen(image_path, question)
            else:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"Unknown mode: {mode}",
                )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )

    async def _capture_screen(
        self, output_path: str | None, region: dict | None
    ) -> ToolResult:
        """Capture screen screenshot."""
        system = platform.system()

        try:
            if system == "Windows":
                return await self._capture_windows(output_path, region)
            elif system == "Darwin":
                return await self._capture_mac(output_path, region)
            elif system == "Linux":
                return await self._capture_linux(output_path, region)
            else:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"Unsupported platform: {system}",
                )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Screenshot failed: {str(e)}",
            )

    async def _capture_windows(
        self, output_path: str | None, region: dict | None
    ) -> ToolResult:
        """Capture screen on Windows."""
        try:
            import mss
            import numpy as np

            with mss.mss() as sct:
                if region:
                    monitor = {
                        "left": region.get("x", 0),
                        "top": region.get("y", 0),
                        "width": region.get("width", 1920),
                        "height": region.get("height", 1080),
                    }
                else:
                    monitor = sct.monitors[1]

                img = sct.grab(monitor)
                img_np = np.array(img)

                import cv2

                img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)

                output = output_path or "screenshot.png"
                cv2.imwrite(output, img_bgr)

                _, buffer = cv2.imencode(".png", img_bgr)
                b64 = base64.b64encode(buffer).decode("utf-8")

                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.SUCCESS,
                    content=f"Screenshot saved to: {output}",
                    metadata={"path": output, "image_b64": b64},
                )
        except ImportError:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="mss or opencv-python not installed. Run: pip install mss opencv-python",
            )

    async def _capture_mac(
        self, output_path: str | None, region: dict | None
    ) -> ToolResult:
        """Capture screen on macOS."""
        try:
            import subprocess

            if region:
                x = region.get("x", 0)
                y = region.get("y", 0)
                width = region.get("width", 1920)
                height = region.get("height", 1080)
                cmd = [
                    "screencapture",
                    "-x",
                    "-R", f"{x},{y},{width},{height}",
                ]
            else:
                cmd = ["screencapture", "-x"]

            output = output_path or "screenshot.png"
            cmd.append(output)

            subprocess.run(cmd, check=True)

            p = Path(output)
            b64 = base64.b64encode(p.read_bytes()).decode("utf-8")

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=f"Screenshot saved to: {output}",
                metadata={"path": output, "image_b64": b64},
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"macOS screenshot failed: {str(e)}",
            )

    async def _capture_linux(
        self, output_path: str | None, region: dict | None
    ) -> ToolResult:
        """Capture screen on Linux."""
        try:
            import mss
            import numpy as np
            import cv2

            with mss.mss() as sct:
                if region:
                    monitor = {
                        "left": region.get("x", 0),
                        "top": region.get("y", 0),
                        "width": region.get("width", 1920),
                        "height": region.get("height", 1080),
                    }
                else:
                    monitor = sct.monitors[1]

                img = sct.grab(monitor)
                img_np = np.array(img)
                img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)

                output = output_path or "screenshot.png"
                cv2.imwrite(output, img_bgr)

                _, buffer = cv2.imencode(".png", img_bgr)
                b64 = base64.b64encode(buffer).decode("utf-8")

                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.SUCCESS,
                    content=f"Screenshot saved to: {output}",
                    metadata={"path": output, "image_b64": b64},
                )
        except ImportError:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="mss or opencv-python not installed. Run: pip install mss opencv-python",
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Linux screenshot failed: {str(e)}",
            )

    async def _analyze_screen(
        self, image_path: str | None, question: str | None
    ) -> ToolResult:
        """Analyze screenshot with vision model."""
        if not image_path:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="image_path is required for analyze mode",
            )

        p = Path(image_path)
        if not p.exists():
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Image not found: {image_path}",
            )

        try:
            import cv2

            img_bytes = p.read_bytes()
            img_np = cv2.imdecode(
                np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR
            )
            _, buffer = cv2.imencode(".jpg", img_np)
            img_b64 = base64.b64encode(buffer).decode("utf-8")

            prompt = question or "Describe this screenshot in detail."

            from manus.models import get_adapter

            adapter = get_adapter("gpt-4o")
            from manus.core.types import Message, MessageRole

            content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_b64}",
                        "detail": "high",
                    },
                },
            ]

            messages = [Message(role=MessageRole.USER, content=content)]
            response = await adapter.chat(messages=messages, max_tokens=1024)

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=response.get("content", "No analysis available"),
                metadata={"image_path": str(p)},
            )
        except ImportError:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="opencv-python not installed. Run: pip install opencv-python",
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Screenshot analysis failed: {str(e)}",
            )
