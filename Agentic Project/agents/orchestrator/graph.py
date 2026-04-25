from __future__ import annotations

from collections.abc import Callable

from shared.schemas.project_state import ProjectState


from typing import Any

PhaseRunner = Callable[..., ProjectState]


class WorkflowGraph:
    def __init__(self, story: PhaseRunner, audio: PhaseRunner, video: PhaseRunner) -> None:
        self._phase_map = {
            "story": story,
            "audio": audio,
            "video": video,
        }

    def run_phase(self, phase: str, state: ProjectState, progress_cb: Callable[[int, str], None] | None = None) -> ProjectState:
        return self._phase_map[phase](state, progress_cb=progress_cb)
