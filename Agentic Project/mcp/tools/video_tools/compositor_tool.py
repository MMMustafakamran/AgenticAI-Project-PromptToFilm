from __future__ import annotations

from pathlib import Path

from shared.schemas.project_state import ProjectState


def _scene_duration_sec(state: ProjectState, scene_id: str, fallback_duration: int) -> float:
    scene = next((item for item in state.scenes if item.scene_id == scene_id), None)
    if scene and scene.audio_start_ms is not None and scene.audio_end_ms is not None and scene.audio_end_ms > scene.audio_start_ms:
        return max(1.0, (scene.audio_end_ms - scene.audio_start_ms) / 1000)

    lines = [entry for entry in state.audio.timing_manifest if entry.scene_id == scene_id]
    if not lines:
        return float(fallback_duration)
    start_ms = min(entry.start_ms for entry in lines)
    end_ms = max(entry.end_ms for entry in lines)
    return max(1.0, (end_ms - start_ms) / 1000)


def compose_video(state: ProjectState, output_path: Path) -> str:
    from moviepy import AudioFileClip, CompositeVideoClip, ImageClip, TextClip, concatenate_videoclips

    output_path.parent.mkdir(parents=True, exist_ok=True)
    clips = []

    for scene in state.scenes:
        scene_duration = _scene_duration_sec(state, scene.scene_id, scene.duration_sec)
        image_clip = (
            ImageClip(scene.image_path)
            .with_duration(scene_duration)
            .resized(height=720)
            .with_position("center")
        )
        animated = image_clip.resized(lambda t: 1.0 + (0.05 * (t / max(scene_duration, 1))))
        overlays = [animated]
        if state.video.subtitles_enabled:
            lines = [entry for entry in state.audio.timing_manifest if entry.scene_id == scene.scene_id]
            if lines:
                subtitle_text = "\n".join(f"{entry.character_name}: {entry.text}" for entry in lines)
                try:
                    subtitle_clip = (
                        TextClip(
                            text=subtitle_text,
                            font_size=28,
                            color="#f8f1de",
                            bg_color="#132435",
                            size=(1100, None),
                            method="caption",
                        )
                        .with_duration(scene_duration)
                        .with_position(("center", 600))
                    )
                    overlays.append(subtitle_clip)
                except Exception:
                    pass
        scene_clip = CompositeVideoClip(overlays, size=(1280, 720)).with_duration(scene_duration)
        scene.clip_path = str(output_path.parent / f"{scene.scene_id}.mp4")
        clips.append(scene_clip)

    final = concatenate_videoclips(clips, method="compose")
    if state.audio.final_audio_path:
        final = final.with_audio(AudioFileClip(state.audio.final_audio_path))
    final.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac", logger=None)
    for clip in clips:
        clip.close()
    final.close()
    return str(output_path)
