"""
Ani-Log Mock Backend
────────────────────
Lightweight development server — no ML, no GPU, no Docker needed.
Returns realistic sample data for all frontend features.

Usage:
    pip install fastapi uvicorn
    python mock_server.py
    # or: uvicorn mock_server:app --reload --port 8000
"""

import uuid
import time
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Ani-Log Mock API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory state ────────────────────────────────────────────────────────────

_capture_state = {
    "session_id": None,
    "status": "idle",          # idle | capturing | stopped
    "total_frames": 0,
    "characters_found": 0,
    "scenes_detected": 0,
    "started_at": None,
}

_sessions = [
    {
        "id": "sess-001",
        "title": "Attack on Titan — Season 4",
        "status": "stopped",
        "started_at": "2026-03-01T14:00:00Z",
        "ended_at":   "2026-03-01T14:47:22Z",
        "total_frames": 2834,
        "thumbnail_url": None,
    },
    {
        "id": "sess-002",
        "title": "Demon Slayer — Mugen Train",
        "status": "stopped",
        "started_at": "2026-03-02T20:15:00Z",
        "ended_at":   "2026-03-02T22:03:11Z",
        "total_frames": 6541,
        "thumbnail_url": None,
    },
    {
        "id": "sess-003",
        "title": "Jujutsu Kaisen — Season 2",
        "status": "stopped",
        "started_at": "2026-03-03T18:30:00Z",
        "ended_at":   "2026-03-03T19:52:44Z",
        "total_frames": 4102,
        "thumbnail_url": None,
    },
]

_characters = [
    {
        "id": "char-001",
        "name": "Levi Ackermann",
        "description": "Section Commander of the Survey Corps — humanity's strongest soldier. Short, silver-eyed, and relentlessly precise with his blades.",
        "appearance_count": 342,
        "first_seen_at": "2026-03-01T14:03:11Z",
        "thumbnail_url": None,
        "metadata": {"hair_color": "black", "eye_color": "silver", "affiliation": "Survey Corps"},
    },
    {
        "id": "char-002",
        "name": "Mikasa Ackermann",
        "description": "One of the most skilled soldiers in the 104th Cadet Corps. Always wears a red scarf gifted by Eren.",
        "appearance_count": 298,
        "first_seen_at": "2026-03-01T14:05:44Z",
        "thumbnail_url": None,
        "metadata": {"hair_color": "black", "eye_color": "gray", "affiliation": "Survey Corps"},
    },
    {
        "id": "char-003",
        "name": "Armin Arlert",
        "description": "Brilliant strategist and childhood friend of Eren. Platinum blond hair, exceptional tactical mind.",
        "appearance_count": 211,
        "first_seen_at": "2026-03-01T14:07:02Z",
        "thumbnail_url": None,
        "metadata": {"hair_color": "blond", "eye_color": "blue", "affiliation": "Survey Corps"},
    },
    {
        "id": "char-004",
        "name": "Eren Yeager",
        "description": "The main protagonist. Brown-haired soldier with a fierce determination and the power of the Attack Titan.",
        "appearance_count": 401,
        "first_seen_at": "2026-03-01T14:01:58Z",
        "thumbnail_url": None,
        "metadata": {"hair_color": "brown", "eye_color": "green", "affiliation": "Survey Corps"},
    },
    {
        "id": "char-005",
        "name": "Historia Reiss",
        "description": "Small blond girl with blue eyes. Heir to the throne and former member of the 104th.",
        "appearance_count": 89,
        "first_seen_at": "2026-03-01T14:22:14Z",
        "thumbnail_url": None,
        "metadata": {"hair_color": "blond", "eye_color": "blue", "affiliation": "Survey Corps"},
    },
    {
        "id": "char-006",
        "name": "Hange Zoë",
        "description": "Section Commander and passionate researcher obsessed with Titans. Long brown hair, thick glasses.",
        "appearance_count": 176,
        "first_seen_at": "2026-03-01T14:14:31Z",
        "thumbnail_url": None,
        "metadata": {"hair_color": "brown", "eye_color": "brown", "affiliation": "Survey Corps"},
    },
    {
        "id": "char-007",
        "name": "Erwin Smith",
        "description": "Commander of the Survey Corps. Blond with a strong jaw and an unwavering will to reach the truth.",
        "appearance_count": 134,
        "first_seen_at": "2026-03-01T14:18:05Z",
        "thumbnail_url": None,
        "metadata": {"hair_color": "blond", "eye_color": "blue", "affiliation": "Survey Corps"},
    },
    {
        "id": "char-008",
        "name": "Reiner Braun",
        "description": "Armored Titan shifter. Broad-shouldered blond cadet with a split loyalty between mission and comrades.",
        "appearance_count": 167,
        "first_seen_at": "2026-03-01T14:09:52Z",
        "thumbnail_url": None,
        "metadata": {"hair_color": "blond", "eye_color": "hazel", "affiliation": "Warrior Unit"},
    },
]

_scenes = [
    {
        "id": "scene-001",
        "session_id": "sess-001",
        "scene_index": 0,
        "start_time": 62.0,
        "end_time": 198.0,
        "thumbnail_url": None,
        "description": "Levi and his squad infiltrate Wall Maria through heavy fog at dawn.",
        "location": "Wall Maria — outer district",
        "characters": [_characters[0], _characters[1]],
        "items": [
            {"id": "item-001", "label": "ODM Gear", "category": "equipment", "confidence": 0.97, "timestamp": 65.0, "bbox": None},
        ],
    },
    {
        "id": "scene-002",
        "session_id": "sess-001",
        "scene_index": 1,
        "start_time": 198.0,
        "end_time": 334.5,
        "thumbnail_url": None,
        "description": "Armin lays out the plan on a map as the cadets prepare for the counterattack.",
        "location": "Trost District — command room",
        "characters": [_characters[2], _characters[3]],
        "items": [
            {"id": "item-002", "label": "Battle map", "category": "object", "confidence": 0.88, "timestamp": 205.0, "bbox": None},
        ],
    },
    {
        "id": "scene-003",
        "session_id": "sess-001",
        "scene_index": 2,
        "start_time": 334.5,
        "end_time": 487.0,
        "thumbnail_url": None,
        "description": "Historia reveals her true identity to Ymir as they flee through the underground caverns.",
        "location": "Underground city passage",
        "characters": [_characters[4]],
        "items": [],
    },
    {
        "id": "scene-004",
        "session_id": "sess-002",
        "scene_index": 0,
        "start_time": 12.0,
        "end_time": 165.0,
        "thumbnail_url": None,
        "description": "The Mugen Train accelerates through the night as passengers fall into enchanted sleep.",
        "location": "Mugen Train — exterior",
        "characters": [],
        "items": [
            {"id": "item-003", "label": "Katana", "category": "weapon", "confidence": 0.95, "timestamp": 20.0, "bbox": None},
        ],
    },
    {
        "id": "scene-005",
        "session_id": "sess-002",
        "scene_index": 1,
        "start_time": 165.0,
        "end_time": 391.0,
        "thumbnail_url": None,
        "description": "A massive castle silhouette looms over the next village. Drums can be heard in the distance.",
        "location": "Castle courtyard at dusk",
        "characters": [],
        "items": [],
    },
    {
        "id": "scene-006",
        "session_id": "sess-003",
        "scene_index": 0,
        "start_time": 30.0,
        "end_time": 214.0,
        "thumbnail_url": None,
        "description": "Students spar at a school in Shibuya — Gojo arrives late wearing a blindfold.",
        "location": "Jujutsu High — training grounds",
        "characters": [],
        "items": [
            {"id": "item-004", "label": "Blindfold", "category": "clothing", "confidence": 0.99, "timestamp": 33.0, "bbox": None},
        ],
    },
]

_story_arcs = [
    {
        "id": "arc-001",
        "title": "The Fall of Shiganshina — Arc Summary",
        "summary": "Humanity faces its first major defeat in generations. Colossal and Armored Titans breach Wall Maria, triggering a desperate evacuation. Eren's mother is consumed before his eyes. This moment shatters his innocence and plants the seeds of an obsessive will to eradicate all Titans — whatever the cost.",
        "character_ids": ["char-001", "char-002", "char-003", "char-004"],
        "scene_ids": ["scene-001", "scene-002"],
        "generated_at": "2026-03-01T15:10:00Z",
    },
    {
        "id": "arc-002",
        "title": "Return to Shiganshina — Strategic Confrontation",
        "summary": "The Survey Corps executes its most carefully planned expedition yet. Erwin's gambit draws the Beast Titan into open combat while Levi conducts a solo assassination run. Armin's tactical brilliance turns near defeat into a fragile, costly victory — but the human cost is devastating.",
        "character_ids": ["char-001", "char-003", "char-007"],
        "scene_ids": ["scene-003"],
        "generated_at": "2026-03-01T15:45:00Z",
    },
]

# ── Pydantic request models ────────────────────────────────────────────────────

class CaptureStartRequest(BaseModel):
    title: str = "My Session"
    fps: int = 2
    source: str = "screen"

class CharacterUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class SummaryGenerateRequest(BaseModel):
    session_id: str
    scene_ids: Optional[list[str]] = None

# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _search_text(obj: dict, q: str) -> bool:
    q = q.lower()
    fields = [
        str(obj.get("name", "")),
        str(obj.get("description", "")),
        str(obj.get("label", "")),
        str(obj.get("location", "")),
    ]
    return any(q in f.lower() for f in fields)

# ── Routes — Capture ──────────────────────────────────────────────────────────

@app.get("/api/capture/status")
def get_capture_status():
    elapsed = 0
    if _capture_state["started_at"]:
        elapsed = int(time.time() - _capture_state["started_at"])
        if _capture_state["status"] == "capturing":
            _capture_state["total_frames"] = elapsed * _capture_state.get("fps", 2)
            _capture_state["scenes_detected"] = max(0, elapsed // 30)
            _capture_state["characters_found"] = min(8, elapsed // 20)

    return {
        "session_id": _capture_state["session_id"] or "",
        "status": _capture_state["status"],
        "total_frames": _capture_state["total_frames"],
        "characters_found": _capture_state["characters_found"],
        "scenes_detected": _capture_state["scenes_detected"],
        "elapsed_seconds": elapsed,
    }

@app.post("/api/capture/start")
def start_capture(req: CaptureStartRequest):
    if _capture_state["status"] == "capturing":
        raise HTTPException(400, "Capture session already running")

    session_id = str(uuid.uuid4())
    new_session = {
        "id": session_id,
        "title": req.title,
        "status": "capturing",
        "started_at": _now(),
        "ended_at": None,
        "total_frames": 0,
        "thumbnail_url": None,
    }
    _sessions.insert(0, new_session)

    _capture_state.update({
        "session_id": session_id,
        "status": "capturing",
        "total_frames": 0,
        "characters_found": 0,
        "scenes_detected": 0,
        "started_at": time.time(),
        "fps": req.fps,
    })

    return {
        "session_id": session_id,
        "status": "capturing",
        "message": f"Capture started at {req.fps} FPS",
    }

@app.post("/api/capture/stop")
def stop_capture():
    if _capture_state["status"] != "capturing":
        raise HTTPException(400, "No active capture session")

    sid = _capture_state["session_id"]
    for s in _sessions:
        if s["id"] == sid:
            s["status"] = "stopped"
            s["ended_at"] = _now()
            s["total_frames"] = _capture_state["total_frames"]
            break

    _capture_state.update({
        "status": "stopped",
        "session_id": None,
        "started_at": None,
    })

    return {"status": "stopped", "message": "Capture session stopped"}

# ── Routes — Characters ───────────────────────────────────────────────────────

@app.get("/api/characters")
def list_characters(
    sort_by: str = Query("appearance_count"),
    limit: int = Query(50),
    offset: int = Query(0),
):
    chars = list(_characters)
    if sort_by == "name":
        chars.sort(key=lambda c: c["name"])
    elif sort_by == "first_seen_at":
        chars.sort(key=lambda c: c["first_seen_at"], reverse=True)
    else:
        chars.sort(key=lambda c: c["appearance_count"], reverse=True)
    return chars[offset: offset + limit]

@app.get("/api/characters/{character_id}")
def get_character(character_id: str):
    char = next((c for c in _characters if c["id"] == character_id), None)
    if not char:
        raise HTTPException(404, "Character not found")
    return {
        **char,
        "appearances": [
            {"id": str(uuid.uuid4()), "scene_id": "scene-001", "timestamp": 65.0, "confidence": 0.94, "bbox": None},
            {"id": str(uuid.uuid4()), "scene_id": "scene-002", "timestamp": 205.0, "confidence": 0.91, "bbox": None},
        ],
        "related_characters": [c for c in _characters if c["id"] != character_id][:3],
    }

@app.patch("/api/characters/{character_id}")
def update_character(character_id: str, req: CharacterUpdateRequest):
    char = next((c for c in _characters if c["id"] == character_id), None)
    if not char:
        raise HTTPException(404, "Character not found")
    if req.name is not None:
        char["name"] = req.name
    if req.description is not None:
        char["description"] = req.description
    return char

# ── Routes — Scenes ───────────────────────────────────────────────────────────

@app.get("/api/scenes")
def list_scenes(session_id: Optional[str] = None):
    if session_id:
        return [s for s in _scenes if s["session_id"] == session_id]
    return _scenes

@app.get("/api/scenes/{scene_id}")
def get_scene(scene_id: str):
    scene = next((s for s in _scenes if s["id"] == scene_id), None)
    if not scene:
        raise HTTPException(404, "Scene not found")
    return scene

# ── Routes — Sessions ─────────────────────────────────────────────────────────

@app.get("/api/sessions/")
def list_sessions():
    return _sessions

@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    session = next((s for s in _sessions if s["id"] == session_id), None)
    if not session:
        raise HTTPException(404, "Session not found")
    return session

@app.get("/api/sessions/{session_id}/scenes")
def get_session_scenes(session_id: str):
    return [s for s in _scenes if s["session_id"] == session_id]

@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    global _sessions
    before = len(_sessions)
    _sessions = [s for s in _sessions if s["id"] != session_id]
    if len(_sessions) == before:
        raise HTTPException(404, "Session not found")
    return {"status": "deleted"}

# ── Routes — Search ───────────────────────────────────────────────────────────

@app.get("/api/search")
def search(
    q: str = Query(...),
    category: str = Query("all"),
    limit: int = Query(20),
):
    results = []

    if category in ("all", "characters"):
        for c in _characters:
            if _search_text(c, q):
                results.append({
                    "id": c["id"],
                    "type": "character",
                    "label": c["name"],
                    "description": c["description"],
                    "thumbnail_url": c["thumbnail_url"],
                    "score": 0.92,
                    "metadata": c.get("metadata"),
                })

    if category in ("all", "scenes"):
        for s in _scenes:
            if _search_text(s, q):
                results.append({
                    "id": s["id"],
                    "type": "scene",
                    "label": s.get("location") or f"Scene {s['scene_index']+1}",
                    "description": s.get("description"),
                    "thumbnail_url": s.get("thumbnail_url"),
                    "score": 0.78,
                    "metadata": {"session_id": s["session_id"]},
                })

    # Fuzzy fallback — partial word match
    if not results:
        q_parts = q.lower().split()
        for c in _characters:
            text = (c["name"] + " " + str(c.get("description", ""))).lower()
            if any(p in text for p in q_parts):
                results.append({
                    "id": c["id"],
                    "type": "character",
                    "label": c["name"],
                    "description": c["description"],
                    "thumbnail_url": c["thumbnail_url"],
                    "score": 0.55,
                    "metadata": c.get("metadata"),
                })

    return {"query": q, "total": len(results), "results": results[:limit]}

# ── Routes — Summary / Story Arcs ─────────────────────────────────────────────

@app.get("/api/summary")
def list_story_arcs(session_id: Optional[str] = None):
    if session_id:
        return [a for a in _story_arcs]  # all arcs for demo
    return _story_arcs

@app.get("/api/summary/{arc_id}")
def get_story_arc(arc_id: str):
    arc = next((a for a in _story_arcs if a["id"] == arc_id), None)
    if not arc:
        raise HTTPException(404, "Story arc not found")
    return arc

@app.post("/api/summary/generate")
def generate_summary(req: SummaryGenerateRequest):
    new_arc = {
        "id": str(uuid.uuid4()),
        "title": f"Auto-generated Summary — Session {req.session_id[:8]}",
        "summary": "The episode opens with an ominous calm. Key characters converge on a fortified position as tensions escalate. A decisive confrontation follows, revealing long-hidden loyalties and setting the stage for an irreversible turning point in the narrative.",
        "character_ids": [c["id"] for c in _characters[:4]],
        "scene_ids": req.scene_ids or [s["id"] for s in _scenes[:3]],
        "generated_at": _now(),
    }
    _story_arcs.append(new_arc)
    return new_arc

# ── Static data dir stub ──────────────────────────────────────────────────────

@app.get("/data/{path:path}")
def serve_data(path: str):
    raise HTTPException(404, "No thumbnail available in mock server")

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("\n🎌  Ani-Log Mock Backend starting on http://localhost:8000")
    print("📖  Docs available at http://localhost:8000/docs\n")
    uvicorn.run("mock_server:app", host="0.0.0.0", port=8000, reload=True)
