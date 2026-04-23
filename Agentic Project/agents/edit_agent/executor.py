from __future__ import annotations

from shared.schemas.project_state import EditRecord, ProjectState


class EditExecutor:
    def apply(self, state: ProjectState, command: str, intent: str, target: str) -> ProjectState:
        lowered = command.lower()
        if target == "audio":
            for character in state.characters:
                if "softer" in lowered:
                    character.voice_style = f"{character.voice_style}, soft and gentle"
                elif "energetic" in lowered or "stronger" in lowered:
                    character.voice_style = f"{character.voice_style}, energetic and bold"
                else:
                    character.voice_style = f"{character.voice_style}, adjusted tone"
        elif target == "video_frame":
            for scene in state.scenes:
                if "darker" in lowered:
                    scene.visual_prompt = f"{scene.visual_prompt}, darker mood, lower exposure"
                elif "brighter" in lowered:
                    scene.visual_prompt = f"{scene.visual_prompt}, brighter lighting, hopeful glow"
                elif "design" in lowered:
                    scene.visual_prompt = f"{scene.visual_prompt}, refreshed character design"
        elif target == "video":
            if "remove subtitle" in lowered:
                state.video.subtitles_enabled = False
            elif "add subtitle" in lowered:
                state.video.subtitles_enabled = True
            elif "speed" in lowered:
                for scene in state.scenes:
                    scene.duration_sec = max(8, scene.duration_sec - 2)
        else:
            state.prompt = f"{state.prompt}\nRevision note: {command}"
        state.edits.append(EditRecord(command=command, target=target, intent=intent))
        return state
