"""Capture session routes — start/stop screen capture, get status."""

import asyncio
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from loguru import logger

from app.models.schemas import CaptureStartRequest, CaptureStartResponse, CaptureStatusResponse
from app.services.frame_processor import get_frame_processor
from app.services.scene_analyzer import get_scene_analyzer
from app.services.vector_store import get_vector_store

router = APIRouter()

# Active capture task reference
_capture_task: asyncio.Task | None = None


@router.post("/start", response_model=CaptureStartResponse)
async def start_capture(request: CaptureStartRequest):
    """Start a new screen capture session."""
    global _capture_task

    processor = get_frame_processor()
    if processor.is_running:
        raise HTTPException(400, "Capture session already running")

    session_id = str(uuid.uuid4())

    # Determine source — use "zmq" when C++ engine is expected
    source = request.source

    # Start capture in background task (fps + title forwarded)
    _capture_task = asyncio.create_task(
        processor.start_capture(
            session_id=session_id,
            source=source,
            fps=request.fps,
            title=request.title,
        )
    )

    logger.info(f"Capture session started: {session_id} (source={source}, fps={request.fps})")

    return CaptureStartResponse(
        session_id=session_id,
        status="capturing",
        message=f"Capture started at {request.fps} FPS via {source}",
    )


@router.post("/stop")
async def stop_capture():
    """Stop the current capture session."""
    processor = get_frame_processor()
    if not processor.is_running:
        raise HTTPException(400, "No active capture session")

    await processor.stop_capture()

    return {"status": "stopped", "message": "Capture session stopped"}


@router.get("/status", response_model=CaptureStatusResponse)
async def get_status():
    """Get current capture session status."""
    processor = get_frame_processor()
    stats = processor.stats
    scene_analyzer = get_scene_analyzer()

    # ChromaDB may not be running — default to 0 gracefully
    try:
        vector_store = get_vector_store()
        characters_found = vector_store.get_character_count()
    except Exception:
        characters_found = 0

    return CaptureStatusResponse(
        session_id=stats.get("session_id") or None,
        status="capturing" if stats["running"] else "idle",
        total_frames=stats["frame_count"],
        characters_found=characters_found,
        scenes_detected=scene_analyzer.scene_count,
        elapsed_seconds=stats["elapsed_seconds"],
    )


@router.websocket("/ws")
async def capture_websocket(websocket: WebSocket):
    """WebSocket endpoint for live capture feed updates."""
    await websocket.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            processor = get_frame_processor()
            stats = processor.stats

            await websocket.send_json({
                "type": "status",
                "data": {
                    "running": stats["running"],
                    "frame_count": stats["frame_count"],
                    "elapsed": stats["elapsed_seconds"],
                },
            })

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
