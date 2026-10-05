import re
from typing import Dict, Any, List, Optional
from backend.app.knowledge.confidence import verify_claims


def ResponseBuilderProgramFamily(value):
    """
    Map a program string onto a coarse program family.

    Shared by evidence normalization (TASK 5) and grounding validation
    (TASK 7) so BCA -> BBA / BCA -> Data Science mismatches are detected
    identically at both boundaries.
    """
    text = str(value or "").lower().replace(".", "")
    if re.search(r"\bbtech\b|bachelor of technology|computer science engineering|information technology", text):
        return "btech"
    if re.search(r"\bbca\b|bachelor of computer applications", text):
        return "bca"
    if re.search(r"\bbba\b|bachelor of business administration", text):
        return "bba"
    if re.search(r"\bmca\b|master of computer applications", text):
        return "mca"
    if re.search(r"\bmba\b|master of business administration", text):
        return "mba"
    # A named specialisation (Data Science, AI, ...) is its own family so a
    # BCA request can never be answered with a Data Science record.
    if re.search(r"\bdata\s+science\b", text):
        return "data_science"
    if re.search(r"\bartificial\s+intelligence\b|\bai\b", text):
        return "artificial_intelligence"
    return None

class GroundingValidator:
    HELPFUL_CLARIFICATION_MESSAGE = (
        "I couldn't verify that specific information from the connected "
        "official college sources. Could you please clarify which program, "
        "department, or topic you are asking about?"
    )

    @classmethod
    def clarification_needed(cls, query_spec, retrieved_evidence=None) -> bool:
        """
        P0.1 (TASK 10): clarification decisions are driven by the QuerySpec
        and the AVAILABLE EVIDENCE -- never by re-reading the question.

        Rules:
          * "What hostel facilities are available at AIT?"
            -> spec.program is None and evidence is category-generic
            -> NO program clarification.
          * "What is the BCA fee?"
            -> spec.program == "BCA"
            -> NO program clarification.
          * "What is the fee?"
            -> spec.program is None AND the retrieved evidence spans MORE
            THAN ONE program family, so program disambiguation is genuinely
            required
            -> clarification IS allowed.
        """
        if query_spec is None:
            return True
        # An explicit program in the spec already disambiguates.
        if getattr(query_spec, "program", None):
            return False
        evidence = retrieved_evidence or []
        if not evidence:
            return False
        families = set()
        for item in evidence:
            program = item.get("program") or item.get("course")
            if not program:
                continue
            family = ResponseBuilderProgramFamily(program)
            if family:
                families.add(family)
        # A single program family in the evidence needs no clarification;
        # several competing families genuinely require disambiguation.
        return len(families) > 1

    @classmethod
    def validate_answer(
        cls,
        query: str = "",
        route: str = "",
        retrieved_evidence: List[Dict[str, Any]] = None,
        query_spec=None,
        candidate_answer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        P0.1: grounding validation receives
            QuerySpec + normalized evidence + candidate answer.

        Query intent is NEVER reconstructed from the raw query text.  The
        `query` argument is used only for optional phrasing / term-overlap
        diagnostics, never to re-derive program, category or year.

        Structured evidence is still flattened by verify_claims before claim
        validation, so structured records such as
            {"program": "BCA", "value": "₹32,000", "academic_year": "2026-27"}
        support "The BCA fee is ₹32,000 for 2026-27." and REJECT
        "The BBA fee is ₹32,000." (different program family).
        """
        retrieved_evidence = retrieved_evidence or []
        if query_spec is not None:
            # Route and query text are DERIVED FROM THE SPEC, not the text.
            query = query or query_spec.retrieval_text
            # A spec carrying a resolved institutional topic is an
            # institutional query even when `route` has not been stamped yet.
            if not route:
                route = getattr(query_spec, "route", None) or ""
                if not route:
                    route = (
                        "institutional"
                        if retrieved_evidence
                        or getattr(query_spec, "category", None)
                        or getattr(query_spec, "topic", None)
                        or getattr(query_spec, "program", None)
                        else "general_educational"
                    )
        elif route == "":
            route = "institutional" if retrieved_evidence else "general_educational"

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
        if route in ["institutional", "ait_institutional", "visual"]:
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

            # A verified badge requires claim-level support, not merely the
            # presence of a tenant-owned document.  Refuse unsupported model
            # additions and let the caller expose an unverified/no-information
            # result instead of presenting unrelated evidence as fact.
            claim_check = verify_claims(candidate_answer or "", retrieved_evidence)

            # P0.1: program-identity check against the QuerySpec, not the text.
            # "The BBA fee is ₹32,000." must FAIL when the spec says BCA.
            if query_spec is not None and getattr(query_spec, "program", None):
                expected_family = ResponseBuilderProgramFamily(
                    getattr(query_spec, "program")
                )
                if expected_family:
                    # (a) The CANDIDATE ANSWER itself must not name a
                    # different program than the spec. This is the exact
                    # P0.1 acceptance example: BCA evidence grounds
                    # "The BCA fee is ..." but NOT "The BBA fee is ...".
                    answer_programs = re.findall(
                        r"\b(?:b\.?tech|bca|bba|mba|mca|data\s+science|"
                        r"artificial\s+intelligence)\b",
                        (candidate_answer or "").lower(),
                    )
                    if answer_programs:
                        answer_families = {
                            ResponseBuilderProgramFamily(p)
                            for p in answer_programs
                        }
                        answer_families.discard(None)
                        if answer_families and expected_family not in answer_families:
                            return {
                                "grounding_status": "unverified",
                                "is_grounded": False,
                                "confidence": 0.0,
                                "evidence_count": len(retrieved_evidence),
                                "unsupported_claims": [{
                                    "claim": ", ".join(sorted(answer_families)),
                                    "reason": "program_identity_mismatch",
                                }],
                                "answer": cls.HELPFUL_CLARIFICATION_MESSAGE,
                            }
                    # (b) The evidence must belong to the requested family.
                    candidate_programs = [
                        str(item.get("program") or item.get("course") or "")
                        for item in retrieved_evidence
                    ]
                    candidate_families = {
                        ResponseBuilderProgramFamily(p) for p in candidate_programs
                    }
                    candidate_families.discard(None)
                    if candidate_families and expected_family not in candidate_families:
                        return {
                            "grounding_status": "unverified",
                            "is_grounded": False,
                            "confidence": 0.0,
                            "evidence_count": len(retrieved_evidence),
                            "unsupported_claims": [
                                {
                                    "claim": getattr(query_spec, "program"),
                                    "reason": "program_identity_mismatch",
                                }
                            ],
                            "answer": cls.HELPFUL_CLARIFICATION_MESSAGE,
                        }

            # P0.1: tenant isolation at the grounding boundary too. Evidence
            # from another college can never ground an answer.
            if query_spec is not None and getattr(query_spec, "college_id", None):
                expected_college = getattr(query_spec, "college_id")
                if any(
                    item.get("college_id") and item.get("college_id") != expected_college
                    for item in retrieved_evidence
                ):
                    return {
                        "grounding_status": "unverified",
                        "is_grounded": False,
                        "confidence": 0.0,
                        "evidence_count": 0,
                        "answer": cls.HELPFUL_CLARIFICATION_MESSAGE,
                    }

            query_terms = set(re.findall(r"\b[a-z0-9]{2,}\b", (query or "").lower()))
            answer_terms = set(re.findall(r"\b[a-z0-9]{2,}\b", (candidate_answer or "").lower()))
            subject_terms = {
                term for term in query_terms & answer_terms
                if term not in {"what", "the", "fee", "fees", "is", "are", "average", "package"}
            }
            evidence_blob = " ".join(str(item.get("details") or item.get("content") or "").lower() for item in retrieved_evidence)
            # The query subject can be phrased differently in the evidence
            # (for example, "placement package" vs "average package"). The
            # claim-level verifier remains authoritative; do not add a second
            # exact-query-term gate that rejects valid paraphrases.

            if not claim_check["verified"]:
                return {
                    "grounding_status": "unverified",
                    "is_grounded": False,
                    "confidence": 0.0,
                    "evidence_count": len(retrieved_evidence),
                    "unsupported_claims": claim_check["unsupported_claims"],
                    "answer": cls.HELPFUL_CLARIFICATION_MESSAGE,
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
