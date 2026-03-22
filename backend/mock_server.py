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

import io
import json
import os
import uuid
import time
import struct
import zlib
import threading
import pathlib
from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
import mss
import mss.tools
from PIL import Image
import cv2
import numpy as np

# ── In-memory state ────────────────────────────────────────────────────────────

DATA_DIR = pathlib.Path(__file__).parent / "data" / "sessions"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = DATA_DIR.parent / "mock_state.json"
MAX_SCENES_PER_SESSION = 2500
MAX_CAPTURE_FRAMES = 18000  # safety cap for very long sessions

_capture_state = {
    "session_id": None,
    "status": "idle",          # idle | capturing | stopped
    "total_frames": 0,
    "characters_found": 0,
    "scenes_detected": 0,
    "started_at": None,
}

_capture_thread: Optional[threading.Thread] = None
_capture_stop_event = threading.Event()
_capture_frame_characters: dict[int, list[str]] = {}
_capture_unique_characters: set[str] = set()
_face_cascade: Any = None
_hog_detector: Any = None

AUTO_NAME_PREFIX = "Detected Character"

_sessions = [
    {
        "id": "sess-001",
        "title": "Attack on Titan — Season 4",
        "status": "stopped",
        "started_at": "2026-03-01T14:00:00Z",
        "ended_at":   "2026-03-01T14:47:22Z",
        "total_frames": 2834,
        "scene_count": 3,
        "first_thumbnail_url": "/api/placeholder/0?w=640&h=360",
    },
    {
        "id": "sess-002",
        "title": "Demon Slayer — Mugen Train",
        "status": "stopped",
        "started_at": "2026-03-02T20:15:00Z",
        "ended_at":   "2026-03-02T22:03:11Z",
        "total_frames": 6541,
        "scene_count": 2,
        "first_thumbnail_url": "/api/placeholder/3?w=640&h=360",
    },
    {
        "id": "sess-003",
        "title": "Jujutsu Kaisen — Season 2",
        "status": "stopped",
        "started_at": "2026-03-03T18:30:00Z",
        "ended_at":   "2026-03-03T19:52:44Z",
        "total_frames": 4102,
        "scene_count": 1,
        "first_thumbnail_url": "/api/placeholder/5?w=640&h=360",
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
        "thumbnail_url": "/api/placeholder/0?w=640&h=360",
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
        "thumbnail_url": "/api/placeholder/1?w=640&h=360",
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
        "thumbnail_url": "/api/placeholder/2?w=640&h=360",
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
        "thumbnail_url": "/api/placeholder/3?w=640&h=360",
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
        "thumbnail_url": "/api/placeholder/4?w=640&h=360",
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
        "thumbnail_url": "/api/placeholder/5?w=640&h=360",
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

app = FastAPI(title="Ani-Log Mock API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CaptureStartRequest(BaseModel):
    title: str = "My Session"
    fps: int = 2
    source: str = "screen"
    performance_mode: bool = False
    adaptive_keyframes: bool = False

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


def _save_state() -> None:
    """Persist mock state so sessions survive server restarts."""
    payload = {
        "sessions": _sessions,
        "characters": _characters,
        "scenes": _scenes,
        "story_arcs": _story_arcs,
        "saved_at": _now(),
    }
    tmp = STATE_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True)
    tmp.replace(STATE_FILE)


def _load_state() -> None:
    """Load persisted mock state, if available."""
    global _sessions, _characters, _scenes, _story_arcs
    if not STATE_FILE.exists():
        return
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        _sessions = payload.get("sessions", _sessions)
        _characters = payload.get("characters", _characters)
        _scenes = payload.get("scenes", _scenes)
        _story_arcs = payload.get("story_arcs", _story_arcs)
    except Exception as e:
        print(f"[state] failed to load {STATE_FILE}: {e}")


def _get_face_cascade() -> Any:
    """Lazy-load OpenCV Haar cascade used as a lightweight character detector."""
    global _face_cascade
    if _face_cascade is None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _face_cascade = cv2.CascadeClassifier(cascade_path)
    return _face_cascade


def _get_hog_detector() -> Any:
    """Lazy-load OpenCV people detector as a fallback for anime scenes."""
    global _hog_detector
    if _hog_detector is None:
        hog = cv2.HOGDescriptor()
        hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        _hog_detector = hog
    return _hog_detector


def _face_feature(crop_bgr: np.ndarray) -> list[float]:
    """Spatial-pyramid HSV + Sobel-edge descriptor for anime character re-ID.

    Layout (272 dims, L2-normalised):
      - Global H+S histogram 16×8  = 128 bins  (overall colour identity)
      - 2×2 quadrant H+S histograms 8×4 × 4 = 128 bins  (spatial layout)
      - Sobel edge-magnitude histogram 16 bins  (structural shape cue)
    """
    full = cv2.resize(crop_bgr, (64, 64), interpolation=cv2.INTER_AREA)
    hsv  = cv2.cvtColor(full, cv2.COLOR_BGR2HSV)
    feat: list[float] = []

    # Global H+S histogram — 16×8 = 128 bins
    h_global = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256]).flatten()
    feat.extend(h_global.tolist())

    # Spatial 2×2 grid — per-quadrant H+S 8×4 = 32 bins × 4 quadrants = 128 bins
    half = 32
    for oy in (0, half):
        for ox in (0, half):
            quad = hsv[oy:oy + half, ox:ox + half]
            qh = cv2.calcHist([quad], [0, 1], None, [8, 4], [0, 180, 0, 256]).flatten()
            feat.extend(qh.tolist())

    # Sobel edge-magnitude histogram — 16 bins (shape / line-art cue)
    gray = cv2.cvtColor(full, cv2.COLOR_BGR2GRAY).astype(np.float32)
    sx   = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sy   = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag  = np.sqrt(sx ** 2 + sy ** 2)
    edge_hist = np.histogram(mag, bins=16, range=(0.0, 512.0))[0].astype(np.float32)
    feat.extend(edge_hist.tolist())

    # L2-normalise to unit vector so Euclidean distance ≈ angular similarity
    arr = np.array(feat, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr.tolist()


def _feature_distance(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 999.0
    av = np.array(a, dtype=np.float32)
    bv = np.array(b, dtype=np.float32)
    return float(np.linalg.norm(av - bv))


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _face_confidence(img_w: int, img_h: int, box_w: int, box_h: int) -> float:
    area = float(max(1, box_w * box_h)) / float(max(1, img_w * img_h))
    # Heuristic confidence: larger stable face boxes are usually stronger detections.
    return _clamp01(0.55 + min(area * 14.0, 0.40))


def _hog_confidence(weight: float) -> float:
    # Map HOG SVM margin to 0..1 with a soft clamp.
    conf = 0.5 + (1.0 / (1.0 + float(np.exp(-weight))) - 0.5)
    return _clamp01(conf)


def _character_confidence(ch: dict) -> Optional[float]:
    raw = ch.get("confidence")
    if isinstance(raw, (int, float)):
        return _clamp01(float(raw))
    meta = ch.get("metadata") or {}
    meta_conf = meta.get("confidence")
    if isinstance(meta_conf, (int, float)):
        return _clamp01(float(meta_conf))
    # Static seeded demo characters may not have a model confidence.
    return None


def _fallback_character_thumbnail(char_id: str) -> str:
    idx = abs(hash(char_id)) % 10
    return f"/api/placeholder/{idx}?w=320&h=420"


def _is_auto_named(ch: dict) -> bool:
    name = str(ch.get("name", ""))
    return name.startswith(AUTO_NAME_PREFIX)


def _dedup_characters(session_id: str) -> int:
    """Merge near-identical characters discovered in the same session.

    Only touches characters whose ``metadata.session_id`` matches *session_id*
    so named/seeded demo characters are never affected.
    Returns the number of duplicates removed.
    """
    candidates = [
        c for c in _characters
        if (c.get("metadata") or {}).get("session_id") == session_id
        and (c.get("metadata") or {}).get("feature")
    ]
    if len(candidates) < 2:
        return 0

    parent: dict[str, str] = {c["id"]: c["id"] for c in candidates}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # Union similar characters (transitively) to avoid pairwise-only misses.
    for i in range(len(candidates)):
        a = candidates[i]
        feat_a = (a.get("metadata") or {}).get("feature", [])
        for j in range(i + 1, len(candidates)):
            b = candidates[j]
            feat_b = (b.get("metadata") or {}).get("feature", [])
            if _feature_distance(feat_a, feat_b) <= 0.36:
                union(a["id"], b["id"])

    groups: dict[str, list[dict]] = {}
    for c in candidates:
        groups.setdefault(find(c["id"]), []).append(c)

    remap: dict[str, str] = {}
    for members in groups.values():
        if len(members) < 2:
            continue
        # Prefer manually renamed identities over auto-generated names, then appearance count.
        keep = sorted(
            members,
            key=lambda c: (
                1 if _is_auto_named(c) else 0,
                -int(c.get("appearance_count", 0)),
            ),
        )[0]
        for m in members:
            if m["id"] == keep["id"]:
                continue
            keep["appearance_count"] = int(keep.get("appearance_count", 0)) + int(m.get("appearance_count", 0))
            remap[m["id"]] = keep["id"]

    if not remap:
        return 0

    for sc in _scenes:
        if sc.get("session_id") != session_id:
            continue
        new_chars: list[dict] = []
        seen: set[str] = set()
        for ch in sc.get("characters", []):
            cid = str(ch.get("id"))
            target_id = remap.get(cid, cid)
            if target_id in seen:
                continue
            target = next((c for c in _characters if c.get("id") == target_id), ch)
            new_chars.append(_with_character_confidence(target))
            seen.add(target_id)
        sc["characters"] = new_chars

    for k, ids in list(_capture_frame_characters.items()):
        replaced = [remap.get(cid, cid) for cid in ids]
        _capture_frame_characters[k] = list(dict.fromkeys(replaced))

    to_remove = set(remap.keys())
    _characters[:] = [c for c in _characters if c["id"] not in to_remove]
    return len(to_remove)


def _dedup_existing_characters() -> int:
    """Consolidate duplicates from all discovered sessions."""
    session_ids = {
        str((c.get("metadata") or {}).get("session_id"))
        for c in _characters
        if (c.get("metadata") or {}).get("session_id")
    }
    merged = 0
    for sid in session_ids:
        merged += _dedup_characters(sid)
    if merged:
        _save_state()
    return merged


def _with_character_confidence(ch: dict) -> dict:
    out = dict(ch)
    conf = _character_confidence(ch)
    if conf is not None:
        out["confidence"] = conf
    thumb = out.get("thumbnail_url")
    if not thumb:
        out["thumbnail_url"] = _fallback_character_thumbnail(str(out.get("id", "char")))
    return out


def _match_or_create_character(
    session_id: str,
    frame_idx: int,
    crop_rgb: Image.Image,
    detection_confidence: float,
    detector_source: str,
) -> str:
    """Match a detected face to an existing character or create a new one."""
    crop_bgr = cv2.cvtColor(np.array(crop_rgb), cv2.COLOR_RGB2BGR)
    feat = _face_feature(crop_bgr)

    # Match only against characters discovered from captured sessions.
    best_id: Optional[str] = None
    best_dist = 999.0
    for ch in _characters:
        meta = ch.get("metadata") or {}
        stored = meta.get("feature")
        if not stored:
            continue
        d = _feature_distance(feat, stored)
        if d < best_dist:
            best_dist = d
            best_id = ch.get("id")

    if best_id is not None and best_dist <= 0.50:
        for ch in _characters:
            if ch.get("id") == best_id:
                prev_count = int(ch.get("appearance_count", 0))
                prev_conf = _character_confidence(ch) or 0.0
                ch["appearance_count"] = prev_count + 1
                ch["confidence"] = ((prev_conf * prev_count) + detection_confidence) / max(1, prev_count + 1)
                meta = ch.get("metadata") or {}
                # Update feature template as exponential moving average (25% new sample)
                # so the reference stays fresh across lighting/pose changes
                stored_feat = meta.get("feature")
                if stored_feat and len(stored_feat) == len(feat):
                    alpha = 0.25
                    updated = [(1 - alpha) * s + alpha * f for s, f in zip(stored_feat, feat)]
                    norm = float(np.linalg.norm(updated))
                    if norm > 0:
                        updated = [v / norm for v in updated]
                    meta["feature"] = updated
                meta["last_seen_frame"] = frame_idx
                meta["last_session_id"] = session_id
                meta["source"] = detector_source
                meta["confidence"] = ch["confidence"]
                ch["metadata"] = meta
                return best_id

    # New discovered character.
    char_id = f"char-{uuid.uuid4().hex[:8]}"
    detected_idx = sum(1 for c in _characters if _is_auto_named(c)) + 1
    char_name = f"{AUTO_NAME_PREFIX} {detected_idx}"
    char_dir = DATA_DIR / session_id / "characters"
    char_dir.mkdir(parents=True, exist_ok=True)
    char_path = char_dir / f"{char_id}.jpg"
    crop_rgb.save(str(char_path), "JPEG", quality=90)

    _characters.append({
        "id": char_id,
        "name": char_name,
        "description": "Auto-detected from capture (face-based matcher).",
        "appearance_count": 1,
        "confidence": detection_confidence,
        "first_seen_at": _now(),
        "thumbnail_url": f"/data/sessions/{session_id}/characters/{char_id}.jpg",
        "metadata": {
            "source": detector_source,
            "session_id": session_id,
            "first_seen_frame": frame_idx,
            "confidence": detection_confidence,
            "feature": feat,
        },
    })
    return char_id


def _detect_characters(session_id: str, frame_idx: int, pil_img: Image.Image) -> list[str]:
    """Detect likely anime characters (faces) and track them across frames."""
    bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    cascade = _get_face_cascade()

    faces = cascade.detectMultiScale(
        gray,
        scaleFactor=1.08,
        minNeighbors=4,
        minSize=(36, 36),
    )

    ids: list[str] = []
    detections: list[tuple[int, int, int, int, float, str]] = [
        (int(x), int(y), int(w), int(h), _face_confidence(pil_img.width, pil_img.height, int(w), int(h)), "opencv_haar_face")
        for (x, y, w, h) in faces
    ]

    # Fallback: if no faces are detected, try a person detector.
    if len(detections) == 0:
        hog = _get_hog_detector()
        rects, weights = hog.detectMultiScale(
            bgr,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05,
        )
        detections = [
            (int(x), int(y), int(w), int(h), _hog_confidence(float(wt)), "opencv_hog_person")
            for (x, y, w, h), wt in list(zip(rects, weights))[:4]
        ]

    for (x, y, w, h, conf, source) in detections:
        x1, y1 = max(0, int(x)), max(0, int(y))
        x2, y2 = min(pil_img.width, int(x + w)), min(pil_img.height, int(y + h))
        if x2 <= x1 or y2 <= y1:
            continue
        crop = pil_img.crop((x1, y1, x2, y2))
        ids.append(_match_or_create_character(session_id, frame_idx, crop, conf, source))

    # Deduplicate while preserving order.
    uniq_ids = list(dict.fromkeys(ids))
    return uniq_ids


def _get_character_refs(char_ids: list[str]) -> list[dict]:
    refs: list[dict] = []
    for cid in char_ids:
        ch = next((c for c in _characters if c.get("id") == cid), None)
        if ch:
            refs.append(_with_character_confidence(ch))
    return refs

# ── Routes — Capture ──────────────────────────────────────────────────────────

@app.get("/api/capture/status")
def get_capture_status():
    elapsed = 0
    if _capture_state["started_at"]:
        elapsed = int(time.time() - _capture_state["started_at"])

    return {
        "session_id": _capture_state["session_id"] or "",
        "status": _capture_state["status"],
        "total_frames": _capture_state["total_frames"],
        "characters_found": _capture_state["characters_found"],
        "scenes_detected": _capture_state["scenes_detected"],
        "elapsed_seconds": elapsed,
    }

def _capture_loop(
    session_id: str,
    fps: int,
    stop_event: threading.Event,
    adaptive_keyframes: bool,
    detection_stride: int,
    keyframe_threshold: float = 14.0,
    max_keyframe_gap_sec: float = 4.0,
):
    """Background thread: captures the screen using mss at the given FPS."""
    session_dir = DATA_DIR / session_id / "scenes"
    session_dir.mkdir(parents=True, exist_ok=True)

    interval = 1.0 / max(fps, 1)
    frame_idx = 0
    last_saved_gray: Optional[np.ndarray] = None
    last_saved_ts = 0.0
    _capture_frame_characters.clear()
    _capture_unique_characters.clear()

    with mss.mss() as sct:
        monitor = sct.monitors[1]  # primary monitor
        while not stop_event.is_set():
            t0 = time.monotonic()
            try:
                if frame_idx >= MAX_CAPTURE_FRAMES:
                    print(f"[capture] reached MAX_CAPTURE_FRAMES={MAX_CAPTURE_FRAMES}, stopping")
                    stop_event.set()
                    break

                raw = sct.grab(monitor)
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                # Resize to reasonable web size (max 1280 wide)
                if img.width > 1280:
                    ratio = 1280 / img.width
                    img = img.resize((1280, int(img.height * ratio)), Image.LANCZOS)

                keep_frame = True
                if adaptive_keyframes:
                    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
                    small_gray = cv2.resize(gray, (160, 90), interpolation=cv2.INTER_AREA)
                    now_ts = time.monotonic()
                    if last_saved_gray is not None:
                        diff = cv2.absdiff(small_gray, last_saved_gray)
                        diff_score = float(np.mean(diff))
                        due_keepalive = (now_ts - last_saved_ts) >= max_keyframe_gap_sec
                        keep_frame = diff_score >= keyframe_threshold or due_keepalive
                    if keep_frame:
                        last_saved_gray = small_gray
                        last_saved_ts = now_ts

                if not keep_frame:
                    elapsed = time.monotonic() - t0
                    sleep_time = interval - elapsed
                    if sleep_time > 0:
                        stop_event.wait(sleep_time)
                    continue

                path = session_dir / f"scene_{frame_idx:04d}.jpg"
                img.save(str(path), "JPEG", quality=85)

                # Run detector every N saved frames in performance mode to reduce CPU spikes.
                if frame_idx % max(1, detection_stride) == 0:
                    try:
                        char_ids = _detect_characters(session_id, frame_idx, img)
                    except Exception as det_err:
                        print(f"[detect] frame {frame_idx} error: {det_err}")
                        char_ids = []
                else:
                    char_ids = _capture_frame_characters.get(frame_idx - 1, [])
                _capture_frame_characters[frame_idx] = char_ids
                for cid in char_ids:
                    _capture_unique_characters.add(cid)

                frame_idx += 1
                _capture_state["total_frames"] = frame_idx
                _capture_state["scenes_detected"] = frame_idx
                _capture_state["characters_found"] = len(_capture_unique_characters)
            except Exception as e:
                print(f"[capture] frame {frame_idx} error: {e}")

            # Sleep for remaining interval
            elapsed = time.monotonic() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                stop_event.wait(sleep_time)


@app.post("/api/capture/start")
def start_capture(req: CaptureStartRequest):
    global _capture_thread
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
        "scene_count": 0,
        "first_thumbnail_url": None,
        "capture_fps": None,
        "performance_mode": None,
        "adaptive_keyframes": None,
    }
    _sessions.insert(0, new_session)
    _save_state()

    effective_fps = req.fps
    adaptive_keyframes = bool(req.adaptive_keyframes)
    detection_stride = 1
    if req.performance_mode:
        # Keep output smoother while still lowering compute cost.
        effective_fps = max(effective_fps, 6)
        adaptive_keyframes = True
        detection_stride = 3

    new_session["capture_fps"] = effective_fps
    new_session["performance_mode"] = req.performance_mode
    new_session["adaptive_keyframes"] = adaptive_keyframes

    _capture_state.update({
        "session_id": session_id,
        "status": "capturing",
        "total_frames": 0,
        "characters_found": 0,
        "scenes_detected": 0,
        "started_at": time.time(),
        "fps": effective_fps,
        "performance_mode": req.performance_mode,
        "adaptive_keyframes": adaptive_keyframes,
        "detection_stride": detection_stride,
    })

    # Launch real screen capture in background thread
    _capture_stop_event.clear()
    _capture_thread = threading.Thread(
        target=_capture_loop,
        args=(session_id, effective_fps, _capture_stop_event, adaptive_keyframes, detection_stride),
        daemon=True,
    )
    _capture_thread.start()

    return {
        "session_id": session_id,
        "status": "capturing",
        "message": f"Capture started at {effective_fps} FPS (adaptive keyframes: {'on' if adaptive_keyframes else 'off'}, detection stride: {detection_stride})",
    }

@app.post("/api/capture/stop")
def stop_capture():
    global _capture_thread
    if _capture_state["status"] != "capturing":
        raise HTTPException(400, "No active capture session")

    # Stop the capture thread
    _capture_stop_event.set()
    if _capture_thread and _capture_thread.is_alive():
        _capture_thread.join(timeout=3)
    _capture_thread = None

    sid = _capture_state["session_id"]
    elapsed = int(time.time() - _capture_state["started_at"]) if _capture_state["started_at"] else 0
    total_frames = _capture_state["total_frames"]
    fps = _capture_state.get("fps", 2)

    # Build scene entries from actual captured screenshots
    _generate_real_scenes(sid, total_frames, fps)

    # Merge characters that are too similar (same person, different crops)
    n_merged = _dedup_characters(sid)
    if n_merged:
        print(f"[dedup] merged {n_merged} duplicate character(s) for session {sid[:8]}")

    for s in _sessions:
        if s["id"] == sid:
            s["status"] = "stopped"
            s["ended_at"] = _now()
            s["total_frames"] = total_frames
            scene_count = len([sc for sc in _scenes if sc["session_id"] == sid])
            s["scene_count"] = scene_count
            if scene_count > 0:
                s["first_thumbnail_url"] = f"/data/sessions/{sid}/scenes/scene_0000.jpg"
            break

    _capture_state.update({
        "status": "stopped",
        "session_id": None,
        "started_at": None,
    })
    _save_state()

    return {"status": "stopped", "message": f"Capture stopped — {total_frames} frames saved"}


def _generate_real_scenes(session_id: str, total_frames: int, fps: int):
    """Create scene entries from actual captured screenshots on disk."""
    session_dir = DATA_DIR / session_id / "scenes"
    if not session_dir.exists():
        return

    # List all captured JPEG files sorted by name
    files = sorted(session_dir.glob("scene_*.jpg"))
    if not files:
        return

    interval = 1.0 / max(fps, 1)  # seconds between frames

    # Protect memory/API payload size for long recordings by downsampling scene rows.
    stride = max(1, int(np.ceil(len(files) / MAX_SCENES_PER_SESSION)))
    sampled = files[::stride]

    for i, fpath in enumerate(sampled):
        original_idx = i * stride
        scene_id = str(uuid.uuid4())
        start_time = original_idx * interval
        end_time = min((original_idx + stride) * interval, len(files) * interval)
        frame_char_ids = _capture_frame_characters.get(original_idx, [])
        _scenes.append({
            "id": scene_id,
            "session_id": session_id,
            "scene_index": i,
            "start_time": start_time,
            "end_time": end_time,
            "thumbnail_url": f"/data/sessions/{session_id}/scenes/{fpath.name}",
            "description": f"Screen capture frame {original_idx + 1}",
            "location": "Desktop",
            "characters": _get_character_refs(frame_char_ids),
            "items": [],
        })

# ── Routes — Characters ───────────────────────────────────────────────────────

@app.get("/api/characters")
def list_characters(
    sort_by: str = Query("appearance_count"),
    limit: int = Query(50),
    offset: int = Query(0),
):
    _dedup_existing_characters()
    chars = list(_characters)
    chars = [_with_character_confidence(c) for c in chars]
    if sort_by == "name":
        chars.sort(key=lambda c: c["name"])
    elif sort_by == "first_seen_at":
        chars.sort(key=lambda c: c["first_seen_at"], reverse=True)
    elif sort_by == "confidence":
        chars.sort(key=lambda c: c.get("confidence", 0), reverse=True)
    else:
        chars.sort(key=lambda c: c["appearance_count"], reverse=True)
    return chars[offset: offset + limit]

@app.get("/api/characters/{character_id}")
def get_character(character_id: str):
    char = next((c for c in _characters if c["id"] == character_id), None)
    if not char:
        raise HTTPException(404, "Character not found")
    return {
        **_with_character_confidence(char),
        "appearances": [
            {"id": str(uuid.uuid4()), "scene_id": "scene-001", "timestamp": 65.0, "confidence": 0.94, "bbox": None},
            {"id": str(uuid.uuid4()), "scene_id": "scene-002", "timestamp": 205.0, "confidence": 0.91, "bbox": None},
        ],
        "related_characters": [_with_character_confidence(c) for c in _characters if c["id"] != character_id][:3],
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
    _save_state()
    return _with_character_confidence(char)

@app.delete("/api/characters/{character_id}")
def delete_character(character_id: str):
    global _characters, _scenes
    before = len(_characters)
    _characters = [c for c in _characters if c["id"] != character_id]
    if len(_characters) == before:
        raise HTTPException(404, "Character not found")
    # Remove from all scene character lists
    for sc in _scenes:
        sc["characters"] = [
            ch for ch in sc.get("characters", [])
            if ch.get("id") != character_id
        ]
    _save_state()
    return {"status": "deleted"}

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
    # Always include scene_count based on actual scenes
    session["scene_count"] = len([sc for sc in _scenes if sc["session_id"] == session_id])
    return session

@app.get("/api/sessions/{session_id}/scenes")
def get_session_scenes(session_id: str):
    return [s for s in _scenes if s["session_id"] == session_id]

@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    global _sessions, _scenes
    before = len(_sessions)
    _sessions = [s for s in _sessions if s["id"] != session_id]
    if len(_sessions) == before:
        raise HTTPException(404, "Session not found")

    # Remove scenes from this session.
    _scenes = [sc for sc in _scenes if sc.get("session_id") != session_id]

    # Remove files on disk for this session.
    session_dir = DATA_DIR / session_id
    if session_dir.exists():
        for p in sorted(session_dir.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink(missing_ok=True)
            else:
                p.rmdir()
        session_dir.rmdir()

    _save_state()
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
    _save_state()
    return new_arc

# ── Placeholder image generator ───────────────────────────────────────────────

# Anime-inspired color palette for scene placeholders
_SCENE_COLORS = [
    (75, 0, 130),    # deep indigo
    (139, 0, 0),     # dark red
    (0, 100, 0),     # dark green
    (25, 25, 112),   # midnight blue
    (128, 0, 128),   # purple
    (139, 69, 19),   # saddle brown
    (0, 128, 128),   # teal
    (72, 61, 139),   # dark slate blue
    (178, 34, 34),   # firebrick
    (47, 79, 79),    # dark slate gray
]

def _make_png(width: int, height: int, r: int, g: int, b: int,
              label: str = "", sub: str = "") -> bytes:
    """Generate a minimal PNG image with a gradient background and text overlay.
    
    Pure Python — no Pillow/PIL dependency.
    Creates a simple gradient with a darker bottom for cinematic feel.
    """
    # Build raw pixel rows (RGBA) with vertical gradient
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter: None
        t = y / max(height - 1, 1)  # 0 at top, 1 at bottom
        darken = 1.0 - 0.5 * t      # darken toward bottom
        pr = max(0, min(255, int(r * darken)))
        pg = max(0, min(255, int(g * darken)))
        pb = max(0, min(255, int(b * darken)))
        for _x in range(width):
            raw.extend((pr, pg, pb, 255))

    # Draw a simple text-like centered rectangle block as a label indicator
    # (We can't render real text without PIL, but we can draw geometric shapes)
    # Draw a semi-transparent dark bar across the center for the "label area"
    bar_h = height // 5
    bar_y_start = (height - bar_h) // 2
    for y in range(bar_y_start, bar_y_start + bar_h):
        row_offset = y * (1 + width * 4) + 1  # +1 for filter byte
        for x in range(width):
            px = row_offset + x * 4
            # Blend with semi-transparent black
            raw[px]     = raw[px]     // 2
            raw[px + 1] = raw[px + 1] // 2
            raw[px + 2] = raw[px + 2] // 2

    # Draw a small white rectangle as a "play" icon in the center
    icon_w, icon_h = min(20, width // 8), min(24, height // 8)
    cx, cy = width // 2 - icon_w // 2, height // 2 - icon_h // 2
    for y in range(cy, cy + icon_h):
        if y < 0 or y >= height:
            continue
        row_offset = y * (1 + width * 4) + 1
        for x in range(cx, cx + icon_w):
            if x < 0 or x >= width:
                continue
            # Triangle shape: only draw if x is within the triangle at this row
            rel_y = (y - cy) / max(icon_h - 1, 1)
            tri_width = int(icon_w * (0.5 - abs(rel_y - 0.5)) * 2)
            rel_x = x - cx
            if rel_x < (icon_w - tri_width) // 2 or rel_x >= (icon_w + tri_width) // 2:
                continue
            px = row_offset + x * 4
            raw[px] = 255
            raw[px + 1] = 255
            raw[px + 2] = 255
            raw[px + 3] = 200

    # Encode as PNG
    def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    idat = zlib.compress(bytes(raw), 6)

    out = b"\x89PNG\r\n\x1a\n"
    out += _png_chunk(b"IHDR", ihdr)
    out += _png_chunk(b"IDAT", idat)
    out += _png_chunk(b"IEND", b"")
    return out


@app.get("/api/placeholder/{scene_index}")
def placeholder_image(scene_index: int, w: int = Query(640), h: int = Query(360)):
    """Generate a placeholder scene thumbnail image."""
    w = min(w, 1280)
    h = min(h, 720)
    color = _SCENE_COLORS[scene_index % len(_SCENE_COLORS)]
    png_data = _make_png(w, h, *color, label=f"Scene {scene_index + 1}")
    return Response(content=png_data, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


@app.get("/data/{path:path}")
def serve_data(path: str):
    """Serve captured screenshots and other session data from disk."""
    base_dir = (pathlib.Path(__file__).parent / "data").resolve()
    file_path = (base_dir / path).resolve()
    # Guard against path traversal attacks
    if not str(file_path).startswith(str(base_dir)):
        raise HTTPException(403, "Access denied")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, f"File not found: {path}")
    # Determine media type
    suffix = file_path.suffix.lower()
    media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    media_type = media_types.get(suffix, "application/octet-stream")
    return FileResponse(str(file_path), media_type=media_type,
                        headers={"Cache-Control": "public, max-age=3600"})


# Load persisted state on startup.
_load_state()

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("\n🎌  Ani-Log Mock Backend starting on http://localhost:8000")
    print("📖  Docs available at http://localhost:8000/docs\n")
    uvicorn.run("mock_server:app", host="0.0.0.0", port=8000, reload=True)
