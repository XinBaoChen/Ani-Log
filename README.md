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

Open the dashboard at http://localhost:3000

---

### Option B — Manual Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# C++ Capture Engine
cd capture_engine
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release

# Frontend
cd frontend
npm install
npm run dev
```

### Service URLs

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
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

## Stretch Goals

These are features planned for future development once the core pipeline is solid.

### Autonomous Anime Episode Watcher with Fine-Tuned AI Companion

The largest vision for Ani-Log's future: a model fine-tuned specifically on anime knowledge — characters, lore, story arcs, studios, genres, and cultural context — that can **actively watch episodes alongside you and answer anything in real time**.

**What it would do:**
- Automatically load and watch anime episodes frame by frame alongside the user
- Recognise not just *who* is on screen, but *what they mean* — backstory, relationships, power levels, motivations, and narrative role
- Answer natural language questions mid-episode: *"Who is that?", "What arc are we in?", "Has this character appeared before?"*
- Provide spoiler-aware commentary calibrated to how far into the series you are
- Generate rich per-episode breakdowns covering plot, character development, and thematic notes

**Why fine-tuned and not a general LLM:**
Off-the-shelf models have incomplete or hallucinated anime knowledge. A model fine-tuned on structured anime data — MAL, AniList, fan wikis, episode transcripts — would give accurate, confident answers for obscure series, not just mainstream titles.

**Planned tech approach:**
- Fine-tune a mid-size instruction model (Mistral 7B / LLaMA 3) on a curated anime knowledge dataset
- Add vision capabilities so the model processes actual video frames, not just text metadata
- Expose a chat panel in the dashboard so users can converse with the AI while watching
- Optional voice output so the AI can narrate live — like a knowledgeable friend sitting beside you

---

### Other Future Features

| Feature | Description |
|---|---|
| **Spoiler Shield** | Suppress a character's wiki entry on first appearance until the user explicitly unlocks it |
| **Cross-Series Linking** | Surface connections when different anime share character archetypes or visual themes |
| **Community Sync** | Export Ani-Log data in a format compatible with AniList and MyAnimeList profiles |
| **Mobile Companion** | Lightweight mobile app that syncs with your desktop Ani-Log instance |
| **Voice Commands** | Trigger search and capture controls hands-free while watching |

---

## License

MIT — free to use, modify, and build on.