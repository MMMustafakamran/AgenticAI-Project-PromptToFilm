from pathlib import Path

from fastapi.testclient import TestClient

import backend.app as backend_module


def test_healthcheck():
    client = TestClient(backend_module.app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_projects_list_and_create_project(monkeypatch):
    client = TestClient(backend_module.app)

    async def fake_run_full_project(project_id: str):
        state = backend_module.workflow.state_manager.load_state(project_id)
        state.status = "completed"
        backend_module.workflow.state_manager.save_state(state)

    monkeypatch.setattr(backend_module.workflow, "run_full_project", fake_run_full_project)

    response = client.post("/projects", json={"prompt": "A lantern opens a sky bridge."})
    assert response.status_code == 200
    project_id = response.json()["project_id"]

    listing = client.get("/projects")
    assert listing.status_code == 200
    assert any(project["project_id"] == project_id for project in listing.json())


def test_artifacts_edit_and_undo_endpoints(monkeypatch):
    client = TestClient(backend_module.app)
    state = backend_module.workflow.state_manager.create_project("A violinist bends moonlight into a map.")
    project_dir = Path(backend_module.OUTPUTS_ROOT) / state.project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    state.status = "completed"
    state.artifacts.story_json = str(project_dir / "story.json")
    Path(state.artifacts.story_json).write_text("{}", encoding="utf-8")
    backend_module.workflow.state_manager.save_state(state)
    backend_module.workflow.state_manager.save_version(state, trigger="seed", changed_phase="story", artifact_paths=[state.artifacts.story_json])

    async def fake_apply_edit(project_id: str, command: str):
        current = backend_module.workflow.state_manager.load_state(project_id)
        current.prompt = f"{current.prompt}\n{command}"
        backend_module.workflow.state_manager.save_state(current)
        backend_module.workflow.state_manager.save_version(current, trigger="edit:test", changed_phase="edit", artifact_paths=[current.artifacts.story_json])
        return current

    monkeypatch.setattr(backend_module.workflow, "apply_edit", fake_apply_edit)

    artifacts = client.get(f"/projects/{state.project_id}/artifacts")
    assert artifacts.status_code == 200
    assert artifacts.json()["story_json"]

    edited = client.post(f"/projects/{state.project_id}/edit", json={"command": "Regenerate script"})
    assert edited.status_code == 200

    reverted = client.post(f"/projects/{state.project_id}/undo", json={})
    assert reverted.status_code == 200
    assert reverted.json()["current_version"] == "v1"
