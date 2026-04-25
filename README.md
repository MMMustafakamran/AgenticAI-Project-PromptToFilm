# Agentic AI Final Project

This repository contains the semester project deliverables for an agentic AI short-film generator. The implementation lives in [Agentic Project/Readme.md](./Agentic%20Project/Readme.md) and includes:

- Story generation with Gemini-first validated structured output
- Edge TTS primary audio generation with ElevenLabs backup
- Pollinations primary image generation with OpenAI Images backup
- FastAPI backend, React frontend, edit agent, undo/version history, and sample generated artifacts
- Unit and integration tests for the main pipeline paths

## Repository Layout

- `Agentic Project/` application source code
- `Agentic Project/tests/` unit and integration tests
- `Agentic Project/data/outputs/` generated sample artifacts
- `Agentic AI Final Project - 2026.md` assignment brief

## Quick Start

Backend:

```bash
cd "Agentic Project"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

Frontend:

```bash
cd "Agentic Project/frontend"
npm install
npm run dev
```

## Key Environment Variables

```env
GEMINI_API_KEY=
EDGE_TTS_DEFAULT_VOICE=en-US-JennyNeural
EDGE_TTS_VOICE_MAP={"Aanya":"en-US-JennyNeural","Rafi":"en-US-GuyNeural"}
ELEVENLABS_API_KEY=
OPENAI_API_KEY=
POLLINATIONS_MODEL=flux
```

## Notes for Grading/Demo

- The pipeline is designed to stay lightweight on slower laptops by avoiding heavy local model inference.
- If remote image generation fails on all configured providers, the system now reports a clear failure instead of creating placeholder frames.
- Full project setup, API routes, and workflow details are documented in [Agentic Project/Readme.md](./Agentic%20Project/Readme.md).
