import re
from typing import Dict, Any, List, Optional

class GroundingValidator:
    HELPFUL_CLARIFICATION_MESSAGE = (
        "I couldn't verify that specific information from the connected "
        "official college sources. Could you please clarify which program, "
        "department, or topic you are asking about?"
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

        # 3. Institutional queries require verified evidence (P1-3 FIX)
        if route in ["ait_institutional", "ait_visual"]:
            # §SPEC (verified-label bug): the badge must reflect what the answer
            # ACTUALLY is, not merely that some evidence was retrieved. If the
            # candidate answer is an explicit "couldn't verify" refusal, it is
            # NOT a verified college fact even when weak evidence exists —
            # otherwise the UI shows "Verified College Fact" above a refusal.
            def _is_refusal(answer):
                if not answer:
                    return False
                a = answer.lower()
                return (
                    "couldn't verify" in a
                    or "could not verify" in a
                    or "no verified" in a
                    or "i searched the official media repository" in a
                )

            if not retrieved_evidence or _is_refusal(candidate_answer):
                return {
                    "grounding_status": "unverified",
                    "is_grounded": False,
                    "confidence": 0.0,
                    "evidence_count": 0,
                    "answer": candidate_answer if candidate_answer else cls.HELPFUL_CLARIFICATION_MESSAGE
                }

            # Guard against generic page-title answers for factual questions
            if candidate_answer and retrieved_evidence:
                # Check if answer looks like it's just returning source titles instead of factual content
                answer_lower = candidate_answer.lower()

                # Patterns that indicate the answer is just metadata, not factual content
                generic_patterns = [
                    r'^\s*(ahmedabad institute of technology\s*—?\s*)+\s*$',
                    r'^\s*(committees?\s*&?\s*governing\s+councils?\s*)+\s*$',
                    r'^\s*(ait\s*group\s*)+\s*$',
                    r'^\s*(governing\s+council\s*)+\s*$',
                ]

                # Check if answer matches generic patterns and is very short
                is_generic_only = any(re.match(pattern, answer_lower) for pattern in generic_patterns)
                is_very_short = len(candidate_answer.strip()) < 100

                # If answer is generic and short, but we have good evidence, regenerate from evidence
                if is_generic_only and is_very_short:
                    # Try to extract a better answer from the evidence
                    for evidence in retrieved_evidence:
                        details = evidence.get("details", "")
                        section = evidence.get("section", "")

                        # If evidence has actual factual content, use it directly
                        if details and len(str(details)) > 50:
                            # Simple fallback: return the evidence content directly
                            improved_answer = f"Based on official college records:\n\n{section}\n{details}"
                            return {
                                "grounding_status": "verified",
                                "is_grounded": True,
                                "confidence": 0.98,
                                "evidence_count": len(retrieved_evidence),
                                "answer": improved_answer
                            }

            return {
                "grounding_status": "verified",
                "is_grounded": True,
                "confidence": 0.98,
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
