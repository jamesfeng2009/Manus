"""Video processing tools."""

import base64
import tempfile
from pathlib import Path

from manus.tools.base import Tool, ToolResult, ToolStatus


class VideoTool(Tool):
    """Video processing tool for frame extraction and analysis."""

    def __init__(self):
        super().__init__(
            name="video",
            description="Process video files: extract frames or analyze video content.",
            parameters={
                "video_path": {
                    "schema": {"type": "string", "description": "Path to video file"},
                    "required": True,
                },
                "mode": {
                    "schema": {
                        "type": "string",
                        "enum": ["frames", "analyze", "info"],
                        "description": "Mode: 'frames' (extract frames), 'analyze' (analyze with vision), 'info' (get video info)",
                    },
                    "required": True,
                },
                "frame_interval": {
                    "schema": {"type": "integer", "description": "Extract one frame every N seconds"},
                    "required": False,
                },
                "max_frames": {
                    "schema": {"type": "integer", "description": "Maximum number of frames to extract"},
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
        video_path: str,
        mode: str,
        frame_interval: int = 5,
        max_frames: int = 10,
        question: str | None = None,
        **kwargs,
    ) -> ToolResult:
        """Execute video processing."""
        try:
            p = Path(video_path)
            if not p.exists():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"Video file not found: {video_path}",
                )

            if mode == "frames":
                return await self._extract_frames(str(p), frame_interval, max_frames)
            elif mode == "analyze":
                return await self._analyze_video(str(p), question)
            elif mode == "info":
                return await self._get_video_info(str(p))
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

    async def _extract_frames(
        self, video_path: str, frame_interval: int, max_frames: int
    ) -> ToolResult:
        """Extract frames from video."""
        try:
            import cv2

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error="Cannot open video file",
                )

            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0

            interval_frames = int(fps * frame_interval)
            extracted = []
            frame_count = 0
            extracted_count = 0

            while extracted_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % interval_frames == 0:
                    _, buffer = cv2.imencode(".jpg", frame)
                    b64 = base64.b64encode(buffer).decode("utf-8")
                    timestamp = frame_count / fps
                    extracted.append(
                        {
                            "frame_index": frame_count,
                            "timestamp": round(timestamp, 2),
                            "image_b64": b64,
                        }
                    )
                    extracted_count += 1

                frame_count += 1

            cap.release()

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=f"Extracted {len(extracted)} frames",
                metadata={
                    "frames": extracted,
                    "total_frames": total_frames,
                    "duration": round(duration, 2),
                    "fps": round(fps, 2),
                },
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
                error=f"Frame extraction failed: {str(e)}",
            )

    async def _analyze_video(self, video_path: str, question: str | None) -> ToolResult:
        """Analyze video using vision model."""
        frames_result = await self._extract_frames(video_path, 5, 3)

        if frames_result.status != ToolStatus.SUCCESS:
            return frames_result

        frames = frames_result.metadata.get("frames", [])
        if not frames:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="No frames extracted",
            )

        prompt = question or "Describe this video in detail."

        try:
            from manus.models import get_adapter

            adapter = get_adapter("gpt-4o")
            from manus.core.types import Message, MessageRole

            content = [{"type": "text", "text": prompt}]
            for frame in frames[:3]:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{frame['image_b64']}",
                            "detail": "low",
                        },
                    }
                )

            messages = [Message(role=MessageRole.USER, content=content)]
            response = await adapter.chat(messages=messages, max_tokens=1024)

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=response.get("content", "No analysis available"),
                metadata={"frames_analyzed": len(frames[:3])},
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Video analysis failed: {str(e)}",
            )

    async def _get_video_info(self, video_path: str) -> ToolResult:
        """Get video metadata."""
        try:
            import cv2

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error="Cannot open video file",
                )

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0

            cap.release()

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=f"Video: {width}x{height}, {round(fps, 2)} fps, {round(duration, 2)}s",
                metadata={
                    "width": width,
                    "height": height,
                    "fps": round(fps, 2),
                    "frame_count": frame_count,
                    "duration": round(duration, 2),
                },
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
                error=f"Failed to get video info: {str(e)}",
            )
