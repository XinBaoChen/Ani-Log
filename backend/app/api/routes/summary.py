"""Summary routes — generate and retrieve story arc summaries."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.models import StoryArc, Scene, Character, CharacterAppearance
from app.models.schemas import SummaryGenerateRequest, StoryArcResponse
from app.services.summarizer import get_summarizer

router = APIRouter()


@router.post("/generate", response_model=StoryArcResponse)
async def generate_summary(
    request: SummaryGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a story arc summary for a capture session."""
    # Fetch all scenes for this session
    scenes_result = await db.execute(
        select(Scene)
        .where(Scene.session_id == request.session_id)
        .options(
            selectinload(Scene.character_appearances).selectinload(CharacterAppearance.character),
            selectinload(Scene.items),
        )
        .order_by(Scene.start_time)
    )
    scenes = scenes_result.scalars().unique().all()

    if not scenes:
        raise HTTPException(404, "No scenes found for this session")

    # Build scene logs
    scene_logs = []
    all_character_ids: set[str] = set()

    for scene in scenes:
        chars = []
        for appearance in scene.character_appearances:
            char = appearance.character
            chars.append({"name": char.name, "id": char.id})
            all_character_ids.add(char.id)

        items = [{"label": item.label, "category": item.category} for item in scene.items]

        scene_logs.append({
            "scene_index": scene.scene_index,
            "start_time": scene.start_time,
            "end_time": scene.end_time,
            "location": scene.location,
            "description": scene.description,
            "characters": chars,
            "items": items,
        })

    # Fetch character info
    char_result = await db.execute(
        select(Character).where(Character.id.in_(all_character_ids))
    )
    characters = char_result.scalars().all()

    character_info = [
        {
            "name": c.name,
            "appearance_count": c.appearance_count,
            "description": c.description,
        }
        for c in characters
    ]

    # Generate summary
    summarizer = get_summarizer()
    summary_data = await summarizer.generate_summary(
        scene_logs=scene_logs,
        character_info=character_info,
        detail_level=request.detail_level,
    )

    # Store arc
    arc = StoryArc(
        session_id=request.session_id,
        title=summary_data["title"],
        summary=summary_data["summary"],
        character_ids=list(all_character_ids),
        scene_ids=[s.id for s in scenes],
    )
    db.add(arc)
    await db.commit()
    await db.refresh(arc)

    return StoryArcResponse(
        id=arc.id,
        title=arc.title,
        summary=arc.summary,
        character_ids=arc.character_ids,
        scene_ids=arc.scene_ids,
        generated_at=arc.generated_at,
    )


@router.get("/{arc_id}", response_model=StoryArcResponse)
async def get_summary(
    arc_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific story arc summary."""
    result = await db.execute(
        select(StoryArc).where(StoryArc.id == arc_id)
    )
    arc = result.scalar_one_or_none()

    if not arc:
        raise HTTPException(404, "Story arc not found")

    return StoryArcResponse(
        id=arc.id,
        title=arc.title,
        summary=arc.summary,
        character_ids=arc.character_ids,
        scene_ids=arc.scene_ids,
        generated_at=arc.generated_at,
    )


@router.get("/", response_model=list[StoryArcResponse])
async def list_summaries(
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all story arc summaries."""
    query = select(StoryArc).order_by(StoryArc.generated_at.desc())

    if session_id:
        query = query.where(StoryArc.session_id == session_id)

    result = await db.execute(query)
    arcs = result.scalars().all()

    return [
        StoryArcResponse(
            id=arc.id,
            title=arc.title,
            summary=arc.summary,
            character_ids=arc.character_ids,
            scene_ids=arc.scene_ids,
            generated_at=arc.generated_at,
        )
        for arc in arcs
    ]
