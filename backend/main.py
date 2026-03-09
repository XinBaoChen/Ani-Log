"""Ani-Log Backend — FastAPI Entry Point"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.core.config import settings
from app.core.database import init_db
from app.api.routes import capture, characters, scenes, search, summary
from app.api.routes import sessions as sessions_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("🎌 Ani-Log starting up...")
    await init_db()
    # Ensure data dir exists
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    logger.info("✅ Database initialized")
    yield
    logger.info("🛑 Ani-Log shutting down...")


app = FastAPI(
    title="Ani-Log",
    description="Autonomous Scene Contextualizer — searchable anime wiki builder",
    version="0.1.0",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ──────────────────────────────────────────────────
app.include_router(capture.router,          prefix="/api/capture",    tags=["Capture"])
app.include_router(characters.router,       prefix="/api/characters",  tags=["Characters"])
app.include_router(scenes.router,           prefix="/api/scenes",      tags=["Scenes"])
app.include_router(sessions_router.router,  prefix="/api/sessions",    tags=["Sessions"])
app.include_router(search.router,           prefix="/api/search",      tags=["Search"])
app.include_router(summary.router,          prefix="/api/summary",     tags=["Summary"])

# ─── Static files — serve captured thumbnails ────────────────
_data_dir = settings.data_dir.resolve()
_data_dir.mkdir(parents=True, exist_ok=True)
app.mount("/data", StaticFiles(directory=str(_data_dir)), name="data")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ani-log"}
