import re
from typing import List, Dict, Any, Optional

class ContextManager:
    """
    Manages conversational memory, context resolution, and follow-up query expansion.
    Handles Section 8 requirements:
    - Elliptical course shifts ("BCA fees?" -> "what about MCA?" -> "What are MCA fees?")
    - Coreference resolution ("who teaches it?", "where is her office?")
    - Follow-ups ("placement" -> "how it look?" -> "How are AIT placements?")
    """

    COURSE_KEYWORDS = ["bca", "mca", "bba", "mba", "b.tech cse", "btech cse", "cse", "b.tech it", "btech it", "it", "mechanical", "civil", "electrical"]

    @classmethod
    def resolve_context(cls, current_query: str, recent_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Resolves follow-up queries using recent conversational history.
        Returns resolved_query, inferred_intent, and inferred_topic.
        """
        if not recent_messages:
            return {
                "resolved_query": current_query,
                "inferred_intent": None,
                "inferred_topic": None,
                "context_applied": False
            }

        query_clean = current_query.strip()
        query_lower = query_clean.lower()


        # Exclude the current user query if already stored in recent_messages
        history = [m for m in recent_messages if m.get("content", "").strip().lower() != query_lower]
        if not history:
            return {
                "resolved_query": current_query,
                "inferred_intent": None,
                "inferred_topic": None,
                "context_applied": False
            }

        # Extract last user query and last assistant answer from prior turns
        last_user_msg = None
        last_asst_msg = None
        for m in reversed(history):
            if m.get("sender") == "user" and not last_user_msg:
                last_user_msg = m.get("content", "")
            elif m.get("sender") == "assistant" and not last_asst_msg:
                last_asst_msg = m.get("content", "")

        last_context_text = f"{last_user_msg or ''} {last_asst_msg or ''}".lower()

        # An explicit subject/topic in a new question takes precedence over
        # prior conversation context. Context is only for genuine ellipses.
        explicit_topic = re.search(
            r"\b(anti[- ]?ragging|sports|library|internal complaint|canteen|academic|student grievance|iqac|intake|catalog|courses?|programs?|fees?|tuition|faculty|who teaches|dbms)\b",
            query_lower,
        )
        has_explicit_subject = bool(explicit_topic)

        def detect_topic(text: str) -> Optional[str]:
            t = text.lower()
            if any(w in t for w in ["placement", "placements", "package", "recruiter", "tpo", "recruiters"]):
                return "PLACEMENT"
            if any(w in t for w in ["fee", "fees", "tuition", "cost", "charge"]):
                return "FEES"
            if any(w in t for w in ["admission", "apply", "eligibility", "acpc"]):
                return "ADMISSION"
            if any(w in t for w in ["faculty", "prof", "teacher", "who teaches", "hod", "coordinator"]):
                return "FACULTY"
            if any(w in t for w in ["library"]):
                return "LIBRARY"
            if any(w in t for w in ["lab", "computer lab", "laboratory"]):
                return "LAB"
            if any(w in t for w in ["campus", "ground", "sports", "canteen", "cafeteria"]):
                return "CAMPUS"
            if any(w in t for w in ["committee", "council", "squad", "cell", "iqac", "grievance"]):
                return "COMMITTEE"
            return None

        # Prioritize previous user's query intent, then assistant answer content
        last_topic = detect_topic(last_user_msg or "") or detect_topic(last_asst_msg or "")


        # 2. Case A: Elliptical Course Change ("what about MCA?", "and for BBA?", "MCA?", "B.Tech CSE?")
        # If user asks "what about <course>?" or just "<course>?" after discussing fees/admission/placement
        for course in cls.COURSE_KEYWORDS:
            pattern = rf"\b(?:what\s+about|and\s+for|how\s+about|aur|ane)?\s*{re.escape(course)}\s*\??$"
            if re.search(pattern, query_lower):
                if last_topic == "FEES":
                    return {
                        "resolved_query": f"What are the fees for {course.upper()} at AIT?",
                        "inferred_intent": "FEES",
                        "inferred_topic": course.upper(),
                        "context_applied": True
                    }
                elif last_topic == "ADMISSION":
                    return {
                        "resolved_query": f"What is the admission process and eligibility for {course.upper()} at AIT?",
                        "inferred_intent": "ADMISSION",
                        "inferred_topic": course.upper(),
                        "context_applied": True
                    }
                elif last_topic == "PLACEMENT":
                    return {
                        "resolved_query": f"What are the placement statistics for {course.upper()} at AIT?",
                        "inferred_intent": "PLACEMENT",
                        "inferred_topic": course.upper(),
                        "context_applied": True
                    }

        # 3. Case B: Follow-up questions like "how it look?", "how does it look?", "how is it?", "kaisa hai?", "ketlu che?"
        if re.search(r"\b(how\s+(?:does\s+)?it\s+look|how\s+it\s+look|how\s+is\s+it|kaisa\s+hai|kaisa\s+h|ketlu\s+che)\b", query_lower):
            if last_topic == "PLACEMENT":
                return {
                    "resolved_query": "How are the placement opportunities and statistics at AIT?",
                    "inferred_intent": "PLACEMENT",
                    "inferred_topic": "PLACEMENT",
                    "context_applied": True
                }
            elif last_topic in ["CAMPUS", "LIBRARY", "LAB"]:
                return {
                    "resolved_query": f"Show photos of AIT {last_topic.lower()}",
                    "inferred_intent": "IMAGE_REQUEST",
                    "inferred_topic": last_topic,
                    "context_applied": True
                }
            elif last_topic == "FEES":
                return {
                    "resolved_query": "What are the fee structure and payment details at AIT?",
                    "inferred_intent": "FEES",
                    "inferred_topic": "FEES",
                    "context_applied": True
                }

        # 4. Case C: Committee follow-up context ("list all members", "who is the chairman", etc.)
        if last_topic == "COMMITTEE" and not has_explicit_subject:
            # Extract committee name from previous context only for an
            # elliptical follow-up such as "list all members".
            committee_match = re.search(r"\b(ANTI-RAGGING SQUAD|SPORTS COMMITTEE|LIBRARY COMMITTEE|INTERNAL COMPLAINT COMMITTEE|Canteen Committee|Academic Council|Student Grievance|IQAC)\b", last_context_text, re.IGNORECASE)
            if committee_match:
                committee_name = committee_match.group(1)

                # Follow-up patterns for committees
                if re.search(r"\b(list\s+all\s+members|members|who\s+are\s+the\s+members)\b", query_lower):
                    return {
                        "resolved_query": f"List all members of the {committee_name} at AIT",
                        "inferred_intent": "AIT_COMMITTEE",
                        "inferred_topic": committee_name,
                        "context_applied": True
                    }
                elif re.search(r"\b(who\s+is\s+the\s+chairman|chairman|who\s+is\s+the\s+head|head)\b", query_lower):
                    return {
                        "resolved_query": f"Who is the Chairman of the {committee_name} at AIT",
                        "inferred_intent": "AIT_COMMITTEE",
                        "inferred_topic": committee_name,
                        "context_applied": True
                    }
                elif re.search(r"\b(tell\s+me\s+about|about|details)\b", query_lower):
                    return {
                        "resolved_query": f"Tell me about the {committee_name} at AIT",
                        "inferred_intent": "AIT_COMMITTEE",
                        "inferred_topic": committee_name,
                        "context_applied": True
                    }

        # 5. Case D: Pronoun coreference ("who teaches it?", "where is her office?", "tell me about it")
        resolved = query_clean
        pronoun_match = re.search(r"\b(her|his|its|their|she|he|it)\b", query_lower)
        if pronoun_match and not has_explicit_subject:
            pronoun = pronoun_match.group(1)

            # Check if pronoun refers to a faculty member
            for msg in reversed(recent_messages):
                content = msg.get("content", "")
                prof_match = re.search(r"\b(Prof\.|Professor|Dr\.|Mr\.|Mrs\.|Ms\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", content)
                if prof_match:
                    faculty_name = f"{prof_match.group(1)} {prof_match.group(2)}"
                    if pronoun in ["her", "his"]:
                        resolved = re.sub(rf"\b{pronoun}\b", f"{faculty_name}'s", resolved, flags=re.IGNORECASE)
                    else:
                        resolved = re.sub(rf"\b{pronoun}\b", faculty_name, resolved, flags=re.IGNORECASE)
                    return {
                        "resolved_query": resolved,
                        "inferred_intent": "FACULTY",
                        "inferred_topic": faculty_name,
                        "context_applied": True
                    }

            # Check if pronoun refers to a subject or facility
            for ent in ["DBMS", "Python", "DSA", "Java", "Computer Networks", "Library", "Computer Lab", "Canteen", "Sports Ground"]:
                if ent.lower() in last_context_text:
                    if pronoun in ["it", "its"]:
                        resolved = re.sub(rf"\b{pronoun}\b", ent, resolved, flags=re.IGNORECASE)
                        return {
                            "resolved_query": resolved,
                            "inferred_intent": "SUBJECT" if ent in ["DBMS", "Python", "DSA", "Java", "Computer Networks"] else "FACILITIES",
                            "inferred_topic": ent,
                            "context_applied": True
                        }

        return {
            "resolved_query": resolved,
            "inferred_intent": None,
            "inferred_topic": None,
            "context_applied": resolved != current_query
        }

    @classmethod
    def resolve_coreference(cls, current_query: str, recent_messages: List[Dict[str, Any]]) -> str:
        """Backward-compatible helper."""
        res = cls.resolve_context(current_query, recent_messages)
        return res["resolved_query"]

context_manager = ContextManager()
