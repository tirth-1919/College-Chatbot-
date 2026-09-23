"""
Knowledge Gap service (Knowledge Gap Center §8-§12, §26, §42, §43).

Responsibilities:
- Detect when the assistant failed to answer reliably (unanswered question detection).
- Record / deduplicate KnowledgeGap rows (occurrence_count++ instead of new rows).
- Infer category / course / academic-year conservatively (no invented facts).
- Never mutate tenant identity: college_id is always passed in from authoritative context.
"""
import re
from datetime import datetime, timezone
from typing import Optional

from backend.app.models.knowledge import KnowledgeGap

# Categories that may be auto-assigned (§11). Only assigned when the query
# contains an unambiguous keyword for the category.
CATEGORY_KEYWORDS = {
    "Admissions": ["admission", "admissions", "eligibility criteria", "cutoff", "entrance", "application form"],
    "Courses": ["course", "courses", "program", "branch", "btech", "b.tech", "bca", "mca", "mba", "diploma", "degree"],
    "Fees": ["fee", "fees", "tuition", "cost", "charge", "payment", "scholarship amount"],
    "Faculty": ["faculty", "professor", "teacher", "lecturer", "hod", "who teaches"],
    "Departments": ["department", "departments", "hod of"],
    "Scholarships": ["scholarship", "freeship", "stipend"],
    "Examinations": ["exam", "examination", "result", "marks", "grade", "revaluation"],
    "Academic Calendar": ["calendar", "semester dates", "holiday", "timetable", "schedule", "academic year dates"],
    "Hostel": ["hostel", "dormitory", "accommodation", "mess"],
    "Library": ["library", "book", "journal", "reading room"],
    "Transport": ["transport", "bus", "route", "pickup"],
    "Placements": ["placement", "package", "recruiter", "internship offer"],
    "Events": ["event", "fest", "seminar", "workshop"],
    "Facilities": ["facility", "facilities", "canteen", "gym", "lab", "laboratory", "wifi"],
    "Rules": ["rule", "rules", "dress code", "attendance policy", "regulation"],
    "Contact": ["contact", "phone number", "email of", "address of", "reach the college"],
}

# Course codes commonly mentioned (§12)
COURSE_PATTERNS = [
    "MCA", "BCA", "B.Tech", "BTech", "MBA", "BBA", "M.Tech", "MTech", "Diploma",
    "B.Com", "M.Com", "B.Sc", "M.Sc", "PhD", "B.E.", "M.E.",
]

ACADEMIC_YEAR_RE = re.compile(r"20\d{2}\s*[-/]\s*\d{2,4}")

# Signals in the assistant's answer that it could not answer reliably (§7).
UNANSWERED_TEXT_PATTERNS = [
    "couldn't find verified information",
    "could not find verified information",
    "couldn't verify",
    "could not verify",
    "i couldn't identify that college",
    "couldn't find matching information",
    "couldn't reach any ai provider",
    "could you please clarify",
    "couldn't find any verified information",
]

MAX_SAMPLE_ANSWER = 500
MAX_DEDUP_LENGTH = 255

# Stopwords dropped when building the fuzzy (word-variant) grouping key (§9, §42).
_FUZZY_STOPWORDS = {
    "what", "is", "are", "was", "were", "the", "a", "an", "of", "for", "to",
    "in", "on", "at", "do", "does", "did", "how", "when", "who", "where",
    "can", "i", "my", "me", "about", "please", "with", "and", "or", "it",
    "its", "their", "there", "tell", "give", "get", "know", "want", "any",
}


def fuzzy_key(q: str) -> frozenset:
    """Meaningful-token set of a question (stopwords removed). Used only as a
    SECOND-chance grouping key when the exact normalized key misses — e.g.
    "what is hostel eligibility" vs "what are hostel eligibility rules"."""
    tokens = re.findall(r"[a-z0-9.\-]+", normalize_question(q))
    return frozenset(t for t in tokens if t not in _FUZZY_STOPWORDS)


def normalize_question(q: str) -> str:
    """Normalize a question for duplicate grouping (§42): lowercase, whitespace
    and punctuation normalization. Safe — no semantic analysis."""
    s = (q or "").lower().strip()
    s = re.sub(r"[\?!.।,;:\"'\u2018\u2019\u201c\u201d()]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Weak (generic) keywords — they only decide the category when no STRONG
# keyword matched. "hostel rules" → Hostel, but "hostel fee" (two strong
# categories) stays None so admins set it (§11: never guess when ambiguous).
WEAK_KEYWORDS = {
    "rule", "rules", "policy", "policies", "regulation", "regulations",
    "timing", "timings", "hours", "schedule", "information", "info",
    "details", "criteria", "criteria of", "requirement", "requirements",
    "process", "procedure", "contact", "phone number", "address of",
    "reach the college",
}


def extract_category(q: str) -> Optional[str]:
    """Infer category only when unambiguous (§11). Returns None when unsure.

    Strong category keywords win over weak/generic ones. Two conflicting
    strong matches (e.g. "hostel fee") → None.
    """
    ql = " " + (q or "").lower() + " "
    strong, weak = set(), set()
    for cat, kws in CATEGORY_KEYWORDS.items():
        for kw in kws:
            hit = f" {kw} " in ql or ql.startswith(f" {kw} ") or f" {kw}?" in ql + "?"
            if not hit:
                continue
            if kw in WEAK_KEYWORDS:
                weak.add(cat)
            else:
                strong.add(cat)
            break
    if len(strong) == 1:
        return next(iter(strong))
    if not strong and len(weak) == 1:
        return next(iter(weak))
    return None  # ambiguous or no match — admin can set it


def extract_course(q: str) -> Optional[str]:
    ql = (q or "").lower()
    for c in COURSE_PATTERNS:
        if c.lower() in ql:
            return c
    return None


def extract_academic_year(q: str) -> Optional[str]:
    m = ACADEMIC_YEAR_RE.search(q or "")
    if not m:
        return None
    return re.sub(r"\s+", "", m.group(0))


def is_unanswered(text: str, grounding_status: str) -> bool:
    """Detect a non-answer from BOTH the grounding signal and the answer text (§7).

    grounding_status is authoritative when it marks the answer unverified/rejected;
    text patterns catch providers that answered with a no-info message while
    still claiming verified.
    """
    if grounding_status in ("unverified", "rejected"):
        return True
    tl = (text or "").lower()
    return any(p in tl for p in UNANSWERED_TEXT_PATTERNS)


def record_gap(
    db,
    *,
    college_id: Optional[str],
    question: str,
    sample_answer: Optional[str] = None,
    reason: str = "no_verified_source",
    conversation_id: Optional[str] = None,
    message_id: Optional[str] = None,
    detected_intent: Optional[str] = None,
    missing_entity: Optional[str] = None,
    source: str = "chat",
) -> Optional[KnowledgeGap]:
    """Create-or-update a deduplicated KnowledgeGap row (§8, §9, §42).

    Grouping key: (college_id, normalize_question(question)).
    Returns the gap row (new or updated), or None on invalid input.
    This NEVER changes tenant identity — college_id comes from the caller's
    authoritative conversation/user context.
    """
    q = (question or "").strip()
    if not q:
        return None
    norm = normalize_question(q)[:MAX_DEDUP_LENGTH]
    if not norm:
        return None

    now = datetime.now(timezone.utc)
    existing = (
        db.query(KnowledgeGap)
        .filter(KnowledgeGap.college_id == college_id, KnowledgeGap.dedup_key == norm)
        .first()
    )
    if existing is None:
        # Second-chance fuzzy grouping (§9/§42): merge word-variants of the same
        # underlying question into the existing OPEN gap instead of a new row.
        # Restricted to unresolved gaps so resolved/dismissed ones stay closed,
        # and to the same college so tenants never merge (§38).
        fk = fuzzy_key(q)
        if fk:
            candidates = (
                db.query(KnowledgeGap)
                .filter(
                    KnowledgeGap.college_id == college_id,
                    ~KnowledgeGap.status.in_(["RESOLVED", "DISMISSED", "DUPLICATE"]),
                )
                .order_by(KnowledgeGap.last_seen_at.desc())
                .limit(200)
                .all()
            )
            for cand in candidates:
                ck = fuzzy_key(cand.user_query or "")
                if not ck:
                    continue
                # Subset match ("hostel eligibility" ⊂ "hostel eligibility rules")
                # or strong Jaccard overlap groups word-variants of the same gap.
                jaccard = len(fk & ck) / len(fk | ck)
                if ck <= fk or fk <= ck or jaccard >= 0.6:
                    existing = cand
                    break
    if existing:
        existing.occurrence_count = (existing.occurrence_count or 1) + 1
        existing.last_seen_at = now
        # Keep the first question as canonical, refresh the latest sample answer.
        if sample_answer:
            existing.sample_answer = (sample_answer or "")[:MAX_SAMPLE_ANSWER]
        # Resolved gaps that recur reopen as OPEN for review.
        if existing.status in ("RESOLVED", "DISMISSED", "DUPLICATE"):
            existing.status = "OPEN"
            existing.resolved_at = None
            existing.resolved_by = None
        _apply_metadata(existing, q)
        db.commit()
        return existing

    gap = KnowledgeGap(
        college_id=college_id,
        user_query=q,
        dedup_key=norm,
        detected_intent=detected_intent,
        missing_entity=missing_entity,
        status="OPEN",
        occurrence_count=1,
        first_seen_at=now,
        last_seen_at=now,
        sample_answer=(sample_answer or "")[:MAX_SAMPLE_ANSWER],
        conversation_id=conversation_id,
        message_id=message_id,
        reason=reason,
    )
    _apply_metadata(gap, q)
    db.add(gap)
    db.commit()
    return gap


def _apply_metadata(gap: KnowledgeGap, question: str) -> None:
    """Conservatively enrich gap metadata; never overwrite admin-set values."""
    if not gap.category:
        gap.category = extract_category(question)
    if not gap.course:
        gap.course = extract_course(question)
    if not gap.academic_year:
        gap.academic_year = extract_academic_year(question)


def compute_priority(gap: KnowledgeGap, negative_feedback_count: int = 0) -> str:
    """Explainable priority (§29): frequency + recent activity + report severity.
    Not presented as factual certainty — the UI shows the contributing signals."""
    from datetime import timedelta
    score = 0
    occ = gap.occurrence_count or 1
    if occ >= 20:
        score += 3
    elif occ >= 8:
        score += 2
    elif occ >= 3:
        score += 1
    if gap.last_seen_at:
        last_seen = gap.last_seen_at
        if last_seen.tzinfo is None:  # SQLite returns naive UTC datetimes
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - last_seen
        if age < timedelta(days=1):
            score += 2
        elif age < timedelta(days=7):
            score += 1
    if negative_feedback_count >= 5:
        score += 3
    elif negative_feedback_count >= 2:
        score += 2
    elif negative_feedback_count >= 1:
        score += 1
    if gap.category in ("Admissions", "Fees", "Examinations"):
        score += 1
    return "High" if score >= 5 else "Medium" if score >= 2 else "Low"


VALID_STATUSES = {"OPEN", "UNDER_REVIEW", "IN_PROGRESS", "RESOLVED", "DISMISSED", "DUPLICATE"}
