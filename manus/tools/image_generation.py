from typing import Any

from manus.tools.base import Tool, ToolResult, ToolStatus
from manus.models.adapters.image import (
    ImageGenFactory,
    ImageResult,
)


class ImageGenerationTool(Tool):
    """图像生成工具"""

    def __init__(self, default_provider: str = "dalle"):
        super().__init__(
            name="image_generation",
            description="根据文本描述生成图像。支持 DALL-E (OpenAI), Stable Diffusion (Stability AI), FLUX 等模型。",
        )
        self.default_provider = default_provider
        self._adapters: dict[str, Any] = {}

    def _get_adapter(self, provider: str):
        if provider not in self._adapters:
            self._adapters[provider] = ImageGenFactory.create(provider)
        return self._adapters[provider]

    async def execute(self, **kwargs) -> ToolResult:
        prompt = kwargs.get("prompt", "")
        provider = kwargs.get("provider", self.default_provider)
        size = kwargs.get("size", "1024x1024")
        quality = kwargs.get("quality", "standard")
        style = kwargs.get("style", "natural")
        negative_prompt = kwargs.get("negative_prompt", "")

        if not prompt:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error="Prompt is required",
            )

        try:
            adapter = self._get_adapter(provider)
            result = await adapter.generate(
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
                negative_prompt=negative_prompt,
            )

            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                content=result.image_url,
                metadata={
                    "provider": result.provider,
                    "model": result.model,
                    "revised_prompt": result.revised_prompt,
                },
            )

        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
            )

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "图像描述文本",
                    },
                    "provider": {
                        "type": "string",
                        "enum": ["dalle", "stable", "replicate"],
                        "description": "图像生成供应商",
                        "default": self.default_provider,
                    },
                    "size": {
                        "type": "string",
                        "enum": ["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"],
                        "description": "图像尺寸 (DALL-E)",
                        "default": "1024x1024",
                    },
                    "quality": {
                        "type": "string",
                        "enum": ["standard", "hd"],
                        "description": "图像质量",
                        "default": "standard",
                    },
                    "style": {
                        "type": "string",
                        "enum": ["natural", "vivid", "anime"],
                        "description": "图像风格",
                        "default": "natural",
                    },
                    "negative_prompt": {
                        "type": "string",
                        "description": "负面提示词 (Stable Diffusion)",
                    },
                },
                "required": ["prompt"],
            },
        }
