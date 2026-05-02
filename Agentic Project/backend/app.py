from __future__ import annotations

import asyncio
import json
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.orchestrator.workflow import WorkflowService
from shared.utils.paths import OUTPUTS_ROOT


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
LOGGER = logging.getLogger(__name__)


app = FastAPI(title="Agentic AI Shorts MVP", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

workflow = WorkflowService()
app.mount("/artifacts", StaticFiles(directory=str(OUTPUTS_ROOT)), name="artifacts")


class CreateProjectRequest(BaseModel):
    prompt: str
    num_scenes: int = 2


class EditRequest(BaseModel):
    command: str


class UndoRequest(BaseModel):
    version_id: str | None = None


@app.get("/")
async def root() -> dict:
    return {"name": "Agentic AI Shorts MVP", "status": "ok"}


@app.get("/projects")
async def list_projects():
    return workflow.state_manager.list_projects()


@app.post("/projects")
async def create_project(payload: CreateProjectRequest):
    state = workflow.state_manager.create_project(payload.prompt, payload.num_scenes)
    LOGGER.info("Created project %s", state.project_id)
    asyncio.create_task(workflow.run_full_project(state.project_id))
    return workflow.state_manager.load_state(state.project_id).model_dump(mode="json")


@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    try:
        state = workflow.state_manager.load_state(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    return state.model_dump(mode="json")


@app.post("/projects/{project_id}/run-phase/{phase}")
async def rerun_phase(project_id: str, phase: str):
    if phase not in {"story", "audio", "video"}:
        raise HTTPException(status_code=400, detail="Unsupported phase")
    try:
        await workflow.run_phase(project_id, phase, trigger="manual")
        return workflow.state_manager.load_state(project_id).model_dump(mode="json")
    except Exception as exc:
        LOGGER.exception("Manual rerun failed for project %s phase %s", project_id, phase)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/projects/{project_id}/edit")
async def apply_edit(project_id: str, payload: EditRequest):
    try:
        state = await workflow.apply_edit(project_id, payload.command)
        return state.model_dump(mode="json")
    except Exception as exc:
        LOGGER.exception("Edit endpoint failed for project %s", project_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/projects/{project_id}/undo")
async def undo(project_id: str, payload: UndoRequest):
    state = workflow.undo(project_id, payload.version_id)
    return state.model_dump(mode="json")


@app.get("/projects/{project_id}/artifacts")
async def get_artifacts(project_id: str):
    state = workflow.state_manager.load_state(project_id)
    return state.artifacts.model_dump(mode="json")


@app.get("/projects/{project_id}/events")
async def stream_events(project_id: str):
    queue = workflow.broker.subscribe(project_id)

    async def event_stream():
        try:
            yield "data: " + json.dumps({"type": "hello", "project_id": project_id}) + "\n\n"
            while True:
                event = await queue.get()
                yield "data: " + json.dumps(event) + "\n\n"
        finally:
            workflow.broker.unsubscribe(project_id, queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
