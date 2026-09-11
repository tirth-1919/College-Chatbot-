from typing import Dict, Any

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
        "RESULT", "EVENT", "CONTACT", "LOCATION", "AIT_GENERAL"
    }

    @classmethod
    def route_query(
        cls,
        text: str,
        intent_info: Dict[str, Any],
        entities: Dict[str, Any],
        has_user_files: bool = False
    ) -> str:
        intent = intent_info.get("intent", "").upper()
        text_lower = text.lower()

        # 1. Greetings & Casual Conversation (Section 5: must NOT enter institutional verification)
        if intent in ["GREETING", "GENERAL_CONVERSATION"]:
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

        # 5. AIT Institutional Facts
        has_college_mention = any(k in text_lower for k in [
            "ait", "college", "fees", "fee", "admission", "admissions", "placement",
            "placements", "faculty", "professor", "hod", "principal", "campus", "hostel",
            "gtu", "ahmedabad institute", "canteen", "library", "sports ground"
        ])
        has_entities = (
            len(entities.get("programs", [])) > 0 or
            len(entities.get("facilities", [])) > 0 or
            len(entities.get("faculty", [])) > 0 or
            len(entities.get("topics", [])) > 0
        )

        if intent in cls.INSTITUTIONAL_INTENTS or has_college_mention or has_entities:
            return "ait_institutional"

        # 6. Fallback checks
        if any(term in text_lower for term in ["what is", "how does", "explain", "code for", "algorithm", "tutorial"]):
            return "general_educational"

        return "conversational"

source_router = SourceRouter()
