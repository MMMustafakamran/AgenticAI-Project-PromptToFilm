from __future__ import annotations

import logging

from shared.utils.files import write_json
from shared.utils.paths import OUTPUTS_ROOT
from state_manager.state_manager import StateManager
from agents.audio_agent.agent import AudioAgent
from agents.edit_agent.agent import EditAgent
from agents.orchestrator.graph import WorkflowGraph
from agents.orchestrator.state import EventBroker
from agents.story_agent.agent import StoryAgent
from agents.video_agent.agent import VideoAgent


LOGGER = logging.getLogger(__name__)


class WorkflowService:
    def __init__(self, state_manager: StateManager | None = None, broker: EventBroker | None = None) -> None:
        self.state_manager = state_manager or StateManager()
        self.broker = broker or EventBroker()
        self.story_agent = StoryAgent()
        self.audio_agent = AudioAgent()
        self.video_agent = VideoAgent()
        self.edit_agent = EditAgent()
        self.graph = WorkflowGraph(self.story_agent.run, self.audio_agent.run, self.video_agent.run)

    async def run_full_project(self, project_id: str) -> None:
        state = self.state_manager.load_state(project_id)
        state.status = "running"
        self.state_manager.save_state(state)
        try:
            for phase in ("story", "audio", "video"):
                state = await self.run_phase(project_id, phase, trigger="pipeline")
            state.status = "completed"
            state.current_phase = "idle"
            self.state_manager.save_state(state)
            await self.broker.publish(project_id, {"type": "status", "status": "completed"})
        except Exception as exc:
            LOGGER.exception("Pipeline failed for project %s", project_id)
            state.status = "failed"
            state.last_error = str(exc)
            state.current_phase = "idle"
            self.state_manager.save_state(state)
            await self.broker.publish(project_id, {"type": "status", "status": "failed", "error": str(exc)})

    async def run_phase(self, project_id: str, phase: str, trigger: str = "manual"):
        state = self.state_manager.load_state(project_id)
        state.current_phase = phase
        state.status = "running"
        self._invalidate_downstream(state, phase)
        self.state_manager.save_state(state)
        await self.broker.publish(project_id, {"type": "phase", "phase": phase, "status": "started"})
        try:
            updated = self.graph.run_phase(phase, state)
            updated.current_phase = phase
            updated.status = "running"
            updated.last_error = None
            self._persist_artifacts(updated)
            artifact_paths = self._artifact_paths(updated)
            self.state_manager.save_state(updated)
            self.state_manager.save_version(updated, trigger=trigger, changed_phase=phase, artifact_paths=artifact_paths)
            await self.broker.publish(project_id, {"type": "phase", "phase": phase, "status": "completed"})
            return self.state_manager.load_state(project_id)
        except Exception as exc:
            LOGGER.exception("Phase %s failed for project %s", phase, project_id)
            state.status = "failed"
            state.current_phase = "idle"
            state.last_error = f"{phase} phase failed: {exc}"
            self.state_manager.save_state(state)
            await self.broker.publish(project_id, {"type": "phase", "phase": phase, "status": "failed", "error": str(exc)})
            raise

    async def apply_edit(self, project_id: str, command: str):
        state = self.state_manager.load_state(project_id)
        state.current_phase = "edit"
        state.status = "running"
        self.state_manager.save_state(state)
        try:
            updated_state, phases, intent, target = self.edit_agent.prepare(state, command)
            self.state_manager.save_state(updated_state)
            for phase in phases:
                updated_state = await self.run_phase(project_id, phase, trigger=f"edit:{intent}")
            self.state_manager.save_version(
                updated_state,
                trigger=f"edit:{intent}",
                changed_phase="edit",
                artifact_paths=self._artifact_paths(updated_state),
            )
            updated_state.status = "completed"
            updated_state.current_phase = "idle"
            updated_state.last_error = None
            self.state_manager.save_state(updated_state)
            await self.broker.publish(project_id, {"type": "edit", "intent": intent, "target": target, "status": "completed"})
            return updated_state
        except Exception as exc:
            LOGGER.exception("Edit command failed for project %s: %s", project_id, command)
            state.status = "failed"
            state.current_phase = "idle"
            state.last_error = f"Edit failed: {exc}"
            self.state_manager.save_state(state)
            await self.broker.publish(project_id, {"type": "edit", "status": "failed", "error": str(exc)})
            raise

    def undo(self, project_id: str, version_id: str | None = None):
        return self.state_manager.revert_to_version(project_id, version_id)

    def _persist_artifacts(self, state) -> None:
        output_dir = OUTPUTS_ROOT / state.project_id
        write_json(output_dir / "story.json", state.story.model_dump(mode="json"))
        write_json(output_dir / "timing_manifest.json", [entry.model_dump(mode="json") for entry in state.audio.timing_manifest])
        state.artifacts.story_json = str(output_dir / "story.json")
        state.artifacts.timing_manifest_json = str(output_dir / "timing_manifest.json")

    def _artifact_paths(self, state) -> list[str]:
        paths = [
            state.artifacts.story_json,
            state.artifacts.timing_manifest_json,
            state.artifacts.subtitle_file,
            state.artifacts.final_audio,
            state.artifacts.final_video,
            *state.artifacts.scene_images,
        ]
        return [path for path in paths if path]

    def _invalidate_downstream(self, state, phase: str) -> None:
        if phase == "story":
            for scene in state.scenes:
                scene.audio_start_ms = None
                scene.audio_end_ms = None
                scene.image_path = None
                scene.image_provider = None
                scene.image_status = "pending"
                scene.image_error = None
                scene.clip_path = None
            for character in state.characters:
                character.voice_name = None
            state.audio.dialogue_tracks = []
            state.audio.timing_manifest = []
            state.audio.bgm_track = None
            state.audio.final_audio_path = None
            state.audio.provider = "pending"
            state.audio.providers_used = []
            state.video.scene_images = []
            state.video.scene_clips = []
            state.video.subtitle_file = None
            state.video.final_video_path = None
            state.video.image_provider = "pending"
            state.video.image_providers = []
            state.artifacts.timing_manifest_json = None
            state.artifacts.final_audio = None
            state.artifacts.subtitle_file = None
            state.artifacts.final_video = None
            state.artifacts.scene_images = []
        elif phase == "audio":
            for scene in state.scenes:
                scene.audio_start_ms = None
                scene.audio_end_ms = None
                scene.clip_path = None
            state.video.scene_images = []
            state.video.scene_clips = []
            state.video.subtitle_file = None
            state.video.final_video_path = None
            state.video.image_provider = "pending"
            state.video.image_providers = []
            state.artifacts.final_video = None
            state.artifacts.subtitle_file = None
        elif phase == "video":
            for scene in state.scenes:
                scene.clip_path = None
