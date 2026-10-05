import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.intelligence.language import language_engine
from backend.app.intelligence.intent import intent_classifier
from backend.app.intelligence.entities import entity_extractor
from backend.app.intelligence.query_rewriter import query_rewriter
from backend.app.chat.context import context_manager
from backend.app.knowledge.source_router import source_router
from backend.app.knowledge.database import knowledge_db
from backend.app.knowledge.rag import rag_engine
from backend.app.knowledge.grounding import grounding_validator
from backend.app.images.retrieval import image_retrieval_engine
from backend.app.ai.router import ai_router
from backend.app.ai.prompts import build_system_prompt
from backend.app.chat.response_builder import (
    ADMIN_DB_SOURCE_TYPES,
    evidence_relevance,
    response_builder,
)
from backend.app.models.conversation import Message, Conversation
from backend.app.models.knowledge import KnowledgeGap
OFFICIAL_WEBSITE = "OFFICIAL_WEBSITE"
ADMIN_VERIFIED = "ADMIN_VERIFIED"
GEMINI_UNVERIFIED = "GEMINI_UNVERIFIED"
NO_VERIFIED_INFORMATION = "NO_VERIFIED_INFORMATION"
PROVIDER_ERROR = "PROVIDER_ERROR"

# P0.3 (defect 7): generic source priority, applied ONLY among evidence that
# already passed the hard relevance constraints.  Official website beats
# admin-verified, which beats Gemini; an irrelevant official page can never
# win, because it never reaches this ordering.
SOURCE_PRIORITY = {
    "website_snapshot": 3,
    OFFICIAL_WEBSITE: 3,
    ADMIN_VERIFIED: 2,
    "entity_db": 2,
    "document_chunk": 1,
}


def _citation_source_type(citation: Dict[str, Any], item: Dict[str, Any]) -> str:
    """
    Canonical source_type for one ranked citation.

    Derived from the EVIDENCE item that produced it, so a citation can never
    advertise one provenance while the answer was built from another.
    """
    item_type = (item or {}).get("source_type")
    if item_type == "website_snapshot":
        return OFFICIAL_WEBSITE
    return ADMIN_VERIFIED


def _answer_source_type(citations: List[Dict[str, Any]]) -> str:
    """
    P0.3: the answer's own source type is that of the citation the answer was
    actually built from (the top-ranked relevant evidence), never an
    independent guess.
    """
    if not citations:
        return ADMIN_VERIFIED
    return citations[0].get("source_type") or ADMIN_VERIFIED


def _source_label(
    source_type: Optional[str],
    college_name: Optional[str],
    query_spec=None,
) -> Optional[str]:
    """
    P0.1: provenance is generated from the selected EvidenceItem + QuerySpec.

    College identity comes from `query_spec.college_name` (or the DB row
    fetched into it).  It is NEVER reconstructed from the raw question --
    a question mentioning another college can never relabel provenance.

    Official:
        🌐 Official Website — {college_name}
    Admin:
        🗄️ {college_name} Database
    Gemini:
        🤖 Gemini Answer — Not Verified
    """
    if query_spec is not None:
        college_name = query_spec.college_name or college_name

    if source_type == OFFICIAL_WEBSITE:
        return f"🌐 Official Website — {college_name}" if college_name else "🌐 Official Website"
    if source_type == ADMIN_VERIFIED:
        return f"🗄️ {college_name} Database" if college_name else "🗄️ College Database"
    if source_type == GEMINI_UNVERIFIED:
        return "🤖 Gemini Answer — Not Verified"
    if source_type == NO_VERIFIED_INFORMATION:
        return "No verified college information"
    return None

def _ait_tenant_id(db: Session) -> Optional[str]:
    """AIT tenant id by code (fallback: first ACTIVE college for legacy data)."""
    from backend.app.models.college import College
    c = db.query(College).filter(College.code == "AIT").first()
    return c.id if c else None


class ChatOrchestrator:
    @classmethod
    def _split_snapshot_sections(cls, content: str):
        """
        P0.3: split a stored page body into its `SECTION:`-delimited sections.

        This is the generic structure the crawler already writes
        ("SECTION: Library\\n..."), so no per-page knowledge is required. A page
        without the marker yields a single unnamed section, which preserves the
        previous whole-page behaviour.
        """
        if not content:
            return []
        parts = re.split(r"(?=SECTION:\s*)", content)
        sections = []
        for part in parts:
            if not part or not part.strip():
                continue
            match = re.match(r"\s*SECTION:\s*([^\n]*)", part)
            sections.append({
                "title": (match.group(1).strip() if match else "") or "",
                "content": part.strip(),
            })
        return sections or [{"title": "", "content": content.strip()}]

    @classmethod
    def select_website_section(cls, website_evidence, query_spec):
        """
        P0.3: choose the ONE section of an official page that answers the
        question, ranked with the SAME generic relevance mechanism used for
        evidence.

        A DBMS question selects the DBMS section, a Courses question the Courses
        section, a Placement Cell question the Placement Cell section. There
        are deliberately no `if library` / `if hostel` / `if placement`
        branches: every decision comes from the shared relevance score, so a
        page section is never selected merely because it happened to be first.
        """
        best = None
        for item in website_evidence:
            base = str(item.get("details") or "").strip()
            if not base:
                continue
            candidates = cls._split_snapshot_sections(base)
            if len(candidates) <= 1:
                # An unstructured page is its own best section, but still pass
                # it through the shared relevance gate.  A page's retrieval
                # score alone is not enough when several pages share generic
                # words such as "facilities".
                probe = dict(item, details=base, value=base, content=base)
                score = evidence_relevance(probe, query_spec)
                if score is None:
                    continue
                score += float(item.get("relevance_score") or 0)
                if best is None or score > best[0]:
                    best = (score, item, base, item.get("section") or item.get("title"))
                continue
            for section in candidates:
                probe = {
                    "college_id": item.get("college_id"),
                    "source_type": "website_snapshot",
                    "title": item.get("title"),
                    # The section's own title is the strongest subject signal,
                    # exactly as a titled record's category would be.
                    "category": section["title"] or None,
                    "topic": section["title"] or None,
                    "name": section["title"] or item.get("title"),
                    "details": section["content"],
                    "value": section["content"],
                    "section": section["title"],
                    "source_url": item.get("source_url"),
                    "active": item.get("active", True),
                    "verified": item.get("verified", True),
                    "status": item.get("status", "ACTIVE"),
                }
                score = evidence_relevance(probe, query_spec)
                if score is None:
                    continue
                # A page that is itself relevant to the question is a better
                # host than an unrelated page that happens to share a word.
                score += float(item.get("relevance_score") or 0)
                if best is None or score > best[0]:
                    best = (
                        score,
                        item,
                        section["content"],
                        section["title"] or item.get("section") or item.get("title"),
                    )
        if best is None:
            return None
        return {"item": best[1], "content": best[2], "section": best[3]}

    @classmethod
    def _persist_live_snapshot(
        cls,
        db: Session,
        page: Dict[str, Any],
        college_id: Optional[str] = None,
        query_spec=None,
    ) -> None:
        """Upsert a live-fetched official page into website_snapshots.

        `query_spec` is accepted explicitly for tenant-aware persistence: the
        canonical college_id is taken from the spec when the caller does not
        supply one, so a live page can never be cached against an unresolved
        or foreign tenant. No schema change is involved.
        """
        if not college_id and query_spec is not None:
            college_id = getattr(query_spec, "college_id", None)
        try:
            from datetime import datetime, timezone
            import hashlib as _hashlib
            from backend.app.models.knowledge import WebsiteSnapshot
            # A live page is safe to cache only after the canonical tenant has
            # already been resolved.  URL text is not an ownership signal.
            if not college_id:
                return
            content = (page.get("content") or "")[:100000]
            if not content:
                return

            content_hash = _hashlib.sha256(
                content.encode("utf-8")
            ).hexdigest()
            now = datetime.now(timezone.utc)

            existing = db.query(WebsiteSnapshot).filter(
                WebsiteSnapshot.college_id == college_id,
                WebsiteSnapshot.url == page["url"],
            ).first()

            if not existing:
                db.add(
                    WebsiteSnapshot(
                        url=page["url"],
                        college_id=college_id,
                        title=page.get("title") or page["url"],
                        content_hash=content_hash,
                        text_content=content,
                        status_code=page.get("status_code") or 200,
                        last_crawled_at=now,
                    )
                )
            elif existing.content_hash != content_hash:
                existing.title = page.get("title") or existing.title
                existing.content_hash = content_hash
                existing.text_content = content
                existing.status_code = page.get("status_code") or 200
                existing.last_crawled_at = now
            else:
                existing.last_crawled_at = now

            db.commit()

        except Exception:
            logging.getLogger("ait.orchestrator").warning(
                "Live-fetch snapshot caching failed for %s",
                page.get("url"),
                exc_info=True,
            )
            db.rollback()

    @classmethod
    async def process_chat(
        cls,
        db: Session,
        conversation_id: str,
        user_message_text: str,
        user_id: Optional[str] = None,
        college_id: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        persist_message: bool = True,
    ) -> Dict[str, Any]:
        """
        Master Chat Orchestration Pipeline.

        Processes user query through:
        Language Detection -> Query Normalization ->
        Intent Detection -> Entity Extraction ->
        Context Follow-up Resolution ->
        Intent-Aware Source Routing ->
        Grounded Retrieval -> Natural Answer Generation.
        """

        # 0. Prompt Injection Defense & Untrusted Content Sanitization
        from backend.app.security.prompt_guard import prompt_guard

        is_safe, sanitized_msg = prompt_guard.inspect_user_input(
            user_message_text
        )

        if not is_safe:
            user_message_text = sanitized_msg

        # 1. Fetch conversation history for coreference and follow-up context
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        recent_msgs = []

        if conv:
            recent_db_msgs = (
                db.query(Message)
                .filter(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
                .all()
            )

            recent_msgs = [
                {
                    "sender": m.sender,
                    "content": m.content,
                }
                for m in recent_db_msgs[-8:]
            ]

        # 2. Context Follow-up & Coreference Resolution
        context_res = context_manager.resolve_context(
            user_message_text,
            recent_msgs,
        )

        resolved_query = context_res["resolved_query"]

        # 3. Multilingual Language Detection
        lang_info = language_engine.detect_language(resolved_query)
        detected_lang = lang_info.get("language", "en")
        from backend.app.intelligence.query_rewriter import query_rewriter
        understanding_query = query_rewriter.rewrite_query(resolved_query, detected_lang)["normalized_query"]
        understanding_query = re.sub(r"\blateset\b", "latest", understanding_query, flags=re.IGNORECASE)
        understanding_query = re.sub(r"\bevnts?\b", "events", understanding_query, flags=re.IGNORECASE)

        # 4. Intent Classification
        intent_info = intent_classifier.classify_intent(understanding_query)

        if (
            intent_info["intent"] == "UNKNOWN"
            and context_res.get("inferred_intent")
        ):
            intent_info["intent"] = context_res["inferred_intent"]
            intent_info["confidence"] = 0.85

        # 5. Academic Entity & Topic Extraction.
        # Its output is immediately folded into the canonical QuerySpec below.
        entities = entity_extractor.extract_entities(understanding_query)

        if (
            context_res.get("inferred_topic")
            and context_res["inferred_topic"]
            not in entities["topics"]
        ):
            entities["topics"].append(
                context_res["inferred_topic"]
            )

        # 5. Query understanding builds the ONE canonical QuerySpec.
        # Every downstream stage (routing, DB retrieval, website retrieval,
        # evidence normalization, answer building, grounding, provenance,
        # Gemini fallback, clarification) reads this object and nothing else.
        #
        # The legacy `entities` dict is retained ONLY as the input to spec
        # construction (it carries the multi-value entity bag); it is never
        # read again after this point.

        # 6. Query Rewriting & Normalization
        rewritten = query_rewriter.rewrite_query(
            resolved_query,
            detected_lang,
        )
        search_query = re.sub(r"\blateset\b", "latest", rewritten["normalized_query"], flags=re.IGNORECASE)
        search_query = re.sub(r"\bevnts?\b", "events", search_query, flags=re.IGNORECASE)

        from backend.app.intelligence.entities import EntityExtractor
        from backend.app.models.college import College as _College

        college_name = None
        if college_id:
            _c = (
                db.query(_College)
                .filter(_College.id == college_id)
                .first()
            )
            college_name = _c.name if _c else None

        # 6.5 Build the single canonical QuerySpec after understanding.
        query_spec = EntityExtractor.extract_query_understanding(
            understanding_query, college_id=college_id,
            intent=intent_info.get("intent"),
        )
        # Merge the multi-value entity bag resolved in step 5 onto the spec.
        for _key, _attr in (
            ("programs", "programs"), ("topics", "topics"),
            ("facilities", "facilities"), ("subjects", "subjects"),
            ("faculty", "faculty_names"),
        ):
            _legacy = list(entities.get(_key) or [])
            if _key == "programs":
                _legacy = [p for p in _legacy if p in (query_spec.programs or [])]
            if not _legacy:
                continue
            _current = list(getattr(query_spec, _attr) or [])
            for _value in _legacy:
                if _value not in _current:
                    _current.append(_value)
            setattr(query_spec, _attr, _current)
        if entities.get("semester") and not query_spec.semester:
            query_spec.semester = entities.get("semester")
        if not query_spec.topic and query_spec.topics:
            query_spec.topic = query_spec.topics[0]
        if not query_spec.category and query_spec.topic:
            query_spec.category = query_spec.topic
        if not query_spec.program and query_spec.programs:
            query_spec.program = query_spec.programs[0]
        if not query_spec.entity and (
            query_spec.subjects or query_spec.facilities or query_spec.faculty_names
        ):
            query_spec.entity = (
                query_spec.subjects or query_spec.facilities or query_spec.faculty_names
            )[0]
        query_spec.college_name = college_name
        query_spec.confidence = intent_info.get("confidence")

        # 7. Source Router -- receives the QuerySpec, nothing else.
        has_user_files = bool(attachments)

        route = source_router.route_query(
            query_spec,
            has_user_files=has_user_files,
        )
        query_spec.route = route
        # Institutional facts without a resolved tenant must not reach retrieval
        # or the general-AI fallback (which could invent a college answer).
        missing_college = route in ("institutional", "ait_institutional", "visual") and not query_spec.college_id
        # 8. Retrieval & Response Formulation
        system_prompt = build_system_prompt(
            college_name or "the selected college",
            query_spec=query_spec,
        )

        gemini_invoked = False
        retrieved_images = []
        retrieved_entities = []
        retrieved_chunks = []
        citations = []
        table_data = None
        text_content = ""
        grounding_status = "verified"
        provider_failure_message = None

        # ---------------------------------------------------------
        # PATH A: GREETING & CASUAL CONVERSATION
        # ---------------------------------------------------------
        if route == "greeting":

            if any(
                w in resolved_query.lower()
                for w in ["bye", "goodbye", "see you"]
            ):
                text_content = (
                    f"Goodbye! Feel free to return anytime if you have "
                    f"more questions about {college_name}. "
                    "Best of luck with your studies!"
                    if college_name
                    else
                    "Goodbye! Feel free to return anytime if you have "
                    "more questions. Best of luck with your studies!"
                )

            elif any(
                w in resolved_query.lower()
                for w in ["thank", "thanks"]
            ):
                text_content = (
                    f"You're very welcome! If you need details on "
                    f"{college_name} admissions, fees, placements, or "
                    "courses, I'm always here to help. 👋"
                    if college_name
                    else
                    "You're very welcome! If you need details on "
                    "courses, fees, admissions, or placements, "
                    "I'm always here to help. 👋"
                )

            else:
                text_content = (
                    f"Hello! 👋 Welcome to the {college_name} AI Assistant. "
                    "How can I help you today with admissions, courses, "
                    "fees, placements, faculty, or campus facilities?"
                    if college_name
                    else
                    "Hello! 👋 Welcome to the AI FAQ College Chat Bot. "
                    "How can I help you today with admissions, courses, "
                    "fees, placements, faculty, or campus facilities?"
                )

            grounding_status = "conversational"

        # ---------------------------------------------------------
        # PATH B: VISUAL MEDIA REQUEST
        # ---------------------------------------------------------
        elif route in ("visual", "ait_visual"):

            retrieved_images = (
                image_retrieval_engine.match_visual_query(
                    db,
                    search_query,
                    college_id=college_id,
                )
            )

            if retrieved_images:
                text_content = (
                    "Here are verified official photos matching "
                    "your request:"
                )
            else:
                retrieved_images = (
                    image_retrieval_engine.match_visual_query(
                        db,
                        "campus",
                        college_id=query_spec.college_id,
                    )
                )

                if retrieved_images:
                    text_content = (
                        "Here are official photographs of the "
                        "campus and facilities:"
                    )
                else:
                    text_content = (
                        "I searched the official media repository, "
                        "but no verified official photo is currently "
                        "published for that specific facility."
                    )

        # ---------------------------------------------------------
        # PATH C: INSTITUTIONAL FACTS
        # ---------------------------------------------------------
        elif route in ("ait_institutional", "institutional"):

            query_lower = search_query.lower()

            # P0.1: all query-shape flags come from the QuerySpec, once.
            is_transport_query = query_spec.is_transport_query
            is_catalog_query = (
                (query_spec.intent or "") == "COURSES"
                and query_spec.is_courses_listing_query
            )
            is_committee_query = query_spec.is_committee_query
            is_placement_query = (
                query_spec.is_placement_query
                or (query_spec.intent or "") == "PLACEMENT"
            )

            # Source priority / tenant handling
            # Source routing may use the canonical AIT tenant as a policy
            # decision, but ownership is always the resolved College.id passed
            # into every retrieval query.
            is_ait = college_id == _ait_tenant_id(db)
            website_snaps = []

            if is_ait:
                if is_catalog_query:
                    retrieved_entities = knowledge_db.get_by_category(
                        db,
                        "program",
                        college_id=query_spec.college_id,
                    )
                else:
                    retrieved_entities = knowledge_db.query_entities(
                        db,
                        search_query,
                        college_id=query_spec.college_id,
                        query_spec=query_spec,
                    )
                website_snaps = knowledge_db.query_website_snapshots(
                    db,
                    search_query,
                    college_id=query_spec.college_id,
                    query_spec=query_spec,
                )
                if query_spec.is_fee_query or "FEES" in (query_spec.topics or []):
                    fee_query = search_query if query_spec.programs else "fees"
                    retrieved_entities = knowledge_db.query_entities(
                        db, fee_query, college_id=college_id,
                        query_spec=query_spec,
                    )
                    if query_spec.programs and retrieved_entities:
                        requested_program = str(
                            query_spec.program or query_spec.programs[0]
                        ).split("(", 1)[0].strip().lower()
                        retrieved_entities = [
                            item for item in retrieved_entities
                            if requested_program in str(item.get("name", "")).lower()
                            or requested_program in str(item.get("details", {})).lower()
                        ]
            else:
                website_snaps = knowledge_db.query_website_snapshots(
                    db,
                    search_query,
                    college_id=query_spec.college_id,
                    query_spec=query_spec,
                )
                retrieved_entities = knowledge_db.query_entities(
                        db,
                        search_query,
                        college_id=query_spec.college_id,
                        query_spec=query_spec,
                    )

            if is_committee_query:
                website_snaps = knowledge_db.query_website_snapshots(
                    db,
                    search_query,
                    college_id=college_id,
                    query_spec=query_spec,
                )
                retrieved_entities = [
                    e
                    for e in retrieved_entities
                    if any(
                        term
                        in (
                            f"{e.get('name', '')} "
                            f"{e.get('details', '')}"
                        ).lower()
                        for term in [
                            "committee",
                            "council",
                            "squad",
                            "iqac",
                            "grievance",
                            "cell",
                        ]
                    )
                ]

            # -----------------------------------------------------
            # 2. Entity fallback: Search by program
            # -----------------------------------------------------
            if (
                not retrieved_entities
                and not website_snaps
                and query_spec.programs
            ):
                fallback_entities = []

                for prog in query_spec.programs:
                    fallback_entities.extend(
                        knowledge_db.query_entities(
                            db,
                            prog,
                            college_id=college_id,
                            query_spec=query_spec,
                        )
                    )

                # P0.1: academic year and fee-ness come from the QuerySpec.
                requested_years_fb = query_spec.requested_years
                is_fee_query_fb = query_spec.is_fee_query

                if requested_years_fb and is_fee_query_fb:
                    fallback_entities = [
                        e
                        for e in fallback_entities
                        if any(
                            (
                                e.get("academic_year")
                                and year.replace(" ", "")
                                in str(
                                    e.get("academic_year")
                                ).replace(" ", "")
                            )
                            or (
                                year.replace(" ", "")
                                in str(
                                    e.get("details", {})
                                ).lower()
                            )
                            for year in requested_years_fb
                        )
                    ]

                retrieved_entities = fallback_entities

            # -----------------------------------------------------
            # 3. Topic fallback
            #
            # IMPORTANT TRANSPORTATION FIX:
            # Transportation is often classified as FACILITIES.
            # Do NOT query the broad "facilities" topic because it
            # can return unrelated placement/faculty/library/etc.
            # records.
            # -----------------------------------------------------
            if not retrieved_entities and not website_snaps:

                current_intent = query_spec.intent

                is_transport_query = query_spec.is_transport_query

                if (
                    current_intent == "FEES"
                    or "FEES" in (query_spec.topics or [])
                ):
                    retrieved_entities = (
                        knowledge_db.query_entities(
                            db,
                            search_query if query_spec.programs else "fees",
                            college_id=college_id,
                            query_spec=query_spec,
                        )
                    )

                elif (
                    current_intent
                    in ["PLACEMENT", "placement_info"]
                    or "PLACEMENT" in (query_spec.topics or [])
                ):
                    retrieved_entities = (
                        knowledge_db.query_entities(
                            db,
                            "placement",
                            college_id=college_id,
                            query_spec=query_spec,
                        )
                    )

                elif (
                    current_intent
                    in ["FACULTY", "faculty_lookup"]
                    or "FACULTY" in (query_spec.topics or [])
                ):
                    retrieved_entities = (
                        knowledge_db.query_entities(
                            db,
                            "faculty",
                            college_id=college_id,
                            query_spec=query_spec,
                        )
                    )

                elif current_intent in [
                    "LIBRARY",
                    "LAB",
                    "CAMPUS",
                    "FACILITIES",
                ]:

                    # Transportation must preserve the original query.
                    # A broad "facilities" query can retrieve unrelated
                    # placement, faculty, library, event, or contact data.
                    fallback_query = (
                        search_query
                        if is_transport_query
                        else current_intent.lower()
                    )

                    retrieved_entities = (
                        knowledge_db.query_entities(
                            db,
                            fallback_query,
                            college_id=college_id,
                            query_spec=query_spec,
                        )
                    )

                    # Final transportation relevance guard.
                    if (
                        is_transport_query
                        and retrieved_entities
                    ):
                        retrieved_entities = [
                            e
                            for e in retrieved_entities
                            if knowledge_db.topic_relevance_score(
                                search_query,
                                (
                                    f"{e.get('name', '')} "
                                    f"{e.get('category', '')} "
                                    f"{e.get('details', '')}"
                                ),
                                title=e.get("name", ""),
                                url=e.get("source_url", ""),
                            )
                            is not None
                        ]

                elif current_intent in [
                    "ADMISSION",
                    "ADMISSION_DATES",
                    "ELIGIBILITY",
                ]:
                    retrieved_entities = (
                        knowledge_db.query_entities(
                            db,
                            "contact",
                            college_id=college_id,
                        )
                    )

            # -----------------------------------------------------
            # 4. LOCATION / CONTACT
            # -----------------------------------------------------
            if query_spec.intent in (
                "LOCATION",
                "CONTACT",
            ):
                contact_hits = (
                    knowledge_db.query_entities(
                        db,
                        "location address contact",
                        college_id=query_spec.college_id,
                        query_spec=query_spec,
                    )
                )

                seen_names = {
                    e.get("name")
                    for e in retrieved_entities
                }

                retrieved_entities = (
                    retrieved_entities
                    + [
                        e
                        for e in contact_hits
                        if e.get("name") not in seen_names
                    ][:5]
                )

            # -----------------------------------------------------
            # 5. Official website
            # -----------------------------------------------------
            if not is_ait:
                pass
            elif is_committee_query:
                website_snaps = knowledge_db.query_website_snapshots(
                    db,
                    search_query,
                    college_id=college_id,
                    query_spec=query_spec,
                )
            elif not retrieved_entities:
                website_snaps = knowledge_db.query_website_snapshots(
                    db,
                    search_query,
                    college_id=college_id,
                    query_spec=query_spec,
                )

            # -----------------------------------------------------
            # Live AIT website fallback
            # -----------------------------------------------------
            if (
                not retrieved_entities
                and not website_snaps
                and not is_committee_query
                and college_id == _ait_tenant_id(db)
            ):
                from backend.app.knowledge.crawler import (
                    website_crawler,
                )

                page = (
                    await website_crawler.fetch_relevant_page(
                        search_query
                    )
                )

                page_content = (
                    (page.get("content") or "").lower()
                    if page
                    else ""
                )

                requested_programs = [
                    program.split("(", 1)[0]
                    .strip()
                    .lower()
                    for program in (query_spec.programs or [])
                ]

                program_scope_matches = (
                    not requested_programs
                    or any(
                        program in page_content
                        for program in requested_programs
                    )
                )

                if (
                    page
                    and page.get("content")
                    and page.get("extraction_status")
                    == "EXTRACTED"
                    and program_scope_matches
                ):
                    website_snaps = [
                        {
                            "url": page["url"],
                            "title": page["title"],
                            "content": page["content"],
                            "text_content": page["content"],
                            "source_domain": "aitindia.in",
                            "authority": (
                                f"Official "
                                f"{college_name or 'Ahmedabad Institute of Technology'} "
                                "Website"
                            ),
                        }
                    ]

                    cls._persist_live_snapshot(
                        db,
                        page,
                        college_id=query_spec.college_id,
                        query_spec=query_spec,
                    )

            # -----------------------------------------------------
            # 6. Institutional RAG
            # -----------------------------------------------------
            retrieved_chunks = rag_engine.search(
                db,
                search_query,
                college_id=college_id,
                user_id=None,
                top_k=3,
            )

            if retrieved_entities or (
                website_snaps
                and not is_committee_query
            ):
                retrieved_chunks = []

            # -----------------------------------------------------
            # Evidence aggregation
            # -----------------------------------------------------
            all_evidence = []

            if is_committee_query:

                ranked_snapshots = []
                query_keywords = set(
                    search_query.lower().split()
                )

                for s in website_snaps:
                    section = (
                        s.get("section_title") or ""
                    ).lower()

                    content = (
                        s.get("content") or ""
                    ).lower()

                    score = 0

                    for keyword in query_keywords:
                        if len(keyword) > 2:
                            if keyword in section:
                                score += 10

                            if keyword in content:
                                score += 2

                    if len(content) < 50:
                        score -= 5

                    ranked_snapshots.append(
                        (score, s)
                    )

                ranked_snapshots.sort(
                    key=lambda x: x[0],
                    reverse=True,
                )

                for score, s in ranked_snapshots:
                    all_evidence.append(
                        {
                            "id": s.get("id"),
                            "college_id": s.get("college_id"),
                            "title": s.get("title"),
                            "name": (
                                s.get("section_title")
                                or s.get("title")
                                or f"{college_name or 'College'} Official Website"
                            ),
                            "details": (
                                s.get("content") or ""
                            ),
                            "source_type": (
                                "website_snapshot"
                            ),
                            "active": s.get("active", True),
                            "last_crawled_at": s.get("last_crawled_at"),
                            "created_at": s.get("created_at"),
                            "updated_at": s.get("updated_at"),
                            "date": s.get("date"),
                            "summary": s.get("summary"),
                            "description": s.get("description"),
                            "topic": s.get("topic"),
                            "metadata": s.get("metadata"),
                            "source_url": s.get(
                                "url",
                                "",
                            ),
                            "section": s.get(
                                "section_title"
                            ),
                        }
                    )

                    citations.append(
                        {
                            "title": (
                                s.get("section_title")
                                or s.get(
                                    "title",
                                    "Official Website",
                                )
                            ),
                            "source_url": s.get(
                                "url",
                                "",
                            ),
                            "authority": (
                                s.get("authority")
                                or f"Official {college_name or 'College'} Website"
                            ),
                            "section": s.get(
                                "section_title"
                            ),
                            "source_type": (
                                "OFFICIAL_COLLEGE_WEBSITE"
                            ),
                        }
                    )

            # -----------------------------------------------------
            # DB entities
            # -----------------------------------------------------
            for e in retrieved_entities:

                _auth = (
                    e.get("authority")
                    or f"{college_name or 'College'} Verified Database"
                )

                if "demo" in _auth.lower():
                    _auth = (
                        f"{_auth} — NOT official information "
                        "(development test data)"
                    )

                all_evidence.append(
                    {
                        "id": e.get("id"),
                        "college_id": e.get("college_id"),
                        "name": e.get("name"),
                        "category": e.get("category"),
                        "topic": e.get("topic") or e.get("category"),
                        "program": e.get("program") or e.get("course") or (e.get("details") or {}).get("program") if isinstance(e.get("details"), dict) else e.get("program") or e.get("course"),
                        "course": e.get("course"),
                        "academic_year": e.get("academic_year"),
                        "details": e.get("details"),
                        "source_type": "entity_db",
                        "verified": e.get("is_verified", False),
                        "status": e.get("status", "ACTIVE"),
                        "authority": _auth,
                        "source_url": e.get(
                            "source_url",
                            "",
                        ),
                    }
                )

                citations.append(
                    {
                        "title": e.get("name"),
                        "source_url": e.get(
                            "source_url",
                            "",
                        ),
                        "authority": _auth,
                        "source_type": (
                            "DEMO_TEST_DATA"
                            if "demo" in _auth.lower()
                            else "DATABASE"
                        ),
                    }
                )

            # -----------------------------------------------------
            # Normal website snapshots
            # -----------------------------------------------------
            if not is_committee_query:

                for s in website_snaps:
                    all_evidence.append(
                        {
                            "id": s.get("id"),
                            "college_id": s.get("college_id"),
                            "title": s.get("title"),
                            "name": (
                                s.get("section_title")
                                or s.get("title")
                                or f"{college_name or 'College'} Official Website"
                            ),
                            "details": (
                                s.get("content") or ""
                            ),
                            "category": s.get("category"),
                            "topic": s.get("topic"),
                            "summary": s.get("summary"),
                            "description": s.get("description"),
                            "metadata": s.get("metadata"),
                            "source_type": (
                                "website_snapshot"
                            ),
                            "active": s.get("active", True),
                            "last_crawled_at": s.get("last_crawled_at"),
                            "created_at": s.get("created_at"),
                            "updated_at": s.get("updated_at"),
                            "date": s.get("date"),
                            "source_url": s.get(
                                "url",
                                "",
                            ),
                            "section": s.get(
                                "section_title"
                            ),
                        }
                    )

                    citations.append(
                        {
                            "title": (
                                s.get("section_title")
                                or s.get(
                                    "title",
                                    "Official Website",
                                )
                            ),
                            "source_url": s.get(
                                "url",
                                "",
                            ),
                            "authority": (
                                s.get("authority")
                                or f"Official {college_name or 'College'} Website"
                            ),
                            "section": s.get(
                                "section_title"
                            ),
                            "source_type": (
                                "OFFICIAL_COLLEGE_WEBSITE"
                            ),
                        }
                    )

            # -----------------------------------------------------
            # RAG evidence
            # -----------------------------------------------------
            for c in retrieved_chunks:

                all_evidence.append(
                    {
                        "name": c.get(
                            "title",
                            "Official Institutional Document",
                        ),
                        "details": c.get(
                            "content",
                            "",
                        ),
                        "source_type": "document_chunk",
                        "college_id": c.get("college_id"),
                        "source_url": c.get(
                            "source_url",
                            "",
                        ),
                    }
                )

                citations.append(
                    {
                        "title": c.get(
                            "title",
                            "Institutional Document",
                        ),
                        "source_url": c.get(
                            "source_url",
                            "",
                        ),
                        "authority": (
                            f"{college_name or 'College'} "
                            "Official Document"
                        ),
                    }
                )

            # Normalize and gate ALL candidates before source priority, answer
            # construction, grounding or citation selection. No source can win
            # simply because it is official or admin-verified.
            #
            # P0.3 (defect 7) GENERIC SOURCE SELECTION:
            #   1. hard relevance constraints  (evidence_relevance -> None drops)
            #   2. semantic relevance score
            #   3. evidence ranking            (by that score)
            #   4. source priority             (only AMONG relevant evidence)
            #
            #   OFFICIAL_WEBSITE > ADMIN_VERIFIED > GEMINI_UNVERIFIED
            #
            # An irrelevant official page can therefore NEVER outrank a
            # relevant admin record: it was already removed in step 1.
            ranked = []
            for item, citation in zip(all_evidence, citations):
                score = evidence_relevance(item, query_spec)
                if score is not None:
                    ranked.append((item, citation, score))
            temporal = bool(getattr(query_spec, "temporal_qualifier", None))
            def evidence_timestamp(item):
                from datetime import datetime, timezone
                metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
                for candidate in (
                    item.get("event_date"), item.get("date"), item.get("published_at"),
                    item.get("publication_date"), item.get("last_crawled_at"),
                    item.get("updated_at"), item.get("created_at"),
                    metadata.get("event_date"), metadata.get("date"),
                    metadata.get("published_at"), metadata.get("publication_date"),
                ):
                    if not candidate:
                        continue
                    try:
                        parsed = candidate if isinstance(candidate, datetime) else datetime.fromisoformat(str(candidate).replace("Z", "+00:00"))
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=timezone.utc)
                        return parsed.timestamp()
                    except (TypeError, ValueError, OverflowError):
                        continue
                return float("-inf")
            if temporal:
                # Relevance must remain primary. Dates only order candidates
                # that passed the generic topical relevance gate.
                ranked.sort(key=lambda row: (
                    row[2], evidence_timestamp(row[0]),
                    SOURCE_PRIORITY.get(row[0].get("source_type"), 0),
                ), reverse=True)
            else:
                ranked.sort(key=lambda row: (
                    row[2], SOURCE_PRIORITY.get(row[0].get("source_type"), 0)
                ), reverse=True)
            all_evidence = [dict(item, relevance_score=score) for item, _, score in ranked]
            # Recompute the canonical source_type on each surviving citation so
            # provenance and answer_status can never disagree with it.
            citations = []
            for item, citation, _ in ranked:
                canonical = _citation_source_type(citation, item)
                citation = dict(citation)
                citation["source_type"] = canonical
                citation["official_citation"] = canonical == OFFICIAL_WEBSITE
                citations.append(citation)

            # -----------------------------------------------------
            # 7. Generate grounded answer
            # -----------------------------------------------------
            if all_evidence and not missing_college:

                website_evidence = [
                    item for item in all_evidence
                    if item.get("source_type") == "website_snapshot"
                ]
                # P0.3 (defect 2): the answer comes from the BEST RELEVANT
                # SECTION, not from whatever snapshot happened to be ranked
                # first. A DBMS question selects the DBMS section even when the
                # Library page outranks it for lexical reasons.
                selected_section = cls.select_website_section(
                    website_evidence, query_spec
                ) if website_evidence else None
                if selected_section:
                    text_content = str(selected_section["content"] or "").strip()
                elif any(
                    item.get("source_type") in ADMIN_DB_SOURCE_TYPES
                    for item in all_evidence
                ):
                    # Admin-verified records are the answer's facts, not page
                    # metadata, so their structured value is returned verbatim.
                    text_content = response_builder.build_grounded_answer(
                        all_evidence, query_spec=query_spec, query=resolved_query
                    )
                    if not text_content:
                        text_content = " ".join(
                            str(item.get("details") or "").strip()
                            for item in all_evidence if str(item.get("details") or "").strip()
                        )
                else:
                    text_content = response_builder.build_grounded_answer(
                        all_evidence, query_spec=query_spec, query=resolved_query
                    )
                if not text_content:
                    text_content = "I couldn't verify that specific information from the connected college sources. I will not guess."

                grounding_res = (
                    grounding_validator.validate_answer(
                        query=user_message_text,
                        route=route,
                        query_spec=query_spec,
                        retrieved_evidence=all_evidence,
                        candidate_answer=text_content,
                    )
                )

                text_content = grounding_res["answer"]
                grounding_status = (
                    grounding_res["grounding_status"]
                )

                # Rebuild any rejected answer from the same normalized evidence
                # before allowing the no-evidence/Gemini path to remain visible.
                if grounding_status == "unverified" and all_evidence:
                    rebuilt_answer = response_builder.build_grounded_answer(
                        all_evidence, query_spec=query_spec, query=resolved_query
                    )
                    if rebuilt_answer:
                        retry_grounding = grounding_validator.validate_answer(
                            query=user_message_text,
                            route=route,
                            query_spec=query_spec,
                            retrieved_evidence=all_evidence,
                            candidate_answer=rebuilt_answer,
                        )
                        if retry_grounding["grounding_status"] == "verified":
                            text_content = retry_grounding["answer"]
                            grounding_status = "verified"
                # If the provider returns an unsupported fallback despite
                # official website evidence, use the retrieved page content as
                # the grounded answer instead of downgrading valid evidence to
                # Gemini-unverified. This remains tenant-scoped and generic.
                if grounding_status == "unverified" and any(
                    item.get("source_type") == "website_snapshot"
                    for item in all_evidence
                ):
                    # Re-select the same best relevant section rather than
                    # falling back to an arbitrary official page.
                    fallback_section = cls.select_website_section(
                        [item for item in all_evidence
                         if item.get("source_type") == "website_snapshot"],
                        query_spec,
                    )
                    text_content = str(
                        (fallback_section or {}).get("content") or ""
                    ).strip()
                    grounding_status = "verified" if text_content else grounding_status
            elif missing_college:

                # Fail closed: no tenant, no retrieval, no provider.
                text_content = (
                    "Please select a college so I can check its verified information."
                )
                grounding_status = "unverified"

            else:

                # Institutional questions fail closed after verified official and
                # admin evidence has been exhausted.  Gemini remains available
                # only through the general/non-institutional route below; it must
                # never turn an institutional evidence gap into unrelated advice.
                topic_label = str(query_spec.topic or query_spec.category or "institutional").lower()
                if query_spec.temporal_qualifier:
                    text_content = (
                        f"The {query_spec.temporal_qualifier} information about {topic_label} at "
                        f"{college_name or 'the selected college'} could not be verified from the "
                        "available official website or admin-verified records."
                    )
                else:
                    field_label = str(query_spec.requested_field or "information").lower()
                    if field_label.endswith("s") and not field_label.endswith("ss"):
                        field_label = field_label[:-1]
                    text_content = (
                        f"The specific {topic_label} {field_label} requirements could not be "
                        "verified from the official college website or admin-verified records."
                    )
                grounding_status = "unverified"

                from backend.app.knowledge.gaps import record_gap
                record_gap(
                    db,
                    college_id=college_id,
                    question=user_message_text,
                    sample_answer=text_content,
                    reason="no_verified_source",
                    conversation_id=conversation_id,
                    detected_intent=intent_info.get("intent"),
                    missing_entity=str(entities),
                )

        # ---------------------------------------------------------
        # PATH D: PRIVATE USER DOCUMENT SEARCH
        # ---------------------------------------------------------
        elif route == "user_file_specific" and user_id:

            retrieved_chunks = rag_engine.search(
                db,
                search_query,
                user_id=user_id,
                top_k=4,
            )

            if retrieved_chunks:
                context_str = "\n\n".join(
                    [
                        c["content"]
                        for c in retrieved_chunks
                    ]
                )

                text_content = (
                    "Based on your uploaded document:\n\n"
                    f"{context_str}"
                )
            else:
                text_content = (
                    "I could not find matching information "
                    "in your uploaded documents."
                )

            grounding_status = "user_context"

        # ---------------------------------------------------------
        # PATH E: GENERAL EDUCATIONAL / CONVERSATIONAL
        # ---------------------------------------------------------
        else:

            gemini_invoked = True
            text_content = (
                await ai_router.generate_response(
                    prompt=resolved_query,
                    system_instruction=system_prompt,
                    evidence=None,
                    context_history=recent_msgs,
                    db=db,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    query_spec=query_spec,
                )
            )

            grounding_status = "general_ai"

        # ---------------------------------------------------------
        # 9. Format response blocks and citations
        # ---------------------------------------------------------
        if route in ("ait_institutional", "institutional"):

            if grounding_status == "verified":

                _src_url = (
                    citations[0].get("source_url")
                    if citations
                    else None
                )

                _src_parts = (
                    _src_url or ""
                ).split("/")

                _src_domain = (
                    _src_parts[2]
                    if len(_src_parts) > 2
                    and _src_parts[2]
                    else None
                )

                provenance = {
                    "authority": (
                        citations[0].get("authority")
                        if citations
                        else (
                            college_name
                            or "Verified College Database"
                        )
                    ),
                    "source_type": _answer_source_type(citations),
                    "source_context": {
                        "active_college_id": college_id,
                        "active_college_name": college_name,
                        "source_label": _source_label(
                            _answer_source_type(citations),
                            college_name,
                            query_spec,
                        ),
                    },
                    "answer_status": _answer_source_type(citations),
                    "verified": True,
                    "source_domain": _src_domain,
                    "source_url": (
                        citations[0].get(
                            "source_url"
                        )
                        if citations
                        else None
                    ),
                    "verified_at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                    "retrieved_at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                    "section": (
                        citations[0].get(
                            "section"
                        )
                        if citations
                        else None
                    ),
                }
                provenance["source_label"] = _source_label(
                    provenance["source_type"], college_name, query_spec
                )

            else:

                source_type = GEMINI_UNVERIFIED if gemini_invoked else NO_VERIFIED_INFORMATION
                citations = []
                provenance = {
                    "authority": (
                        "General AI Academic Knowledge — "
                        "Gemini-generated, not verified by the college"
                        if source_type == GEMINI_UNVERIFIED
                        else "No verified college source was available"
                    ),
                    "source_type": source_type,
                    "answer_status": source_type,
                    "source_context": {
                        "active_college_id": college_id,
                        "active_college_name": college_name,
                        "provenance": "no_verified_source" if source_type == NO_VERIFIED_INFORMATION else "gemini_unverified",
                    },
                    "verified": False,
                    "source_domain": None,
                    "verified_at": "Unverified - Fallback Response",
                }
                provenance["source_label"] = _source_label(source_type, college_name, query_spec)

        elif route in ("visual", "ait_visual"):

            provenance = (
                {
                    "authority": (
                        college_name
                        or "Official College Media Repository"
                    ),
                    "source_type": OFFICIAL_WEBSITE,
                    "answer_status": OFFICIAL_WEBSITE,
                    "source_context": {
                        "active_college_id": college_id,
                        "active_college_name": college_name,
                    },
                    "verified": True,
                    "source_label": _source_label(OFFICIAL_WEBSITE, college_name, query_spec),
                    "source_domain": None,
                    "verified_at": "Official Media Repository",
                }
                if retrieved_images
                else None
            )

        else:
            provenance = {
                "authority": "General AI Academic Knowledge — Gemini-generated, not verified by the college",
                "source_type": GEMINI_UNVERIFIED,
                "answer_status": GEMINI_UNVERIFIED,
                "source_context": {
                    "active_college_id": college_id,
                    "active_college_name": college_name,
                    "provenance": "gemini_unverified",
                },
                "verified": False,
                "source_label": _source_label(GEMINI_UNVERIFIED, college_name, query_spec),
                "source_domain": None,
                "verified_at": "Unverified - General AI Response",
            }

        suggestions = []

        if route in ("ait_institutional", "institutional"):
            suggestions = [
                "What are the eligibility criteria?",
                "Tell me about placements",
                "Show campus photos",
            ]

        elif route in ("visual", "ait_visual"):
            suggestions = [
                "Show computer lab",
                "Show library",
                "What courses are offered?",
            ]

        elif route == "greeting":
            suggestions = [
                "What are the fees?",
                "Tell me about placements",
                "Show campus photos",
            ]

        blocks = response_builder.build_blocks(
            text_content=text_content,
            images=retrieved_images,
            table_data=table_data,
            citations=citations,
            provenance=provenance,
            suggestions=suggestions,
        )

        # ---------------------------------------------------------
        # 10. Never persist or stream an empty answer
        # ---------------------------------------------------------
        if not (text_content or "").strip():

            text_content = (
                "I'm sorry — I couldn't reach any AI provider "
                "right now. Please try again in a moment."
            )

            grounding_status = "unverified"

        # ---------------------------------------------------------
        # 9.5 Unanswered-question detection
        # ---------------------------------------------------------
        if (
            route == "ait_institutional"
            and grounding_status not in ("verified",)
        ):

            from backend.app.knowledge.gaps import (
                record_gap,
                is_unanswered,
            )

            if is_unanswered(
                text_content,
                grounding_status,
            ):

                record_gap(
                    db,
                    college_id=college_id,
                    question=user_message_text,
                    sample_answer=text_content,
                    reason=(
                        "low_confidence"
                        if grounding_status != "unverified"
                        else "no_verified_source"
                    ),
                    conversation_id=conversation_id,
                    detected_intent=intent_info.get(
                        "intent"
                    ),
                )

        # ---------------------------------------------------------
        # 10. Persist message to database
        # ---------------------------------------------------------
        message_id = str(uuid.uuid4())

        assistant_msg = Message(
            id=message_id,
            conversation_id=conversation_id,
            sender="assistant",
            content=text_content,
            blocks=blocks,
            language=detected_lang,
            intent=intent_info.get("intent"),
            grounding_status=grounding_status,
            citations=citations,
            provenance=provenance or {},
        )

        if persist_message:
            db.add(assistant_msg)
            db.commit()

        return {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "text_content": text_content,
            "blocks": blocks,
            "grounding_status": (
                assistant_msg.grounding_status
            ),
            "source_type": (provenance or {}).get("source_type"),
            "source_context": (provenance or {}).get("source_context"),
            "answer_status": (provenance or {}).get("answer_status"),
            "verified": (provenance or {}).get("verified", False),
            "language": detected_lang,
        }


chat_orchestrator = ChatOrchestrator()