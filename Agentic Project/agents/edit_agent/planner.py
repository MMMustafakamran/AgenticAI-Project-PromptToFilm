from __future__ import annotations


def rerun_plan_for_target(target: str) -> list[str]:
    if target == "script":
        return ["story", "audio", "video"]
    if target == "audio":
        return ["audio", "video"]
    return ["video"]
