# Optional neural retrieval components with deterministic safe fallbacks.
# Neural components only produce relevance signals; application controls remain deterministic.
import hashlib
import math
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_VERSION = "retrieval-1"

class EmbeddingService:
    def __init__(self):
        self._model = None
        self._attempted = False
    def _load(self):
        if not self._attempted:
            self._attempted = True
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            except Exception:
                self._model = None
        return self._model
    def encode(self, text: str) -> List[float]:
        model = self._load()
        if model is not None:
            return [float(x) for x in model.encode(text or "", normalize_embeddings=True).tolist()]
        # Portable fallback for SQLite/development and environments without the
        # optional model package. It is never used as a security decision.
        vector = [0.0] * 64
        for token in re.findall(r"[a-z0-9]+", (text or "").lower()):
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:2], "big") % len(vector)
            vector[index] += 1.0 if digest[2] % 2 else -1.0
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]

    def similarity(self, left: str, right: str) -> float:
        a, b = self.encode(left), self.encode(right)
        return max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b))))

embedding_service = EmbeddingService()

class Reranker:
    # Cross-encoder adapter; lexical fallback is conservative and explainable.
    def __init__(self):
        self._model = None
        self._attempted = False
    def _load(self):
        if not self._attempted:
            self._attempted = True
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            except Exception:
                self._model = None
        return self._model
    def score(self, query: str, text: str) -> float:
        model = self._load()
        if model is not None:
            return float(model.predict([(query or "", text or "")])[0])
        q = set(re.findall(r"[a-z0-9]+", (query or "").lower()))
        t = set(re.findall(r"[a-z0-9]+", (text or "").lower()))
        return len(q & t) / max(len(q), 1)

reranker = Reranker()

def hybrid_score(query: str, text: str, lexical_score: float = 0.0) -> Tuple[float, float, float]:
    semantic = (embedding_service.similarity(query, text) + 1.0) / 2.0
    neural = reranker.score(query, text)
    combined = (0.35 * min(1.0, lexical_score) + 0.35 * semantic + 0.30 * min(1.0, max(0.0, neural)))
    return combined, semantic, neural
