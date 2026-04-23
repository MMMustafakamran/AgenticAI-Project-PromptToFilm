from __future__ import annotations

from io import BytesIO
from pathlib import Path
from textwrap import fill
from urllib.parse import quote_plus

import requests
from PIL import Image, ImageDraw, ImageFont

from mcp.tools.system_tools.logger_tool import get_logger
from shared.utils.paths import env


LOGGER = get_logger("image-generator")


class SceneImageGenerator:
    def __init__(self) -> None:
        self.pollinations_model = env("POLLINATIONS_MODEL", "flux")

    def generate(self, prompt: str, output_path: Path, title: str) -> str:
        image = self._try_pollinations(prompt)
        if image is None:
            image = self._placeholder_image(prompt, title)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
        return str(output_path)

    def _try_pollinations(self, prompt: str) -> Image.Image | None:
        url = f"https://image.pollinations.ai/prompt/{quote_plus(prompt)}?model={self.pollinations_model}&width=1280&height=720"
        try:
            response = requests.get(url, timeout=90)
            response.raise_for_status()
            return Image.open(BytesIO(response.content)).convert("RGB")
        except Exception as exc:  # pragma: no cover - network fallback
            LOGGER.warning("Pollinations failed: %s", exc)
            return None

    def _placeholder_image(self, prompt: str, title: str) -> Image.Image:
        image = Image.new("RGB", (1280, 720), color=(12, 18, 28))
        draw = ImageDraw.Draw(image)
        draw.rectangle((48, 48, 1232, 672), outline=(242, 177, 52), width=4)
        font = ImageFont.load_default()
        draw.text((80, 90), title, fill=(247, 239, 223), font=font)
        draw.text((80, 160), fill(prompt, width=44), fill=(194, 211, 224), font=font)
        draw.ellipse((970, 90, 1180, 300), fill=(255, 160, 75))
        draw.rectangle((80, 540, 560, 610), fill=(24, 62, 88))
        draw.text((96, 562), "Placeholder frame generated locally", fill=(246, 232, 205), font=font)
        return image
