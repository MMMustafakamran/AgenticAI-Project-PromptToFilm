from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DialogueLine(BaseModel):
    character_id: str
    character_name: str
    text: str
    emotion: str = "neutral"


class SceneState(BaseModel):
    scene_id: str
    title: str
    duration_sec: int = Field(ge=8, le=15)
    narration: str
    dialogue: list[DialogueLine]
    visual_prompt: str
    mood: str
    subtitle_lines: list[str]
    image_path: str | None = None
    image_provider: str | None = None
    image_status: Literal["pending", "generated", "failed"] = "pending"
    image_error: str | None = None
    audio_start_ms: int | None = None
    audio_end_ms: int | None = None
    clip_path: str | None = None


class CharacterState(BaseModel):
    character_id: str
    name: str
    role: str
    voice_style: str
    visual_description: str
    voice_name: str | None = None


class DialogueTrack(BaseModel):
    scene_id: str
    line_index: int
    character_id: str
    text: str
    file_path: str
    duration_ms: int
    provider: str = "unknown"
    voice_name: str | None = None


class TimingManifestEntry(BaseModel):
    scene_id: str
    audio_file: str
    start_ms: int
    end_ms: int
    text: str
    character_name: str
    provider: str = "unknown"
    voice_name: str | None = None


class AudioState(BaseModel):
    dialogue_tracks: list[DialogueTrack] = Field(default_factory=list)
    bgm_track: str | None = None
    bgm_volume: float = 0.2
    timing_manifest: list[TimingManifestEntry] = Field(default_factory=list)
    final_audio_path: str | None = None
    provider: str = "pending"
    providers_used: list[str] = Field(default_factory=list)


class VideoState(BaseModel):
    scene_images: list[str] = Field(default_factory=list)
    scene_clips: list[str] = Field(default_factory=list)
    subtitle_file: str | None = None
    final_video_path: str | None = None
    subtitles_enabled: bool = True
    image_provider: str = "pending"
    image_providers: list[str] = Field(default_factory=list)


class EditRecord(BaseModel):
    command: str
    target: Literal["script", "audio", "video_frame", "video"]
    intent: str
    target_label: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ArtifactIndex(BaseModel):
    story_json: str | None = None
    timing_manifest_json: str | None = None
    subtitle_file: str | None = None
    final_audio: str | None = None
    final_video: str | None = None
    scene_images: list[str] = Field(default_factory=list)


class VersionRecord(BaseModel):
    version_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    trigger: str
    changed_phase: str
    artifact_paths: list[str] = Field(default_factory=list)
    parent_version: str | None = None
    snapshot_path: str | None = None


class StoryState(BaseModel):
    title: str = ""
    logline: str = ""
    tone: str = "hopeful cinematic"
    summary: str = ""
    provider: str = "fallback"


class ProjectState(BaseModel):
    project_id: str
    prompt: str
    num_scenes: int = 2
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    current_phase: Literal["idle", "story", "audio", "video", "edit"] = "idle"
    current_version: str | None = None
    story: StoryState = Field(default_factory=StoryState)
    characters: list[CharacterState] = Field(default_factory=list)
    scenes: list[SceneState] = Field(default_factory=list)
    audio: AudioState = Field(default_factory=AudioState)
    video: VideoState = Field(default_factory=VideoState)
    edits: list[EditRecord] = Field(default_factory=list)
    artifacts: ArtifactIndex = Field(default_factory=ArtifactIndex)
    versions: list[VersionRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_error: str | None = None

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()

    def output_dir(self, root: Path) -> Path:
        return root / self.project_id
