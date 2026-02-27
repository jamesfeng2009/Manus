from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass
from typing import Any
import os

import httpx

from manus.core.exceptions import ModelAuthenticationError, ModelError


@dataclass
class ImageResult:
    """图像生成结果"""
    image_url: str
    thumbnail_url: str | None = None
    revised_prompt: str | None = None
    provider: str = ""
    model: str = ""
    metadata: dict | None = None


class ImageGenAdapter(ABC):
    """图像生成适配器基类"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 60,
    ):
        self.api_key = api_key or ""
        self.base_url = base_url or ""
        self.timeout = timeout

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        **kwargs,
    ) -> ImageResult:
        """生成图像"""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """获取供应商名称"""
        pass

    def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.timeout)


class DalleAdapter(ImageGenAdapter):
    """OpenAI DALL-E 适配器"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "dall-e-3",
        timeout: int = 60,
    ):
        super().__init__(
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
            base_url="https://api.openai.com/v1",
            timeout=timeout,
        )
        self.model = model

    async def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "natural",
        n: int = 1,
        **kwargs,
    ) -> ImageResult:
        if not self.api_key:
            raise ModelAuthenticationError("OPENAI_API_KEY not found")

        async with self._get_client() as client:
            response = await client.post(
                f"{self.base_url}/images/generations",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "size": size,
                    "quality": quality,
                    "style": style,
                    "n": n,
                },
            )

            if response.status_code != 200:
                raise ModelError(f"DALL-E error: {response.text}")

            data = response.json()
            image_data = data["data"][0]

            return ImageResult(
                image_url=image_data["url"],
                revised_prompt=image_data.get("revised_prompt"),
                provider="openai",
                model=self.model,
            )

    def get_provider_name(self) -> str:
        return "dalle"


class StabilityAdapter(ImageGenAdapter):
    """Stability AI 适配器"""

    def __init__(
        self,
        api_key: str | None = None,
        engine_id: str = "stable-diffusion-xl-1024-v1-0",
        timeout: int = 120,
    ):
        super().__init__(
            api_key=api_key or os.environ.get("STABILITY_API_KEY"),
            base_url="https://api.stability.ai/v1",
            timeout=timeout,
        )
        self.engine_id = engine_id

    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 30,
        cfg_scale: int = 7,
        samples: int = 1,
        **kwargs,
    ) -> ImageResult:
        if not self.api_key:
            raise ModelAuthenticationError("STABILITY_API_KEY not found")

        async with self._get_client() as client:
            response = await client.post(
                f"{self.base_url}/generation/{self.engine_id}/text-to-image",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/json",
                },
                json={
                    "text_prompts": [
                        {"text": prompt, "weight": 1},
                        *({"text": negative_prompt, "weight": -1} if negative_prompt else []),
                    ],
                    "cfg_scale": cfg_scale,
                    "height": height,
                    "width": width,
                    "steps": steps,
                    "samples": samples,
                },
            )

            if response.status_code != 200:
                raise ModelError(f"Stability AI error: {response.text}")

            data = response.json()
            base64_image = data["artifacts"][0]["base64"]
            image_url = f"data:image/png;base64,{base64_image}"

            return ImageResult(
                image_url=image_url,
                provider="stability",
                model=self.engine_id,
            )

    def get_provider_name(self) -> str:
        return "stability"


class ReplicateAdapter(ImageGenAdapter):
    """Replicate 适配器 (支持 FLUX, SD, etc.)"""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: int = 120,
    ):
        super().__init__(
            api_key=api_key or os.environ.get("REPLICATE_API_KEY"),
            base_url="https://api.replicate.com/v1",
            timeout=timeout,
        )

    async def generate(
        self,
        prompt: str,
        model: str = "black-forest-labs/flux-schnell",
        version: str | None = None,
        **kwargs,
    ) -> ImageResult:
        if not self.api_key:
            raise ModelAuthenticationError("REPLICATE_API_KEY not found")

        async with self._get_client() as client:
            create_response = await client.post(
                f"{self.base_url}/predictions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "version": version,
                    "input": {
                        "prompt": prompt,
                        **kwargs,
                    },
                },
            )

            if create_response.status_code != 201:
                raise ModelError(f"Replicate error: {create_response.text}")

            prediction = create_response.json()
            prediction_id = prediction["id"]

            while True:
                status_response = await client.get(
                    f"{self.base_url}/predictions/{prediction_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                status_data = status_response.json()

                if status_data["status"] == "succeeded":
                    output = status_data["output"]
                    image_url = output if isinstance(output, str) else output[0]
                    break
                elif status_data["status"] == "failed":
                    raise ModelError(f"Replicate failed: {status_data.get('error')}")

                await asyncio.sleep(1)

            return ImageResult(
                image_url=image_url,
                provider="replicate",
                model=model,
            )

    def get_provider_name(self) -> str:
        return "replicate"


class ImageGenFactory:
    """图像生成器工厂"""

    _adapters: dict[str, type[ImageGenAdapter]] = {
        "dalle": DalleAdapter,
        "stable": StabilityAdapter,
        "replicate": ReplicateAdapter,
    }

    @classmethod
    def create(
        cls,
        provider: str,
        **kwargs,
    ) -> ImageGenAdapter:
        adapter_class = cls._adapters.get(provider.lower())
        if not adapter_class:
            raise ValueError(f"Unknown provider: {provider}")
        return adapter_class(**kwargs)

    @classmethod
    def register(cls, name: str, adapter_class: type[ImageGenAdapter]):
        cls._adapters[name.lower()] = adapter_class
