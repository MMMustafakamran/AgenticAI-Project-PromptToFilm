from __future__ import annotations

from shared.schemas.project_state import EditRecord, ProjectState, SceneState


class EditExecutor:
    def apply(self, state: ProjectState, command: str, intent: str, target: str, details: dict[str, str | int | bool | None]) -> ProjectState:
        lowered = command.lower()
        target_label = self._target_label(state, details)

        if target == "audio":
            self._apply_audio_edit(state, lowered, details)
        elif target == "video_frame":
            self._apply_video_frame_edit(state, details)
        elif target == "video":
            self._apply_video_edit(state, details)
        else:
            state.prompt = f"{state.prompt}\nRevision note: {command}"

        state.edits.append(EditRecord(command=command, target=target, intent=intent, target_label=target_label))
        return state

    def _apply_audio_edit(self, state: ProjectState, lowered: str, details: dict[str, str | int | bool | None]) -> None:
        targets = self._select_characters(state, details.get("character_id"))
        tone = str(details.get("tone") or "adjusted")
        for character in targets:
            base_style = character.voice_style.split(",")[0].strip()
            if tone == "soft":
                character.voice_style = f"{base_style}, soft and gentle"
            elif tone == "energetic":
                character.voice_style = f"{base_style}, energetic and bold"
            else:
                character.voice_style = f"{base_style}, adjusted tone"
            if "different voice" in lowered or "new voice" in lowered:
                character.voice_name = None

    def _apply_video_frame_edit(self, state: ProjectState, details: dict[str, str | int | bool | None]) -> None:
        scenes = self._select_scenes(state, details.get("scene_id"))
        visual_change = str(details.get("visual_change") or "lighting")
        for scene in scenes:
            if visual_change == "darker":
                scene.visual_prompt = f"{scene.visual_prompt}, darker mood, lower exposure"
            elif visual_change == "brighter":
                scene.visual_prompt = f"{scene.visual_prompt}, brighter lighting, hopeful glow"
            elif visual_change == "design":
                scene.visual_prompt = f"{scene.visual_prompt}, refreshed character design"
            else:
                scene.visual_prompt = f"{scene.visual_prompt}, refined cinematic lighting"

    def _apply_video_edit(self, state: ProjectState, details: dict[str, str | int | bool | None]) -> None:
        if details.get("subtitles_enabled") is not None:
            state.video.subtitles_enabled = bool(details["subtitles_enabled"])
            return

        delta = int(details.get("duration_delta") or 0)
        for scene in self._select_scenes(state, details.get("scene_id")):
            scene.duration_sec = max(8, min(15, scene.duration_sec + delta))

    def _select_characters(self, state: ProjectState, character_id: str | int | bool | None):
        if isinstance(character_id, str):
            matches = [character for character in state.characters if character.character_id == character_id]
            if matches:
                return matches
        return state.characters

    def _select_scenes(self, state: ProjectState, scene_id: str | int | bool | None) -> list[SceneState]:
        if isinstance(scene_id, str):
            matches = [scene for scene in state.scenes if scene.scene_id == scene_id]
            if matches:
                return matches
        return state.scenes

    def _target_label(self, state: ProjectState, details: dict[str, str | int | bool | None]) -> str | None:
        scene_id = details.get("scene_id")
        if isinstance(scene_id, str):
            return scene_id
        character_id = details.get("character_id")
        if isinstance(character_id, str):
            character = next((item for item in state.characters if item.character_id == character_id), None)
            return character.name if character else character_id
        return None
