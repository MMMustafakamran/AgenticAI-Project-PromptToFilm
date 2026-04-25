from __future__ import annotations

from mcp.tools.system_tools.logger_tool import get_logger
from shared.schemas.project_state import CharacterState, DialogueLine, ProjectState, SceneState, StoryState
from mcp.tools.llm_tools.text_generator import StoryGenerator
from agents.story_agent.planner import enforce_story_constraints


from collections.abc import Callable

LOGGER = get_logger("story-agent")


class StoryAgent:
    def __init__(self) -> None:
        self.generator = StoryGenerator()

    def run(self, state: ProjectState, progress_cb: Callable[[int, str], None] | None = None) -> ProjectState:
        if progress_cb: progress_cb(10, "Applying narrative constraints...")
        prompt = enforce_story_constraints(state.prompt)
        if progress_cb: progress_cb(40, "Calling language model for story generation...")
        payload, provider = self.generator.generate_story_payload(prompt)
        try:
            if progress_cb: progress_cb(80, "Parsing and validating story structure...")
            self._apply_payload(state, payload, provider)
            if progress_cb: progress_cb(100, "Story finalized")
        except Exception as exc:
            LOGGER.warning("Story payload validation failed, using deterministic fallback: %s", exc)
            if progress_cb: progress_cb(80, "Validation failed, falling back to deterministic template...")
            fallback_payload = self.generator.fallback_story_payload(prompt)
            self._apply_payload(state, fallback_payload, "fallback")
            if progress_cb: progress_cb(100, "Story finalized with fallback")
        return state

    def _apply_payload(self, state: ProjectState, payload: dict, provider: str) -> None:
        state.story = StoryState.model_validate(payload["story"])
        state.story.provider = provider
        state.characters = [
            CharacterState(
                character_id=f"char_{index + 1}",
                name=character["name"],
                role=character["role"],
                voice_style=character["voice_style"],
                visual_description=character["visual_description"],
                voice_name=character.get("voice_name"),
            )
            for index, character in enumerate(payload["characters"])
        ]
        characters_by_name = {character.name: character for character in state.characters}
        state.scenes = []
        for index, scene in enumerate(payload["scenes"]):
            dialogue = []
            for item in scene["dialogue"]:
                character = characters_by_name[item["character_name"]]
                dialogue.append(
                    DialogueLine(
                        character_id=character.character_id,
                        character_name=character.name,
                        text=item["text"],
                        emotion=item.get("emotion", "neutral"),
                    )
                )
            state.scenes.append(
                SceneState(
                    scene_id=f"scene_{index + 1}",
                    title=scene["title"],
                    duration_sec=scene["duration_sec"],
                    narration=scene["narration"],
                    dialogue=dialogue,
                    visual_prompt=scene["visual_prompt"],
                    mood=scene["mood"],
                    subtitle_lines=scene["subtitle_lines"],
                )
            )
