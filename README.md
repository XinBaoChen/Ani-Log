# 🎌 Ani-Log — Autonomous Scene Contextualizer

> A tool that runs on your PC while you watch anime and automatically builds a searchable "Wiki" of every character, location, and item it sees.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![C++](https://img.shields.io/badge/C++-17-00599C?logo=cplusplus)
![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-orange)
![YOLO-World](https://img.shields.io/badge/YOLO--World-Detection-green)
![CLIP](https://img.shields.io/badge/CLIP-Features-purple)

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Ani-Log System                            │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│  C++ Engine  │ Python Core  │  Vector DB   │   Frontend UI      │
│              │              │              │                    │
│ Screen       │ YOLO-World   │ ChromaDB     │ Next.js Search     │
│ Capture ───► │ Detection    │              │ Engine             │
│              │      │       │              │                    │
│ Frame        │ CLIP Feature │ Character    │ Character Wiki     │
│ Sampler      │ Extraction   │ Embeddings   │                    │
│              │      │       │              │ Scene Timeline     │
│ IPC Bridge   │ Multi-Object │ Scene Index  │                    │
│ (ZeroMQ)     │ Tracking     │              │ Story Arc View     │
│              │      │       │              │                    │
│              │ Local LLM    │ Arc Data     │ Capture Controls   │
│              │ Summarizer   │              │                    │
└──────────────┴──────────────┴──────────────┴────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- CMake 3.20+
- Docker & Docker Compose (optional)
- GPU with CUDA support (recommended)

### 1. Docker Compose (Recommended)

```bash
cp .env.example .env
docker compose up --build
```

### 2. Manual Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# C++ Capture Engine
cd capture_engine
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build .

# Frontend
cd frontend
npm install
npm run dev
```

### 3. Access
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **ChromaDB**: http://localhost:8100

---

## 🏗️ Project Structure

```
Ani-Log/
├── backend/              # Python FastAPI + Vision Pipeline
│   ├── app/
│   │   ├── api/routes/   # REST endpoints
│   │   ├── core/         # Config, DB connections
│   │   ├── models/       # Pydantic schemas
│   │   ├── services/     # Vision, tracking, LLM
│   │   └── tasks/        # Background processing
│   └── main.py
├── capture_engine/       # C++ Screen Scraper
│   ├── src/              # Capture, sampling, IPC
│   └── CMakeLists.txt
├── frontend/             # Next.js Search UI
│   └── src/
│       ├── app/          # Pages & routes
│       ├── components/   # UI components
│       ├── lib/          # API client
│       ├── store/        # Zustand state
│       └── types/        # TypeScript types
└── docker-compose.yml
```

## 🧠 Core Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Object Detection | YOLO-World | Open-vocabulary detection of characters, items, locations |
| Feature Extraction | CLIP (ViT-L/14) | Semantic embeddings for re-identification |
| Multi-Object Tracking | ByteTrack + CLIP | Track entities across scene cuts |
| Vector Database | ChromaDB | Store & retrieve character feature vectors |
| Story Summarization | Local LLM (Ollama) | Generate story arc summaries from logs |
| Screen Capture | C++ (DirectX/X11) | Low-latency frame grabbing |
| IPC | ZeroMQ | C++ ↔ Python communication |
| Backend | FastAPI | REST API + WebSocket |
| Frontend | Next.js 14 | Search engine UI |

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/capture/start` | Start screen capture session |
| `POST` | `/api/capture/stop` | Stop capture session |
| `GET` | `/api/search?q=` | Search characters, locations, items |
| `GET` | `/api/characters` | List all detected characters |
| `GET` | `/api/characters/{id}` | Character detail with appearances |
| `GET` | `/api/scenes` | Scene timeline |
| `GET` | `/api/scenes/{id}` | Scene detail |
| `POST` | `/api/summary/generate` | Generate story arc summary |
| `GET` | `/api/summary/{arc_id}` | Get arc summary |
| `WS` | `/ws/capture` | Live capture feed |

## Team Roles

- **Vision Lead** — YOLO-World detection pipeline, CLIP feature extraction
- **Database Architect** — ChromaDB vector store, indexing, similarity search
- **C++ Backend** — Screen scraper, frame sampler, ZeroMQ IPC bridge
- **Frontend** — Next.js search engine UI for local anime collection
- **NLP/Integration** — Local LLM story arc summarization

## License

MIT
