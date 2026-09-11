import uuid
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
from backend.app.ai.prompts import AIT_SYSTEM_PROMPT
from backend.app.chat.response_builder import response_builder
from backend.app.models.conversation import Message, Conversation
from backend.app.models.knowledge import KnowledgeGap

class ChatOrchestrator:
    @classmethod
    async def process_chat(
        cls,
        db: Session,
        conversation_id: str,
        user_message_text: str,
        user_id: Optional[str] = None,
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

        # 7. Source Router (Section 11)
        has_user_files = bool(attachments)
        route = source_router.route_query(search_query, intent_info, entities, has_user_files=has_user_files)

        # 8. Retrieval & Response Formulation
        retrieved_images = []
        retrieved_entities = []
        retrieved_chunks = []
        citations = []
        table_data = None
        grounding_status = "verified"

        # --- PATH A: GREETING & CASUAL CONVERSATION (Section 5) ---
        if route == "greeting":
            if any(w in resolved_query.lower() for w in ["bye", "goodbye", "see you"]):
                text_content = "Goodbye! Feel free to return anytime if you have more questions about Ahmedabad Institute of Technology (AIT). Best of luck with your studies!"
            elif any(w in resolved_query.lower() for w in ["thank", "thanks"]):
                text_content = "You're very welcome! If you need details on AIT admissions, fees, placements, or courses, I'm always here to help. 👋"
            else:
                text_content = (
                    "Hello! 👋 Welcome to Ahmedabad Institute of Technology (AIT) AI Assistant. "
                    "How can I help you today with admissions, courses, fees, placements, faculty, or campus facilities?"
                )
            grounding_status = "conversational"

        # --- PATH B: VISUAL MEDIA REQUEST (P0 Real AIT Images) ---
        elif route == "ait_visual":
            retrieved_images = image_retrieval_engine.match_visual_query(db, search_query)
            if retrieved_images:
                text_content = "Here are verified official photos from Ahmedabad Institute of Technology matching your request:"
            else:
                # If specific photo missing, retrieve general campus imagery
                retrieved_images = image_retrieval_engine.match_visual_query(db, "campus")
                if retrieved_images:
                    text_content = "Here are official photographs of Ahmedabad Institute of Technology campus and facilities:"
                else:
                    text_content = "I searched the official AIT media repository, but no verified official photo is currently published for that specific facility."

        # --- PATH C: AIT INSTITUTIONAL FACTS (Sections 7, 17) ---
        elif route == "ait_institutional":
            # 1. Primary: Search verified DB entities
            retrieved_entities = knowledge_db.query_entities(db, search_query)

            # 2. Entity fallback: Search by program
            if not retrieved_entities and entities.get("programs"):
                for prog in entities["programs"]:
                    retrieved_entities.extend(knowledge_db.query_entities(db, prog))

            # 3. Topic fallback: Search by intent or detected topic
            if not retrieved_entities:
                current_intent = intent_info.get("intent")
                if current_intent == "FEES" or "FEES" in entities.get("topics", []):
                    retrieved_entities = knowledge_db.query_entities(db, "fees")
                elif current_intent in ["PLACEMENT", "placement_info"] or "PLACEMENT" in entities.get("topics", []):
                    retrieved_entities = knowledge_db.query_entities(db, "placement")
                elif current_intent in ["FACULTY", "faculty_lookup"] or "FACULTY" in entities.get("topics", []):
                    retrieved_entities = knowledge_db.query_entities(db, "faculty")
                elif current_intent in ["LIBRARY", "LAB", "CAMPUS", "FACILITIES"]:
                    target_facility = current_intent.lower()
                    retrieved_entities = knowledge_db.query_entities(db, target_facility)
                elif current_intent in ["ADMISSION", "ADMISSION_DATES", "ELIGIBILITY"]:
                    retrieved_entities = knowledge_db.query_entities(db, "contact")

            # 4. Search official crawled website snapshots
            website_snaps = knowledge_db.query_website_snapshots(db, search_query)
            if website_snaps and not retrieved_entities:
                for s in website_snaps:
                    citations.append({
                        "title": s.get("title", "AIT Official Website"),
                        "source_url": s.get("url", "https://www.aitindia.in"),
                        "authority": "Official Crawled AIT Website"
                    })

            # 5. Search approved institutional RAG
            retrieved_chunks = rag_engine.search(db, search_query, user_id=None, top_k=3)

            # 6. Generate grounded answer
            if retrieved_entities or website_snaps or retrieved_chunks:
                # Synthesize grounded answer
                text_content = await ai_router.generate_response(
                    prompt=resolved_query,
                    system_instruction=AIT_SYSTEM_PROMPT,
                    evidence=retrieved_entities,
                    context_history=recent_msgs,
                    db=db,
                    user_id=user_id,
                    conversation_id=conversation_id
                )
                for e in retrieved_entities[:3]:
                    citations.append({
                        "title": e.get("name"),
                        "source_url": e.get("source_url", "https://www.aitindia.in"),
                        "authority": "AIT Verified Database"
                    })
            else:
                # 7. Gemini fallback (Section 12)
                text_content = await ai_router.generate_response(
                    prompt=resolved_query,
                    system_instruction=AIT_SYSTEM_PROMPT,
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

                # Log knowledge gap for admin dashboard review
                gap = KnowledgeGap(
                    user_query=user_message_text,
                    detected_intent=intent_info.get("intent"),
                    missing_entity=str(entities)
                )
                db.add(gap)
                db.commit()

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
                system_instruction=AIT_SYSTEM_PROMPT,
                evidence=None,
                context_history=recent_msgs,
                db=db,
                user_id=user_id,
                conversation_id=conversation_id
            )
            grounding_status = "general_ai"

        # 9. Format response blocks and citations
        provenance = {
            "authority": "Ahmedabad Institute of Technology (aitindia.in)",
            "source_domain": "aitindia.in",
            "verified_at": "Official Verified Dataset"
        } if route in ["ait_institutional", "ait_visual"] else None

        suggestions = []
        if route == "ait_institutional":
            suggestions = ["What are the eligibility criteria?", "Tell me about AIT placements", "Show campus photos"]
        elif route == "ait_visual":
            suggestions = ["Show AIT computer lab", "Show AIT library", "What courses are offered?"]
        elif route == "greeting":
            suggestions = ["What are the BCA fees?", "Tell me about AIT placements", "Show AIT campus photos"]

        blocks = response_builder.build_blocks(
            text_content=text_content,
            images=retrieved_images,
            table_data=table_data,
            citations=citations,
            provenance=provenance,
            suggestions=suggestions
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
