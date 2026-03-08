"""Scene routes — list scenes, scene detail with characters and items."""

import re
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.models import Scene, CharacterAppearance, Character, DetectedItem
from app.models.schemas import SceneResponse, CharacterResponse, ItemResponse


def _thumb_url(path: str | None) -> str | None:
    """Convert any stored thumbnail_path to a /data/... URL.

    Handles three formats produced by different versions of the code:
    - Old relative Windows:  data\\sessions\\<id>\\scenes\\scene_0001.jpg
    - Old absolute Windows:  G:\\...\\data\\sessions\\...
    - New relative POSIX:    sessions/<id>/scenes/scene_0001.jpg
    """
    if not path:
        return None
    # Normalise to forward slashes
    p = path.replace("\\", "/")
    # Strip any leading drive letter + absolute path up to /data/
    p = re.sub(r'^[A-Za-z]:/.*?/data/', '', p)
    # Strip a leading "data/" that was included in old stored paths
    if p.startswith("data/"):
        p = p[len("data/"):]
    return f"/data/{p}"


router = APIRouter()


@router.get("/", response_model=list[SceneResponse])
async def list_scenes(
    session_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all detected scenes, optionally filtered by session."""
    query = (
        select(Scene)
        .options(
            selectinload(Scene.character_appearances).selectinload(CharacterAppearance.character),
            selectinload(Scene.items),
        )
        .order_by(Scene.start_time)
        .offset(offset)
        .limit(limit)
    )

    if session_id:
        query = query.where(Scene.session_id == session_id)

    result = await db.execute(query)
    scenes = result.scalars().unique().all()

    return [_scene_to_response(scene) for scene in scenes]


@router.get("/{scene_id}", response_model=SceneResponse)
async def get_scene(
    scene_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed info for a specific scene."""
    result = await db.execute(
        select(Scene)
        .options(
            selectinload(Scene.character_appearances).selectinload(CharacterAppearance.character),
            selectinload(Scene.items),
        )
        .where(Scene.id == scene_id)
    )
    scene = result.scalar_one_or_none()

    if not scene:
        raise HTTPException(404, "Scene not found")

    return _scene_to_response(scene)


@router.get("/{scene_id}/characters", response_model=list[CharacterResponse])
async def get_scene_characters(
    scene_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all characters that appeared in a specific scene."""
    result = await db.execute(
        select(Character)
        .join(CharacterAppearance)
        .where(CharacterAppearance.scene_id == scene_id)
        .distinct()
    )
    characters = result.scalars().all()

    return [
        CharacterResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            appearance_count=c.appearance_count,
            first_seen_at=c.first_seen_at,
            thumbnail_url=_thumb_url(c.thumbnail_path),
        )
        for c in characters
    ]


def _scene_to_response(scene: Scene) -> SceneResponse:
    """Convert a Scene ORM object to response schema."""
    # Deduplicate characters (a character may appear multiple times in a scene)
    seen_chars: set[str] = set()
    characters = []
    for appearance in scene.character_appearances:
        char = appearance.character
        if char.id not in seen_chars:
            seen_chars.add(char.id)
            characters.append(
                CharacterResponse(
                    id=char.id,
                    name=char.name,
                    description=char.description,
                    appearance_count=char.appearance_count,
                    first_seen_at=char.first_seen_at,
                    thumbnail_url=_thumb_url(char.thumbnail_path),
                )
            )

    items = [
        ItemResponse(
            id=item.id,
            label=item.label,
            category=item.category,
            confidence=item.confidence,
            timestamp=item.timestamp,
            bbox=item.bbox,
        )
        for item in scene.items
    ]

    return SceneResponse(
        id=scene.id,
        session_id=scene.session_id,
        scene_index=scene.scene_index,
        start_time=scene.start_time,
        end_time=scene.end_time,
        thumbnail_url=_thumb_url(scene.thumbnail_path),
        description=scene.description,
        location=scene.location,
        characters=characters,
        items=items,
    )
