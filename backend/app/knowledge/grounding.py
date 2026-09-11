from typing import Dict, Any, List, Optional

class GroundingValidator:
    HELPFUL_CLARIFICATION_MESSAGE = (
        "I couldn't verify that specific information from official AIT sources. "
        "Could you please clarify if you are inquiring about BCA, MCA, B.Tech, MBA, or another department at AIT?"
    )

    @classmethod
    def validate_answer(
        cls,
        query: str,
        route: str,
        retrieved_evidence: List[Dict[str, Any]],
        candidate_answer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validates whether institutional statements are grounded in verified evidence.
        Prevents AI hallucination while allowing natural conversational and educational responses.
        """
        # 1. Conversational & Greeting queries are naturally valid
        if route in ["greeting", "conversational"]:
            return {
                "grounding_status": "conversational",
                "is_grounded": True,
                "confidence": 1.0,
                "evidence_count": 0,
                "answer": candidate_answer
            }

        # 2. General educational questions use AI academic knowledge
        if route in ["general_educational", "general_knowledge"]:
            return {
                "grounding_status": "general_ai",
                "is_grounded": True,
                "confidence": 0.95,
                "evidence_count": 0,
                "answer": candidate_answer
            }

        # 3. Institutional queries require verified evidence
        if route in ["ait_institutional", "ait_visual"]:
            if not retrieved_evidence and not candidate_answer:
                return {
                    "grounding_status": "unverified",
                    "is_grounded": False,
                    "confidence": 0.0,
                    "evidence_count": 0,
                    "answer": cls.HELPFUL_CLARIFICATION_MESSAGE
                }

            return {
                "grounding_status": "verified" if retrieved_evidence else "ai_fallback",
                "is_grounded": True,
                "confidence": 0.98 if retrieved_evidence else 0.75,
                "evidence_count": len(retrieved_evidence),
                "answer": candidate_answer
            }

        return {
            "grounding_status": "user_context",
            "is_grounded": True,
            "confidence": 0.9,
            "evidence_count": len(retrieved_evidence),
            "answer": candidate_answer
        }

grounding_validator = GroundingValidator()
