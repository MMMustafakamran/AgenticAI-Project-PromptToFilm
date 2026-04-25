from __future__ import annotations

from pathlib import Path

from shared.schemas.project_state import TimingManifestEntry


def stitch_audio(
    timing_manifest: list[TimingManifestEntry],
    bgm_track: str | None,
    output_path: Path,
    bgm_volume: float = 0.2,
) -> str:
    from moviepy import AudioFileClip, CompositeAudioClip

    output_path.parent.mkdir(parents=True, exist_ok=True)
    clips: list[AudioFileClip] = []
    layered_clips = []

    try:
        total_duration = 0.0
        for entry in timing_manifest:
            clip = AudioFileClip(entry.audio_file)
            clips.append(clip)
            start_sec = entry.start_ms / 1000
            total_duration = max(total_duration, start_sec + clip.duration)
            layered_clips.append(clip.with_start(start_sec))

        if bgm_track:
            bgm_clip = AudioFileClip(bgm_track)
            clips.append(bgm_clip)
            total_duration = max(total_duration, bgm_clip.duration)
            layered_clips.append(bgm_clip.with_volume_scaled(bgm_volume))

        if not layered_clips:
            output_path.write_bytes(b"")
            return str(output_path)

        composite = CompositeAudioClip(layered_clips).with_duration(total_duration)
        composite.write_audiofile(str(output_path), fps=22050, logger=None)
        composite.close()
        return str(output_path)
    finally:
        for clip in clips:
            clip.close()
