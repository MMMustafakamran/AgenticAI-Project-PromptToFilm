from __future__ import annotations

from typing import Literal


EditTarget = Literal["script", "audio", "video_frame", "video"]


def classify_edit(command: str) -> tuple[str, EditTarget]:
    text = command.lower()
    if "voice" in text or "music" in text or "audio" in text:
        return "change_voice_tone", "audio"
    if "darker" in text or "brighter" in text or "design" in text or "scene" in text:
        return "make_scene_darker", "video_frame"
    if "subtitle" in text or "video" in text or "speed" in text:
        return "remove_subtitles" if "remove" in text else "video_adjustment", "video"
    return "regenerate_script", "script"
