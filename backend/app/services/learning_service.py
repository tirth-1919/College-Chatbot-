"""
Learning Capture Service — Phase 2 + Phase 3
=============================================
Phase 2: captures every answered student question as a LearningCandidate.
Phase 3: adds exact-duplicate detection, semantic similarity matching,
         occurrence_count aggregation, and question-variation tracking.

Design constraints:
* college_id MUST be provided — no fallback tenant is ever guessed.
* Source constants (OFFICIAL_WEBSITE / ADMIN_VERIFIED / GEMINI_UNVERIFIED …)
  are read from the orchestrator — never re-mapped here.
* All persistence errors are logged and swallowed — the student's answer is
  NEVER blocked by a learning error.
* Semantic similarity is configurable via LEARNING_SIMILARITY_THRESHOLD.
* pgvector is used on PostgreSQL; Python cosine fallback is used everywhere else.
* REJECTED / DUPLICATE candidates are never resurrected.
* Canonical question stays as first-seen; later phrasings become variations.
"""

import json
import logging
import math
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

log = logging.getLogger("ait.learning_service")

# Maximum number of variation strings stored per candidate (prevents unbounded growth).
MAX_VARIATIONS = 20

# ──────────────────────────────────────────────────────────────────────────────
# Similarity threshold — single source of truth
# ──────────────────────────────────────────────────────────────────────────────

def _get_threshold() -> float:
    """Read the configurable threshold from settings at call time.

    Importing lazily so tests can monkeypatch settings.LEARNING_SIMILARITY_THRESHOLD
    without module-load order issues.
    """
    try:
        from backend.app.core.config import settings
        return float(settings.LEARNING_SIMILARITY_THRESHOLD)
    except Exception:
        return 0.88  # safe hard-coded fallback if settings unavailable


# ──────────────────────────────────────────────────────────────────────────────
# Normalisation  (unchanged from Phase 2)
# ──────────────────────────────────────────────────────────────────────────────

def normalize_question(text: str) -> str:
    """Basic deterministic normalisation.

    Steps:
    1. Strip leading / trailing whitespace.
    2. Collapse every run of internal whitespace to a single space.
    3. Lowercase the entire string.
    4. Meaningful punctuation (?, !, .) is preserved.

    Example:
        "  What is BCA   fee?  " -> "what is bca fee?"
    """
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text.lower()


# ──────────────────────────────────────────────────────────────────────────────
# Verification status helper  (unchanged from Phase 2)
# ──────────────────────────────────────────────────────────────────────────────

def _derive_verification_status(answer_source: Optional[str], grounding_status: Optional[str]) -> str:
    """Map orchestrator source + grounding to a verification_status string."""
    from backend.app.chat.orchestrator import (
        OFFICIAL_WEBSITE,
        ADMIN_VERIFIED,
        GEMINI_UNVERIFIED,
        PROVIDER_ERROR,
    )

    if answer_source in (OFFICIAL_WEBSITE, ADMIN_VERIFIED):
        return "verified"
    if answer_source == PROVIDER_ERROR:
        return "provider_error"
    if answer_source == GEMINI_UNVERIFIED:
        return "unverified"
    return grounding_status or "unverified"


# ──────────────────────────────────────────────────────────────────────────────
# Embedding helpers
# ──────────────────────────────────────────────────────────────────────────────

def generate_learning_embedding(text: str) -> Optional[List[float]]:
    """Generate a 64-dim embedding using the project's existing EmbeddingService.

    The service already handles:
    * sentence-transformers model when available (neural, normalized).
    * Deterministic hash fallback when the model package is absent.

    Both paths produce L2-normalised vectors.  The Vector(64) column in the
    LearningCandidate model stores exactly this output dimension.

    Returns None on any failure so callers can degrade gracefully.
    """
    try:
        from backend.app.knowledge.ml import embedding_service
        vec = embedding_service.encode(text or "")
        if not vec:
            return None
        # The schema column is Vector(64); the hash fallback is always 64-dim.
        # When the full ST model is loaded it produces 384 dims which exceeds
        # the column.  Truncate to 64 and re-normalise so the column constraint
        # is respected and cosine distances remain valid.
        if len(vec) > 64:
            vec = vec[:64]
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            vec = [x / norm for x in vec]
        return vec
    except Exception:
        log.debug("Embedding generation failed — similarity matching will be skipped", exc_info=True)
        return None


def calculate_cosine_similarity(a: List[float], b: List[float]) -> float:
    """Pure-Python cosine similarity between two pre-normalised vectors.

    Since both embeddings come from embedding_service.encode() they are already
    L2-normalised, so cosine similarity == dot product.  The clamp to [-1, 1]
    guards against floating-point drift.
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    return max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b))))


# ──────────────────────────────────────────────────────────────────────────────
# Candidate lookups
# ──────────────────────────────────────────────────────────────────────────────

def find_exact_candidate(db: Session, college_id: str, normalized_question: str):
    """Return the best active candidate that exactly matches normalized_question.

    "Active" means status is NOT in (REJECTED, DUPLICATE).
    Scoped strictly to college_id — cross-tenant match is impossible.
    """
    from backend.app.models.learning import LearningCandidate, LEARNING_STATUS_REJECTED, LEARNING_STATUS_DUPLICATE

    return (
        db.query(LearningCandidate)
        .filter(
            LearningCandidate.college_id == college_id,
            LearningCandidate.normalized_question == normalized_question,
            LearningCandidate.status.notin_([LEARNING_STATUS_REJECTED, LEARNING_STATUS_DUPLICATE]),
        )
        .order_by(LearningCandidate.first_asked_at.asc())   # canonical = earliest
        .first()
    )


def find_semantic_candidate(
    db: Session,
    college_id: str,
    embedding: List[float],
    threshold: float,
) -> Tuple[Any, float]:
    """Return (best_candidate, similarity) using pgvector or Python fallback.

    Always scoped to college_id.  Returns (None, 0.0) when no match exceeds
    the threshold.
    """
    from backend.app.models.learning import LearningCandidate, LEARNING_STATUS_REJECTED, LEARNING_STATUS_DUPLICATE

    active_filter = (
        LearningCandidate.college_id == college_id,
        LearningCandidate.status.notin_([LEARNING_STATUS_REJECTED, LEARNING_STATUS_DUPLICATE]),
    )

    # ── pgvector path (PostgreSQL only) ────────────────────────────────────────
    try:
        dialect = getattr(getattr(db, "bind", None), "dialect", None)
        if dialect is None:
            # SQLAlchemy 2.x style
            dialect = db.get_bind().dialect
        if getattr(dialect, "name", None) == "postgresql":
            distance_col = LearningCandidate.embedding_vector.cosine_distance(embedding)
            rows = (
                db.query(LearningCandidate, distance_col.label("distance"))
                .filter(
                    *active_filter,
                    LearningCandidate.embedding_vector.is_not(None),
                )
                .order_by(distance_col)
                .limit(1)
                .all()
            )
            if rows:
                candidate, distance = rows[0]
                similarity = max(0.0, 1.0 - float(distance))
                if similarity >= threshold:
                    log.debug(
                        "Phase3 pgvector match: candidate=%s similarity=%.4f",
                        candidate.id, similarity,
                    )
                    return candidate, similarity
            return None, 0.0
    except Exception:
        log.debug("pgvector query failed — falling back to Python cosine", exc_info=True)

    # ── Python fallback (SQLite / dev / no pgvector) ──────────────────────────
    candidates = (
        db.query(LearningCandidate)
        .filter(
            *active_filter,
            LearningCandidate.embedding_json.is_not(None),
        )
        .all()
    )

    best_candidate = None
    best_similarity = -1.0

    for cand in candidates:
        try:
            stored_vec = json.loads(cand.embedding_json)
            sim = calculate_cosine_similarity(embedding, stored_vec)
            if sim > best_similarity:
                best_similarity = sim
                best_candidate = cand
        except Exception:
            continue

    if best_similarity >= threshold:
        log.debug(
            "Phase3 Python-cosine match: candidate=%s similarity=%.4f",
            best_candidate.id if best_candidate else "none", best_similarity,
        )
        return best_candidate, best_similarity

    return None, 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Aggregation into an existing candidate
# ──────────────────────────────────────────────────────────────────────────────

def aggregate_into_candidate(
    db: Session,
    candidate,
    original_question: str,
    match_type: str,
) -> None:
    """Increment occurrence_count, update last_asked_at, append variation."""
    now = datetime.now(timezone.utc)
    candidate.occurrence_count = (candidate.occurrence_count or 1) + 1
    candidate.last_asked_at = now

    # Append variation when the wording differs from the canonical question.
    # Also skip if it's already in the variations list to avoid duplicates.
    if original_question and original_question != candidate.question:
        variations: list = list(candidate.variations or [])
        if original_question not in variations:
            variations.append(original_question)
            # Bound the list to prevent unbounded DB growth.
            candidate.variations = variations[-MAX_VARIATIONS:]
        else:
            candidate.variations = variations   # ensure list is assigned back

    db.add(candidate)
    db.commit()

    log.debug(
        "Phase3 aggregate: id=%s match=%s count=%d",
        candidate.id, match_type, candidate.occurrence_count,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Primary capture function
# ──────────────────────────────────────────────────────────────────────────────

def capture_question(
    db: Session,
    *,
    college_id: str,
    question: str,
    generated_answer: Optional[str],
    answer_source: Optional[str],
    grounding_status: Optional[str],
    conversation_id: Optional[str] = None,
    detected_intent: Optional[str] = None,
    category: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist or aggregate a LearningCandidate for the given answered question.

    Phase 3 decision tree
    ---------------------
    1. Exact match (same college_id + normalized_question, active status)?
       → aggregate (increment count, append variation if text differs)
    2. Semantic match (same college_id, embedding cosine >= threshold, active)?
       → aggregate
    3. No match?
       → insert new candidate

    Failures are **logged and swallowed** — the student answer is never blocked.
    """
    if not college_id:
        log.warning(
            "capture_question called without college_id — skipping "
            "(question=%r)", (question or "")[:120]
        )
        return

    # Derive normalised form and verification status outside the main try block
    # so we can still log the values if we hit an error inside.
    normalized = normalize_question(question)
    verification_status = _derive_verification_status(answer_source, grounding_status)

    metadata: Dict[str, Any] = {
        "learning_capture_version": 2,   # Phase 3 increments version tag
        "effective_college_id": college_id,
    }
    if extra_metadata:
        for key in ("routing_intent", "source_count", "source_types", "provider", "route"):
            if key in extra_metadata:
                metadata[key] = extra_metadata[key]

    try:
        from backend.app.models.learning import LearningCandidate

        # ── STEP 1: exact duplicate ────────────────────────────────────────────
        exact = find_exact_candidate(db, college_id, normalized)
        if exact is not None:
            aggregate_into_candidate(db, exact, question, "EXACT")
            log.debug(
                "Phase3 exact-dup: college=%s candidate=%s", college_id, exact.id
            )
            return

        # ── STEP 2: semantic match ────────────────────────────────────────────
        embedding: Optional[List[float]] = None
        try:
            embedding = generate_learning_embedding(question)
        except Exception:
            log.debug("Embedding generation raised — semantic match skipped", exc_info=True)

        threshold = _get_threshold()
        semantic_match = None
        similarity = 0.0
        if embedding is not None:
            try:
                semantic_match, similarity = find_semantic_candidate(
                    db, college_id, embedding, threshold
                )
            except Exception:
                log.debug("Semantic search raised — will create new candidate", exc_info=True)

        if semantic_match is not None:
            aggregate_into_candidate(db, semantic_match, question, "SEMANTIC")
            log.debug(
                "Phase3 semantic-match: college=%s candidate=%s sim=%.4f",
                college_id, semantic_match.id, similarity,
            )
            return

        # ── STEP 3: new candidate ─────────────────────────────────────────────
        now = datetime.now(timezone.utc)
        candidate = LearningCandidate(
            id=str(uuid.uuid4()),
            college_id=college_id,
            question=question,
            normalized_question=normalized,
            detected_intent=detected_intent or None,
            category=category or None,
            generated_answer=generated_answer,
            answer_source=answer_source,
            verification_status=verification_status,
            conversation_id=conversation_id,
            metadata_json=metadata,
            first_asked_at=now,
            last_asked_at=now,
            # occurrence_count defaults to 1 from the Phase 1 model default.
            embedding_json=json.dumps(embedding) if embedding is not None else None,
            embedding_vector=embedding,
        )
        db.add(candidate)
        db.commit()
        log.debug(
            "Phase3 new candidate: id=%s college=%s source=%s",
            candidate.id, college_id, answer_source,
        )

    except Exception:
        log.error(
            "Learning capture failed (college_id=%r, question=%r). "
            "Chat answer is NOT affected.",
            college_id,
            (question or "")[:120],
            exc_info=True,
        )
        try:
            db.rollback()
        except Exception:
            pass
