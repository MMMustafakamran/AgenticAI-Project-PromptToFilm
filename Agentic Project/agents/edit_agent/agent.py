from __future__ import annotations

from agents.edit_agent.executor import EditExecutor
from agents.edit_agent.intent_classifier import classify_edit
from agents.edit_agent.planner import rerun_plan_for_target
from shared.schemas.project_state import ProjectState


class EditAgent:
    def __init__(self) -> None:
        self.executor = EditExecutor()

    def prepare(self, state: ProjectState, command: str) -> tuple[ProjectState, list[str], str, str]:
        intent, target = classify_edit(command)
        updated_state = self.executor.apply(state, command, intent, target)
        return updated_state, rerun_plan_for_target(target), intent, target
