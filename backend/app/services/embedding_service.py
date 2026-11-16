"""Gemini Vector Embedding Service (text-embedding-004, 768 Dimensions).

Generates semantic embeddings for pgvector-backed retrieval. Deterministic
fallback vectors are intentionally excluded from the live storage path: if the
Gemini embedding API cannot produce a valid 768-dim vector, the indexing or
retrieval action fails loudly so it can be marked as failed instead of silently
persisting meaningless synthetic embeddings.
"""

import logging
from typing import List
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Manages 768-dimensional vector embeddings for institutional RAG."""

    DIMENSION = 768
    MODEL_NAME = "text-embedding-004"

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_EMBEDDING_MODEL or self.MODEL_NAME
        self.is_placeholder_key = (
            not self.api_key
            or "placeholder" in self.api_key.lower()
            or len(self.api_key) < 15
        )

    def generate_deterministic_embedding(self, text: str) -> List[float]:
        """Utility retained for tests and explicit offline simulation only.

        It must not be used as a production replacement for real embeddings.
        """
        raise RuntimeError(
            "Deterministic fallback embeddings are intentionally unavailable in the live path; "
            "use a real Gemini embedding response or fail the indexing task."
        )

    async def get_embedding(self, text: str) -> List[float]:
        """Generates a 768-dim embedding for a single text chunk or query."""
        cleaned = text.strip()
        if not cleaned:
            return [0.0] * self.DIMENSION

        if self.is_placeholder_key:
            raise RuntimeError(
                "Gemini embedding API is not configured; refusing to store synthetic fallback vectors."
            )

        try:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.model_name}:embedContent?key={self.api_key}"
            )
            payload = {
                "model": f"models/{self.model_name}",
                "content": {"parts": [{"text": cleaned[:8000]}]},
                "outputDimensionality": self.DIMENSION,
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    raise RuntimeError(f"Gemini embedding API returned HTTP {res.status_code}: {res.text[:400]}")

                data = res.json()
                values = data.get("embedding", {}).get("values", [])
                if len(values) != self.DIMENSION:
                    raise RuntimeError(
                        f"Gemini embedding API returned {len(values)} values; expected {self.DIMENSION}."
                    )
                return values
        except Exception as exc:
            logger.error("Gemini embedding generation failed for chunk: %s", exc, exc_info=True)
            raise RuntimeError(f"Embedding generation failed: {exc}") from exc

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of text chunks."""
        results: List[List[float]] = []
        for text in texts:
            emb = await self.get_embedding(text)
            results.append(emb)
        return results


embedding_service = EmbeddingService()

