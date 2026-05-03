from __future__ import annotations

from pathlib import Path

from mcp.tools.vision_tools.image_edit_tool import apply_filter
from shared.schemas.project_state import EditRecord, ProjectState, SceneState


class EditExecutor:
    def apply(
        self,
        state: ProjectState,
        command: str,
        intent: str,
        target: str,
        details: dict[str, str | int | bool | None],
    ) -> ProjectState:
        lowered = command.lower()
        target_label = self._target_label(state, details)

        if target == "audio":
            self._apply_audio_edit(state, lowered, intent, details)
        elif target == "video_frame":
            self._apply_video_frame_edit(state, intent, details)
        elif target == "video":
            self._apply_video_edit(state, details)
        else:
            # script — append revision note so LLM sees it on re-run
            state.prompt = f"{state.prompt}\nRevision note: {command}"

        state.edits.append(
            EditRecord(command=command, target=target, intent=intent, target_label=target_label)
        )
        return state

    # ------------------------------------------------------------------
    # Audio edits
    # ------------------------------------------------------------------
    def _apply_audio_edit(
        self,
        state: ProjectState,
        lowered: str,
        intent: str,
        details: dict[str, str | int | bool | None],
    ) -> None:
        # BGM volume adjustment — do NOT touch voices
        if "bgm" in intent or "background_music" in intent or "bgm_volume" in intent or "background music" in lowered:
            raw = details.get("duration_delta") or details.get("tone")
            if raw is not None:
                try:
                    state.audio.bgm_volume = max(0.0, min(1.0, float(raw)))
                except (ValueError, TypeError):
                    pass
            # Keyword overrides
            if "lower" in lowered or "quiet" in lowered or "softer" in lowered or "reduce" in lowered:
                state.audio.bgm_volume = max(0.0, state.audio.bgm_volume - 0.05)
            elif "louder" in lowered or "higher" in lowered or "increase" in lowered or "boost" in lowered:
                state.audio.bgm_volume = min(1.0, state.audio.bgm_volume + 0.08)
            return

        # Voice tone change — update voice_style on target character(s)
        targets = self._select_characters(state, details.get("character_id"))
        tone = str(details.get("tone") or "adjusted")
        for character in targets:
            base_style = character.voice_style.split(",")[0].strip()
            if tone in ("soft", "gentle", "calm", "whisper"):
                character.voice_style = f"{base_style}, soft and gentle"
            elif tone in ("deep", "bold", "energetic", "strong"):
                character.voice_style = f"{base_style}, energetic and bold"
            elif tone in ("whispered", "whisper"):
                character.voice_style = f"{base_style}, whispering"
            else:
                character.voice_style = f"{base_style}, {tone} tone"
            if "different voice" in lowered or "new voice" in lowered or "change voice" in lowered:
                character.voice_name = None

    # ------------------------------------------------------------------
    # Video frame edits
    # ------------------------------------------------------------------
    def _apply_video_frame_edit(
        self,
        state: ProjectState,
        intent: str,
        details: dict[str, str | int | bool | None],
    ) -> None:
        visual_change = str(details.get("visual_change") or "")

        if "character_design" in intent or "change_character" in intent:
            self._apply_character_design_edit(state, details, visual_change)
        else:
            self._apply_visual_filter_edit(state, details, visual_change)

    def _apply_visual_filter_edit(
        self,
        state: ProjectState,
        details: dict[str, str | int | bool | None],
        visual_change: str,
    ) -> None:
        """Apply PIL filter in-place. Does NOT clear image_path so Kaggle is NOT re-called."""
        scenes = self._select_scenes(state, details.get("scene_id"))
        for scene in scenes:
            # Update the visual_prompt so future re-renders respect the change
            if visual_change:
                scene.visual_prompt = f"{scene.visual_prompt}, {visual_change} aesthetic"
            # Apply filter to existing image file immediately (PNG only; mp4 skipped)
            if scene.image_path:
                img_path = Path(scene.image_path)
                if img_path.exists() and img_path.suffix.lower() == ".png":
                    apply_filter(str(img_path), visual_change or "darker")

    def _apply_character_design_edit(
        self,
        state: ProjectState,
        details: dict[str, str | int | bool | None],
        design_change: str,
    ) -> None:
        """Update character visual_description and CLEAR image_path so Kaggle re-renders."""
        char_ref = details.get("character_id")
        targets = self._select_characters(state, char_ref)
        for character in targets:
            if design_change:
                character.visual_description = f"{character.visual_description}, {design_change}"
            # Reset voice so TTS picks fresh voice based on new description
            character.voice_name = None

        # Find scenes featuring these characters and clear their image paths
        target_ids = {c.character_id for c in targets}
        for scene in state.scenes:
            scene_char_ids = {line.character_id for line in scene.dialogue}
            if not target_ids or scene_char_ids & target_ids:
                scene.image_path = None
                scene.image_provider = None
                scene.image_status = "pending"
                scene.image_error = None

    # ------------------------------------------------------------------
    # Video-level edits (subtitles, pacing)
    # ------------------------------------------------------------------
    def _apply_video_edit(
        self,
        state: ProjectState,
        details: dict[str, str | int | bool | None],
    ) -> None:
        if details.get("subtitles_enabled") is not None:
            state.video.subtitles_enabled = bool(details["subtitles_enabled"])
            return

        delta = int(details.get("duration_delta") or 0)
        if delta:
            for scene in self._select_scenes(state, details.get("scene_id")):
                scene.duration_sec = max(8, min(15, scene.duration_sec + delta))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _select_characters(self, state: ProjectState, character_ref: str | int | bool | None):
        if isinstance(character_ref, str) and character_ref:
            # Match by ID or by name (case-insensitive)
            matches = [
                c for c in state.characters
                if c.character_id == character_ref
                or c.name.lower() == character_ref.lower()
            ]
            if matches:
                return matches
        return state.characters

    def _select_scenes(self, state: ProjectState, scene_id: str | int | bool | None) -> list[SceneState]:
        if isinstance(scene_id, str) and scene_id:
            matches = [s for s in state.scenes if s.scene_id == scene_id]
            if matches:
                return matches
        return state.scenes

    def _target_label(self, state: ProjectState, details: dict[str, str | int | bool | None]) -> str | None:
        scene_id = details.get("scene_id")
        if isinstance(scene_id, str) and scene_id:
            return scene_id
        character_id = details.get("character_id")
        if isinstance(character_id, str) and character_id:
            character = next(
                (c for c in state.characters if c.character_id == character_id or c.name.lower() == character_id.lower()),
                None,
            )
            return character.name if character else character_id
        return None
