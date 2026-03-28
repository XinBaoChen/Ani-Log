"""Search routes — semantic search across characters, scenes, items."""

from fastapi import APIRouter, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.models.schemas import SearchQuery, SearchResponse, SearchResult
from app.models.models import Character, Scene, DetectedItem
from app.core.database import get_db
from app.api.routes.scenes import _thumb_url
from app.services.feature_extractor import get_feature_extractor
from app.services.vector_store import get_vector_store

router = APIRouter()


async def _fallback_keyword_search(
    q: str,
    category: str,
    limit: int,
    db: AsyncSession,
) -> list[SearchResult]:
    q_like = f"%{q}%"
    results: list[SearchResult] = []

    if category in ("all", "characters"):
        char_rows = await db.execute(
            select(Character)
            .where(or_(Character.name.ilike(q_like), Character.description.ilike(q_like)))
            .limit(limit)
        )
        for c in char_rows.scalars().all():
            results.append(SearchResult(
                id=c.id,
                type="character",
                label=c.name,
                description=c.description,
                thumbnail_url=_thumb_url(c.thumbnail_path),
                score=0.55,
                metadata={"source": "keyword_fallback"},
            ))

    if category in ("all", "scenes") and len(results) < limit:
        scene_rows = await db.execute(
            select(Scene)
            .where(or_(Scene.description.ilike(q_like), Scene.location.ilike(q_like)))
            .limit(limit)
        )
        for s in scene_rows.scalars().all():
            results.append(SearchResult(
                id=s.id,
                type="scene",
                label=f"Scene {s.scene_index}",
                description=s.description or s.location,
                thumbnail_url=_thumb_url(s.thumbnail_path),
                score=0.50,
                metadata={"session_id": s.session_id, "source": "keyword_fallback"},
            ))

    if category in ("all", "items") and len(results) < limit:
        item_rows = await db.execute(
            select(DetectedItem, Scene.thumbnail_path)
            .join(Scene, Scene.id == DetectedItem.scene_id)
            .where(or_(DetectedItem.label.ilike(q_like), DetectedItem.category.ilike(q_like)))
            .limit(limit)
        )
        for item, thumb_path in item_rows.all():
            results.append(SearchResult(
                id=item.id,
                type="item",
                label=item.label,
                description=f"{item.category} in scene {item.scene_id[:8]}",
                thumbnail_url=_thumb_url(thumb_path),
                score=0.48,
                metadata={"scene_id": item.scene_id, "source": "keyword_fallback"},
            ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


@router.get("/", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    category: str = Query("all", description="all | characters | scenes | items"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Semantic search across the Ani-Log database.

    Uses CLIP text embeddings to find visually and semantically
    matching characters, scenes, and items.

    Example queries:
    - "blue haired girl with sword"
    - "castle at night"
    - "dragon breathing fire"
    """
    results: list[SearchResult] = []
    try:
        extractor = get_feature_extractor()
        vector_store = get_vector_store()

        # Encode text query with CLIP
        text_embedding = extractor.extract_text_features(q)

        if float((text_embedding ** 2).sum()) > 0:
            raw_results = vector_store.search_by_text_embedding(
                text_embedding=text_embedding,
                category=category,
                limit=limit,
            )

            results = [
                SearchResult(
                    id=r["id"],
                    type=r["type"],
                    label=r["metadata"].get("name", r["metadata"].get("label", r["id"])),
                    description=r["metadata"].get("description"),
                    thumbnail_url=r["metadata"].get("thumbnail_url"),
                    score=r["score"],
                    metadata=r["metadata"],
                )
                for r in raw_results
            ]
    except Exception:
        results = []

    if not results:
        results = await _fallback_keyword_search(q=q, category=category, limit=limit, db=db)

    return SearchResponse(
        query=q,
        total=len(results),
        results=results,
    )


@router.post("/", response_model=SearchResponse)
async def search_post(query: SearchQuery):
    """Search via POST body (for complex queries)."""
    return await search(
        q=query.query,
        category=query.category,
        limit=query.limit,
    )
