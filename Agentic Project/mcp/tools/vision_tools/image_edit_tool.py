from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


def darken_image(image_path: str, factor: float = 0.7) -> str:
    path = Path(image_path)
    image = Image.open(path).convert("RGB")
    ImageEnhance.Brightness(image).enhance(factor).save(path)
    return str(path)


def brighten_image(image_path: str, factor: float = 1.35) -> str:
    path = Path(image_path)
    image = Image.open(path).convert("RGB")
    ImageEnhance.Brightness(image).enhance(factor).save(path)
    return str(path)


def saturate_image(image_path: str, factor: float = 1.6) -> str:
    path = Path(image_path)
    image = Image.open(path).convert("RGB")
    ImageEnhance.Color(image).enhance(factor).save(path)
    return str(path)


def desaturate_image(image_path: str) -> str:
    """Convert to grayscale noir effect."""
    path = Path(image_path)
    image = Image.open(path).convert("RGB")
    ImageEnhance.Color(image).enhance(0.0).save(path)
    return str(path)


def sharpen_image(image_path: str) -> str:
    path = Path(image_path)
    image = Image.open(path).convert("RGB")
    ImageEnhance.Sharpness(image).enhance(2.0).save(path)
    return str(path)


def apply_vignette(image_path: str) -> str:
    """Apply dark cinematic vignette (dark edges, bright center) using PIL only."""
    path = Path(image_path)
    img = Image.open(path).convert("RGB")
    w, h = img.size

    dark = ImageEnhance.Brightness(img).enhance(0.25)

    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    margin_x, margin_y = int(w * 0.18), int(h * 0.18)
    draw.ellipse([margin_x, margin_y, w - margin_x, h - margin_y], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=min(w, h) * 0.12))

    Image.composite(img, dark, mask).save(path)
    return str(path)


def apply_filter(image_path: str, filter_name: str) -> str:
    """Dispatch to the correct filter by name keyword."""
    lower = filter_name.lower()
    if "dark" in lower:
        return darken_image(image_path)
    if "bright" in lower or "light" in lower:
        return brighten_image(image_path)
    if "desatur" in lower or "gray" in lower or "grey" in lower or "noir" in lower or "black and white" in lower:
        return desaturate_image(image_path)
    if "satur" in lower or "vivid" in lower or "vibrant" in lower:
        return saturate_image(image_path)
    if "vignette" in lower or "cinematic border" in lower:
        return apply_vignette(image_path)
    if "sharp" in lower or "crisp" in lower:
        return sharpen_image(image_path)
    return image_path
