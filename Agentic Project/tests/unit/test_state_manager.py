from state_manager.state_manager import StateManager


def test_revert_preserves_version_history():
    manager = StateManager()
    state = manager.create_project("A dancer follows a comet through the city.")

    state.prompt = "Prompt version one"
    manager.save_state(state)
    manager.save_version(state, trigger="story", changed_phase="story", artifact_paths=[])

    state = manager.load_state(state.project_id)
    state.prompt = "Prompt version two"
    manager.save_state(state)
    manager.save_version(state, trigger="audio", changed_phase="audio", artifact_paths=[])

    restored = manager.revert_to_version(state.project_id, "v1")

    assert restored.current_version == "v1"
    assert len(restored.versions) == 2
