# Agentic AI Shorts MVP

This project implements a local-first, cloud-ready MVP for the semester brief: one prompt goes through story generation, dialogue audio, scene image generation, video composition, and an edit agent with undo/version history.

## What is implemented

- FastAPI backend with project creation, phase reruns, edits, undo, artifact endpoints, and SSE progress events
- Shared Pydantic project state with version snapshots
- Story, audio, video, and edit agents
- Pollinations-first image generation with local placeholder fallback
- Cloud-ready TTS hook with synthetic fallback when no API key is set
- React workflow UI for prompt input, phase reruns, version history, edits, and video preview
- Unit and integration tests for core MVP behavior

## Stack

- Backend: FastAPI, Pydantic, SQLite, requests
- Media: Pillow, MoviePy
- Frontend: React + Vite
- Providers:
  - Story: Gemini if configured, otherwise deterministic fallback
  - TTS: ElevenLabs if configured, otherwise synthetic fallback
  - Image: Pollinations Flux if reachable, otherwise generated placeholder frames

## Setup

### Backend

```bash
cd "Agentic Project"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

Optional environment variables:

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
POLLINATIONS_MODEL=flux
```

### Frontend

```bash
cd "Agentic Project/frontend"
npm install
npm run dev
```

If needed, point the frontend to another backend URL:

```env
VITE_API_BASE=http://127.0.0.1:8000
```

## Core API

- `POST /projects`
- `GET /projects/{id}`
- `POST /projects/{id}/run-phase/{phase}`
- `POST /projects/{id}/edit`
- `POST /projects/{id}/undo`
- `GET /projects/{id}/artifacts`
- `GET /projects/{id}/events`

## Demo-ready edit commands

- `Change voice tone`
- `Make scene darker`
- `Remove subtitles`
- `Speed up scene`
- `Regenerate script`

## Notes

- The MVP is intentionally tuned for a 2-scene, 20-30 second short film.
- Local fallbacks keep the demo usable even when cloud provider keys are missing.
- For the strongest final submission, configure at least one cloud LLM and one cloud TTS provider before recording the demo.
