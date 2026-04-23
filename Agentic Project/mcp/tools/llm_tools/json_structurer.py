from __future__ import annotations

from shared.schemas.project_state import ProjectState


def validate_project_state(payload: dict) -> ProjectState:
    return ProjectState.model_validate(payload)
