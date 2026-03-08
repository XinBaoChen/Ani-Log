"""Character routes — list, detail, update, search similar."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.models import Character, CharacterAppearance, Scene
from app.models.schemas import (
    CharacterResponse,
    CharacterDetailResponse,
    CharacterUpdateRequest,
    AppearanceResponse,
)
from app.services.vector_store import get_vector_store
from app.services.feature_extractor import get_feature_extractor

router = APIRouter()


@router.get("/", response_model=list[CharacterResponse])
async def list_characters(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("appearance_count", description="appearance_count | first_seen_at | name"),
    db: AsyncSession = Depends(get_db),
):
    """List all detected characters."""
    order_col = {
        "appearance_count": Character.appearance_count.desc(),
        "first_seen_at": Character.first_seen_at.desc(),
        "name": Character.name.asc(),
    }.get(sort_by, Character.appearance_count.desc())

    query = select(Character).order_by(order_col).offset(offset).limit(limit)
    result = await db.execute(query)
    characters = result.scalars().all()

    return [
        CharacterResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            appearance_count=c.appearance_count,
            first_seen_at=c.first_seen_at,
            thumbnail_url=f"/data/thumbnails/{c.id}.jpg" if c.thumbnail_path else None,
            metadata=c.metadata_,
        )
        for c in characters
    ]


@router.get("/{character_id}", response_model=CharacterDetailResponse)
async def get_character(
    character_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed info for a specific character."""
    result = await db.execute(
        select(Character).where(Character.id == character_id)
    )
    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(404, "Character not found")

    # Get appearances
    appearances_result = await db.execute(
        select(CharacterAppearance)
        .where(CharacterAppearance.character_id == character_id)
        .order_by(CharacterAppearance.timestamp)
    )
    appearances = appearances_result.scalars().all()

    # Find related characters (co-appearing in same scenes)
    scene_ids = [a.scene_id for a in appearances]
    related = []

    if scene_ids:
        related_result = await db.execute(
            select(Character)
            .join(CharacterAppearance)
            .where(
                CharacterAppearance.scene_id.in_(scene_ids),
                Character.id != character_id,
            )
            .distinct()
            .limit(10)
        )
        related = related_result.scalars().all()

    return CharacterDetailResponse(
        id=character.id,
        name=character.name,
        description=character.description,
        appearance_count=character.appearance_count,
        first_seen_at=character.first_seen_at,
        thumbnail_url=f"/data/thumbnails/{character.id}.jpg" if character.thumbnail_path else None,
        metadata=character.metadata_,
        appearances=[
            AppearanceResponse(
                id=a.id,
                scene_id=a.scene_id,
                timestamp=a.timestamp,
                confidence=a.confidence,
                bbox=a.bbox,
            )
            for a in appearances
        ],
        related_characters=[
            CharacterResponse(
                id=r.id,
                name=r.name,
                description=r.description,
                appearance_count=r.appearance_count,
                first_seen_at=r.first_seen_at,
                thumbnail_url=f"/data/thumbnails/{r.id}.jpg" if r.thumbnail_path else None,
            )
            for r in related
        ],
    )


@router.patch("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: str,
    data: CharacterUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update character info (e.g., assign a name)."""
    result = await db.execute(
        select(Character).where(Character.id == character_id)
    )
    character = result.scalar_one_or_none()

    if not character:
        raise HTTPException(404, "Character not found")

    if data.name is not None:
        character.name = data.name
    if data.description is not None:
        character.description = data.description

    await db.commit()
    await db.refresh(character)

    return CharacterResponse(
        id=character.id,
        name=character.name,
        description=character.description,
        appearance_count=character.appearance_count,
        first_seen_at=character.first_seen_at,
        thumbnail_url=f"/data/thumbnails/{character.id}.jpg" if character.thumbnail_path else None,
        metadata=character.metadata_,
    )


@router.get("/{character_id}/similar", response_model=list[CharacterResponse])
async def find_similar_characters(
    character_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Find visually similar characters using CLIP embeddings."""
    result = await db.execute(
        select(Character).where(Character.id == character_id)
    )
    character = result.scalar_one_or_none()

    if not character or not character.chroma_id:
        raise HTTPException(404, "Character not found or no embedding available")

    vector_store = get_vector_store()
    extractor = get_feature_extractor()

    # Get character's embedding from ChromaDB
    matches = vector_store.find_similar_character(
        embedding=extractor.extract_text_features(character.name or "anime character"),
        top_k=limit + 1,
        threshold=0.3,
    )

    # Exclude self
    similar_ids = [m["id"] for m in matches if m["id"] != character_id][:limit]

    if not similar_ids:
        return []

    similar_result = await db.execute(
        select(Character).where(Character.id.in_(similar_ids))
    )
    similar_chars = similar_result.scalars().all()

    return [
        CharacterResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            appearance_count=c.appearance_count,
            first_seen_at=c.first_seen_at,
            thumbnail_url=f"/data/thumbnails/{c.id}.jpg" if c.thumbnail_path else None,
        )
        for c in similar_chars
    ]
