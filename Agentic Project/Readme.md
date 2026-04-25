# Agentic AI Shorts MVP

This project implements a local-first, cloud-ready MVP for the semester brief: one prompt goes through story generation, dialogue audio, scene image generation, video composition, and an edit agent with undo/version history.

## What is implemented

- FastAPI backend with project creation, phase reruns, edits, undo, artifact endpoints, and SSE progress events
- Shared Pydantic project state with version snapshots
- Story, audio, video, and edit agents
- Pollinations-first image generation with OpenAI Images backup and explicit failure reporting
- Edge TTS first with ElevenLabs backup for cloud voice generation
- React workflow UI for prompt input, phase reruns, version history, edits, and video preview
- Unit and integration tests for core MVP behavior

## Stack

- Backend: FastAPI, Pydantic, SQLite, requests
- Media: Pillow, MoviePy
- Frontend: React + Vite
- Providers:
  - Story: Gemini if configured and valid, otherwise deterministic fallback
  - TTS: Edge TTS first, ElevenLabs backup
  - Image: Pollinations Flux first, OpenAI Images backup

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
GEMINI_FALLBACK_MODELS=gemini-2.5-flash-lite,gemini-2.0-flash,gemini-2.0-flash-lite
EDGE_TTS_DEFAULT_VOICE=en-US-JennyNeural
EDGE_TTS_VOICE_MAP={"Aanya":"en-US-JennyNeural","Rafi":"en-US-GuyNeural"}
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
POLLINATIONS_MODEL=flux
OPENAI_API_KEY=
OPENAI_IMAGE_MODEL=gpt-image-1
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
- Heavy local inference is intentionally avoided so the project can run on slower laptops.
- If both remote image providers fail for a scene, the run fails clearly instead of producing placeholder frames.
- For the strongest final submission, configure Gemini, OpenAI Images, and ElevenLabs before recording the demo.
