from __future__ import annotations

from shared.schemas.project_state import CharacterState, DialogueLine, ProjectState, SceneState, StoryState
from mcp.tools.llm_tools.text_generator import StoryGenerator
from agents.story_agent.planner import enforce_story_constraints


class StoryAgent:
    def __init__(self) -> None:
        self.generator = StoryGenerator()

    def run(self, state: ProjectState) -> ProjectState:
        payload = self.generator.generate_story_payload(enforce_story_constraints(state.prompt))
        state.story = StoryState.model_validate(payload["story"])
        state.characters = [
            CharacterState(
                character_id=f"char_{index + 1}",
                name=character["name"],
                role=character["role"],
                voice_style=character["voice_style"],
                visual_description=character["visual_description"],
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
        return state
