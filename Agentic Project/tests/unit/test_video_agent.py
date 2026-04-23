from pathlib import Path

from agents.audio_agent.agent import AudioAgent
from agents.story_agent.agent import StoryAgent
from agents.video_agent.agent import VideoAgent
from shared.schemas.project_state import ProjectState


def test_video_agent_generates_artifacts(monkeypatch):
    state = StoryAgent().run(ProjectState(project_id="proj_video_test", prompt="A paper boat crosses a neon canal."))
    state = AudioAgent().run(state)

    def fake_compose_video(current_state, output_path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake mp4")
        return str(output_path)

    monkeypatch.setattr("agents.video_agent.agent.compose_video", fake_compose_video)

    updated = VideoAgent().run(state)

    assert len(updated.video.scene_images) == 2
    assert updated.video.final_video_path
    assert Path(updated.video.final_video_path).exists()
