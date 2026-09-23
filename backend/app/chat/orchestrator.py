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
from backend.app.chat.response_builder import response_builder
from backend.app.models.conversation import Message, Conversation
from backend.app.models.knowledge import KnowledgeGap

def _ait_tenant_id(db: Session) -> Optional[str]:
    """AIT tenant id by code (fallback: first ACTIVE college for legacy data)."""
    from backend.app.models.college import College
    c = db.query(College).filter(College.code == "AIT").first()
    return c.id if c else None


class ChatOrchestrator:
    @classmethod
    def _persist_live_snapshot(cls, db: Session, page: Dict[str, Any],
                               college_id: Optional[str] = None) -> None:
        """Upsert a live-fetched official page into website_snapshots using the
        same shape as AitWebsiteCrawler.synchronize_website(): hash-based
        change detection, last_crawled_at refresh, and 100k content cap.
        The snapshot is stamped with the ACTIVE tenant (§18) so it can never
        leak into another college's retrieval. Persistence failures must never
        break the answer for the current question, so errors are swallowed
        and logged."""
        try:
            from datetime import datetime, timezone
            import hashlib as _hashlib
            from backend.app.models.knowledge import WebsiteSnapshot

            content = (page.get("content") or "")[:100000]
            if not content:
                return
            content_hash = _hashlib.sha256(content.encode("utf-8")).hexdigest()
            now = datetime.now(timezone.utc)
            existing = db.query(WebsiteSnapshot).filter(
                WebsiteSnapshot.url == page["url"]
            ).first()
            if not existing:
                db.add(WebsiteSnapshot(
                    url=page["url"],
                    college_id=college_id,
                    title=page.get("title") or page["url"],
                    content_hash=content_hash,
                    text_content=content,
                    status_code=page.get("status_code") or 200,
                    last_crawled_at=now,
                ))
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
                "Live-fetch snapshot caching failed for %s", page.get("url"),
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
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Master Chat Orchestration Pipeline conforming to Sections 2-15.
        Processes user query through Language Detection -> Query Normalization ->
        Intent Detection -> Entity Extraction -> Context Follow-up Resolution ->
        Intent-Aware Source Routing -> Grounded Retrieval -> Natural Answer Generation.
        """
        # 0. Prompt Injection Defense & Untrusted Content Sanitization
        from backend.app.security.prompt_guard import prompt_guard
        is_safe, sanitized_msg = prompt_guard.inspect_user_input(user_message_text)
        if not is_safe:
            user_message_text = sanitized_msg

        # 1. Fetch conversation history for coreference and follow-up context
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        recent_msgs = []
        if conv:
            recent_db_msgs = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).all()
            recent_msgs = [
                {"sender": m.sender, "content": m.content}
                for m in recent_db_msgs[-8:]
            ]


        # 2. Context Follow-up & Coreference Resolution (Section 8)
        context_res = context_manager.resolve_context(user_message_text, recent_msgs)
        resolved_query = context_res["resolved_query"]

        # 3. Multilingual Language Detection (EN, GU, HI, Gujlish, Hinglish)
        lang_info = language_engine.detect_language(resolved_query)
        detected_lang = lang_info.get("language", "en")

        # 4. Intent Classification (Section 4)
        intent_info = intent_classifier.classify_intent(resolved_query)
        if intent_info["intent"] == "UNKNOWN" and context_res.get("inferred_intent"):
            intent_info["intent"] = context_res["inferred_intent"]
            intent_info["confidence"] = 0.85

        # 5. Academic Entity & Topic Extraction
        entities = entity_extractor.extract_entities(resolved_query)
        if context_res.get("inferred_topic") and context_res["inferred_topic"] not in entities["topics"]:
            entities["topics"].append(context_res["inferred_topic"])

        # 6. Query Rewriting & Normalization (Section 10)
        rewritten = query_rewriter.rewrite_query(resolved_query, detected_lang)
        search_query = rewritten["normalized_query"]

        # 6.5 Active tenant identity (§15): every label, citation and prompt is
        # derived from the PERSISTED conversation college — never hard-coded.
        college_name = None
        if college_id:
            from backend.app.models.college import College as _College
            _c = db.query(_College).filter(_College.id == college_id).first()
            college_name = _c.name if _c else None

        # 7. Source Router (Section 11)
        has_user_files = bool(attachments)
        route = source_router.route_query(search_query, intent_info, entities, has_user_files=has_user_files, college_id=college_id)

        # 8. Retrieval & Response Formulation
        # Tenant-aware system prompt (§15/§67): the ACTIVE college is the
        # only institutional authority named in the prompt.
        system_prompt = build_system_prompt(college_name or "the selected college")
        retrieved_images = []
        retrieved_entities = []
        retrieved_chunks = []
        citations = []
        table_data = None
        text_content = ""
        grounding_status = "verified"
        provider_failure_message = None

        # --- PATH A: GREETING & CASUAL CONVERSATION (Section 5) ---
        # Tenant-aware: the greeting names the ACTIVE college only (never a
        # hard-coded AIT welcome for a generic/multi-college platform).
        if route == "greeting":
            if any(w in resolved_query.lower() for w in ["bye", "goodbye", "see you"]):
                text_content = (
                    f"Goodbye! Feel free to return anytime if you have more questions about {college_name}. "
                    "Best of luck with your studies!"
                    if college_name else
                    "Goodbye! Feel free to return anytime if you have more questions. Best of luck with your studies!"
                )
            elif any(w in resolved_query.lower() for w in ["thank", "thanks"]):
                text_content = (
                    f"You're very welcome! If you need details on {college_name} admissions, fees, placements, or courses, I'm always here to help. 👋"
                    if college_name else
                    "You're very welcome! If you need details on courses, fees, admissions, or placements, I'm always here to help. 👋"
                )
            else:
                text_content = (
                    f"Hello! 👋 Welcome to the {college_name} AI Assistant. "
                    "How can I help you today with admissions, courses, fees, placements, faculty, or campus facilities?"
                    if college_name else
                    "Hello! 👋 Welcome to the AI FAQ College Chat Bot. "
                    "How can I help you today with admissions, courses, fees, placements, faculty, or campus facilities?"
                )
            grounding_status = "conversational"

        # --- PATH B: VISUAL MEDIA REQUEST (P0 Verified College Images) ---
        # Tenant-scoped: images are filtered to the ACTIVE college (§15).
        elif route == "ait_visual":
            retrieved_images = image_retrieval_engine.match_visual_query(db, search_query, college_id=college_id)
            if retrieved_images:
                text_content = "Here are verified official photos matching your request:"
            else:
                # If specific photo missing, retrieve general campus imagery
                retrieved_images = image_retrieval_engine.match_visual_query(db, "campus", college_id=college_id)
                if retrieved_images:
                    text_content = "Here are official photographs of the campus and facilities:"
                else:
                    text_content = "I searched the official media repository, but no verified official photo is currently published for that specific facility."

        # --- PATH C: AIT INSTITUTIONAL FACTS (Sections 7, 17) ---
        elif route == "ait_institutional":
            # 1. Primary: use intent-specific verified DB retrieval.
            query_lower = search_query.lower()
            is_catalog_query = intent_info.get("intent") == "COURSES" and any(
                term in query_lower for term in ["catalog", "courses", "programs", "program list", "academic catalog"]
            )
            is_committee_query = any(term in query_lower for term in [
                "committee", "council", "squad", "iqac", "grievance", "chairman", "chairperson"
            ])
            is_placement_query = any(term in query_lower for term in [
                "placement", "placements", "highest package", "average package",
                "placement rate", "recruiter", "recruiters", "training and placement",
                "placement cell", "companies visiting"
            ]) or intent_info.get("intent") == "PLACEMENT"
            # §SPEC: source priority = OFFICIAL WEBSITE -> DATABASE -> GEMINI.
            # For AIT (the legacy tenant) DB-first routing is kept for backward
            # compatibility; every other tenant (e.g. RCTI) MUST consult its
            # official website snapshots first.
            is_ait = college_id in (None, _ait_tenant_id(db))
            if is_ait:
                if is_catalog_query:
                    retrieved_entities = knowledge_db.get_by_category(db, "program", college_id=college_id)
                else:
                    retrieved_entities = knowledge_db.query_entities(db, search_query, college_id=college_id)
            else:
                website_snaps = knowledge_db.query_website_snapshots(db, search_query, college_id=college_id)
                if website_snaps:
                    # Official website answered — database is NOT consulted so
                    # it can never override the website for this question.
                    retrieved_entities = []
                else:
                    retrieved_entities = knowledge_db.query_entities(db, search_query, college_id=college_id)
            if is_committee_query:
                # Do not let generic facility/faculty matches satisfy a committee query.
                # A future verified DB committee record remains eligible by its own content.
                retrieved_entities = [e for e in retrieved_entities if any(
                    term in f"{e.get('name', '')} {e.get('details', '')}".lower()
                    for term in ["committee", "council", "squad", "iqac", "grievance", "cell"]
                )]

            # 2. Entity fallback: Search by program
            if not retrieved_entities and entities.get("programs"):
                fallback_entities = []
                for prog in entities["programs"]:
                    fallback_entities.extend(knowledge_db.query_entities(db, prog, college_id=college_id))
                # Re-validate the academic-year constraint against the ORIGINAL
                # query. The program-name-only re-query drops the year/fee
                # context, so query_entities' year guard never fires and it
                # would return an undated fee entity as if it answered a
                # year-specific question.
                requested_years_fb = re.findall(r"20\d{2}\s*[-/]\s*\d{2,4}", search_query.lower())
                is_fee_query_fb = any(
                    w in query_lower for w in ["fee", "fees", "tuition", "cost", "charge"]
                )
                if requested_years_fb and is_fee_query_fb:
                    fallback_entities = [
                        e for e in fallback_entities
                        if any(
                            (e.get("academic_year") and year.replace(" ", "") in str(e.get("academic_year")).replace(" ", ""))
                            or (year.replace(" ", "") in str(e.get("details", {})).lower())
                            for year in requested_years_fb
                        )
                    ]
                retrieved_entities = fallback_entities

            # 3. Topic fallback: Search by intent or detected topic
            if not retrieved_entities:
                current_intent = intent_info.get("intent")
                if current_intent == "FEES" or "FEES" in entities.get("topics", []):
                    retrieved_entities = knowledge_db.query_entities(db, "fees", college_id=college_id)
                elif current_intent in ["PLACEMENT", "placement_info"] or "PLACEMENT" in entities.get("topics", []):
                    retrieved_entities = knowledge_db.query_entities(db, "placement", college_id=college_id)
                elif current_intent in ["FACULTY", "faculty_lookup"] or "FACULTY" in entities.get("topics", []):
                    retrieved_entities = knowledge_db.query_entities(db, "faculty", college_id=college_id)
                elif current_intent in ["LIBRARY", "LAB", "CAMPUS", "FACILITIES"]:
                    target_facility = current_intent.lower()
                    retrieved_entities = knowledge_db.query_entities(db, target_facility, college_id=college_id)
                elif current_intent in ["ADMISSION", "ADMISSION_DATES", "ELIGIBILITY"]:
                    retrieved_entities = knowledge_db.query_entities(db, "contact", college_id=college_id)

            # §SPEC (location/address): for LOCATION/CONTACT questions always
            # merge THIS tenant's verified contact/location records (filtered by
            # conversation.college_id), even when an overview entity already
            # matched. Never touches another college's records.
            if intent_info.get("intent") in ("LOCATION", "CONTACT"):
                contact_hits = knowledge_db.query_entities(
                    db, "location address contact", college_id=college_id
                )
                seen_names = {e.get("name") for e in retrieved_entities}
                retrieved_entities = retrieved_entities + [
                    e for e in contact_hits if e.get("name") not in seen_names
                ][:5]

            # 4. Search the official site only when the verified DB has no usable hit.
            # This preserves DB-first routing and avoids an official page overriding trusted DB data.
            # EXCEPTION: For committee queries, always search website since DB lacks committee data
            # Non-AIT tenants already resolved website_snaps above (website-first).
            if not is_ait:
                pass  # website-first already applied for this tenant
            elif is_committee_query:
                website_snaps = knowledge_db.query_website_snapshots(db, search_query, college_id=college_id)
            else:
                website_snaps = [] if retrieved_entities else knowledge_db.query_website_snapshots(db, search_query, college_id=college_id)
            # A current sync may be absent; discover and fetch the best official page on a website miss.
            # Live SPA re-fetch is AIT-specific (aitindia.in bundle crawler); other
            # tenants rely on their own crawled snapshots (§18).
            if (not retrieved_entities and not website_snaps and not is_committee_query
                    and college_id in (None, _ait_tenant_id(db))):
                from backend.app.knowledge.crawler import website_crawler
                page = await website_crawler.fetch_relevant_page(search_query)
                page_content = (page.get("content") or "").lower() if page else ""
                requested_programs = [
                    program.split("(", 1)[0].strip().lower()
                    for program in entities.get("programs", [])
                ]
                program_scope_matches = not requested_programs or any(
                    program in page_content for program in requested_programs
                )
                if (page and page.get("content") and
                        page.get("extraction_status") == "EXTRACTED" and
                        program_scope_matches):
                    website_snaps = [{"url": page["url"], "title": page["title"],
                                      "content": page["content"], "text_content": page["content"],
                                      "source_domain": "aitindia.in",
                                      "authority": f"Official {college_name or 'Ahmedabad Institute of Technology'} Website"}]
                    # Cache the live-fetched page as a tenant-stamped
                    # WebsiteSnapshot so future similar queries resolve via
                    # query_website_snapshots() instead of repeating the full
                    # live discovery crawl.
                    self._persist_live_snapshot(db, page, college_id=college_id)

            # 5. Search approved institutional RAG, but do not let lower-priority
            # document evidence override a verified DB or official-site hit.
            # CRITICAL: Pass college_id to ensure tenant-isolated retrieval.
            retrieved_chunks = rag_engine.search(db, search_query, college_id=college_id, user_id=None, top_k=3)
            if retrieved_entities or (website_snaps and not is_committee_query):
                retrieved_chunks = []

            # P1-1/P1-2 FIX: Aggregate all verified institutional evidence sources
            # For committee queries, prioritize website snapshots over DB entities
            all_evidence = []

            # Add website snapshots first for committee queries (higher priority)
            if is_committee_query:
                # Rank website snapshots by section relevance
                ranked_snapshots = []
                query_keywords = set(search_query.lower().split())

                for s in website_snaps:
                    section = (s.get("section_title") or "").lower()
                    content = (s.get("content") or "").lower()
                    score = 0

                    # Exact section match gets highest score
                    for keyword in query_keywords:
                        if len(keyword) > 2 and keyword in section:
                            score += 10
                        if len(keyword) > 2 and keyword in content:
                            score += 2

                    # Penalize generic content
                    if len(content) < 50:
                        score -= 5

                    ranked_snapshots.append((score, s))

                # Sort by relevance score
                ranked_snapshots.sort(key=lambda x: x[0], reverse=True)

                for score, s in ranked_snapshots:
                    all_evidence.append({
                        "name": s.get("section_title") or s.get("title") or f"{college_name or 'College'} Official Website",
                        "details": s.get("content") or "",
                        "source_type": "website_snapshot",
                        "source_url": s.get("url", ""),
                        "section": s.get("section_title")
                    })
                    citations.append({
                        "title": s.get("section_title") or s.get("title", "Official Website"),
                        "source_url": s.get("url", ""),
                        "authority": s.get("authority") or f"Official {college_name or 'College'} Website",
                        "section": s.get("section_title"),
                        "source_type": "OFFICIAL_COLLEGE_WEBSITE"
                    })

            # Add DB entities (lower priority for committee queries)
            for e in retrieved_entities:
                # §44/§79: provenance must reflect the record's own authority.
                # DEMO (non-official) test records carry a DEMO authority label
                # and are never presented as official website information.
                _auth = e.get("authority") or f"{college_name or 'College'} Verified Database"
                if "demo" in _auth.lower():
                    _auth = f"{_auth} — NOT official information (development test data)"
                all_evidence.append({
                    "name": e.get("name"),
                    "details": e.get("details"),
                    "source_type": "entity_db",
                    "source_url": e.get("source_url", "")
                })
                citations.append({
                    "title": e.get("name"),
                    "source_url": e.get("source_url", ""),
                    "authority": _auth,
                    "source_type": "DEMO_TEST_DATA" if "demo" in _auth.lower() else "DATABASE"
                })

            # Add website snapshots for non-committee queries (normal priority)
            if not is_committee_query:
                for s in website_snaps:
                    all_evidence.append({
                        "name": s.get("section_title") or s.get("title") or f"{college_name or 'College'} Official Website",
                        "details": s.get("content") or "",
                        "source_type": "website_snapshot",
                        "source_url": s.get("url", ""),
                        "section": s.get("section_title")
                    })
                    citations.append({
                        "title": s.get("section_title") or s.get("title", "Official Website"),
                        "source_url": s.get("url", ""),
                        "authority": s.get("authority") or f"Official {college_name or 'College'} Website",
                        "section": s.get("section_title"),
                        "source_type": "OFFICIAL_COLLEGE_WEBSITE"
                    })

            for c in retrieved_chunks:
                all_evidence.append({
                    "name": c.get("title", "Official Institutional Document"),
                    "details": c.get("content", ""),
                    "source_type": "document_chunk",
                    "source_url": c.get("source_url", "")
                })
                citations.append({
                    "title": c.get("title", "Institutional Document"),
                    "source_url": c.get("source_url", ""),
                    "authority": f"{college_name or 'College'} Official Document"
                })

            # 6. Generate grounded answer
            if all_evidence:
                text_content = await ai_router.generate_response(
                    prompt=resolved_query,
                    system_instruction=system_prompt,
                    evidence=all_evidence,
                    context_history=recent_msgs,
                    db=db,
                    user_id=user_id,
                    conversation_id=conversation_id
                )
                grounding_res = grounding_validator.validate_answer(
                    query=user_message_text,
                    route=route,
                    retrieved_evidence=all_evidence,
                    candidate_answer=text_content
                )
                text_content = grounding_res["answer"]
                grounding_status = grounding_res["grounding_status"]
            elif is_placement_query:
                text_content = (
                    f"I couldn't verify current placement information from the available official {college_name or 'college'} sources."
                )
                grounding_status = "unverified"
            else:
                # 7. Gemini fallback (Section 12)
                text_content = await ai_router.generate_response(
                    prompt=resolved_query,
                    system_instruction=system_prompt,
                    evidence=None,
                    context_history=recent_msgs,
                    db=db,
                    user_id=user_id,
                    conversation_id=conversation_id
                )
                grounding_res = grounding_validator.validate_answer(
                    query=user_message_text,
                    route=route,
                    retrieved_evidence=[],
                    candidate_answer=text_content
                )
                text_content = grounding_res["answer"]
                grounding_status = grounding_res["grounding_status"]

                # Log knowledge gap for admin dashboard review — deduplicated
                # grouping per college so identical questions increment
                # occurrence_count instead of creating new rows (§8/§9/§42).
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

        # --- PATH D: PRIVATE USER DOCUMENT SEARCH ---
        elif route == "user_file_specific" and user_id:
            retrieved_chunks = rag_engine.search(db, search_query, user_id=user_id, top_k=4)
            if retrieved_chunks:
                context_str = "\n\n".join([c["content"] for c in retrieved_chunks])
                text_content = f"Based on your uploaded document:\n\n{context_str}"
            else:
                text_content = "I could not find matching information in your uploaded documents."
            grounding_status = "user_context"

        # --- PATH E: GENERAL EDUCATIONAL / CONVERSATIONAL (Section 6) ---
        else:
            text_content = await ai_router.generate_response(
                prompt=resolved_query,
                system_instruction=system_prompt,
                evidence=None,
                context_history=recent_msgs,
                db=db,
                user_id=user_id,
                conversation_id=conversation_id
            )
            grounding_status = "general_ai"

        # 9. Format response blocks and citations (P1-15: Dynamic Provenance)
        # Provenance is derived from the ACTIVE college only (§15): an RCTI
        # answer never cites an AIT domain/authority, and vice versa.
        if route == "ait_institutional":
            if grounding_status == "verified":
                _src_url = citations[0].get("source_url") if citations else None
                _src_parts = (_src_url or "").split("/")
                _src_domain = _src_parts[2] if len(_src_parts) > 2 and _src_parts[2] else None
                provenance = {
                    "authority": citations[0].get("authority") if citations else (college_name or "Verified College Database"),
                    "source_type": citations[0].get("source_type", "DATABASE") if citations else "DATABASE",
                    "source_domain": _src_domain,
                    "source_url": citations[0].get("source_url") if citations else None,
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "section": citations[0].get("section") if citations else None,
                }
            else:
                provenance = {
                    "authority": "General AI Academic Knowledge — ⚠ Gemini-generated, not verified by the college",
                    "source_domain": None,
                    "verified_at": "Unverified - Fallback Response"
                }
        elif route == "ait_visual":
            provenance = {
                "authority": college_name or "Official College Media Repository",
                "source_domain": None,
                "verified_at": "Official Media Repository"
            } if retrieved_images else None
        else:
            provenance = None

        suggestions = []
        if route == "ait_institutional":
            suggestions = ["What are the eligibility criteria?", "Tell me about placements", "Show campus photos"]
        elif route == "ait_visual":
            suggestions = ["Show computer lab", "Show library", "What courses are offered?"]
        elif route == "greeting":
            suggestions = ["What are the fees?", "Tell me about placements", "Show campus photos"]

        blocks = response_builder.build_blocks(
            text_content=text_content,
            images=retrieved_images,
            table_data=table_data,
            citations=citations,
            provenance=provenance,
            suggestions=suggestions
        )

        # 10. Never persist or stream an empty answer: if every provider failed,
        # emit a user-safe message instead of a blank bubble stuck on Thinking.
        if not (text_content or "").strip():
            text_content = (
                "I'm sorry — I couldn't reach any AI provider right now. "
                "Please try again in a moment."
            )
            grounding_status = "unverified"

        # 9.5 Unanswered-question detection (§7): any institutional answer that
        # is not reliably grounded creates/updates a Knowledge Gap for review.
        if route == "ait_institutional" and grounding_status not in ("verified",):
            from backend.app.knowledge.gaps import record_gap, is_unanswered
            if is_unanswered(text_content, grounding_status):
                record_gap(
                    db,
                    college_id=college_id,
                    question=user_message_text,
                    sample_answer=text_content,
                    reason="low_confidence" if grounding_status != "unverified" else "no_verified_source",
                    conversation_id=conversation_id,
                    detected_intent=intent_info.get("intent"),
                )

        # 10. Persist message to database
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
            provenance=provenance or {}
        )
        db.add(assistant_msg)
        db.commit()

        return {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "text_content": text_content,
            "blocks": blocks,
            "grounding_status": assistant_msg.grounding_status,
            "language": detected_lang
        }

chat_orchestrator = ChatOrchestrator()
