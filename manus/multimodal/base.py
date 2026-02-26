"""Multi-modal input/output processing."""

import base64
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class MediaType(Enum):
    """Media type enumeration."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"


@dataclass
class MediaContent:
    """Content with media type."""

    media_type: MediaType
    data: str
    mime_type: str | None = None
    filename: str | None = None

    @classmethod
    def from_text(cls, text: str) -> "MediaContent":
        return cls(media_type=MediaType.TEXT, data=text, mime_type="text/plain")

    @classmethod
    def from_image(cls, image_data: bytes, mime_type: str = "image/png") -> "MediaContent":
        b64 = base64.b64encode(image_data).decode("utf-8")
        return cls(media_type=MediaType.IMAGE, data=b64, mime_type=mime_type)

    @classmethod
    def from_image_path(cls, path: str | Path) -> "MediaContent":
        p = Path(path)
        ext = p.suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_map.get(ext, "image/png")
        data = base64.b64encode(p.read_bytes()).decode("utf-8")
        return cls(media_type=MediaType.IMAGE, data=data, mime_type=mime_type, filename=str(p.name))

    @classmethod
    def from_audio(cls, audio_data: bytes, mime_type: str = "audio/wav") -> "MediaContent":
        b64 = base64.b64encode(audio_data).decode("utf-8")
        return cls(media_type=MediaType.AUDIO, data=b64, mime_type=mime_type)

    @classmethod
    def from_video(cls, video_data: bytes, mime_type: str = "video/mp4") -> "MediaContent":
        b64 = base64.b64encode(video_data).decode("utf-8")
        return cls(media_type=MediaType.VIDEO, data=b64, mime_type=mime_type)

    def to_dict(self) -> dict[str, Any]:
        return {
            "media_type": self.media_type.value,
            "data": self.data,
            "mime_type": self.mime_type,
            "filename": self.filename,
        }


class MediaProcessor(ABC):
    """Abstract base class for media processors."""

    @abstractmethod
    async def process(self, content: MediaContent) -> dict[str, Any]:
        """Process media content."""
        pass


class ImageProcessor(MediaProcessor):
    """Process images for vision models."""

    async def process(self, content: MediaContent) -> dict[str, Any]:
        """Process image for vision model input."""
        if content.media_type != MediaType.IMAGE:
            raise ValueError("Not an image")

        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{content.mime_type};base64,{content.data}",
                "detail": "high",
            },
        }


class AudioProcessor(MediaProcessor):
    """Process audio for transcription."""

    async def process(self, content: MediaContent) -> dict[str, Any]:
        """Process audio for transcription."""
        if content.media_type != MediaType.AUDIO:
            raise ValueError("Not an audio")

        return {
            "type": "audio",
            "data": content.data,
            "mime_type": content.mime_type,
        }


class VideoProcessor(MediaProcessor):
    """Process video frames."""

    async def process(self, content: MediaContent) -> dict[str, Any]:
        """Process video for frame extraction."""
        if content.media_type != MediaType.VIDEO:
            raise ValueError("Not a video")

        return {
            "type": "video",
            "data": content.data,
            "mime_type": content.mime_type,
        }


class MultiModalConverter:
    """Convert multi-modal content to LLM-compatible format."""

    def __init__(self):
        self.processors = {
            MediaType.IMAGE: ImageProcessor(),
            MediaType.AUDIO: AudioProcessor(),
            MediaType.VIDEO: VideoProcessor(),
        }

    async def convert_to_messages(
        self,
        contents: list[MediaContent],
    ) -> list[dict[str, Any]]:
        """Convert media contents to LLM message format."""
        parts = []

        for content in contents:
            if content.media_type == MediaType.TEXT:
                parts.append({"type": "text", "text": content.data})
            else:
                processor = self.processors.get(content.media_type)
                if processor:
                    processed = await processor.process(content)
                    parts.append(processed)

        return parts

    def supports_vision(self, model_id: str) -> bool:
        """Check if model supports vision."""
        vision_models = ["gpt-4o", "gpt-4-turbo", "claude-3", "gemini"]
        return any(m in model_id.lower() for m in vision_models)

    def supports_audio(self, model_id: str) -> bool:
        """Check if model supports audio."""
        return "whisper" in model_id.lower() or "audio" in model_id.lower()


class MultiModalInput:
    """Handle multi-modal user input."""

    def __init__(self):
        self.converter = MultiModalConverter()

    async def parse_input(
        self,
        user_input: str,
        attachments: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Parse user input with attachments."""
        contents = [MediaContent.from_text(user_input)]

        if attachments:
            for path in attachments:
                p = Path(path)
                if not p.exists():
                    continue

                suffix = p.suffix.lower()
                if suffix in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
                    contents.append(MediaContent.from_image_path(str(p)))
                elif suffix in [".mp3", ".wav", ".ogg", ".m4a"]:
                    contents.append(MediaContent.from_audio(p.read_bytes(), f"audio/{suffix[1:]}"))
                elif suffix in [".mp4", ".avi", ".mov"]:
                    contents.append(MediaContent.from_video(p.read_bytes(), f"video/{suffix[1:]}"))
                else:
                    contents.append(MediaContent(
                        media_type=MediaType.FILE,
                        data=base64.b64encode(p.read_bytes()).decode("utf-8"),
                        mime_type="application/octet-stream",
                        filename=p.name,
                    ))

        return await self.converter.convert_to_messages(contents)


_multimodal_converter: MultiModalConverter | None = None


def get_multimodal_converter() -> MultiModalConverter:
    """Get global multi-modal converter."""
    global _multimodal_converter
    if _multimodal_converter is None:
        _multimodal_converter = MultiModalConverter()
    return _multimodal_converter
