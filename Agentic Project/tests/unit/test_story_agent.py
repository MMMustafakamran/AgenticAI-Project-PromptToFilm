from agents.story_agent.agent import StoryAgent
from shared.schemas.project_state import ProjectState


def test_story_agent_returns_two_scenes(monkeypatch):
    agent = StoryAgent()
    state = ProjectState(project_id="proj_story_test", prompt="A child discovers a tiny moon inside a lantern.")
    payload = agent.generator.fallback_story_payload(state.prompt)
    monkeypatch.setattr(agent.generator, "generate_story_payload", lambda prompt: (payload, "fallback"))

    updated = agent.run(state)

    assert len(updated.scenes) == 2
    assert 1 <= len(updated.characters) <= 3
    assert all(scene.duration_sec >= 8 for scene in updated.scenes)


def test_story_agent_records_provider(monkeypatch):
    agent = StoryAgent()
    state = ProjectState(project_id="proj_story_provider", prompt="A lighthouse learns to sing.")

    payload = agent.generator.fallback_story_payload(state.prompt)
    monkeypatch.setattr(agent.generator, "generate_story_payload", lambda prompt: (payload, "gemini-2.0-flash"))

    updated = agent.run(state)

    assert updated.story.provider == "gemini-2.0-flash"
