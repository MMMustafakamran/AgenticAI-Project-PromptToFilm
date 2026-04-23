from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance


def darken_image(image_path: str) -> str:
    path = Path(image_path)
    image = Image.open(path).convert("RGB")
    darker = ImageEnhance.Brightness(image).enhance(0.7)
    darker.save(path)
    return str(path)
