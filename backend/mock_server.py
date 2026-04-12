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
import urllib.parse
import urllib.request
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
    "skipped_frames": 0,
    "error_frames": 0,
    "characters_found": 0,
    "scenes_detected": 0,
    "started_at": None,
}

_capture_thread: Optional[threading.Thread] = None
_capture_stop_event = threading.Event()
_capture_frame_characters: dict[int, list[str]] = {}
_capture_unique_characters: set[str] = set()
_recent_detections: list[dict[str, Any]] = []
_pending_candidates: dict[str, list[dict[str, Any]]] = {}
_face_cascade: Any = None
_hog_detector: Any = None
_insightface_detector: Any = None

AUTO_NAME_PREFIX = "Detected Character"
UNKNOWN_NAME_PREFIX = "Unknown Character"

GENERIC_SESSION_TITLES = {
    "my anime session",
    "character detection validation",
    "character test",
    "balanced stress smoke",
    "perf stress smoke",
}

KNOWN_ANIME_ROSTERS: dict[str, list[str]] = {
    "attack on titan": [
        "Eren Yeager", "Mikasa Ackermann", "Armin Arlert", "Levi Ackermann",
        "Hange Zoe", "Erwin Smith", "Historia Reiss", "Reiner Braun",
        "Jean Kirstein", "Connie Springer", "Sasha Blouse", "Annie Leonhart",
    ],
    "demon slayer": [
        "Tanjiro Kamado", "Nezuko Kamado", "Zenitsu Agatsuma", "Inosuke Hashibira",
        "Kyojuro Rengoku", "Giyu Tomioka", "Shinobu Kocho", "Tengen Uzui",
    ],
    "jujutsu kaisen": [
        "Yuji Itadori", "Megumi Fushiguro", "Nobara Kugisaki", "Satoru Gojo",
        "Suguru Geto", "Kento Nanami", "Maki Zenin", "Yuta Okkotsu",
    ],
    "takagi": [
        "Takagi", "Nishikata", "Mina Hibino", "Sanae Tsukimoto", "Yukari Tenkawa",
    ],
    "karakai jouzu no takagi": [
        "Takagi", "Nishikata", "Mina Hibino", "Sanae Tsukimoto", "Yukari Tenkawa",
    ],
}

_roster_cache: dict[str, list[str]] = {}
_roster_entry_cache: dict[str, list[dict[str, Optional[str]]]] = {}

# Optional CLIP labeling stack (lazy loaded)
_torch = None
_open_clip = None
_clip_model = None
_clip_preprocess = None
_clip_tokenizer = None
_clip_device = "cpu"

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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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


def _get_insightface_detector() -> Any:
    """Lazy-load InsightFace detector (popular robust face detector)."""
    global _insightface_detector
    if _insightface_detector is not None:
        return _insightface_detector
    try:
        from insightface.app import FaceAnalysis  # noqa: PLC0415

        app = FaceAnalysis(providers=["CPUExecutionProvider"])
        app.prepare(ctx_id=-1, det_size=(640, 640))
        _insightface_detector = app
        return _insightface_detector
    except Exception:
        _insightface_detector = False
        return None


def _detect_faces_insightface(bgr: np.ndarray) -> list[tuple[int, int, int, int, float, str]]:
    detector = _get_insightface_detector()
    if detector is None:
        return []
    out: list[tuple[int, int, int, int, float, str]] = []
    try:
        faces = detector.get(bgr)
    except Exception:
        return []
    for f in faces:
        if not hasattr(f, "bbox"):
            continue
        x1, y1, x2, y2 = [int(v) for v in f.bbox.tolist()]
        w = max(1, x2 - x1)
        h = max(1, y2 - y1)
        score = float(getattr(f, "det_score", 0.9))
        out.append((x1, y1, w, h, _clamp01(score), "insightface"))
    return out


def _smart_character_crop(pil_img: Image.Image, box: tuple[int, int, int, int]) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Refine a detection box so saved thumbnail focuses on visible character region."""
    x1, y1, w, h = box
    x2, y2 = x1 + w, y1 + h
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(pil_img.width, x2), min(pil_img.height, y2)
    if x2 <= x1 or y2 <= y1:
        return pil_img.crop((0, 0, min(64, pil_img.width), min(64, pil_img.height))), (0, 0, min(64, pil_img.width), min(64, pil_img.height))

    # Expand slightly upward and around to include hairstyle/head context.
    bw, bh = x2 - x1, y2 - y1
    ex = int(bw * 0.18)
    ey_top = int(bh * 0.30)
    ey_bottom = int(bh * 0.12)
    rx1 = max(0, x1 - ex)
    ry1 = max(0, y1 - ey_top)
    rx2 = min(pil_img.width, x2 + ex)
    ry2 = min(pil_img.height, y2 + ey_bottom)

    crop = pil_img.crop((rx1, ry1, rx2, ry2))
    arr = np.array(crop.convert("RGB"), dtype=np.uint8)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # Use edges to remove low-information blank borders.
    edges = cv2.Canny(gray, 60, 140)
    ys, xs = np.where(edges > 0)
    if len(xs) > 30 and len(ys) > 30:
        lx = int(np.percentile(xs, 3))
        rx = int(np.percentile(xs, 97))
        ty = int(np.percentile(ys, 3))
        by = int(np.percentile(ys, 97))
        if rx > lx + 20 and by > ty + 20:
            # small margin after trim
            mx = max(2, int((rx - lx) * 0.08))
            my = max(2, int((by - ty) * 0.08))
            lx = max(0, lx - mx)
            rx = min(arr.shape[1], rx + mx)
            ty = max(0, ty - my)
            by = min(arr.shape[0], by + my)
            crop = Image.fromarray(arr[ty:by, lx:rx])
            rx1, ry1 = rx1 + lx, ry1 + ty
            rx2, ry2 = rx1 + (rx - lx), ry1 + (by - ty)

    return crop, (rx1, ry1, rx2, ry2)


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


def _bbox_iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0

    area_a = max(1, aw * ah)
    area_b = max(1, bw * bh)
    union = area_a + area_b - inter
    return float(inter / max(1, union))


def _nms_detections(
    detections: list[tuple[int, int, int, int, float, str]],
    iou_threshold: float = 0.35,
) -> list[tuple[int, int, int, int, float, str]]:
    """Suppress overlapping detections to avoid duplicate character creation."""
    if not detections:
        return []

    dets = sorted(detections, key=lambda d: d[4], reverse=True)
    kept: list[tuple[int, int, int, int, float, str]] = []
    for d in dets:
        box_d = (d[0], d[1], d[2], d[3])
        if any(_bbox_iou(box_d, (k[0], k[1], k[2], k[3])) >= iou_threshold for k in kept):
            continue
        kept.append(d)
    return kept


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


def _normalize_title(title: str) -> str:
    norm = title.lower().replace("—", "-")
    norm = " ".join(norm.replace("_", " ").replace("-", " ").split())
    return norm.strip()


def _get_session_title(session_id: str) -> str:
    session = next((s for s in _sessions if s.get("id") == session_id), None)
    if not session:
        return ""
    return str(session.get("title") or "")


def _fetch_jikan_roster_entries(title: str, limit: int = 12) -> list[dict[str, Optional[str]]]:
    """Best-effort roster fetch from Jikan API based on session title."""
    try:
        q = urllib.parse.quote(title)
        search_url = f"https://api.jikan.moe/v4/anime?q={q}&limit=1"
        with urllib.request.urlopen(search_url, timeout=3.5) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
        data = payload.get("data") or []
        if not data:
            return []
        anime_id = data[0].get("mal_id")
        if not anime_id:
            return []

        char_url = f"https://api.jikan.moe/v4/anime/{anime_id}/characters"
        with urllib.request.urlopen(char_url, timeout=3.5) as resp:
            chars_payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
        rows = chars_payload.get("data") or []

        out: list[dict[str, Optional[str]]] = []
        seen: set[str] = set()
        for row in rows:
            char = row.get("character") or {}
            role = str(row.get("role") or "")
            name = str(char.get("name") or "").strip()
            if not name:
                continue
            if role not in ("Main", "Supporting"):
                continue
            if name in seen:
                continue
            images = char.get("images") or {}
            jpg = images.get("jpg") or {}
            webp = images.get("webp") or {}
            image_url = (
                jpg.get("image_url")
                or jpg.get("large_image_url")
                or webp.get("image_url")
                or webp.get("large_image_url")
            )
            out.append({"name": name, "image_url": str(image_url) if image_url else None})
            seen.add(name)
            if len(out) >= limit:
                break
        return out
    except Exception:
        return []


def _get_session_roster_entries(session_id: str) -> list[dict[str, Optional[str]]]:
    title = _get_session_title(session_id)
    norm = _normalize_title(title)
    if not norm:
        return []

    if norm in _roster_entry_cache:
        return _roster_entry_cache[norm]

    for key, roster in KNOWN_ANIME_ROSTERS.items():
        if key in norm:
            entries = [{"name": n, "image_url": None} for n in roster]
            _roster_entry_cache[norm] = entries
            return entries

    if norm in GENERIC_SESSION_TITLES:
        _roster_entry_cache[norm] = []
        return []

    fetched = _fetch_jikan_roster_entries(title)
    _roster_entry_cache[norm] = fetched
    return fetched


def _get_session_roster(session_id: str) -> list[str]:
    title = _get_session_title(session_id)
    norm = _normalize_title(title)
    if not norm:
        return []
    if norm in _roster_cache:
        return _roster_cache[norm]
    entries = _get_session_roster_entries(session_id)
    names = [str(e.get("name") or "").strip() for e in entries if str(e.get("name") or "").strip()]
    _roster_cache[norm] = names
    return names


def _next_character_name_for_session(session_id: str) -> str:
    roster = _get_session_roster(session_id)
    if roster:
        used = {
            str(c.get("name", "")).strip()
            for c in _characters
            if (c.get("metadata") or {}).get("session_id") == session_id
        }
        for candidate in roster:
            if candidate not in used:
                return candidate

    unknown_idx = 1 + sum(
        1
        for c in _characters
        if (c.get("metadata") or {}).get("session_id") == session_id
        and str(c.get("name", "")).startswith(UNKNOWN_NAME_PREFIX)
    )
    return f"{UNKNOWN_NAME_PREFIX} {unknown_idx}"


def _get_torch():
    global _torch
    if _torch is None:
        try:
            import torch as _t  # noqa: PLC0415
            _torch = _t
        except Exception:
            _torch = False
    return None if _torch is False else _torch


def _get_open_clip():
    global _open_clip
    if _open_clip is None:
        try:
            import open_clip as _oc  # noqa: PLC0415
            _open_clip = _oc
        except Exception:
            _open_clip = False
    return None if _open_clip is False else _open_clip


def _ensure_clip_model() -> bool:
    global _clip_model, _clip_preprocess, _clip_tokenizer, _clip_device
    if _clip_model is not None and _clip_preprocess is not None and _clip_tokenizer is not None:
        return True

    torch = _get_torch()
    open_clip = _get_open_clip()
    if torch is None or open_clip is None:
        return False

    try:
        _clip_device = "cuda" if torch.cuda.is_available() else "cpu"
        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32",
            pretrained="laion2b_s34b_b79k",
            device=_clip_device,
        )
        tokenizer = open_clip.get_tokenizer("ViT-B-32")
        model.eval()
        _clip_model = model
        _clip_preprocess = preprocess
        _clip_tokenizer = tokenizer
        return True
    except Exception:
        return False


def _clip_embed_image(img: Image.Image) -> Optional[np.ndarray]:
    if not _ensure_clip_model():
        return None
    torch = _get_torch()
    if torch is None:
        return None
    try:
        with torch.no_grad():
            tensor = _clip_preprocess(img).unsqueeze(0).to(_clip_device)
            vec = _clip_model.encode_image(tensor)
            vec = vec / vec.norm(dim=-1, keepdim=True)
            return vec.cpu().numpy().flatten().astype(np.float32)
    except Exception:
        return None


def _download_image(url: str) -> Optional[Image.Image]:
    try:
        with urllib.request.urlopen(url, timeout=4.5) as resp:
            raw = resp.read()
        with Image.open(io.BytesIO(raw)) as im:
            return im.convert("RGB")
    except Exception:
        return None


def _is_good_character_crop(img: Image.Image) -> bool:
    w, h = img.size
    if w < 40 or h < 40:
        return False
    gray = np.array(img.convert("L"), dtype=np.uint8)
    # Basic focus check; blurry/noisy crops are not suitable for reliable naming.
    focus = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    return focus >= 35.0


def _clip_embed_texts(texts: list[str]) -> Optional[np.ndarray]:
    if not texts:
        return None
    if not _ensure_clip_model():
        return None
    torch = _get_torch()
    if torch is None:
        return None
    try:
        prompts = [f"anime portrait of {t}" for t in texts]
        with torch.no_grad():
            tok = _clip_tokenizer(prompts).to(_clip_device)
            vec = _clip_model.encode_text(tok)
            vec = vec / vec.norm(dim=-1, keepdim=True)
            return vec.cpu().numpy().astype(np.float32)
    except Exception:
        return None


def _resolve_thumbnail_local_path(url: Optional[str]) -> Optional[pathlib.Path]:
    if not url:
        return None
    base_dir = (pathlib.Path(__file__).parent / "data").resolve()
    u = str(url)
    if u.startswith("/data/"):
        rel = u[len("/data/"):]
        p = (base_dir / rel).resolve()
        if str(p).startswith(str(base_dir)) and p.exists():
            return p
    return None


def _assign_names_for_session(session_id: str) -> dict[str, Any]:
    """Assign best-effort character names for a session using roster + CLIP labeling."""
    roster_entries = _get_session_roster_entries(session_id)
    roster = [str(e.get("name") or "").strip() for e in roster_entries if str(e.get("name") or "").strip()]
    auto_chars = [
        c for c in _characters
        if (c.get("metadata") or {}).get("session_id") == session_id and _is_auto_named(c)
    ]
    if not auto_chars:
        return {"assigned": 0, "unknown": 0, "mode": "none"}

    if not roster:
        _compact_auto_character_names(session_id)
        unknown = sum(1 for c in auto_chars if str(c.get("name", "")).startswith(UNKNOWN_NAME_PREFIX))
        return {"assigned": 0, "unknown": unknown, "mode": "no_roster"}

    text_mat = _clip_embed_texts(roster)

    # Image-to-image labeling using roster portraits when available.
    roster_img_indices: list[int] = []
    roster_img_embs: list[np.ndarray] = []
    for idx, entry in enumerate(roster_entries):
        image_url = entry.get("image_url")
        if not image_url:
            continue
        ref_img = _download_image(str(image_url))
        if ref_img is None:
            continue
        rvec = _clip_embed_image(ref_img)
        if rvec is None:
            continue
        roster_img_indices.append(idx)
        roster_img_embs.append(rvec)
    roster_img_mat = np.stack(roster_img_embs) if roster_img_embs else None

    candidates: list[tuple[float, int, int]] = []

    for ci, ch in enumerate(auto_chars):
        path = _resolve_thumbnail_local_path(ch.get("thumbnail_url"))
        if path is None:
            continue
        try:
            with Image.open(path) as img:
                rgb = img.convert("RGB")
        except Exception:
            continue

        if not _is_good_character_crop(rgb):
            continue

        ivec = _clip_embed_image(rgb)
        if ivec is None:
            continue

        # Prefer image-image similarity when roster portraits are available.
        if roster_img_mat is not None:
            sims_img = roster_img_mat @ ivec
            for k, score in enumerate(sims_img.tolist()):
                ni = roster_img_indices[k]
                # Slight boost to image-match path over text-only path.
                candidates.append((float(score + 0.05), ci, ni))

        if text_mat is not None:
            sims_txt = text_mat @ ivec
            for ni, score in enumerate(sims_txt.tolist()):
                candidates.append((float(score), ci, ni))

    assigned_char: set[int] = set()
    assigned_name: set[int] = set()
    accepted: list[tuple[int, int, float]] = []

    # Greedy bipartite assignment.
    for score, ci, ni in sorted(candidates, key=lambda x: x[0], reverse=True):
        if ci in assigned_char or ni in assigned_name:
            continue
        if score < 0.23:
            continue
        assigned_char.add(ci)
        assigned_name.add(ni)
        accepted.append((ci, ni, score))

    # Apply assigned names first.
    for ci, ni, score in accepted:
        ch = auto_chars[ci]
        ch["name"] = roster[ni]
        meta = ch.get("metadata") or {}
        meta["auto_name"] = True
        meta["name_source"] = "clip_label"
        meta["name_score"] = round(float(score), 4)
        ch["metadata"] = meta

    # Remaining auto chars become Unknown N.
    unknown_idx = 1
    assigned_ids = {id(auto_chars[ci]) for ci, _, _ in accepted}
    for ch in auto_chars:
        if id(ch) in assigned_ids:
            continue
        ch["name"] = f"{UNKNOWN_NAME_PREFIX} {unknown_idx}"
        meta = ch.get("metadata") or {}
        meta["auto_name"] = True
        meta["name_source"] = "unknown_fallback"
        ch["metadata"] = meta
        unknown_idx += 1

    # Refresh scene snapshots to show updated names immediately.
    for sc in _scenes:
        if sc.get("session_id") != session_id:
            continue
        seen: set[str] = set()
        refreshed: list[dict] = []
        for ch in sc.get("characters", []):
            cid = str(ch.get("id", ""))
            if not cid or cid in seen:
                continue
            real = next((c for c in _characters if str(c.get("id")) == cid), ch)
            refreshed.append(_with_character_confidence(real))
            seen.add(cid)
        sc["characters"] = refreshed

    return {
        "assigned": len(accepted),
        "unknown": max(0, len(auto_chars) - len(accepted)),
        "mode": "clip" if candidates else "roster_only",
    }


def _create_character_from_detection(
    session_id: str,
    frame_idx: int,
    crop_rgb: Image.Image,
    detection_confidence: float,
    detector_source: str,
    feat: list[float],
) -> str:
    """Persist a newly confirmed character identity."""
    char_id = f"char-{uuid.uuid4().hex[:8]}"
    char_name = _next_character_name_for_session(session_id)
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
            "auto_name": True,
        },
    })
    _compact_auto_character_names(session_id)
    return char_id


def _is_auto_named(ch: dict) -> bool:
    meta = ch.get("metadata") or {}
    if bool(meta.get("auto_name")):
        return True
    name = str(ch.get("name", ""))
    return name.startswith(AUTO_NAME_PREFIX) or name.startswith(UNKNOWN_NAME_PREFIX)


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
        _compact_auto_character_names(session_id)
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
            dist = _feature_distance(feat_a, feat_b)
            a_count = int(a.get("appearance_count", 0))
            b_count = int(b.get("appearance_count", 0))
            # Adaptive merge:
            # - strict for stable identities
            # - more permissive for low-count auto detections (common duplicates)
            threshold = 0.72 if min(a_count, b_count) >= 4 else 0.92
            if dist <= threshold:
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

    # Merge exact duplicate names inside the same session too.
    by_name: dict[str, list[dict]] = {}
    for c in _characters:
        if (c.get("metadata") or {}).get("session_id") != session_id:
            continue
        nm = str(c.get("name") or "").strip().casefold()
        if not nm:
            continue
        by_name.setdefault(nm, []).append(c)

    for members in by_name.values():
        if len(members) < 2:
            continue
        keep = sorted(members, key=lambda c: int(c.get("appearance_count", 0)), reverse=True)[0]
        for m in members:
            if m["id"] == keep["id"]:
                continue
            keep["appearance_count"] = int(keep.get("appearance_count", 0)) + int(m.get("appearance_count", 0))
            remap[m["id"]] = keep["id"]

    if not remap:
        _compact_auto_character_names(session_id)
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
    _compact_auto_character_names(session_id)
    return len(to_remove)


def _compact_auto_character_names(session_id: str) -> None:
    """Rename auto-generated names to a compact sequence per session.

    Keeps manually-assigned names unchanged while making auto labels stable.
    If the anime roster is known, assigns real character names first.
    """
    scoped = [
        c for c in _characters
        if (c.get("metadata") or {}).get("session_id") == session_id and _is_auto_named(c)
    ]
    scoped.sort(key=lambda c: int(c.get("appearance_count", 0)), reverse=True)

    roster = _get_session_roster(session_id)
    used_non_auto = {
        str(c.get("name", "")).strip()
        for c in _characters
        if (c.get("metadata") or {}).get("session_id") == session_id and not _is_auto_named(c)
    }

    if roster:
        r_idx = 0
        for ch in scoped:
            while r_idx < len(roster) and roster[r_idx] in used_non_auto:
                r_idx += 1
            if r_idx < len(roster):
                ch["name"] = roster[r_idx]
                used_non_auto.add(roster[r_idx])
                ch_meta = ch.get("metadata") or {}
                ch_meta["auto_name"] = True
                ch["metadata"] = ch_meta
                r_idx += 1
            else:
                break

    unknown_idx = 1
    for ch in scoped:
        if _is_auto_named(ch) and ch.get("name") in roster:
            continue
        ch["name"] = f"{UNKNOWN_NAME_PREFIX} {unknown_idx}"
        ch_meta = ch.get("metadata") or {}
        ch_meta["auto_name"] = True
        ch["metadata"] = ch_meta
        unknown_idx += 1


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


def _purge_repeated_characters() -> int:
    """Cleanup pass for persisted data: merge duplicates and remove stale refs."""
    merged = _dedup_existing_characters()

    # Cross-session merge for auto-detected identities with very close features.
    global_candidates = [
        c for c in _characters
        if (c.get("metadata") or {}).get("feature") and _is_auto_named(c)
    ]

    if len(global_candidates) >= 2:
        parent: dict[str, str] = {c["id"]: c["id"] for c in global_candidates}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for i in range(len(global_candidates)):
            a = global_candidates[i]
            fa = (a.get("metadata") or {}).get("feature", [])
            for j in range(i + 1, len(global_candidates)):
                b = global_candidates[j]
                fb = (b.get("metadata") or {}).get("feature", [])
                if _feature_distance(fa, fb) <= 0.84:
                    union(a["id"], b["id"])

        groups: dict[str, list[dict]] = {}
        for c in global_candidates:
            groups.setdefault(find(c["id"]), []).append(c)

        remap: dict[str, str] = {}
        for members in groups.values():
            if len(members) < 2:
                continue
            keep = sorted(members, key=lambda c: int(c.get("appearance_count", 0)), reverse=True)[0]
            for m in members:
                if m["id"] == keep["id"]:
                    continue
                keep["appearance_count"] = int(keep.get("appearance_count", 0)) + int(m.get("appearance_count", 0))
                remap[m["id"]] = keep["id"]

        if remap:
            for sc in _scenes:
                seen: set[str] = set()
                new_chars: list[dict] = []
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
            _characters[:] = [c for c in _characters if c.get("id") not in to_remove]
            merged += len(to_remove)

    valid_ids = {str(c.get("id")) for c in _characters}

    # Drop stale/duplicate scene references.
    for sc in _scenes:
        seen: set[str] = set()
        cleaned: list[dict] = []
        for ch in sc.get("characters", []):
            cid = str(ch.get("id", ""))
            if not cid or cid not in valid_ids or cid in seen:
                continue
            seen.add(cid)
            real = next((c for c in _characters if str(c.get("id")) == cid), ch)
            cleaned.append(_with_character_confidence(real))
        sc["characters"] = cleaned

    for k, ids in list(_capture_frame_characters.items()):
        cleaned_ids = [cid for cid in ids if cid in valid_ids]
        _capture_frame_characters[k] = list(dict.fromkeys(cleaned_ids))

    # Prune weak one-off auto identities that commonly come from false detections.
    pruned = 0
    for sid in {
        str((c.get("metadata") or {}).get("session_id"))
        for c in _characters
        if (c.get("metadata") or {}).get("session_id")
    }:
        session_chars = [
            c for c in _characters
            if (c.get("metadata") or {}).get("session_id") == sid and _is_auto_named(c)
        ]
        if len(session_chars) < 3:
            continue

        keep_ids: set[str] = set()
        for c in session_chars:
            conf = _character_confidence(c) or 0.0
            count = int(c.get("appearance_count", 0))
            if count >= 2 or conf >= 0.86:
                keep_ids.add(str(c.get("id")))

        # Ensure we keep at least one auto identity per session.
        if not keep_ids and session_chars:
            best = sorted(session_chars, key=lambda c: int(c.get("appearance_count", 0)), reverse=True)[0]
            keep_ids.add(str(best.get("id")))

        remove_ids = {
            str(c.get("id"))
            for c in session_chars
            if str(c.get("id")) not in keep_ids
        }
        if not remove_ids:
            continue

        _characters[:] = [c for c in _characters if str(c.get("id")) not in remove_ids]
        pruned += len(remove_ids)

        for sc in _scenes:
            seen: set[str] = set()
            cleaned: list[dict] = []
            for ch in sc.get("characters", []):
                cid = str(ch.get("id", ""))
                if cid in remove_ids or cid in seen:
                    continue
                real = next((c for c in _characters if str(c.get("id")) == cid), ch)
                cleaned.append(_with_character_confidence(real))
                seen.add(cid)
            sc["characters"] = cleaned

        _compact_auto_character_names(sid)

    return merged + pruned


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
    bbox: tuple[int, int, int, int],
) -> Optional[str]:
    """Match a detected face to an existing character or create a new one."""
    crop_bgr = cv2.cvtColor(np.array(crop_rgb), cv2.COLOR_RGB2BGR)
    feat = _face_feature(crop_bgr)

    # Fast path: reuse the previous-frame identity if overlap + feature look close.
    for prev in _recent_detections:
        prev_id = str(prev.get("id", ""))
        prev_box = prev.get("bbox")
        prev_feat = prev.get("feature")
        if not prev_id or not isinstance(prev_box, tuple) or not isinstance(prev_feat, list):
            continue
        if _bbox_iou(bbox, prev_box) < 0.38:
            continue
        if _feature_distance(feat, prev_feat) <= 0.68:
            for ch in _characters:
                if ch.get("id") == prev_id:
                    prev_count = int(ch.get("appearance_count", 0))
                    prev_conf = _character_confidence(ch) or 0.0
                    ch["appearance_count"] = prev_count + 1
                    ch["confidence"] = ((prev_conf * prev_count) + detection_confidence) / max(1, prev_count + 1)
                    meta = ch.get("metadata") or {}
                    meta["last_seen_frame"] = frame_idx
                    meta["last_session_id"] = session_id
                    meta["source"] = detector_source
                    meta["confidence"] = ch["confidence"]
                    meta["feature"] = feat
                    ch["metadata"] = meta
                    return prev_id

    # Match only against characters discovered from captured sessions.
    best_id: Optional[str] = None
    best_dist = 999.0
    for ch in _characters:
        meta = ch.get("metadata") or {}
        if meta.get("session_id") != session_id:
            continue
        stored = meta.get("feature")
        if not stored:
            continue
        d = _feature_distance(feat, stored)
        if d < best_dist:
            best_dist = d
            best_id = ch.get("id")

    if best_id is not None and best_dist <= 0.78:
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

    # Guardrail: ignore weak detections to prevent duplicate spam cards.
    if detection_confidence < 0.70:
        return None

    # Cap the number of auto identities per session to reduce duplicate spam.
    session_auto_chars = [
        c for c in _characters
        if (c.get("metadata") or {}).get("session_id") == session_id and _is_auto_named(c)
    ]
    if best_id is not None and len(session_auto_chars) >= 6:
        for ch in _characters:
            if ch.get("id") == best_id:
                prev_count = int(ch.get("appearance_count", 0))
                prev_conf = _character_confidence(ch) or 0.0
                ch["appearance_count"] = prev_count + 1
                ch["confidence"] = ((prev_conf * prev_count) + detection_confidence) / max(1, prev_count + 1)
                meta = ch.get("metadata") or {}
                meta["last_seen_frame"] = frame_idx
                meta["last_session_id"] = session_id
                meta["source"] = detector_source
                meta["confidence"] = ch["confidence"]
                ch["metadata"] = meta
                return best_id

    # New identity confirmation buffer: require repeated evidence before creating.
    pending = _pending_candidates.setdefault(session_id, [])
    pending[:] = [p for p in pending if frame_idx - int(p.get("last_frame", 0)) <= 15]

    matched_pending: Optional[dict[str, Any]] = None
    for p in pending:
        p_feat = p.get("feature")
        p_bbox = p.get("bbox")
        if not isinstance(p_feat, list) or not isinstance(p_bbox, tuple):
            continue
        if _feature_distance(feat, p_feat) <= 0.90 or _bbox_iou(bbox, p_bbox) >= 0.35:
            matched_pending = p
            break

    if matched_pending is None:
        pending.append({
            "feature": feat,
            "bbox": bbox,
            "hits": 1,
            "last_frame": frame_idx,
            "confidence": detection_confidence,
            "source": detector_source,
        })
        return None

    prev_hits = int(matched_pending.get("hits", 1))
    matched_pending["hits"] = prev_hits + 1
    matched_pending["last_frame"] = frame_idx
    matched_pending["bbox"] = bbox
    matched_pending["source"] = detector_source
    matched_pending["confidence"] = (
        (float(matched_pending.get("confidence", 0.0)) * prev_hits) + detection_confidence
    ) / max(1, prev_hits + 1)

    p_feat = matched_pending.get("feature") or feat
    if isinstance(p_feat, list) and len(p_feat) == len(feat):
        alpha = 0.3
        updated = [(1 - alpha) * s + alpha * f for s, f in zip(p_feat, feat)]
        norm = float(np.linalg.norm(updated))
        if norm > 0:
            updated = [v / norm for v in updated]
        matched_pending["feature"] = updated
    else:
        matched_pending["feature"] = feat

    # Require at least 3 consistent hits before creating a new DB character.
    if int(matched_pending.get("hits", 0)) < 3:
        return None

    pending.remove(matched_pending)
    return _create_character_from_detection(
        session_id=session_id,
        frame_idx=frame_idx,
        crop_rgb=crop_rgb,
        detection_confidence=float(matched_pending.get("confidence", detection_confidence)),
        detector_source=str(matched_pending.get("source", detector_source)),
        feat=(matched_pending.get("feature") or feat),
    )


def _detect_characters(session_id: str, frame_idx: int, pil_img: Image.Image) -> list[str]:
    """Detect likely anime characters (faces) and track them across frames."""
    bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    cascade = _get_face_cascade()

    ids: list[str] = []
    detections: list[tuple[int, int, int, int, float, str]] = _detect_faces_insightface(bgr)

    # Fallback to Haar if InsightFace isn't available.
    if len(detections) == 0:
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.08,
            minNeighbors=4,
            minSize=(36, 36),
        )
        detections = [
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

    detections = _nms_detections(detections)

    current_tracks: list[dict[str, Any]] = []
    for (x, y, w, h, conf, source) in detections:
        x1, y1 = max(0, int(x)), max(0, int(y))
        x2, y2 = min(pil_img.width, int(x + w)), min(pil_img.height, int(y + h))
        if x2 <= x1 or y2 <= y1:
            continue
        crop, refined_box = _smart_character_crop(pil_img, (x1, y1, x2 - x1, y2 - y1))
        if not _is_good_character_crop(crop):
            continue
        cid = _match_or_create_character(
            session_id=session_id,
            frame_idx=frame_idx,
            crop_rgb=crop,
            detection_confidence=conf,
            detector_source=source,
            bbox=(refined_box[0], refined_box[1], refined_box[2] - refined_box[0], refined_box[3] - refined_box[1]),
        )
        if cid:
            ids.append(cid)
            meta = next((c.get("metadata") for c in _characters if c.get("id") == cid), None) or {}
            feat = meta.get("feature")
            if isinstance(feat, list):
                current_tracks.append({
                    "id": cid,
                    "bbox": (refined_box[0], refined_box[1], refined_box[2] - refined_box[0], refined_box[3] - refined_box[1]),
                    "feature": feat,
                })

    global _recent_detections
    _recent_detections = current_tracks[:8]

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

    total_frames = int(_capture_state.get("total_frames", 0) or 0)
    effective_fps = 0.0
    if elapsed > 0:
        effective_fps = float(total_frames) / float(elapsed)

    return {
        "session_id": _capture_state["session_id"] or "",
        "status": _capture_state["status"],
        "total_frames": total_frames,
        "skipped_frames": int(_capture_state.get("skipped_frames", 0) or 0),
        "error_frames": int(_capture_state.get("error_frames", 0) or 0),
        "characters_found": _capture_state["characters_found"],
        "scenes_detected": _capture_state["scenes_detected"],
        "elapsed_seconds": elapsed,
        "effective_fps": round(effective_fps, 3),
    }

def _capture_loop(
    session_id: str,
    fps: int,
    stop_event: threading.Event,
    adaptive_keyframes: bool,
    detection_stride: int,
    keyframe_threshold: float = 14.0,
    max_keyframe_gap_sec: float = 2.0,
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
    global _recent_detections
    _recent_detections = []
    _pending_candidates[session_id] = []

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
                    _capture_state["skipped_frames"] = int(_capture_state.get("skipped_frames", 0)) + 1
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
                _capture_state["error_frames"] = int(_capture_state.get("error_frames", 0)) + 1
                print(f"[capture] frame {frame_idx} error: {e}")

            # Sleep for remaining interval
            elapsed = time.monotonic() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                stop_event.wait(sleep_time)

    _pending_candidates.pop(session_id, None)


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
        "skipped_frames": 0,
        "error_frames": 0,
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
        args=(session_id, effective_fps, _capture_stop_event, adaptive_keyframes, detection_stride, 14.0, 1.0 if req.performance_mode else 2.0),
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
        # Give the worker a short window to flush the latest counters.
        for _ in range(25):
            _capture_thread.join(timeout=0.2)
            if not _capture_thread.is_alive():
                break
    _capture_thread = None

    sid = _capture_state["session_id"]
    elapsed = int(time.time() - _capture_state["started_at"]) if _capture_state["started_at"] else 0
    total_frames = _capture_state["total_frames"]
    skipped_frames = int(_capture_state.get("skipped_frames", 0) or 0)
    error_frames = int(_capture_state.get("error_frames", 0) or 0)
    fps = _capture_state.get("fps", 2)
    effective_fps = (float(total_frames) / float(max(1, elapsed))) if elapsed > 0 else 0.0

    # Build scene entries from actual captured screenshots
    _generate_real_scenes(sid, total_frames, fps)

    # Merge characters that are too similar (same person, different crops)
    n_merged = _dedup_characters(sid)
    if n_merged:
        print(f"[dedup] merged {n_merged} duplicate character(s) for session {sid[:8]}")

    name_stats = _assign_names_for_session(sid)
    if name_stats.get("assigned", 0) or name_stats.get("unknown", 0):
        print(
            f"[naming] assigned={name_stats.get('assigned', 0)} "
            f"unknown={name_stats.get('unknown', 0)} mode={name_stats.get('mode')}"
        )

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

    return {
        "status": "stopped",
        "message": f"Capture stopped — {total_frames} frames saved",
        "total_frames": total_frames,
        "skipped_frames": skipped_frames,
        "error_frames": error_frames,
        "elapsed_seconds": elapsed,
        "effective_fps": round(effective_fps, 3),
    }


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
    include_demo: bool = Query(False),
):
    _dedup_existing_characters()
    chars = list(_characters)

    # If captured-session characters exist, hide seeded demo entries by default.
    has_session_chars = any((c.get("metadata") or {}).get("session_id") for c in chars)
    if has_session_chars and not include_demo:
        chars = [c for c in chars if (c.get("metadata") or {}).get("session_id")]

        # Consolidate named identities across sessions so the grid doesn't show
        # multiple cards for the same character name.
        merged_named: dict[str, dict] = {}
        unknown_rows: list[dict] = []
        for c in chars:
            name = str(c.get("name") or "").strip()
            if not name or name.startswith(UNKNOWN_NAME_PREFIX):
                unknown_rows.append(c)
                continue
            key = name.casefold()
            if key not in merged_named:
                merged_named[key] = dict(c)
                continue

            cur = merged_named[key]
            cur["appearance_count"] = int(cur.get("appearance_count", 0)) + int(c.get("appearance_count", 0))
            cur_conf = _character_confidence(cur) or 0.0
            new_conf = _character_confidence(c) or 0.0
            if new_conf > cur_conf and c.get("thumbnail_url"):
                cur["thumbnail_url"] = c.get("thumbnail_url")
            # Keep the representative id stable, but preserve merged evidence.
            cur_meta = cur.get("metadata") or {}
            cur_meta["merged_sources"] = int(cur_meta.get("merged_sources", 1)) + 1
            cur["metadata"] = cur_meta

        chars = list(merged_named.values()) + unknown_rows

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
        meta = char.get("metadata") or {}
        meta["auto_name"] = False
        char["metadata"] = meta
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

@app.get("/api/sessions")
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


@app.post("/api/sessions/{session_id}/auto-name")
def auto_name_session(session_id: str, anime_title: Optional[str] = Query(None)):
    """Retroactively dedup + rename a session's characters using a supplied anime title."""
    session = next((s for s in _sessions if s.get("id") == session_id), None)
    if not session:
        raise HTTPException(404, "Session not found")

    if anime_title and anime_title.strip():
        session["title"] = anime_title.strip()

    merged = _dedup_characters(session_id)
    name_stats = _assign_names_for_session(session_id)
    _save_state()

    names = [
        c.get("name")
        for c in _characters
        if (c.get("metadata") or {}).get("session_id") == session_id
    ]
    return {
        "status": "ok",
        "session_id": session_id,
        "title": session.get("title"),
        "merged": merged,
        "naming": name_stats,
        "character_count": len(names),
        "names": names,
    }


@app.post("/api/sessions/auto-name-all")
def auto_name_all_sessions(anime_title: Optional[str] = Query(None)):
    """Bulk repair all sessions: dedup + model-assisted naming.

    If anime_title is provided, it is applied only to generic session titles.
    """
    report: list[dict[str, Any]] = []
    total_merged = 0
    total_assigned = 0
    total_unknown = 0

    for s in _sessions:
        sid = str(s.get("id") or "")
        if not sid or sid.startswith("sess-"):
            continue

        title = str(s.get("title") or "")
        if anime_title and _normalize_title(title) in GENERIC_SESSION_TITLES:
            s["title"] = anime_title.strip()

        merged = _dedup_characters(sid)
        naming = _assign_names_for_session(sid)
        total_merged += merged
        total_assigned += int(naming.get("assigned", 0))
        total_unknown += int(naming.get("unknown", 0))

        report.append({
            "session_id": sid,
            "title": s.get("title"),
            "merged": merged,
            "naming": naming,
        })

    _save_state()
    return {
        "status": "ok",
        "sessions": report,
        "total_sessions": len(report),
        "total_merged": total_merged,
        "total_assigned": total_assigned,
        "total_unknown": total_unknown,
    }

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
        return [a for a in _story_arcs if str(a.get("session_id", "")) == session_id]
    return _story_arcs

@app.get("/api/summary/{arc_id}")
def get_story_arc(arc_id: str):
    arc = next((a for a in _story_arcs if a["id"] == arc_id), None)
    if not arc:
        raise HTTPException(404, "Story arc not found")
    return arc

@app.post("/api/summary/generate")
def generate_summary(req: SummaryGenerateRequest):
    session_scene_ids = [s["id"] for s in _scenes if s.get("session_id") == req.session_id]
    selected_scene_ids = req.scene_ids or session_scene_ids[:6]

    char_ids: list[str] = []
    for sc in _scenes:
        if sc.get("id") not in selected_scene_ids:
            continue
        for ch in sc.get("characters", []):
            cid = str(ch.get("id", "")).strip()
            if cid and cid not in char_ids:
                char_ids.append(cid)

    new_arc = {
        "id": str(uuid.uuid4()),
        "session_id": req.session_id,
        "title": f"Auto-generated Summary — Session {req.session_id[:8]}",
        "summary": "The episode opens with an ominous calm. Key characters converge on a fortified position as tensions escalate. A decisive confrontation follows, revealing long-hidden loyalties and setting the stage for an irreversible turning point in the narrative.",
        "character_ids": char_ids[:8],
        "scene_ids": selected_scene_ids,
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
_merged_at_startup = _purge_repeated_characters()
if _merged_at_startup:
    print(f"[startup] merged {_merged_at_startup} duplicate character(s)")
    _save_state()

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("\n🎌  Ani-Log Mock Backend starting on http://localhost:8000")
    print("📖  Docs available at http://localhost:8000/docs\n")
    uvicorn.run("mock_server:app", host="0.0.0.0", port=8000, reload=True)
