"""Application configuration via environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ANI_LOG_",   # avoids collisions with system env vars (e.g. DATABASE_URL)
        extra="ignore",
    )

    # ─── General ─────────────────────────────────────────────
    app_name: str = "Ani-Log"
    debug: bool = True
    log_level: str = "INFO"
    data_dir: Path = Path("./data")

    # ─── Database ────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./data/ani_log.db"

    # ─── ChromaDB ────────────────────────────────────────────
    chroma_host: str = "localhost"
    chroma_port: int = 8001          # port 8000 is now used by FastAPI itself
    chroma_collection_characters: str = "ani_log_characters"
    chroma_collection_scenes: str = "ani_log_scenes"
    chroma_collection_items: str = "ani_log_items"

    # ─── YOLO-World ──────────────────────────────────────────
    yolo_model: str = "yolov8x-worldv2"
    yolo_confidence: float = 0.35
    yolo_device: str = "cuda:0"

    # ─── CLIP ────────────────────────────────────────────────
    clip_model: str = "ViT-L-14"
    clip_pretrained: str = "openai"
    clip_device: str = "cuda:0"

    # ─── Multi-Object Tracking ───────────────────────────────
    tracker_max_age: int = 30
    tracker_min_hits: int = 3
    tracker_iou_threshold: float = 0.3
    reidentification_threshold: float = 0.75

    # ─── Frame Sampling ─────────────────────────────────────
    capture_fps: int = 2
    # Lower = more sensitive (scene change triggered more easily).
    # 0.4 was too strict — use 0.15 so moderate visual changes register as new scenes.
    scene_change_threshold: float = 0.15
    # Guaranteed keyframe every N seconds regardless of scene-change score.
    # Ensures multiple thumbnails even when on-screen content changes slowly.
    keyframe_interval: float = 5.0

    # ─── Ollama ──────────────────────────────────────────────
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # ─── ZeroMQ ──────────────────────────────────────────────
    zmq_capture_port: int = 5555
    zmq_result_port: int = 5556


settings = Settings()

# Ensure data directory exists
settings.data_dir.mkdir(parents=True, exist_ok=True)
