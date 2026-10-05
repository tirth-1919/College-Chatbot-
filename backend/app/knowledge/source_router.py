import re
from typing import Dict, Any, Optional
class SourceRouter:
    """
    Directs queries to appropriate knowledge and processing paths:
    - greeting: Conversational welcome and assistance offerings (Section 5)
    - visual: Verified official college images (Section 60 P0)
    - institutional: Authoritative college database, official website snapshots, RAG
    - general_educational: Computer Science and academic questions handled by AI (Section 6)
    - user_file_specific: Private user attachments and documents
    """

    INSTITUTIONAL_INTENTS = {
        "FEES", "ADMISSION", "DOCUMENTS", "ADMISSION_DATES", "ELIGIBILITY",
        "ADMISSION_PROCESS", "ADMISSION_ELIGIBILITY", "ADMISSION_DOCUMENTS", "ADMISSION_FEES",
        "ADMISSION_APPLICATION", "ADMISSION_ENTRANCE_EXAM", "ADMISSION_MERIT",
        "ADMISSION_COUNSELLING", "ADMISSION_DEADLINE", "ADMISSION_RESERVATION",
        "ADMISSION_CONFIRMATION", "ADMISSION_CANCELLATION", "ADMISSION_REFUND",
        "ADMISSION_CONTACT", "ADMISSION_PROGRAMS", "ADMISSION_HOSTEL",
        "ADMISSION_SCHOLARSHIP", "ADMISSION_NRI", "ADMISSION_INTERNATIONAL",
        "COURSES", "PLACEMENT", "FACULTY", "SUBJECT", "LIBRARY", "LAB", "CAMPUS",
        "DEPARTMENTS", "FACILITIES", "HOSTEL", "TRANSPORT", "SCHOLARSHIP", "EXAM",
        "RESULT", "EVENT", "EVENTS", "CONTACT", "LOCATION", "AFFILIATION", "AIT_GENERAL", "AIT_COMMITTEE"
    }

    # Subject terms that ARE legitimate AIT committee/governance modifiers.
    # Resolved once here (policy, not query understanding) and reused by the
    # governance guards below.
    KNOWN_GOVERNANCE_MODIFIERS = frozenset({
        "sports", "library", "canteen", "academic", "anti", "ragging",
        "anti-ragging", "internal", "complaint", "student", "grievance",
        "iqac", "admission", "placement", "discipline", "examination",
        "hostel", "transport", "scholarship", "ait", "college", "institute",
        "the", "of", "is", "who", "what", "which", "and", "for",
        "a", "an", "about", "tell", "me", "our", "your", "at", "in",
    })

    @classmethod
    def route_query(
        cls,
        query_spec,
        *legacy,
        has_user_files: bool = False,
        college_id: Optional[str] = None,
        intent_info: Optional[Dict[str, Any]] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        P0.1: QuerySpec is the single source of truth for routing.

        The router never re-derives intent / category / topic / program /
        entity / academic_year.  Every lexical signal it needs was resolved
        once, at the query-understanding boundary, and is exposed as a
        boolean or list on the spec.

        Legacy callers may still pass
        ``(text, intent_info, entities, has_user_files, college_id)``.
        That form is converted to a QuerySpec HERE, at this single boundary,
        and is discarded afterwards -- there is never a second representation.
        """
        if legacy or intent_info is not None or entities is not None:
            from backend.app.intelligence.entities import EntityExtractor

            resolved_intent_info = (
                legacy[0] if legacy and isinstance(legacy[0], dict) else (intent_info or {})
            )
            resolved_entities = (
                legacy[1]
                if len(legacy) > 1 and isinstance(legacy[1], dict)
                else (entities or {})
            )
            if len(legacy) > 2 and isinstance(legacy[2], bool):
                has_user_files = has_user_files or legacy[2]
            query_spec = EntityExtractor.build_query_spec_from_legacy(
                query_spec,
                intent_info=resolved_intent_info,
                entities=resolved_entities,
                college_id=college_id,
            )
        elif isinstance(query_spec, str):
            from backend.app.intelligence.entities import EntityExtractor

            query_spec = EntityExtractor.extract_query_understanding(
                query_spec, college_id=college_id
            )

        intent = (query_spec.intent or "").upper()

        # 1. Greetings & Casual Conversation (Section 5: must NOT enter
        # institutional verification).
        if intent in ["GREETING", "GENERAL_CONVERSATION"] or query_spec.is_greeting_phrase:
            return "greeting"

        # 2. Visual Requests (P0 Real AIT Images)
        if intent == "IMAGE_REQUEST" or query_spec.is_visual_request:
            return "visual"

        # 3. User Private File Inquiries
        if has_user_files and query_spec.is_user_file_request:
            return "user_file_specific"

        # Advice is not institutional evidence merely because a college name
        # or student context appears in the question.
        if intent in {"GENERAL_EDUCATIONAL", "GENERAL_KNOWLEDGE", "GENERAL_CAREER_ADVICE"}:
            return "general_educational"

        # Generic programming/web-development guidance is not an
        # institutional question.  Entity extraction may still produce a
        # topic (for example "programming" or "web application"), so this
        # runs before the generic semantic-signal check below.
        if query_spec.is_general_learning_guidance:
            return "general_educational"

        # 4b. An explicit institutional intent inside a conversation whose
        # college is already resolved must go to the institutional
        # retrieval path.  The college name itself is often a STOPWORD in
        # the query ("Where is the college located?"), so the keyword
        # heuristics below cannot see it -- but the backend-tenant context
        # can.
        if (
            query_spec.college_id
            and intent in cls.INSTITUTIONAL_INTENTS
            and intent not in ("AIT_GENERAL", "AIT_COMMITTEE")
        ):
            return "institutional"

        # 5. AIT / institutional facts.
        # Word-boundary matching is resolved on the spec, so substrings such
        # as "council" inside "security council" or "hi" inside "machine"
        # cannot fire a false institutional signal.
        has_strong = query_spec.has_strong_institutional_keyword
        has_weak = query_spec.has_weak_institutional_keyword
        has_ait_mention = query_spec.has_ait_mention
        has_entities = query_spec.has_semantic_signal
        # Ambiguous words ("college", "council", "campus", "committee",
        # "squad") only count as institutional signals when there is another
        # AIT-specific signal in the query.
        has_college_mention = has_strong or (has_weak and (has_ait_mention or has_entities))

        if intent in cls.INSTITUTIONAL_INTENTS and (has_college_mention or has_entities):
            return "institutional"
        if has_college_mention or has_ait_mention or has_entities:
            return "institutional"

        # 5b. Governance keyword with no AIT/institutional context.
        # An external capitalized body ("UN Security Council") is not an
        # AIT question; a lowercase governance term attached to an unknown
        # subject ("machine council?") is not either.
        known_modifiers = cls.KNOWN_GOVERNANCE_MODIFIERS
        governance_match = re.search(
            r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+"
            r"(Council|Committee|Squad)\b",
            query_spec.raw_question or "",
        )
        if governance_match:
            preceding = governance_match.group(1).strip().split()
            non_modifier = [
                w.lower().lstrip("-") for w in preceding
                if w.lower().lstrip("-") not in known_modifiers
            ]
            if non_modifier:
                return "general_educational"

        governance_lower = re.search(
            r"\b([a-z]+(?:\s+[a-z]+)*)\s+(council|committee|squad|chairman|chairperson)\b",
            (query_spec.raw_question or "").lower(),
        )
        if governance_lower and not (has_ait_mention or has_entities):
            subject_words = governance_lower.group(1).split()
            non_modifier = [
                w.lstrip("-") for w in subject_words
                if w.lstrip("-") not in known_modifiers
            ]
            if non_modifier:
                return "general_educational"
        # The governance word may also come AFTER "of the <subject>"
        # (e.g. "chairman of the anti-ragging squad?").
        of_the_subject = re.search(
            r"\b(?:chairman|chairperson|head)\s+of\s+the\s+([a-z-]+(?:\s+[a-z-]+)*)\s+"
            r"(council|committee|squad)\b",
            (query_spec.raw_question or "").lower(),
        )
        if of_the_subject and not (has_ait_mention or has_entities):
            subject_words = of_the_subject.group(1).split()
            non_modifier = [
                w.lstrip("-") for w in subject_words
                if w.lstrip("-") not in known_modifiers
            ]
            if non_modifier:
                return "general_educational"

        # 6. Fallback checks
        if query_spec._has_any(["what is", "how does", "explain", "code for", "algorithm", "tutorial"]):
            return "general_educational"

        # Default: unmatched, non-greeting queries are treated as general
        # educational questions so they reach the AI fallback path (and get
        # logged as knowledge gaps) instead of being misread as small talk.
        return "general_educational"

source_router = SourceRouter()
