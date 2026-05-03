from __future__ import annotations

from pathlib import Path

from mcp.tools.audio_tools.audio_merger import stitch_audio
from mcp.tools.audio_tools.bgm_tool import create_bgm_track
from mcp.tools.audio_tools.tts_tool import TTSGenerator
from shared.schemas.project_state import DialogueTrack, ProjectState, TimingManifestEntry
from shared.utils.paths import OUTPUTS_ROOT


from collections.abc import Callable

class AudioAgent:
    def __init__(self) -> None:
        self.tts = TTSGenerator()

    def run(self, state: ProjectState, progress_cb: Callable[[int, str], None] | None = None) -> ProjectState:
        project_dir = OUTPUTS_ROOT / state.project_id / "audio"
        project_dir.mkdir(parents=True, exist_ok=True)

        # --- BGM-ONLY FAST PATH ---
        # If the timing manifest already has valid audio files, skip TTS entirely
        # and only redo BGM generation + audio stitch. Used for BGM volume edits.
        from pathlib import Path as _Path
        existing_manifest = state.audio.timing_manifest
        if existing_manifest and all(_Path(e.audio_file).exists() for e in existing_manifest):
            if progress_cb: progress_cb(85, "Re-generating background music...")
            bgm_duration = max(20, int(max(
                (max(e.end_ms for e in existing_manifest) / 1000),
                sum(scene.duration_sec for scene in state.scenes)
            )))
            bgm_track_path = project_dir / "bgm.wav"
            bgm_track = create_bgm_track(
                state.scenes[0].mood if state.scenes else "calm",
                bgm_duration,
                bgm_track_path,
            )
            if progress_cb: progress_cb(95, "Re-stitching audio with updated BGM volume...")
            final_audio = stitch_audio(
                timing_manifest=existing_manifest,
                bgm_track=bgm_track,
                output_path=project_dir / "final_audio.wav",
                bgm_volume=state.audio.bgm_volume,
            )
            state.audio.bgm_track = bgm_track
            state.audio.final_audio_path = final_audio
            state.artifacts.final_audio = final_audio
            if progress_cb: progress_cb(100, "Audio re-stitch complete")
            return state
        # --- END FAST PATH ---

        dialogue_tracks: list[DialogueTrack] = []
        timing_manifest: list[TimingManifestEntry] = []
        current_ms = 0
        providers_used: list[str] = []

        total_lines = sum(len(scene.dialogue) for scene in state.scenes)
        lines_processed = 0

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
                    visual_description=character.visual_description,
                )
                lines_processed += 1
                if progress_cb and total_lines > 0:
                    prog = int((lines_processed / total_lines) * 80)
                    progress_cb(prog, f"Synthesized audio for {character.name}")

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

            expected_scene_end_ms = scene_start_ms + (scene.duration_sec * 1000)
            if current_ms < expected_scene_end_ms:
                current_ms = expected_scene_end_ms

            scene.audio_start_ms = scene_start_ms
            scene.audio_end_ms = current_ms

        bgm_duration = max(20, int(max((current_ms / 1000), sum(scene.duration_sec for scene in state.scenes))))
        bgm_track_path = project_dir / "bgm.wav"
        if progress_cb: progress_cb(85, "Generating background music...")
        bgm_track = create_bgm_track(state.scenes[0].mood if state.scenes else "calm", bgm_duration, bgm_track_path)
        if progress_cb: progress_cb(95, "Stitching final audio mix...")
        final_audio = stitch_audio(
            timing_manifest=timing_manifest,
            bgm_track=bgm_track,
            output_path=project_dir / "final_audio.wav",
            bgm_volume=state.audio.bgm_volume,
        )
        if progress_cb: progress_cb(100, "Audio generation complete")

        state.audio.dialogue_tracks = dialogue_tracks
        state.audio.timing_manifest = timing_manifest
        state.audio.bgm_track = bgm_track
        state.audio.final_audio_path = final_audio
        state.audio.provider = providers_used[0] if providers_used else "pending"
        state.audio.providers_used = providers_used
        state.artifacts.final_audio = final_audio
        return state
