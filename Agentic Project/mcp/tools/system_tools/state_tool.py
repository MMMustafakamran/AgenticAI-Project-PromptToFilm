from __future__ import annotations

from shared.schemas.project_state import ProjectState
from state_manager.state_manager import StateManager


class StateTool:
    def __init__(self, manager: StateManager | None = None) -> None:
        self.manager = manager or StateManager()

    def load(self, project_id: str) -> ProjectState:
        return self.manager.load_state(project_id)

    def save(self, state: ProjectState) -> None:
        self.manager.save_state(state)
