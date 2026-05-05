# 🎬 Agentic AI Video Studio
### Prompt → Script → Voice → Video — End-to-End Agentic Pipeline

> **NUCES Islamabad | Agentic AI — Semester Project 2026**  
> Course: Agentic AI | Group Size: 4 Members | Project Type: Full-Stack AI System

---

## 📌 Project Overview

This system accepts a single natural-language prompt and autonomously produces a complete short animated video — including story, dialogue, character voices, visual scenes, and a final composited MP4 — with **zero manual creative intervention**.

The pipeline is composed of **5 modular phases**, all unified by a shared JSON state schema and a real-time web interface:

| Phase | Description |
|-------|-------------|
| **Phase 1** | Story & Script Generation (LLM Agent) |
| **Phase 2** | Audio Generation & TTS (Voice Synthesis) |
| **Phase 3** | Video Composition (Image Gen + MoviePy) |
| **Phase 4** | Full-Stack Web Interface (React + FastAPI) |
| **Phase 5** | Intelligent Edit Agent + Undo/Version System |

---

## 🗂️ Project Structure

```
Agentic Project/
├── agents/
│   ├── story_agent/       # Phase 1: LLM story & script generation
│   ├── audio_agent/       # Phase 2: TTS, voice synthesis, BGM
│   ├── video_agent/       # Phase 3: Image generation & video compositing
│   ├── edit_agent/        # Phase 5: Intent classification & edit execution
│   │   ├── intent_classifier.py
│   │   ├── executor.py
│   │   ├── planner.py
│   │   └── tests/
│   └── orchestrator/      # Central pipeline coordinator (WorkflowService)
├── mcp/
│   └── tools/
│       ├── llm_tools/     # LLM text generation (Groq / Gemini / Anthropic)
│       ├── audio_tools/   # TTS (Edge-TTS) + BGM synthesis
│       ├── video_tools/   # Compositor (MoviePy), subtitle overlay
│       └── vision_tools/  # Image editing filters (PIL)
├── shared/
│   ├── schemas/           # Pydantic schemas — shared ProjectState
│   └── utils/             # Path helpers, file I/O
├── state_manager/         # SQLite-backed state + snapshot/undo system
├── backend/               # FastAPI + Uvicorn REST API + SSE events
├── frontend/              # React + Vite web application
├── data/                  # SQLite database (project_state.db)
├── tests/                 # Unit tests for all phases
├── requirements.txt
├── start-proj.ps1         # One-click startup script (Windows)
└── stop-proj.ps1
```

---

## ⚙️ Technology Stack

| Layer | Technology Used |
|-------|----------------|
| **LLM / Agents** | Groq API (`llama-3.1-8b-instant`), Gemini API, Anthropic Claude |
| **TTS** | Microsoft Edge-TTS (local, free) |
| **Image Generation** | Pollinations AI (API), Gemini Vision |
| **BGM** | Procedural wave synthesis (custom, no external API) |
| **Video Composition** | MoviePy 2.x + PIL (Pillow) |
| **Backend** | FastAPI + Uvicorn |
| **Frontend** | React 18 + Vite + TailwindCSS |
| **Real-time Events** | Server-Sent Events (SSE) |
| **State Store** | SQLite (`state_manager/storage.py`) + file-based JSON snapshots |
| **Schema Validation** | Pydantic v2 |

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- Windows (PowerShell) or Linux/macOS

### 1. Clone the Repository
```bash
git clone https://github.com/MMMustafakamran/AgenticAI-Project-PromptToFilm.git
cd "AgenticAI-Project-PromptToFilm/Agentic Project"
```

### 2. Configure Environment Variables
Create a `.env` file in the project root:
```env
GROQ_API=your_groq_api_key
GEMINI_API=your_gemini_api_key
ANTHROPIC_API=your_anthropic_api_key   # optional
```

### 3. Install Python Dependencies
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies
```bash
cd frontend
npm install
```

### 5. Run the Application

**Windows (recommended):**
```powershell
.\start-proj.ps1
```

**Manual startup:**
```bash
# Terminal 1 — Backend
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open your browser at: **http://localhost:5173**

---

## 🧠 Phase 1 — Story & Script Generation

**Agent:** `agents/story_agent/agent.py`  
**Tool:** `mcp/tools/llm_tools/text_generator.py`

The Story Agent takes a free-form natural language prompt and uses an LLM to produce a fully structured story with characters, scenes, and dialogue.

**Features:**
- Calls Groq (LLaMA 3.1), Gemini, or Anthropic Claude in order of availability
- Auto-retries up to 3 times with corrective feedback if JSON validation fails
- Enforces narrative constraints via `story_agent/planner.py`
- Outputs a validated Pydantic `ProjectState` object with:
  - `story` — title, genre, tone, synopsis
  - `characters[]` — name, role, voice style, visual description
  - `scenes[]` — title, narration, dialogue lines, visual prompt, mood, subtitles

**Output Artifact:** `data/outputs/<project_id>/story.json`

---

## 🎙️ Phase 2 — Audio Generation & Integration

**Agent:** `agents/audio_agent/agent.py`  
**Tools:** `mcp/tools/audio_tools/`

The Audio Agent synthesizes all voice lines and background music, then assembles a timing manifest for A/V sync.

**Features:**
- **TTS (Text-to-Speech):** Uses Microsoft Edge-TTS to generate per-character voice audio with character-specific voice parameters (tone, style, emotion)
- **Background Music (BGM):** Procedural wave synthesis — generates mood-appropriate background tracks using chord overtones, LFO modulation, and smooth 2-second fade-in/fade-out
- **Timing Manifest:** Produces `timing_manifest.json` with `{ scene_id, audio_file, start_ms, end_ms }` for each dialogue line — consumed by Phase 3

**Output Artifacts:** `.wav` audio files + `timing_manifest.json`

---

## 🎥 Phase 3 — Video Generation & Composition

**Agent:** `agents/video_agent/agent.py`  
**Tools:** `mcp/tools/video_tools/compositor_tool.py`, `mcp/tools/vision_tools/image_edit_tool.py`

The Video Agent generates per-scene visuals, applies animations, syncs audio, and exports the final MP4.

**Features:**
- **Image Generation:** Calls Pollinations AI or Gemini to generate scene images from visual prompts
- **Dynamic Visual Effects (Ken Burns style):**
  - Zoom In / Zoom Out effects based on scene's `visual_prompt` keywords
  - Brightness grading: darkens (`dark`), brightens (`bright`, `vivid`) scenes automatically
- **Image Filters (PIL-based):**
  - `darken_image`, `brighten_image`, `saturate_image`, `desaturate_image`
  - Cinematic vignette effect (`apply_vignette`)
  - Sharpening, greyscale/noir conversion
- **Subtitle Overlay:** Optional subtitle burn-in from scene `subtitle_lines`
- **A/V Sync:** Clips are timed to the timing manifest from Phase 2
- **Final Composition:** All scenes concatenated with transitions and merged with audio using MoviePy → exported as `final_output.mp4`

**Output Artifact:** `data/outputs/<project_id>/final_output.mp4`

---

## 🌐 Phase 4 — Full-Stack Web Interface

**Backend:** `backend/app.py` (FastAPI + Uvicorn)  
**Frontend:** `frontend/src/App.jsx` (React 18 + Vite)

**Backend Features:**
- `POST /projects` — Create project and kick off full pipeline
- `GET /projects/{id}` — Fetch live project state (scenes, characters, artifacts)
- `POST /projects/{id}/run-phase/{phase}` — Re-run a single phase independently
- `POST /projects/{id}/edit` — Submit a natural-language edit command
- `POST /projects/{id}/undo` — Revert to a previous version
- `GET /projects/{id}/events` — Server-Sent Events (SSE) stream for real-time progress
- `GET /artifacts/{path}` — Serve generated audio, images, and video files

**Frontend Features:**
- Natural-language prompt input with configurable scene count (1–4)
- Real-time per-phase progress bars (Story → Audio → Video)
- Phase output preview panels (story JSON, timing manifest, render log)
- Integrated video player with download button
- Edit Agent text input for natural-language edits
- Version History panel with one-click Revert buttons
- Per-phase Re-run buttons for selective regeneration

---

## ✏️ Phase 5 — Intelligent Edit Agent & Undo System

**Agent:** `agents/edit_agent/agent.py`  
**Components:** `intent_classifier.py`, `executor.py`, `planner.py`  
**State Management:** `state_manager/state_manager.py`, `state_manager/snapshot.py`

### 5.1 How Editing Works

Users type free-text edit commands in the UI. The system automatically:
1. **Classifies** the intent and target using an LLM (Groq `llama-3.1-8b-instant`)
2. **Executes** targeted mutations to the project state
3. **Re-runs** only the affected downstream phases (not the entire pipeline)
4. **Snapshots** the new state for future undo

### 5.2 Supported Edit Commands

| Example Command | Target | Action |
|----------------|--------|--------|
| `"Change the narrator voice to whispered"` | `audio` | Re-runs TTS for that character with new tone |
| `"Make the final scene darker"` | `video_frame` | Applies darkening filter and regenerates visuals |
| `"Add dramatic background music"` | `audio` | Generates and overlays a new BGM track |
| `"Remove the subtitles"` | `video` | Recomposes video with subtitles disabled |
| `"Make her hair green"` | `video_frame` | Re-generates character visual with updated description |
| `"Speed up the scene"` | `video` | Adjusts duration and recomposes |
| `"Regenerate the script"` | `script` | Re-invokes Phase 1 and cascades through all phases |
| `"Adjust background music volume"` | `audio` | BGM-only fast path — skips full TTS re-synthesis |

### 5.3 Intent Classification

The intent classifier uses Groq's LLM API with a structured system prompt to output a validated JSON intent object:

```json
{
  "intent": "adjust_scene_visuals",
  "target": "video_frame",
  "details": {
    "scene_id": "scene_2",
    "character_id": null,
    "tone": null,
    "visual_change": "darker, more cinematic",
    "subtitles_enabled": null,
    "duration_delta": null
  }
}
```

**Supported intents:** `change_voice_tone` | `adjust_bgm_volume` | `adjust_scene_visuals` | `change_character_design` | `toggle_subtitles` | `adjust_scene_speed` | `regenerate_script`

### 5.4 State Versioning & Undo

Every pipeline run or partial re-run creates a **version snapshot**:

- Each version gets an auto-incremented ID (`v1`, `v2`, `v3`, …)
- Snapshots store the full `ProjectState` JSON + all artifact file paths
- Snapshots are persisted to SQLite (`data/project_state.db`) and as JSON files — **no version is ever permanently lost**
- The UI shows a **Version History panel** with timestamps and trigger descriptions
- Clicking **Revert** on any version restores all assets and the pipeline state to that exact snapshot
- `StateManager.revert_to_version(project_id, version_id)` handles full restoration

```
StateManager.save_version(state, trigger, phase, artifact_paths) → persisted snapshot
StateManager.revert_to_version(project_id, version_id)           → restores state + assets
StateManager.list_projects()                                      → lists all projects
```

### 5.5 Smart Downstream Invalidation

When a phase is re-run, only downstream data is cleared — upstream data is preserved:

- **Re-run Story** → clears all audio + video data, characters, scenes
- **Re-run Audio** → clears final audio + video; preserves images (unless full re-synthesis)
- **Re-run Video** → only clears clip paths; preserves images and audio
- **BGM-only edits** → fast path: skips TTS, only regenerates BGM and recomposes video

---

## 🧪 Testing

Unit tests are provided for each phase:

```bash
# Run all tests
pytest tests/

# Run edit agent intent classifier tests (10+ test types)
pytest agents/edit_agent/tests/test_intent_classifier.py -v
```

Test coverage includes:
- Story schema validation and constraint enforcement
- Audio generation and timing manifest correctness
- Video composition and filter application
- Edit intent classification across 10+ query types
- State snapshot creation and revert correctness

---

## 📐 Shared JSON Schema

All phases communicate through a single `ProjectState` Pydantic model (`shared/schemas/project_state.py`):

```
ProjectState
├── project_id, prompt, status, current_phase
├── story: { title, genre, tone, synopsis, provider }
├── characters[]: { character_id, name, role, voice_style, visual_description, voice_name }
├── scenes[]: { scene_id, title, duration_sec, narration, dialogue[], visual_prompt, mood,
│              subtitle_lines[], audio_start_ms, audio_end_ms, image_path, clip_path }
├── audio: { dialogue_tracks[], bgm_track, timing_manifest[], final_audio_path, provider }
├── video: { scene_images[], subtitle_file, final_video_path, subtitles_enabled }
├── artifacts: { story_json, timing_manifest_json, final_audio, final_video, scene_images[] }
└── versions[]: { version_id, trigger, changed_phase, artifact_paths[], snapshot_path }
```

---

## 📦 Requirements

```
fastapi==0.115.5
uvicorn==0.32.0
pydantic==2.9.2
requests==2.32.3
Pillow==10.4.0
moviepy==2.1.1
pytest==8.3.3
httpx==0.28.1
python-dotenv==1.0.1
edge-tts>=6.1.9,<8
```

---

## 👥 Team & Division of Work

| Member | Phase | Key Responsibilities |
|--------|-------|----------------------|
| Member 1 | Phase 1 — Story & Script | Prompt engineering, LLM integration, JSON schema design, character roster |
| Member 2 | Phase 2 — Audio & TTS | Edge-TTS integration, voice consistency, BGM synthesis, timing manifest |
| Member 3 | Phase 3 — Video Composition | Image generation, MoviePy compositing, visual filters, A/V sync, MP4 export |
| Member 4 | Phase 4 + 5 — Web App & Edit Agent | FastAPI backend, React frontend, SSE events, LangGraph edit agent, state snapshot & undo |

All members are jointly responsible for the shared JSON schema, integration testing, and final presentation.

---

## 📊 Evaluation Criteria

| Criterion | Weight |
|-----------|--------|
| Phase 1 — Story & Script Agent | 15% |
| Phase 2 — Audio Generation | 15% |
| Phase 3 — Video Composition | 20% |
| Phase 4 — Web Interface | 10% |
| Integration & Pipeline | 10% |
| Report & Presentation | 10% |
| Phase 5 — Edit Agent & Undo | 20% |

---

*National University of Computer and Emerging Sciences, Islamabad — Agentic AI Project 2026*
