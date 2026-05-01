from pathlib import Path

import pytest

from agents.video_agent.agent import VideoAgent
from shared.schemas.project_state import ProjectState, SceneState


def _sample_video_state() -> ProjectState:
    return ProjectState(
        project_id="proj_video_test",
        prompt="A paper boat crosses a neon canal.",
        scenes=[
            SceneState(
                scene_id="scene_1",
                title="One",
                duration_sec=12,
                narration="Intro",
                dialogue=[],
                visual_prompt="Neon canal at night",
                mood="curious",
                subtitle_lines=[],
                audio_start_ms=0,
                audio_end_ms=1500,
            ),
            SceneState(
                scene_id="scene_2",
                title="Two",
                duration_sec=12,
                narration="Outro",
                dialogue=[],
                visual_prompt="Boat reaches the lights",
                mood="uplifting",
                subtitle_lines=[],
                audio_start_ms=1500,
                audio_end_ms=3200,
            ),
        ],
    )


def test_video_agent_generates_artifacts(monkeypatch):
    state = _sample_video_state()

    def fake_generate(self, prompt, output_path, title):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"img")
        provider = "pollinations" if "One" in title else "openai"
        return str(output_path), provider

    def fake_generate_video(self, prompt, output_path, title):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"vid")
        return str(output_path), "kaggle-cogvideo"

    def fake_compose_video(current_state, output_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake mp4")
        return str(output_path)

    monkeypatch.setattr("agents.video_agent.agent.compose_video", fake_compose_video)
    monkeypatch.setattr("agents.video_agent.agent.write_subtitles", lambda *args, **kwargs: None)
    monkeypatch.setattr("agents.video_agent.agent.SceneImageGenerator.generate", fake_generate)
    monkeypatch.setattr("agents.video_agent.agent.SceneImageGenerator.generate_video", fake_generate_video)
    monkeypatch.setenv("KAGGLE_API_URL", "")

    updated = VideoAgent().run(state)

    assert len(updated.video.scene_images) == 2
    assert updated.video.image_providers == ["pollinations", "openai"]
    assert updated.scenes[0].image_status == "generated"
    assert updated.video.final_video_path
    assert Path(updated.video.final_video_path).exists()


def test_video_agent_raises_when_all_image_providers_fail(monkeypatch):
    state = _sample_video_state()

    def fake_generate(self, prompt, output_path, title):
        raise RuntimeError("all providers failed")

    monkeypatch.setattr("agents.video_agent.agent.SceneImageGenerator.generate", fake_generate)
    monkeypatch.setenv("KAGGLE_API_URL", "")

    with pytest.raises(RuntimeError):
        VideoAgent().run(state)

    assert state.scenes[0].image_status == "failed"
