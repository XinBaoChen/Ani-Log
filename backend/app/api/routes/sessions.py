"""Sessions routes — list and inspect capture sessions."""

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.config import settings
from app.models.models import CaptureSession, Scene
from app.models.schemas import SessionResponse, SceneResponse
from app.api.routes.scenes import _thumb_url

router = APIRouter()


@router.get("/", response_model=list[SessionResponse])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """List all capture sessions, newest first."""
    result = await db.execute(
        select(CaptureSession)
        .order_by(CaptureSession.started_at.desc())
    )
    sessions = result.scalars().all()

    # Attach scene counts and first thumbnail in a follow-up query per session
    out: list[SessionResponse] = []
    for s in sessions:
        scene_result = await db.execute(
            select(Scene)
            .where(Scene.session_id == s.id)
            .order_by(Scene.scene_index)
        )
        scenes = scene_result.scalars().all()

        first_thumb = None
        for sc in scenes:
            if sc.thumbnail_path:
                first_thumb = _thumb_url(sc.thumbnail_path)
                break

        out.append(SessionResponse(
            id=s.id,
            title=s.title,
            started_at=s.started_at,
            ended_at=s.ended_at,
            total_frames=s.total_frames or 0,
            status=s.status,
            scene_count=len(scenes),
            first_thumbnail_url=first_thumb,
        ))

    return out


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single session by ID."""
    result = await db.execute(
        select(CaptureSession).where(CaptureSession.id == session_id)
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Session not found")

    scene_result = await db.execute(
        select(Scene).where(Scene.session_id == s.id).order_by(Scene.scene_index)
    )
    scenes = scene_result.scalars().all()

    first_thumb = next(
        (_thumb_url(sc.thumbnail_path) for sc in scenes if sc.thumbnail_path),
        None,
    )

    return SessionResponse(
        id=s.id,
        title=s.title,
        started_at=s.started_at,
        ended_at=s.ended_at,
        total_frames=s.total_frames or 0,
        status=s.status,
        scene_count=len(scenes),
        first_thumbnail_url=first_thumb,
    )


@router.get("/{session_id}/scenes", response_model=list[SceneResponse])
async def get_session_scenes(session_id: str, db: AsyncSession = Depends(get_db)):
    """Return all scenes for a session, ordered by time."""
    from sqlalchemy.orm import selectinload
    from app.models.models import CharacterAppearance, Character, DetectedItem
    from app.api.routes.scenes import _scene_to_response

    result = await db.execute(
        select(Scene)
        .options(
            selectinload(Scene.character_appearances).selectinload(CharacterAppearance.character),
            selectinload(Scene.items),
        )
        .where(Scene.session_id == session_id)
        .order_by(Scene.scene_index)
    )
    scenes = result.scalars().unique().all()
    return [_scene_to_response(scene) for scene in scenes]


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a session, all its scenes, and thumbnail files from disk."""
    result = await db.execute(
        select(CaptureSession).where(CaptureSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    # Delete thumbnail files from disk
    session_dir = Path(settings.data_dir) / "sessions" / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)

    # Delete from DB — cascade removes scenes automatically
    await db.delete(session)
    await db.commit()
