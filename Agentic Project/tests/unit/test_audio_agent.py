from agents.audio_agent.agent import AudioAgent
from agents.story_agent.agent import StoryAgent
from shared.schemas.project_state import ProjectState


def test_audio_agent_builds_timing_manifest():
    story_state = StoryAgent().run(ProjectState(project_id="proj_audio_test", prompt="A mechanic repairs a singing bridge."))

    updated = AudioAgent().run(story_state)

    assert updated.audio.final_audio_path
    assert len(updated.audio.dialogue_tracks) == len(updated.audio.timing_manifest)
    assert all(entry.end_ms > entry.start_ms for entry in updated.audio.timing_manifest)
