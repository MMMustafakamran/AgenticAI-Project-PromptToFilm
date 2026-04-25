from __future__ import annotations

import base64
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus

import requests
from PIL import Image, ImageOps

from mcp.tools.system_tools.logger_tool import get_logger
from shared.utils.paths import env


LOGGER = get_logger("image-generator")


class SceneImageGenerator:
    def __init__(self) -> None:
        self.pollinations_model = env("POLLINATIONS_MODEL", "flux")
        self.openai_key = env("OPENAI_API_KEY")
        self.openai_model = env("OPENAI_IMAGE_MODEL", "gpt-image-1")

    def generate(self, prompt: str, output_path: Path, title: str) -> tuple[str, str]:
        errors: list[str] = []

        image = self._try_pollinations(prompt, errors)
        provider = "pollinations"

        if image is None:
            image = self._try_openai(prompt, errors)
            provider = "openai"

        if image is None:
            raise RuntimeError(f"Image generation failed for '{title}': {' | '.join(errors) or 'no provider available'}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
        return str(output_path), provider

    def _try_pollinations(self, prompt: str, errors: list[str]) -> Image.Image | None:
        url = f"https://image.pollinations.ai/prompt/{quote_plus(prompt)}?model={self.pollinations_model}&width=1280&height=720"
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=(6, 16))
                response.raise_for_status()
                LOGGER.info("Pollinations image generation succeeded with model %s", self.pollinations_model)
                return Image.open(BytesIO(response.content)).convert("RGB")
            except Exception as exc:  # pragma: no cover - network fallback
                errors.append(f"pollinations attempt {attempt + 1}: {exc}")
                LOGGER.warning("Pollinations failed on attempt %s: %s", attempt + 1, exc)
                time.sleep(1.2 * (attempt + 1))
        return None

    def _try_openai(self, prompt: str, errors: list[str]) -> Image.Image | None:
        if not self.openai_key:
            errors.append("openai: OPENAI_API_KEY not configured")
            return None

        payload = {
            "model": self.openai_model,
            "prompt": prompt,
            "size": "1024x1024",
        }
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(
                "https://api.openai.com/v1/images/generations",
                json=payload,
                headers=headers,
                timeout=(8, 60),
            )
            response.raise_for_status()
            data = response.json()
            image_b64 = data["data"][0]["b64_json"]
            image = Image.open(BytesIO(base64.b64decode(image_b64))).convert("RGB")
            LOGGER.info("OpenAI image generation succeeded with model %s", self.openai_model)
            return ImageOps.fit(image, (1280, 720))
        except Exception as exc:
            errors.append(f"openai: {exc}")
            LOGGER.warning("OpenAI image generation failed: %s", exc)
            return None
