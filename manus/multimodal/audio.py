"""Audio processing tools (ASR/TTS)."""

import base64
import io
import tempfile
from pathlib import Path

from manus.tools.base import Tool, ToolResult, ToolStatus


class AudioTool(Tool):
    """Audio processing tool for speech recognition and synthesis."""

    def __init__(self):
        super().__init__(
            name="audio",
            description="Process audio files: transcribe speech to text (ASR) or synthesize text to speech (TTS).",
            parameters={
                "audio_path": {
                    "schema": {"type": "string", "description": "Path to audio file for transcription"},
                    "required": False,
                },
                "mode": {
                    "schema": {
                        "type": "string",
                        "enum": ["transcribe", "tts"],
                        "description": "Mode: 'transcribe' (audio to text) or 'tts' (text to audio)",
                    },
                    "required": True,
                },
                "language": {
                    "schema": {"type": "string", "description": "Language code (e.g., 'zh', 'en')"},
                    "required": False,
                },
                "text": {
                    "schema": {"type": "string", "description": "Text to synthesize for TTS mode"},
                    "required": False,
                },
                "voice": {
                    "schema": {"type": "string", "description": "Voice name for TTS"},
                    "required": False,
                },
            },
        )

    async def execute(
        self,
        mode: str,
        audio_path: str | None = None,
        language: str = "zh",
        text: str | None = None,
        voice: str | None = None,
        **kwargs,
    ) -> ToolResult:
        """Execute audio processing."""
        try:
            if mode == "transcribe":
                return await self._transcribe(audio_path, language)
            elif mode == "tts":
                return await self._synthesize(text, language, voice)
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

    async def _transcribe(self, audio_path: str | None, language: str) -> ToolResult:
        """Transcribe audio to text using Whisper."""
        if not audio_path:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="audio_path is required for transcribe mode",
            )

        p = Path(audio_path)
        if not p.exists():
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Audio file not found: {audio_path}",
            )

        try:
            import whisper

            model = whisper.load_model("base")
            result = model.transcribe(str(p), language=language if language else None)

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=result["text"],
                metadata={
                    "language": result.get("language", language),
                    "duration": result.get("duration", 0),
                },
            )
        except ImportError:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="Whisper not installed. Run: pip install openai-whisper",
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Transcription failed: {str(e)}",
            )

    async def _synthesize(
        self, text: str | None, language: str, voice: str | None
    ) -> ToolResult:
        """Synthesize text to speech."""
        if not text:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="text is required for tts mode",
            )

        try:
            import edge_tts

            voice_map = {
                "zh": "zh-CN-XiaoxiaoNeural",
                "en": "en-US-AriaNeural",
            }
            selected_voice = voice or voice_map.get(language, "zh-CN-XiaoxiaoNeural")

            communicate = edge_tts.Communicate(text, selected_voice)
            audio_buffer = io.BytesIO()
            await communicate.save(audio_buffer)
            audio_buffer.seek(0)

            audio_b64 = base64.b64encode(audio_buffer.read()).decode("utf-8")

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=audio_b64,
                metadata={
                    "format": "mp3",
                    "voice": selected_voice,
                    "text_length": len(text),
                },
            )
        except ImportError:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="edge-tts not installed. Run: pip install edge-tts",
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Synthesis failed: {str(e)}",
            )
