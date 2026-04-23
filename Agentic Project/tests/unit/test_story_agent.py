from agents.story_agent.agent import StoryAgent
from shared.schemas.project_state import ProjectState


def test_story_agent_returns_two_scenes():
    agent = StoryAgent()
    state = ProjectState(project_id="proj_story_test", prompt="A child discovers a tiny moon inside a lantern.")

    updated = agent.run(state)

    assert len(updated.scenes) == 2
    assert 1 <= len(updated.characters) <= 3
    assert all(scene.duration_sec >= 8 for scene in updated.scenes)
