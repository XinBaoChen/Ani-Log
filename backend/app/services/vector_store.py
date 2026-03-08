"""ChromaDB Vector Store for character re-identification and semantic search.

Stores CLIP embeddings and enables:
1. Character re-identification across scene cuts
2. Semantic text-based search ("blue-haired girl with sword")
3. Similar character/item discovery
"""

import numpy as np
from loguru import logger

from app.core.config import settings
from app.core.database import get_collection


class VectorStore:
    """Manages ChromaDB collections for Ani-Log entities."""

    def __init__(self):
        self._characters_collection = None
        self._scenes_collection = None
        self._items_collection = None

    @property
    def characters(self):
        if self._characters_collection is None:
            self._characters_collection = get_collection(settings.chroma_collection_characters)
        return self._characters_collection

    @property
    def scenes(self):
        if self._scenes_collection is None:
            self._scenes_collection = get_collection(settings.chroma_collection_scenes)
        return self._scenes_collection

    @property
    def items(self):
        if self._items_collection is None:
            self._items_collection = get_collection(settings.chroma_collection_items)
        return self._items_collection

    # ─── Character Operations ────────────────────────────────
    def add_character(
        self,
        character_id: str,
        embedding: np.ndarray,
        metadata: dict | None = None,
    ):
        """Store a character's CLIP embedding."""
        self.characters.add(
            ids=[character_id],
            embeddings=[embedding.tolist()],
            metadatas=[metadata or {}],
        )
        logger.debug(f"Added character embedding: {character_id}")

    def update_character_embedding(
        self,
        character_id: str,
        embedding: np.ndarray,
        metadata: dict | None = None,
    ):
        """Update a character's embedding (running average)."""
        self.characters.update(
            ids=[character_id],
            embeddings=[embedding.tolist()],
            metadatas=[metadata or {}],
        )

    def find_similar_character(
        self,
        embedding: np.ndarray,
        top_k: int = 5,
        threshold: float | None = None,
    ) -> list[dict]:
        """
        Find characters similar to the given embedding.

        Returns:
            List of {id, score, metadata} dicts
        """
        threshold = threshold or settings.reidentification_threshold

        results = self.characters.query(
            query_embeddings=[embedding.tolist()],
            n_results=top_k,
        )

        matches = []
        if results["ids"] and results["ids"][0]:
            for i, char_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 1.0
                score = 1.0 - distance  # Convert distance to similarity
                if score >= threshold:
                    matches.append({
                        "id": char_id,
                        "score": score,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    })

        return matches

    # ─── Scene Operations ────────────────────────────────────
    def add_scene(
        self,
        scene_id: str,
        embedding: np.ndarray,
        metadata: dict | None = None,
    ):
        """Store a scene's average CLIP embedding."""
        self.scenes.add(
            ids=[scene_id],
            embeddings=[embedding.tolist()],
            metadatas=[metadata or {}],
        )

    # ─── Item Operations ─────────────────────────────────────
    def add_item(
        self,
        item_id: str,
        embedding: np.ndarray,
        metadata: dict | None = None,
    ):
        """Store a detected item's embedding."""
        self.items.add(
            ids=[item_id],
            embeddings=[embedding.tolist()],
            metadatas=[metadata or {}],
        )

    # ─── Search Operations ───────────────────────────────────
    def search_by_text_embedding(
        self,
        text_embedding: np.ndarray,
        category: str = "all",
        limit: int = 20,
    ) -> list[dict]:
        """
        Search across collections using a CLIP text embedding.

        Args:
            text_embedding: CLIP text feature vector
            category: "all", "characters", "scenes", "items"
            limit: Max results per collection

        Returns:
            Unified list of results sorted by similarity
        """
        results = []
        embedding_list = [text_embedding.tolist()]

        collections = {
            "characters": (self.characters, "character"),
            "scenes": (self.scenes, "scene"),
            "items": (self.items, "item"),
        }

        targets = collections if category == "all" else {category: collections.get(category)}

        for col_name, col_info in targets.items():
            if col_info is None:
                continue
            collection, entity_type = col_info

            try:
                query_results = collection.query(
                    query_embeddings=embedding_list,
                    n_results=limit,
                )

                if query_results["ids"] and query_results["ids"][0]:
                    for i, entity_id in enumerate(query_results["ids"][0]):
                        distance = query_results["distances"][0][i] if query_results["distances"] else 1.0
                        score = 1.0 - distance
                        results.append({
                            "id": entity_id,
                            "type": entity_type,
                            "score": score,
                            "metadata": query_results["metadatas"][0][i] if query_results["metadatas"] else {},
                        })
            except Exception as e:
                logger.warning(f"Search failed for {col_name}: {e}")

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def get_character_count(self) -> int:
        """Get total number of stored character embeddings."""
        try:
            return self.characters.count()
        except Exception:
            return 0

    def get_scene_count(self) -> int:
        try:
            return self.scenes.count()
        except Exception:
            return 0


# Singleton
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
