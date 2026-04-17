# 🎌 Ani-Log

### *Your anime — automatically catalogued, searchable, and alive.*

> Ani-Log runs silently in the background while you watch anime. Using computer vision and machine learning, it identifies every character on screen, maps out scene timelines, and builds a fully searchable personal wiki — all in real time, entirely on your local machine.

<br/>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![C++](https://img.shields.io/badge/C++-17-00599C?logo=cplusplus&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=next.js&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-FF6B35)
![YOLO-World](https://img.shields.io/badge/YOLO--World-Detection-00C851)
![CLIP](https://img.shields.io/badge/CLIP-ViT--L/14-7B2FBE)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## What is Ani-Log?

Imagine never losing track of a side character's name, or forgetting which episode a key scene happened in. Ani-Log solves that.

It hooks into your screen at the frame level, samples intelligently, and runs a multi-stage vision pipeline:

1. **Detect** — YOLO-World spots characters and objects in each frame using open-vocabulary detection
2. **Identify** — CLIP (ViT-L/14) extracts semantic feature embeddings for each detected entity
3. **Track** — ByteTrack links the same character across cuts, camera angles, and scene changes
4. **Store** — Feature vectors are indexed in ChromaDB for millisecond similarity search
5. **Summarize** — A local LLM reads the scene log and generates readable story arc summaries
6. **Surface** — A Next.js dashboard lets you search everything, browse character timelines, and review scenes

No cloud. No subscription. No data leaves your machine.

---

## Architecture

```
+==============+====================+==============+====================+
|  C++ Engine  |   Python Backend   |  Vector DB   |   Frontend UI      |
+--------------+--------------------+--------------+--------------------+
| DirectX/X11  | YOLO-World ──────► | ChromaDB     | Next.js 14         |
| Screen       | Detection          |              |                    |
| Capture      |       |            | Character    | Search             |
|      |       | CLIP Feature       | Embeddings   | Characters         |
| Frame        | Extraction ──────► |              | Scenes             |
| Sampler      |       |            | Scene Index  | Sessions           |
|      |       | ByteTrack          |              | Story Arcs         |
| ZeroMQ ────► | Tracking ────────► |              |                    |
| IPC Bridge   |       |            | Arc Data     | Live Capture       |
|              | Ollama LLM ──────► |              | Dashboard          |
+==============+====================+==============+====================+
```

---

## Quick Start

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | |
| Node.js | 18+ | |
| CMake | 3.20+ | For C++ capture engine |
| Docker + Compose | Latest | Optional but recommended |
| CUDA GPU | Any | CPU fallback available, slower |

---

### Option A — Docker Compose (Recommended)

```bash
git clone https://github.com/your-username/ani-log.git
cd ani-log
cp .env.example .env
docker compose up --build
```

Open the dashboard at http://localhost:3001

By default this starts frontend + mock backend together (single command, no separate terminals).
Use only the dashboard URL for normal usage; all API routes are proxied through the frontend at `/api/*`.

Docker persistence note:
- Backend data is bind-mounted from `backend/data` into the container.
- Existing `mock_state.json`, session folders, and local DB files from earlier runs are reused.

Optional full-ML services:

```bash
docker compose --profile ml up --build
```

This also starts ChromaDB and Ollama.

Repeatable Docker smoke check (one command):

```powershell
./docker_smoke.ps1
```

If containers are already up and you only want validation (no compose up step):

```powershell
./docker_smoke.ps1 -SkipComposeUp
```

---

### Option B — Manual Setup (Windows-first)

```powershell
# Backend (Windows PowerShell)
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# C++ Capture Engine (new PowerShell terminal)
cd capture_engine
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release

# Frontend (new PowerShell terminal)
cd frontend
npm install
npm run dev -- --port 3001
```

```bash
# Linux/macOS optional variant
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

# Mock mode (lightweight, no ML/GPU)
cd backend
python mock_server.py

# Quick no-Docker smoke validation (run in a separate PowerShell while mock_server is running)
cd backend
.\manual_smoke_no_docker.ps1


Have both frontend and backend running to see the full experience.
### Service URLs

| Service | URL |
|---|---|
| Dashboard | http://localhost:3001 |
| API + Swagger Docs | http://localhost:8000/docs |
| ChromaDB UI | http://localhost:8100 |

---

## Project Structure

```
Ani-Log/
├── backend/                    # Python FastAPI + Vision Pipeline
│   ├── main.py
│   ├── requirements.txt
│   └── app/
│       ├── api/routes/         # capture, characters, scenes, sessions, search, summary
│       ├── core/               # Config, DB setup
│       ├── models/             # Pydantic schemas
│       ├── services/           # detector, feature_extractor, tracker, vector_store, summarizer
│       └── tasks/              # Background workers
├── capture_engine/             # C++ Real-time Screen Capture
│   ├── CMakeLists.txt
│   └── src/                    # screen_capture, frame_sampler, ipc_bridge
├── frontend/                   # Next.js 14 Dashboard
│   └── src/
│       ├── app/                # App Router pages
│       ├── components/         # UI components
│       ├── lib/                # Typed API client
│       ├── store/              # Zustand state
│       └── types/              # TypeScript types
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Technology Stack

| Layer | Technology | Why |
|---|---|---|
| Screen Capture | C++ 17 + DirectX 11 | Minimal CPU overhead, native OS APIs |
| IPC | ZeroMQ | Sub-millisecond C++ to Python messaging |
| Object Detection | YOLO-World | Open-vocabulary — detects anything without retraining |
| Feature Extraction | CLIP ViT-L/14 | Rich semantic embeddings, strong at anime art styles |
| Multi-Object Tracking | ByteTrack + CLIP Re-ID | Keeps identity across cuts and costume changes |
| Vector Database | ChromaDB | Local, persistent, fast approximate nearest-neighbour |
| Story Summarization | Local LLM (Ollama) | Fully offline narrative generation from scene logs |
| Backend API | FastAPI + WebSocket | Async, typed, auto-documented |
| Frontend | Next.js 14 + Tailwind | App Router, server components, animated UI |
| State Management | Zustand | Lightweight, no boilerplate |

---

## API Reference

### Capture
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/capture/status` | Live state — frames, characters, scenes found |
| `POST` | `/api/capture/start` | Begin a new capture session |
| `POST` | `/api/capture/stop` | Stop capture and persist session |

### Characters
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/characters` | All detected characters with appearance counts |
| `GET` | `/api/characters/{id}` | Full character detail with scene appearances |
| `PATCH` | `/api/characters/{id}` | Update character name or metadata |

### Scenes & Sessions
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/scenes` | Complete scene timeline |
| `GET` | `/api/scenes/{id}` | Scene detail — characters present, timestamp |
| `GET` | `/api/sessions` | All watch sessions |
| `GET` | `/api/sessions/{id}` | Session detail |
| `GET` | `/api/sessions/{id}/scenes` | All scenes within a session |
| `DELETE` | `/api/sessions/{id}` | Delete session and its data |

### Search & Summary
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/search?q=` | Semantic + keyword search across everything |
| `POST` | `/api/summary/generate` | Trigger LLM story arc generation |
| `GET` | `/api/summary/{arc_id}` | Retrieve a generated arc summary |
| `WS` | `/ws/capture` | WebSocket — live frame and detection feed |

---

## Team

| Role | Responsibilities |
|---|---|
| **Vision Lead** | YOLO-World detection pipeline, CLIP feature extraction, re-identification |
| **Database Architect** | ChromaDB vector store design, indexing strategy, similarity search tuning |
| **C++ Engineer** | DirectX screen capture, intelligent frame sampler, ZeroMQ IPC bridge |
| **Frontend Engineer** | Next.js dashboard, animated UI, real-time capture feed, search UX |
| **NLP / Integration** | Ollama LLM integration, story arc summarization, scene log parsing |

---

## Development Status

> **Current mock-mode note:**
> This is now a working lightweight detector for mock mode, but it is not as accurate as the full ML backend (`main.py` + YOLO/CLIP/tracker pipeline).
> If you want much better anime character differentiation (many similar characters), the next step is to run the real backend pipeline and tune thresholds/classes.

### What Is Working Now
- ✅ Real-time screen capture via `mss`
- ✅ Lightweight character detection — OpenCV Haar cascade + HOG + HSV histogram re-ID
- ✅ Performance Mode preset for long sessions — 1 FPS sampling + adaptive keyframes (change-based + keepalive)
- ✅ Character confidence surfaced in UI with confidence sort and minimum-confidence filter
- ✅ Session persistence across server restarts (`mock_state.json`)
- ✅ Long-session safety caps — 18,000 frame hard cap, 2,500 scene stride downsampling
- ✅ Scene viewer with autoplay, crossfade animation, and fullscreen toggle
- ✅ Session stores capture preset metadata (`capture_fps`, `performance_mode`, `adaptive_keyframes`) and shows it in Session detail
- ✅ Confidence filtering now available in Characters, Scenes, and Session detail views
- ✅ Character thumbnails saved to disk with appearance counts
- ✅ Characters linked into every scene response

### What Still Needs Completing (Before Stretch Goals)
- [ ] Wire frontend to the full ML backend (`main.py`) — YOLO-World + CLIP + ChromaDB replacing the mock server
- [ ] Validate the C++ capture engine build and ZeroMQ IPC bridge on a clean machine
- [x] Character rename UX — backend `PATCH /api/characters/{id}` is wired in the Characters UI
- [x] Story arc summary panel — frontend `StoryArcSummary` is connected on Capture and Session Detail pages with session-scoped generation/listing
- [x] Semantic search UI — Search page now supports mode switching (`hybrid`/`semantic`/`keyword`) and score threshold filtering
- [ ] Episode/series metadata — sessions need a title, episode number, and source field in the schema and UI
- [ ] Scene detail modal — clicking a scene card should expand to full frame + character list + timestamp
- [x] End-to-end Docker Compose smoke test — confirmed frontend pages, proxied APIs, semantic search modes, session-scoped summary generation, and persisted historical sessions in Docker

### Docker Validation Snapshot

Validated on 2026-04-16 using Docker Compose (`frontend` + `backend`) with dashboard-only testing via `http://localhost:3001`.

Results:
- ✅ Frontend routes returned HTTP 200: `/`, `/sessions`, `/search`, `/capture`
- ✅ Proxied API routes returned HTTP 200 through frontend URL: `/api/capture/status`, `/api/sessions`, `/api/scenes`, `/api/characters`, `/api/summary`, `/api/search` (`hybrid`, `semantic`, `keyword`)
- ✅ Historical persisted data visible in Docker after mount fix (`sessions_count=20` from existing local state)
- ✅ End-to-end capture/session flow executes through frontend API path without proxy errors
- ✅ Session-scoped story arc generation/filtering works through Docker proxy (`/api/summary/generate`, `/api/summary?session_id=...`)

### Manual Validation Snapshot (No Docker)

Validated locally on 2026-04-12 using:
- Backend: `uvicorn mock_server:app --host 127.0.0.1 --port 8000`
- Frontend: `npm --prefix frontend run dev -- --port 3001`

Results:
- ✅ Frontend routes load: `/` and `/sessions` returned HTTP 200
- ✅ API proxy routes returned HTTP 200: `/api/capture/status`, `/api/sessions`, `/api/scenes`, `/api/summary`
- ✅ End-to-end capture flow worked through frontend API path:
    - `POST /api/capture/start` created a new session ID
    - `POST /api/capture/stop` completed successfully
    - New session was retrievable from `/api/sessions/{id}` and scene rows were returned from `/api/sessions/{id}/scenes`

### Immediate Next Steps (Execution Order)
1. Run a full 30-minute stress test in both presets and capture memory profile over time (this update includes 20-second smoke baselines only).
2. Add false-positive measurement harness for confidence thresholds using a labeled validation clip set.
3. [x] Surface dropped-frame and adaptive-skip counters in `/api/capture/status` to make preset behavior observable in real time.
4. Add CI perf guardrail script that fails if baseline thresholds regress by >20%.

### Stress Test Baseline (Completed)

Two smoke tests were run against the API to establish initial performance gates:

| Preset | Runtime | Frames | Effective FPS | Scene Rows |
|---|---:|---:|---:|---:|
| Performance Mode (1 FPS + adaptive keyframes) | 20.0s | 5 | 0.25 | 5 |
| Balanced (2 FPS, adaptive off) | 22.2s | 44 | 1.98 | 44 |

### Acceptance Thresholds (Current)

| Metric | Threshold | Why |
|---|---|---|
| Balanced Effective FPS | >= 1.7 FPS at 2 FPS target | Keeps capture near real-time target on typical desktop load |
| Performance Mode Effective FPS | <= 0.8 FPS during mostly-static scenes | Confirms storage/CPU savings from adaptive keyframes |
| Session API payload (`/api/sessions/{id}/scenes`) | <= 12 MB for long sessions | Prevents UI lockups and oversized transfer bursts |
| Weak-detection visibility | Confidence filter at 60% should remove most false positives | Gives practical control over noisy detections in UI |

---

## Stretch Goals

The roadmap below is ordered by scope. Each phase assumes the previous one is stable.

---

### Phase 1 — Polish the Core Web App

Get the existing web stack production-ready before building on top of it.

- Replace `mock_server.py` with the real `main.py` pipeline as the default dev backend
- Complete the character detail page — full appearance timeline with scrubber, edit name inline
- Scene detail modal with frame zoom, character tags overlaid, and timestamp copy button
- Export a session as a formatted markdown wiki page or structured JSON
- Dark/light theme respecting OS preference
- Search results page — highlight matched terms, filter by character or scene
- Responsive layout so the dashboard works on a 1080p monitor and a 1440p ultrawide without overflow

---

### Phase 2 — Electron App: The Model Watches for You

**The big shift**: instead of requiring the user to sit in front of the screen, an Electron app wraps the entire Ani-Log stack into a single desktop application that can be pointed at a local video file or stream URL and process the whole episode *autonomously — no human watching required*.

**How it works:**
- The Electron shell bundles the Next.js frontend + FastAPI backend + Python environment into a single distributable (`.exe` / `.dmg` / `.AppImage`)
- A video player component (ffmpeg pipe or libmpv) feeds frames directly into the vision pipeline — no OS screen capture needed; the model literally watches the video for you
- The user queues an episode (or an entire series folder) and walks away — the app processes everything offline
- When processing is complete the full character log, scene timeline, and story arc summaries are already waiting to browse — the wiki is pre-built before the user even presses play

**What changes compared to the current web app:**

| Current Web App | Electron App |
|---|---|
| User must be actively watching on screen | Processes offline; user can be away |
| Screen capture via OS APIs (mss / DirectX) | Direct video frame injection via ffmpeg |
| Browser-accessed UI | Native desktop window with system tray icon |
| Manual start / stop per session | Queue a folder; auto-processes all episodes in order |
| One session at a time | Multi-episode batch queue with per-episode progress |
| Requires separate terminal to run backend | Backend starts and stops automatically with the app |

**Planned Electron architecture:**
```
Electron Main Process
├── Embedded Python runtime  (PyInstaller bundle or venv path)
│   ├── FastAPI backend        (spawned as child process)
│   └── ffmpeg frame feeder    (video → PIL images → pipeline)
├── BrowserWindow
│   └── Next.js dashboard     (served from localhost or bundled export)
└── System Tray
    ├── Processing status indicator
    ├── "Open Dashboard" shortcut
    └── Queue manager
```

**Why Electron and not a pure web app:**
- Cross-platform packaging — one codebase ships to Windows, macOS, and Linux
- Native filesystem access for local anime libraries without a browser file picker
- System tray lets the app run silently in the background while you do other things
- OS notification integration — "Episode 7 complete — 9 characters identified, 3 new"
- Auto-updater support via `electron-updater`

**Build plan:**
1. Extract the Next.js frontend into a static export (or keep it as a local dev server inside Electron)
2. Use `child_process.spawn` from the Electron main process to start `uvicorn` pointing at `main.py`
3. Replace the `mss` capture loop with an `ffmpeg -i {video_path} -vf fps=2 pipe:1` frame pipe feeding directly into the detection pipeline
4. Package with `electron-builder` — produce installers for all three platforms via GitHub Actions

---

### Long-Term Goals

These goals assume Phase 1 (polished web app) and Phase 2 (Electron auto-watcher) are both working and stable.

#### 1. Fine-Tuned Anime AI Companion
The largest vision: a model fine-tuned specifically on anime knowledge — characters, lore, story arcs, studios, genres, cultural context — that can answer anything in real time.

- Ingest MAL / AniList data, episode synopses, character relationship graphs, and fan wiki content into a structured training set
- Fine-tune a mid-size instruction model (Mistral 7B / LLaMA 3.1 8B) on this dataset using LoRA
- Add vision grounding so the model receives actual frames rather than just text metadata
- Expose a real-time Q&A chat panel in the dashboard — user types mid-episode and gets an immediate contextual answer
- Spoiler-aware: the model only reveals knowledge up to the episode the user has currently reached
- Optional voice output using a local TTS engine (Kokoro / Piper) — the AI narrates live like a knowledgeable friend sitting beside you

#### 2. Multi-Source Ingestion
Expand beyond screen capture and local files:
- Browser extension that intercepts HLS/DASH streams directly — no screen capture, perfect quality
- Bulk library import from Plex / Jellyfin / Emby via their REST APIs
- YouTube video processing — fansubs, official clips, recap videos
- Subtitle / transcript alignment — sync detected scenes with `.srt` files for richer scene labels

#### 3. Cross-Series Knowledge Graph
Link characters and themes across every show ever watched:
- Detect shared character archetypes and visual design language across unrelated series
- Build a graph: same voice actor → link characters; same studio → visual style classifier
- Surface: *"This character type appears in 14 other shows you have watched"*
- Track recurring directors and their signature visual styles across a personal watch history

#### 4. Community Wiki Export
Make Ani-Log data useful beyond a single user:
- Export session logs in a format compatible with AniList / MAL update APIs
- Optional: publish anonymised character feature signatures to a shared index so the community can improve re-ID accuracy for everyone
- Self-contained HTML wiki generation per series — shareable without an active server

---

### Reach Goals

Aspirational features — significant engineering effort, but would make Ani-Log genuinely one of a kind.

#### Autonomous Episode Review Agent
Fully autonomous episode processing with zero user input:
- Schedule nightly runs: *"Process tonight's episode of X at 2am"*
- Agent automatically fetches (from local library or a configured source), processes, generates a full wiki update, and sends a morning summary notification
- Discord bot integration — posts character and scene updates to a personal server
- Auto-publishes character wiki updates to a personal Notion page or static site

#### Adaptive Scene Intelligence
Move beyond frame-level visual detection toward semantic understanding:
- Classify emotional tone per scene (action, drama, comedy, flashback) from visual composition and audio energy
- Identify combat intensity in action anime and auto-tag scenes as "power-up", "decisive blow", "standoff"
- Automatically flag spoiler-dense scenes and blur their thumbnails until the user has passed that point in the series

#### Multi-Modal Long-Term Memory
Build a personal anime memory layer that grows over years of watching:
- Track the same character archetype recurring across multiple series over a full watch history
- Surface: *"You have watched 847 episodes featuring this archetype — top shows: X, Y, Z"*
- Mood-based session tagging — the app infers whether a session was emotionally heavy or light and uses that history to surface what to watch next
- Personalised rewatch suggestions keyed to specific scenes: *"You paused here four times — this scene is in your top 1% by engagement"*

#### Spoiler Shield System
A trust layer between what Ani-Log knows and what the user is allowed to see:
- Per-character spoiler locks — suppress a character's full profile until the user has seen their introduction episode
- Community-sourced spoiler markers synced from a lightweight shared API
- Safe browsing mode: all character names and scenes from episodes ahead of the user's progress are hidden behind a click-to-reveal gate

---

## License

MIT — free to use, modify, and build on.