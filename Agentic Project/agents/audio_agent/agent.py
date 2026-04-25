from __future__ import annotations

from pathlib import Path

from mcp.tools.audio_tools.audio_merger import stitch_audio
from mcp.tools.audio_tools.bgm_tool import create_bgm_track
from mcp.tools.audio_tools.tts_tool import TTSGenerator
from shared.schemas.project_state import DialogueTrack, ProjectState, TimingManifestEntry
from shared.utils.paths import OUTPUTS_ROOT


class AudioAgent:
    def __init__(self) -> None:
        self.tts = TTSGenerator()

    def run(self, state: ProjectState) -> ProjectState:
        project_dir = OUTPUTS_ROOT / state.project_id / "audio"
        project_dir.mkdir(parents=True, exist_ok=True)
        dialogue_tracks: list[DialogueTrack] = []
        timing_manifest: list[TimingManifestEntry] = []
        current_ms = 0
        providers_used: list[str] = []

        for scene in state.scenes:
            scene_start_ms = current_ms
            for line_index, line in enumerate(scene.dialogue):
                output_base = project_dir / f"{scene.scene_id}_line_{line_index + 1}"
                character = next(character for character in state.characters if character.character_id == line.character_id)
                provider, file_path, duration_ms, voice_name = self.tts.generate(
                    text=line.text,
                    voice_style=character.voice_style,
                    character_name=character.name,
                    output_base=output_base,
                    voice_seed=(line_index + 1),
                    preferred_voice_name=character.voice_name,
                )
                character.voice_name = character.voice_name or voice_name
                if provider not in providers_used:
                    providers_used.append(provider)
                dialogue_tracks.append(
                    DialogueTrack(
                        scene_id=scene.scene_id,
                        line_index=line_index,
                        character_id=line.character_id,
                        text=line.text,
                        file_path=file_path,
                        duration_ms=duration_ms,
                        provider=provider,
                        voice_name=voice_name,
                    )
                )
                timing_manifest.append(
                    TimingManifestEntry(
                        scene_id=scene.scene_id,
                        audio_file=file_path,
                        start_ms=current_ms,
                        end_ms=current_ms + duration_ms,
                        text=line.text,
                        character_name=line.character_name,
                        provider=provider,
                        voice_name=voice_name,
                    )
                )
                current_ms += duration_ms + 350
            scene.audio_start_ms = scene_start_ms
            scene.audio_end_ms = max(scene_start_ms, current_ms - 350)

        bgm_duration = max(20, int(max((current_ms / 1000), sum(scene.duration_sec for scene in state.scenes))))
        bgm_track_path = project_dir / "bgm.wav"
        bgm_track = create_bgm_track(state.scenes[0].mood if state.scenes else "calm", bgm_duration, bgm_track_path)
        final_audio = stitch_audio(
            timing_manifest=timing_manifest,
            bgm_track=bgm_track,
            output_path=project_dir / "final_audio.wav",
        )

        state.audio.dialogue_tracks = dialogue_tracks
        state.audio.timing_manifest = timing_manifest
        state.audio.bgm_track = bgm_track
        state.audio.final_audio_path = final_audio
        state.audio.provider = providers_used[0] if providers_used else "pending"
        state.audio.providers_used = providers_used
        state.artifacts.final_audio = final_audio
        return state
