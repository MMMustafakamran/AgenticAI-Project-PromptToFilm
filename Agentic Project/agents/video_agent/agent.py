from __future__ import annotations

from pathlib import Path

from mcp.tools.video_tools.compositor_tool import compose_video
from mcp.tools.video_tools.subtitle_tool import write_subtitles
from mcp.tools.vision_tools.image_edit_tool import darken_image
from mcp.tools.vision_tools.image_gen_tool import SceneImageGenerator
from mcp.tools.vision_tools.style_transfer import append_style
from shared.schemas.project_state import ProjectState
from shared.utils.paths import OUTPUTS_ROOT


from collections.abc import Callable

class VideoAgent:
    def __init__(self) -> None:
        self.image_generator = SceneImageGenerator()

    def run(self, state: ProjectState, progress_cb: Callable[[int, str], None] | None = None) -> ProjectState:
        project_dir = OUTPUTS_ROOT / state.project_id / "video"
        image_dir = project_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)

        style_hint = "cinematic 2D animated short, polished lighting, coherent character styling"
        scene_images: list[str] = []
        image_providers: list[str] = []
        
        total_scenes = len(state.scenes)
        
        from shared.utils.paths import env
        use_video = bool(env("KAGGLE_API_URL"))

        for index, scene in enumerate(state.scenes):
            active_character_names = {line.character_name for line in scene.dialogue}
            character_details = []
            for char in state.characters:
                if char.name in active_character_names or not active_character_names:
                    character_details.append(f"{char.name} ({char.visual_description})")
            
            char_context = "Featuring characters: " + "; ".join(character_details) + ". " if character_details else ""
            enhanced_prompt = f"{char_context}{scene.visual_prompt}"
            
            prompt = append_style(enhanced_prompt, style_hint)
            
            scene.image_status = "pending"
            scene.image_error = None
            try:
                if use_video:
                    image_path = image_dir / f"{scene.scene_id}.mp4"
                    if progress_cb: progress_cb(int((index / total_scenes) * 70), f"Rendering video for {scene.scene_id}...")
                    scene.image_path, scene.image_provider = self.image_generator.generate_video(prompt, image_path, scene.title)
                else:
                    image_path = image_dir / f"{scene.scene_id}.png"
                    if progress_cb: progress_cb(int((index / total_scenes) * 70), f"Rendering frame for {scene.scene_id}...")
                    scene.image_path, scene.image_provider = self.image_generator.generate(prompt, image_path, scene.title)
                    if "darker" in scene.visual_prompt.lower():
                        scene.image_path = darken_image(scene.image_path)
            except Exception as exc:
                scene.image_status = "failed"
                scene.image_error = str(exc)
                raise
            
            if progress_cb: progress_cb(int(((index + 1) / total_scenes) * 70), f"Rendered frame for {scene.scene_id}")
            scene.image_status = "generated"
            scene_images.append(scene.image_path)
            if scene.image_provider and scene.image_provider not in image_providers:
                image_providers.append(scene.image_provider)

        subtitle_file = None
        if state.video.subtitles_enabled:
            if progress_cb: progress_cb(75, "Generating subtitles...")
            subtitle_file = write_subtitles(state.audio.timing_manifest, project_dir / "subtitles.srt")

        if progress_cb: progress_cb(85, "Compositing final video and animations...")
        final_video_path = compose_video(state, project_dir / "final_output.mp4")
        if progress_cb: progress_cb(100, "Video compositing complete")
        state.video.scene_images = scene_images
        state.video.scene_clips = [final_video_path]
        state.video.subtitle_file = subtitle_file
        state.video.final_video_path = final_video_path
        state.video.image_provider = image_providers[0] if image_providers else "unknown"
        state.video.image_providers = image_providers
        state.artifacts.scene_images = scene_images
        state.artifacts.subtitle_file = subtitle_file
        state.artifacts.final_video = final_video_path
        return state
