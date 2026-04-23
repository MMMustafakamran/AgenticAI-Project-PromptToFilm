from __future__ import annotations


def enforce_story_constraints(prompt: str) -> str:
    return (
        f"{prompt}\n\n"
        "Constraints: produce exactly 2 scenes, total runtime 20-30 seconds, 1-3 named characters, "
        "visual prompts suitable for text-to-image generation, concise dialogue, emotionally clear ending."
    )
