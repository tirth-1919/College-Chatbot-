"""
CollegeContextManager — the single centralized college-context component.

Responsibilities (Part A §14):
 1. Load user's default college
 2. Load conversation college
 3. Detect explicit college mention
 4. Resolve college names
 5. Resolve aliases
 6. Handle reasonable typos
 7. Determine confidence
 8. Detect context conflicts
 9. Apply access/policy rules
10. Return resolved college_id
11. Persist conversation context when appropriate

College context MUST be resolved BEFORE retrieval (§15): the orchestrator
uses the returned college_id to filter DB/website/RAG sources per tenant.
Gemini never decides which college database is searched.
"""
import re
from difflib import SequenceMatcher
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.models.college import College, CollegeAlias
from backend.app.models.user import User
from backend.app.models.conversation import Conversation

# Confidence thresholds — a weak/ambiguous match is NEVER silently selected (§12)
CONFIDENT_THRESHOLD = 0.80
AMBIGUOUS_THRESHOLD = 0.55

# First-time in-chat onboarding question (§2) — rendered as a normal assistant
# message inside the existing chat section, never a separate route/page.
ONBOARDING_QUESTION = (
    "🤖 Which college information do you want?\n\n"
    "Please enter your college name.\n"
    "Example: RC Technical"
)

# Generic tokens ignored during normalization/matching
_STOP_TOKENS = {
    "college", "institute", "instituteof", "of", "technology", "the", "and",
    "ahmedabad", "in", "engineering", "govt", "government", "technical",
}


def normalize(text: str) -> str:
    """§13 Normalization: lowercase, strip punctuation, collapse spaces,
    drop common abbreviation dots."""
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r"[.\-_]", " ", t)          # R.C. -> r c
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _core_tokens(text: str) -> List[str]:
    """Meaningful tokens of a normalized name (for fuzzy comparisons)."""
    norm = normalize(text)
    return [t for t in norm.split() if t not in _STOP_TOKENS] or norm.split()


class CollegeContextManager:
    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------
    @classmethod
    def resolve(cls, db: Session, name: str) -> Dict[str, Any]:
        """
        Resolve a free-text college name against the College database.
        Returns:
            {
              "status": "RESOLVED" | "AMBIGUOUS" | "NOT_FOUND",
              "college_id": str|None, "college": College|None,
              "confidence": float, "candidates": [ {id,name,code,score}, ... ]
            }
        Exact name/alias/code matches are authoritative. Fuzzy (typo)
        matching (§12) only resolves when confidence is high; otherwise an
        ambiguous candidate list is returned for confirmation.
        """
        raw = (name or "").strip()
        if not raw:
            return {"status": "NOT_FOUND", "college_id": None, "college": None,
                    "confidence": 0.0, "candidates": []}

        norm = normalize(raw)
        norm_squashed = norm.replace(" ", "")

        active_colleges = db.query(College).filter(College.status == "ACTIVE").all()
        if not active_colleges:
            active_colleges = db.query(College).all()

        # Exact normalized name matches must also be unambiguous (§9): if two
        # active colleges share the same normalized name, ask, don't guess.
        name_hits = [c for c in active_colleges
                     if normalize(c.name) == norm or normalize(c.code) == norm]
        if len(name_hits) == 1:
            return cls._resolved(name_hits[0], 1.0)
        if len(name_hits) > 1:
            return {
                "status": "AMBIGUOUS", "college_id": None, "college": None,
                "confidence": 1.0,
                "candidates": [
                    {"id": c.id, "name": c.name, "code": c.code, "score": 1.0}
                    for c in name_hits
                ],
            }
        for c in active_colleges:
            if getattr(c, "slug", None) and normalize(c.slug).replace(" ", "") == norm_squashed:
                return cls._resolved(c, 1.0)

        # 2. Exact alias match (database-backed, §11). If the same normalized
        # alias is registered to more than one active college the match is
        # AMBIGUOUS — never silently pick one (§9).
        alias_rows = db.query(CollegeAlias).filter(
            CollegeAlias.normalized_alias.in_([norm, norm_squashed])
        ).all()
        if alias_rows:
            alias_college_ids = list({r.college_id for r in alias_rows})
            alias_active = [c for c in active_colleges if c.id in alias_college_ids]
            if len(alias_active) == 1:
                return cls._resolved(alias_active[0], 1.0)
            if len(alias_active) > 1:
                return {
                    "status": "AMBIGUOUS", "college_id": None, "college": None,
                    "confidence": 1.0,
                    "candidates": [
                        {"id": c.id, "name": c.name, "code": c.code, "score": 1.0}
                        for c in alias_active
                    ],
                }

        # 3. Fuzzy / typo tolerance (§12) — only above CONFIDENT_THRESHOLD
        scored: List[Tuple[float, College]] = []
        for c in active_colleges:
            score = cls._best_similarity(raw, c)
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)

        top_score, top_college = scored[0]
        if top_score >= CONFIDENT_THRESHOLD:
            return cls._resolved(top_college, round(top_score, 3))

        if top_score >= AMBIGUOUS_THRESHOLD:
            candidates = [
                {"id": c.id, "name": c.name, "code": c.code, "score": round(s, 3)}
                for s, c in scored[:3] if s >= AMBIGUOUS_THRESHOLD
            ]
            return {"status": "AMBIGUOUS", "college_id": None,
                    "college": top_college, "confidence": round(top_score, 3),
                    "candidates": candidates}

        return {"status": "NOT_FOUND", "college_id": None, "college": None,
                "confidence": round(top_score, 3), "candidates": []}

    @classmethod
    def _best_similarity(cls, raw: str, college: College) -> float:
        """Best similarity of the raw text against the college's known names."""
        texts = [college.name, college.code]
        aliases = [a.normalized_alias for a in college.aliases] if hasattr(college, "aliases") else []
        texts.extend(aliases)
        best = 0.0
        raw_core = " ".join(_core_tokens(raw))
        for t in texts:
            if not t:
                continue
            t_core = " ".join(_core_tokens(t))
            # Token-set overlap handles reordered/extra words
            raw_tokens = set(_core_tokens(raw))
            t_tokens = set(_core_tokens(t))
            overlap = 0.0
            if raw_tokens and t_tokens:
                overlap = len(raw_tokens & t_tokens) / max(len(raw_tokens), len(t_tokens))
            seq = SequenceMatcher(None, raw_core, t_core).ratio()
            best = max(best, overlap, seq)
            # Squashed typo comparison catches 'rctechanical' vs 'rctechnical'
            seq_squash = SequenceMatcher(
                None, normalize(raw).replace(" ", ""), normalize(t).replace(" ", "")
            ).ratio()
            best = max(best, seq_squash)
        return best

    @classmethod
    def _resolved(cls, college: College, confidence: float) -> Dict[str, Any]:
        return {"status": "RESOLVED", "college_id": college.id, "college": college,
                "confidence": confidence, "candidates": []}

    # ------------------------------------------------------------------
    # Explicit mention detection (§22, §61)
    # ------------------------------------------------------------------
    @classmethod
    def detect_mention(cls, db: Session, message: str,
                       exclude_college_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Detect an explicit mention of a (different) college inside a normal
        chat question, e.g. "What is the BCA fee at AIT?" while the
        conversation is about RCTI. Returns the same shape as resolve()
        with status RESOLVED, or None when nothing is mentioned.

        The message is scanned against each ACTIVE college's name, code and
        aliases — a lightweight, deterministic, database-backed scan. The
        prompt-injection guard upstream already sanitizes instruction-style
        text; a mere mention never mutates any context by itself (§68).
        """
        raw = (message or "").strip()
        if not raw:
            return None
        norm_msg = normalize(raw)
        squashed = norm_msg.replace(" ", "")

        colleges = db.query(College).filter(College.status == "ACTIVE").all()
        matches: List[Tuple[float, College]] = []
        for c in colleges:
            names = [c.name, c.code] + (
                [a.normalized_alias for a in getattr(c, "aliases", [])]
            )
            for nm in names:
                if not nm:
                    continue
                nm_norm = normalize(nm)
                if not nm_norm:
                    continue
                if nm_norm in norm_msg or nm_norm.replace(" ", "") in squashed:
                    matches.append((1.0, c))
                    break
            else:
                # multi-word names with punctuation differences, e.g. 'rc technical' in msg
                core = " ".join(_core_tokens(nm))
                if core and len(core) > 2 and core in norm_msg:
                    matches.append((0.9, c))
                    continue
                # typo-tolerant mention: fuzzy per-college similarity on a
                # window is expensive; require high squashed similarity only
                # for short codes (e.g. 'ait') typed with a small typo
                if len(nm_norm.replace(" ", "")) <= 6:
                    sq = nm_norm.replace(" ", "")
                    for word in norm_msg.split():
                        if sq and SequenceMatcher(None, word, sq).ratio() >= CONFIDENT_THRESHOLD:
                            matches.append((0.85, c))
                            break

        if not matches:
            return None

        # Strongest match wins; if that's the current college itself, no conflict
        matches.sort(key=lambda m: m[0], reverse=True)
        score, college = matches[0]
        if exclude_college_id and college.id == exclude_college_id:
            return None
        return cls._resolved(college, score)

    # ------------------------------------------------------------------
    # Loaders (§1, §2, §6, §27)
    # ------------------------------------------------------------------
    @classmethod
    def get_user_default(cls, db: Session, user: User) -> Optional[College]:
        if not user or not user.default_college_id:
            return None
        return db.query(College).filter(College.id == user.default_college_id).first()

    @classmethod
    def get_conversation_college(cls, db: Session, conversation: Conversation) -> Optional[College]:
        if not conversation or not conversation.college_id:
            return None
        return db.query(College).filter(College.id == conversation.college_id).first()

    @classmethod
    def get_effective_college_id(cls, db: Session, user: User,
                                 conversation: Optional[Conversation]) -> Optional[str]:
        """
        Authoritative college context precedence (server-derived only, §67):
          1. conversation.college_id (this chat is about X — §5, §27)
          2. users.default_college_id (user's normal preference — §4)
          3. users.college_id (admin tenant linkage, legacy AIT behavior)
        NEVER trusts a frontend-supplied college_id.
        """
        conv_college = cls.get_conversation_college(db, conversation)
        if conv_college:
            return conv_college.id
        default_college = cls.get_user_default(db, user)
        if default_college:
            return default_college.id
        return user.college_id if user else None

    # ------------------------------------------------------------------
    # Persistence (§4, §5, §7, §23, §24, §25, §26)
    # ------------------------------------------------------------------
    @classmethod
    def set_user_default(cls, db: Session, user: User, college_id: str) -> None:
        user.default_college_id = college_id
        db.commit()

    @classmethod
    def forget_user_default(cls, db: Session, user: User) -> None:
        user.default_college_id = None
        db.commit()

    @classmethod
    def set_conversation_college(cls, db: Session, conversation: Conversation,
                                 college_id: str) -> None:
        """Sets THIS conversation's college only. Never touches the user's
        permanent default (§23, §24)."""
        conversation.college_id = college_id
        db.commit()

    @classmethod
    def resolve_and_persist(cls, db: Session, user: User,
                            conversation: Optional[Conversation],
                            college_name: str,
                            set_default: bool = False) -> Dict[str, Any]:
        """
        Full onboarding/switch resolution: resolve free text -> college,
        persist conversation college. The user's permanent default is only
        changed by the explicit /default/change action (§25) — a conversation
        selection or switch NEVER silently becomes the user's default (§23/§24).
        """
        res = cls.resolve(db, college_name)
        if res["status"] == "RESOLVED":
            if conversation:
                cls.set_conversation_college(db, conversation, res["college_id"])
            if set_default:
                cls.set_user_default(db, user, res["college_id"])
        return res


college_context_manager = CollegeContextManager()
