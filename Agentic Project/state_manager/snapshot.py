from __future__ import annotations

from pathlib import Path

from shared.schemas.project_state import ProjectState, VersionRecord
from shared.utils.files import write_json
from shared.utils.paths import STATE_ROOT


def save_snapshot(state: ProjectState, version: VersionRecord) -> Path:
    snapshot_path = STATE_ROOT / state.project_id / f"{version.version_id}.json"
    write_json(snapshot_path, state.model_dump(mode="json"))
    return snapshot_path
