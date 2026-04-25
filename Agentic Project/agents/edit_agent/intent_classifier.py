from __future__ import annotations

import re
from typing import Literal

from shared.schemas.project_state import ProjectState


EditTarget = Literal["script", "audio", "video_frame", "video"]


def classify_edit(command: str, state: ProjectState) -> tuple[str, EditTarget, dict[str, str | int | bool | None]]:
    text = command.lower()
    details: dict[str, str | int | bool | None] = {
        "scene_id": _extract_scene_id(text),
        "character_id": _extract_character_id(text, state),
    }

    if "voice" in text or "music" in text or "audio" in text:
        details["tone"] = _extract_tone(text)
        return "change_voice_tone", "audio", details
    if any(keyword in text for keyword in ("darker", "brighter", "design", "lighting", "visual")):
        details["visual_change"] = _extract_visual_change(text)
        return "adjust_scene_visuals", "video_frame", details
    if "subtitle" in text:
        details["subtitles_enabled"] = "remove" not in text
        return "toggle_subtitles", "video", details
    if "speed" in text or "duration" in text:
        details["duration_delta"] = -2 if any(word in text for word in ("speed", "faster", "shorter")) else 2
        return "adjust_scene_duration", "video", details
    return "regenerate_script", "script", details


def _extract_scene_id(text: str) -> str | None:
    match = re.search(r"scene\s+([12])", text)
    if not match:
        return None
    return f"scene_{match.group(1)}"


def _extract_character_id(text: str, state: ProjectState) -> str | None:
    for character in state.characters:
        if character.name.lower() in text:
            return character.character_id
    return None


def _extract_tone(text: str) -> str:
    if "soft" in text or "gentle" in text:
        return "soft"
    if "energetic" in text or "strong" in text or "bold" in text:
        return "energetic"
    return "adjusted"


def _extract_visual_change(text: str) -> str:
    if "darker" in text:
        return "darker"
    if "brighter" in text:
        return "brighter"
    if "design" in text:
        return "design"
    return "lighting"
