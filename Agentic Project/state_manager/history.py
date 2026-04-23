from __future__ import annotations

from shared.schemas.project_state import ProjectState


def previous_version_id(state: ProjectState) -> str | None:
    if len(state.versions) < 2:
        return None
    return state.versions[-2].version_id
