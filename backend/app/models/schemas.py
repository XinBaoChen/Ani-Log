"""Pydantic schemas for request/response validation."""

from datetime import datetime
from pydantic import BaseModel, Field


# ─── Capture ─────────────────────────────────────────────────
class CaptureStartRequest(BaseModel):
    title: str = "Untitled Session"
    fps: int = Field(default=2, ge=1, le=30)
    source: str = Field(default="screen", description="screen | window | file")
    source_path: str | None = None  # for file mode


class CaptureStartResponse(BaseModel):
    session_id: str
    status: str
    message: str


class CaptureStatusResponse(BaseModel):
    session_id: str | None = None
    status: str
    total_frames: int
    characters_found: int
    scenes_detected: int
    elapsed_seconds: float


# ─── Session ─────────────────────────────────────────────────
class SessionResponse(BaseModel):
    id: str
    title: str
    started_at: datetime
    ended_at: datetime | None = None
    total_frames: int
    status: str
    scene_count: int = 0
    first_thumbnail_url: str | None = None

    class Config:
        from_attributes = True


# ─── Character ───────────────────────────────────────────────
class CharacterBase(BaseModel):
    name: str = "Unknown"
    description: str | None = None


class CharacterResponse(CharacterBase):
    id: str
    appearance_count: int
    first_seen_at: datetime
    thumbnail_url: str | None = None
    metadata: dict | None = None

    class Config:
        from_attributes = True


class CharacterDetailResponse(CharacterResponse):
    appearances: list["AppearanceResponse"] = []
    related_characters: list["CharacterResponse"] = []


class CharacterUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


# ─── Scene ───────────────────────────────────────────────────
class SceneResponse(BaseModel):
    id: str
    session_id: str
    scene_index: int
    start_time: float
    end_time: float | None
    thumbnail_url: str | None = None
    description: str | None = None
    location: str | None = None
    characters: list[CharacterResponse] = []
    items: list["ItemResponse"] = []

    class Config:
        from_attributes = True


# ─── Appearance ──────────────────────────────────────────────
class AppearanceResponse(BaseModel):
    id: str
    scene_id: str
    timestamp: float
    confidence: float
    bbox: list[float] | None = None

    class Config:
        from_attributes = True


# ─── Item ────────────────────────────────────────────────────
class ItemResponse(BaseModel):
    id: str
    label: str
    category: str
    confidence: float
    timestamp: float
    bbox: list[float] | None = None

    class Config:
        from_attributes = True


# ─── Search ──────────────────────────────────────────────────
class SearchQuery(BaseModel):
    query: str
    category: str = Field(default="all", description="all | characters | scenes | items")
    limit: int = Field(default=20, ge=1, le=100)


class SearchResult(BaseModel):
    id: str
    type: str  # character | scene | item
    label: str
    description: str | None = None
    thumbnail_url: str | None = None
    score: float
    metadata: dict | None = None


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResult]


# ─── Summary ────────────────────────────────────────────────
class SummaryGenerateRequest(BaseModel):
    session_id: str
    detail_level: str = Field(default="medium", description="brief | medium | detailed")


class StoryArcResponse(BaseModel):
    id: str
    title: str
    summary: str
    character_ids: list[str] | None = None
    scene_ids: list[str] | None = None
    generated_at: datetime

    class Config:
        from_attributes = True


# ─── Detection (internal) ───────────────────────────────────
class Detection(BaseModel):
    """Raw detection from YOLO-World."""
    bbox: list[float]  # [x1, y1, x2, y2]
    label: str
    confidence: float
    track_id: int | None = None


class FrameAnalysis(BaseModel):
    """Result of analyzing a single frame."""
    frame_index: int
    timestamp: float
    detections: list[Detection]
    scene_changed: bool
    embedding: list[float] | None = None
