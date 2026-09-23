import re
from typing import Dict, Any, Optional
class SourceRouter:
    """
    Directs queries to appropriate knowledge and processing paths:
    - greeting: Conversational welcome and assistance offerings (Section 5)
    - ait_visual: Verified official AIT images (Section 60 P0)
    - ait_institutional: Authoritative college database, official website snapshots, RAG
    - general_educational: Computer Science and academic questions handled by AI (Section 6)
    - user_file_specific: Private user attachments and documents
    """

    INSTITUTIONAL_INTENTS = {
        "FEES", "ADMISSION", "ADMISSION_DATES", "ELIGIBILITY", "COURSES",
        "PLACEMENT", "FACULTY", "SUBJECT", "LIBRARY", "LAB", "CAMPUS",
        "FACILITIES", "HOSTEL", "TRANSPORT", "SCHOLARSHIP", "EXAM",
        "RESULT", "EVENT", "CONTACT", "LOCATION", "AIT_GENERAL", "AIT_COMMITTEE"
    }

    @classmethod
    def route_query(
        cls,
        text: str,
        intent_info: Dict[str, Any],
        entities: Dict[str, Any],
        has_user_files: bool = False,
        college_id: Optional[str] = None,
    ) -> str:
        intent = intent_info.get("intent", "").upper()
        text_lower = text.lower()

        # 1. Greetings & Casual Conversation (Section 5: must NOT enter institutional verification)
        # Only accept a classified greeting or a complete greeting phrase. Never
        # use substring matching: "machine" contains "hi" but is not a greeting.
        common_greetings = [
            "hi", "hello", "hey", "hy", "hyy", "hiii", "hii", "greetings",
            "good morning", "good afternoon", "good evening"
        ]
        normalized_text = re.sub(r"[^a-z0-9 ]", " ", text_lower).strip()
        is_exact_greeting = normalized_text in common_greetings
        is_classified_greeting = intent in ["GREETING", "GENERAL_CONVERSATION"]
        if is_classified_greeting or is_exact_greeting:
            return "greeting"

        # 2. Visual Requests (P0 Real AIT Images)
        if intent == "IMAGE_REQUEST" or any(w in text_lower for w in ["show me", "campus photo", "library photo", "lab photo", "view of", "how it look"]):
            if any(fac in text_lower for fac in ["campus", "library", "lab", "classroom", "canteen", "sports", "ground", "building"]):
                return "ait_visual"

        # 3. User Private File Inquiries
        if has_user_files and any(w in text_lower for w in ["my file", "this pdf", "uploaded document", "attached", "this image", "in my doc"]):
            return "user_file_specific"

        # 4. General Educational Questions (Section 6: programming, DBMS, algorithms, concepts)
        if intent == "GENERAL_EDUCATIONAL":
            return "general_educational"

        # 4b. §SPEC: an explicit institutional intent inside a conversation whose
        # college is already resolved (conversation.college_id persisted) must go
        # to the institutional retrieval path. The college name itself is often a
        # STOPWORD in the query ("Where is the college located?", "Where is R.C.
        # Technical Institute?" after token cleaning), so keyword heuristics
        # below cannot see it — but the backend-tenant context can. This routes
        # "where is the college located?" / "what is the address of the institute?"
        # to tenant-scoped verified retrieval instead of the ungrounded AI path.
        if (
            college_id
            and intent in cls.INSTITUTIONAL_INTENTS
            and intent not in ("AIT_GENERAL", "AIT_COMMITTEE")
        ):
            return "ait_institutional"

        # 5. AIT Institutional Facts
        # Word-boundary matching: bare substring tests like "council" in text
        # fire on "security council", "student council of another university",
        # etc. Match whole words only.
        def _has_word(word: str) -> bool:
            return bool(re.search(rf"\b{re.escape(word)}\b", text_lower))

        strong_keywords = [
            "fees", "fee", "admission", "admissions", "placement",
            "placements", "faculty", "professor", "hod", "principal",
            "hostel", "gtu", "ahmedabad institute", "canteen", "library",
            "sports ground", "iqac", "grievance",
        ]
        weak_keywords = ["college", "campus", "committee", "council", "squad", "chairman", "chairperson"]
        has_strong = any(_has_word(k) for k in strong_keywords)
        has_weak = any(_has_word(k) for k in weak_keywords)
        # Match AIT as a standalone name; substrings such as "artificial"
        # must remain general-AI questions.
        has_ait_mention = bool(re.search(r"\bait\b", text_lower))
        has_entities = (
            len(entities.get("programs", [])) > 0 or
            len(entities.get("facilities", [])) > 0 or
            len(entities.get("faculty", [])) > 0 or
            len(entities.get("topics", [])) > 0
        )
        # Ambiguous words ("college", "council", "campus", "committee",
        # "squad") only count as institutional signals when there is another
        # AIT-specific signal in the query (AIT name, strong keyword, or
        # detected entities). "Ivy League college" or "UN Security Council"
        # must not inherit a "Verified AIT Institutional Fact" citation.
        has_college_mention = has_strong or (has_weak and (has_ait_mention or has_entities))

        if intent in cls.INSTITUTIONAL_INTENTS and (has_college_mention or has_entities):
            return "ait_institutional"
        if has_college_mention or has_ait_mention or has_entities:
            return "ait_institutional"

        # 5b. Governance keyword with no AIT/institutional context.
        # (a) An external capitalized body ("UN Security Council") is not an
        # AIT question — route to the general AI path so it never gets a
        # "Verified AIT Institutional Fact" citation.
        # (b) A lowercase governance term attached to a word that is NOT a
        # known AIT committee modifier ("anti-ragging chairman?" -> no;
        # "sports chairman?" -> no). Only queries whose subject term IS an
        # AIT committee modifier (or an AIT mention/strong keyword handled
        # above) go institutional; others ("machine council?") go to the
        # general AI path.
        # Queries that survive both checks ("library chairman?" with no
        # other signal) proceed to the institutional path, where the
        # DB-level committee name guard decides if a verified record exists;
        # if not, nothing is returned and no false citation is produced.
        known_modifiers = {
            "sports", "library", "canteen", "academic", "anti", "ragging",
            "anti-ragging", "internal", "complaint", "student", "grievance",
            "iqac", "admission", "placement", "discipline", "examination",
            "hostel", "transport", "scholarship", "ait", "college", "institute",
            "the", "of", "is", "who", "what", "which", "and", "for",
            "a", "an", "about", "tell", "me", "our", "your", "at", "in",
        }
        governance_match = re.search(
            r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+"
            r"(Council|Committee|Squad)\b",
            text,
        )
        if governance_match:
            preceding = governance_match.group(1).strip().split()
            non_modifier = [
                w.lower().lstrip("-") for w in preceding
                if w.lower().lstrip("-") not in known_modifiers
            ]
            if non_modifier:
                return "general_educational"

        # (b) lowercase governance word with an unknown/non-AIT subject:
        # "library chairman?" stays institutional (library IS an AIT
        # modifier), "machine council?" does not.
        governance_lower = re.search(
            r"\b([a-z]+(?:\s+[a-z]+)*)\s+(council|committee|squad|chairman|chairperson)\b",
            text_lower,
        )
        if governance_lower and not (has_ait_mention or has_entities):
            subject_words = governance_lower.group(1).split()
            non_modifier = [
                w.lstrip("-") for w in subject_words
                if w.lstrip("-") not in known_modifiers
            ]
            if non_modifier:
                return "general_educational"
        # The governance word may also come AFTER "of the <subject>" (e.g.
        # "chairman of the anti-ragging squad?"); check that window too.
        of_the_subject = re.search(
            r"\b(?:chairman|chairperson|head)\s+of\s+the\s+([a-z-]+(?:\s+[a-z-]+)*)\s+"
            r"(council|committee|squad)\b",
            text_lower,
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
        if any(term in text_lower for term in ["what is", "how does", "explain", "code for", "algorithm", "tutorial"]):
            return "general_educational"

        # Default: unmatched, non-greeting queries are treated as general
        # educational questions so they reach the AI fallback path (and get
        # logged as knowledge gaps) instead of being misread as small talk.
        return "general_educational"

source_router = SourceRouter()
