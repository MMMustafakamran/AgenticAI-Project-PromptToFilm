from __future__ import annotations

import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance

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


def zoom_effect(clip, mode="in"):
    """MoviePy transform function to create a steady zoom effect on an ImageClip or VideoClip."""
    def transform_frame(get_frame, t):
        frame = get_frame(t)
        img = Image.fromarray(frame)
        w, h = img.size
        
        # Calculate subtle zoom factor
        duration = max(clip.duration, 1.0)
        if mode == "in":
            factor = 1.0 + (0.35 * (t / duration))
        else:
            factor = 1.35 - (0.35 * (t / duration))
            
        new_w = int(w * factor)
        new_h = int(h * factor)
        resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Crop back to original dimensions centered
        left = (new_w - w) // 2
        top = (new_h - h) // 2
        return np.array(resized_img.crop((left, top, left + w, top + h)))

    return clip.transform(transform_frame)


def color_effect(clip, factor=1.0):
    """MoviePy transform function to adjust brightness/color grading via PIL."""
    def transform_frame(get_frame, t):
        frame = get_frame(t)
        img = Image.fromarray(frame)
        enhanced = ImageEnhance.Brightness(img).enhance(factor)
        return np.array(enhanced)

    return clip.transform(transform_frame)


def compose_video(state: ProjectState, output_path: Path) -> str:
    from moviepy import AudioFileClip, CompositeVideoClip, ImageClip, VideoFileClip, TextClip, concatenate_videoclips

    output_path.parent.mkdir(parents=True, exist_ok=True)
    clips = []

    for scene in state.scenes:
        scene_duration = _scene_duration_sec(state, scene.scene_id, scene.duration_sec)
        
        if scene.image_path and scene.image_path.endswith(".mp4"):
            video_clip = VideoFileClip(scene.image_path).resized(height=720).with_position("center")
            if video_clip.duration < scene_duration:
                repeats = int(scene_duration / video_clip.duration) + 1
                animated = concatenate_videoclips([video_clip] * repeats, method="compose").subclipped(0, scene_duration)
            else:
                animated = video_clip.subclipped(0, scene_duration)
        else:
            image_clip = (
                ImageClip(scene.image_path)
                .with_duration(scene_duration)
                .resized(height=720)
                .with_position("center")
            )
            animated = image_clip
            
        # Apply visual effects using the Pillow transforms to BOTH images and videos
        p_lower = scene.visual_prompt.lower() if scene.visual_prompt else ""
        
        # Zoom effects
        if "zoom out" in p_lower:
            animated = zoom_effect(animated, mode="out")
        elif "zoom in" in p_lower or "zoom" in p_lower or "pan" in p_lower:
            animated = zoom_effect(animated, mode="in")

        # Brightness/darkness effects
        if "dark" in p_lower:
            animated = color_effect(animated, factor=0.7)
        elif "bright" in p_lower or "light" in p_lower or "vivid" in p_lower:
            animated = color_effect(animated, factor=1.3)
            
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
