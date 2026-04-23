from __future__ import annotations


def append_style(prompt: str, style_hint: str) -> str:
    return f"{prompt}, {style_hint}".strip(", ")
