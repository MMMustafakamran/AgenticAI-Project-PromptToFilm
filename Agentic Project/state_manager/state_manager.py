from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from shared.schemas.project_state import ProjectState, VersionRecord
from shared.utils.files import read_json, write_json
from shared.utils.paths import OUTPUTS_ROOT, ensure_directories
from state_manager.snapshot import save_snapshot
from state_manager.storage import SQLiteStorage


class StateManager:
    def __init__(self, storage: SQLiteStorage | None = None) -> None:
        ensure_directories()
        self.storage = storage or SQLiteStorage()

    def create_project(self, prompt: str) -> ProjectState:
        project_id = f"proj_{uuid.uuid4().hex[:10]}"
        state = ProjectState(project_id=project_id, prompt=prompt)
        self.save_state(state)
        return state

    def state_path(self, project_id: str) -> Path:
        return OUTPUTS_ROOT / project_id / "project_state.json"

    def save_state(self, state: ProjectState) -> None:
        state.touch()
        path = self.state_path(state.project_id)
        write_json(path, state.model_dump(mode="json"))
        with self.storage.connect() as connection:
            connection.execute(
                """
                INSERT INTO projects(project_id, prompt, status, current_phase, current_version, state_path, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    prompt=excluded.prompt,
                    status=excluded.status,
                    current_phase=excluded.current_phase,
                    current_version=excluded.current_version,
                    state_path=excluded.state_path,
                    updated_at=excluded.updated_at
                """,
                (
                    state.project_id,
                    state.prompt,
                    state.status,
                    state.current_phase,
                    state.current_version,
                    str(path),
                    state.updated_at.isoformat(),
                ),
            )

    def load_state(self, project_id: str) -> ProjectState:
        payload = read_json(self.state_path(project_id))
        return ProjectState.model_validate(payload)

    def save_version(self, state: ProjectState, trigger: str, changed_phase: str, artifact_paths: list[str]) -> VersionRecord:
        parent_version = state.current_version
        version = VersionRecord(
            version_id=f"v{len(state.versions) + 1}",
            trigger=trigger,
            changed_phase=changed_phase,
            artifact_paths=artifact_paths,
            parent_version=parent_version,
        )
        state.versions.append(version)
        state.current_version = version.version_id
        snapshot_path = save_snapshot(state, version)
        version.snapshot_path = str(snapshot_path)
        self.save_state(state)
        with self.storage.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO versions(version_id, project_id, created_at, trigger_source, changed_phase, artifact_paths, parent_version, snapshot_path)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version.version_id,
                    state.project_id,
                    version.created_at.isoformat(),
                    version.trigger,
                    version.changed_phase,
                    json.dumps(version.artifact_paths),
                    version.parent_version,
                    version.snapshot_path,
                ),
            )
        return version

    def revert_to_version(self, project_id: str, version_id: str | None = None) -> ProjectState:
        current_state = self.load_state(project_id)
        if not current_state.versions:
            return current_state
        target = None
        if version_id is None and len(current_state.versions) >= 2:
            version_id = current_state.versions[-2].version_id
        for version in current_state.versions:
            if version.version_id == version_id:
                target = version
                break
        if target is None or not target.snapshot_path:
            return current_state
        restored = ProjectState.model_validate(read_json(Path(target.snapshot_path)))
        restored.versions = current_state.versions
        restored.current_version = target.version_id
        restored.status = "completed"
        restored.current_phase = "idle"
        self.save_state(restored)
        return restored
