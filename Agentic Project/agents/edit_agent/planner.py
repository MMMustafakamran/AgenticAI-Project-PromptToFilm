from __future__ import annotations


def rerun_plan_for_target(target: str, intent: str = "") -> list[str]:
    if target == "script":
        return ["story", "audio", "video"]
    if target == "audio":
        return ["audio", "video"]
    if target == "video_frame":
        # Character design change: re-run audio (new voice may be needed) + video (re-render image)
        if "character_design" in intent or "change_character" in intent:
            return ["audio", "video"]
        # Visual filter (darker, brighter, etc.): only re-composite; image reused from disk
        return ["video"]
    # target == "video"
    return ["video"]
