"""Search routes — semantic search across characters, scenes, items."""

from fastapi import APIRouter, Query

from app.models.schemas import SearchQuery, SearchResponse, SearchResult
from app.services.feature_extractor import get_feature_extractor
from app.services.vector_store import get_vector_store

router = APIRouter()


@router.get("/", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    category: str = Query("all", description="all | characters | scenes | items"),
    limit: int = Query(20, ge=1, le=100),
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
    extractor = get_feature_extractor()
    vector_store = get_vector_store()

    # Encode text query with CLIP
    text_embedding = extractor.extract_text_features(q)

    # Search vector database
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
