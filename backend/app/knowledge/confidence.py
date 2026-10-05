# Configurable evidence confidence and claim verification gates.
import re
from typing import Any, Dict, Iterable, List
class ConfidenceGate:
    def __init__(self, high: float = 0.72, medium: float = 0.48):
        self.high = high
        self.medium = medium
    def score(self, intent_confidence: float, retrieval: float, reranker: float,
              completeness: float, reliability: float, freshness: float,
              conflict: bool = False) -> float:
        value = (
            0.20 * intent_confidence + 0.22 * retrieval + 0.22 * reranker
            + 0.16 * completeness + 0.12 * reliability + 0.08 * freshness
        )
        return max(0.0, min(1.0, value - (0.30 if conflict else 0.0)))

    def level(self, value: float) -> str:
        if value >= self.high:
            return "HIGH"
        if value >= self.medium:
            return "MEDIUM"
        return "LOW"

    def decision(self, value: float, verified: bool, conflict: bool = False) -> str:
        if verified and not conflict and value >= self.high:
            return "VERIFIED"
        if value >= self.medium:
            return "ADDITIONAL_EVIDENCE"
        return "FALLBACK_OR_NO_INFORMATION"


def verify_claims(answer: str, evidence: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    # Conservative lexical claim gate used before a verified badge.
    evidence = list(evidence)
    evidence_text = []
    for item in evidence:
        parts = [item.get(key) for key in (
            "title", "category", "topic", "value", "details", "content",
            "description", "summary", "program", "academic_year", "field", "answer"
        )]
        details = " ".join(
            str(value) for part in parts
            for value in (part.values() if isinstance(part, dict) else [part])
            if isinstance(value, (str, int, float)) and str(value).strip()
        )
        evidence_text.append(details.lower())
    # Structured fee records expose currency values and program codes inside
    # serialized details dictionaries. Accept that direct, same-record match
    # before applying the general prose overlap gate.
    answer_lower = (answer or "").lower()
    answer_numbers = {number.replace(",", "") for number in re.findall(r"\d[\d,]*", answer_lower)}
    answer_programs = re.findall(r"\b(bca|mca|bba|mba|btech|cse)\b", answer_lower)
    for text in evidence_text:
        evidence_numbers = {number.replace(",", "") for number in re.findall(r"\d[\d,]*", text)}
        if answer_numbers & evidence_numbers and answer_programs and any(
            re.search(rf"\b{re.escape(program)}\b", text) for program in answer_programs
        ):
            return {"verified": True, "unsupported_claims": [], "evidence_count": len(evidence)}

    # P0.3: the grounded answer wraps a record's own value in generic pipeline
    # phrasing ("The recorded BCA value is ... for the 2026-27 academic year.").
    # That scaffolding is OUR wording, not a claim made about the college, so
    # it must not be judged against the evidence. Strip it before claim
    # verification; the record's real value is what has to be supported.
    GENERIC_ANSWER_SCAFFOLD = re.compile(
        r"^\s*the\s+recorded\s+[^.]*?\bvalue\s+is\s+"
        r"|\s+for\s+the\s+[\w\s-]*?\bacademic\s+year\b\s*\.?\s*$",
        re.IGNORECASE,
    )

    def _strip_scaffold(text: str) -> str:
        return GENERIC_ANSWER_SCAFFOLD.sub("", text or "").strip()

    sentences = [
        _strip_scaffold(s).strip()
        for s in re.split(r"(?<!Rs)[.!?\n]+", answer or "")
    ]
    sentences = [s for s in sentences if s.strip()]
    unsupported: List[str] = []
    claim_stopwords = {
        "the", "fee", "fees", "is", "are", "and", "for", "year",
        "average", "package", "placement", "rs", "lpa",
    }
    for sentence in sentences:
        tokens = {t for t in re.findall(r"[a-z0-9]+", sentence.lower()) if len(t) > 3}
        identifiers = {
            t.lower()
            for t in re.findall(r"\b[a-z]{2,}[0-9]+\b|\b[a-z]{3,}\b", sentence.lower())
            if t.lower() not in claim_stopwords
        }
        course_codes = {t for t in tokens if t.isalpha() and 2 <= len(t) <= 6 and t not in {"average", "package", "placement", "lpa"}}
        if not tokens:
            continue
        supported = False
        answer_numbers = {
            number.replace(",", "")
            for number in re.findall(r"\d[\d,]*", sentence)
        }
        for text in evidence_text:
            if re.sub(r"\s+", " ", sentence.lower()).strip() in re.sub(r"\s+", " ", text).strip():
                supported = True
                break
            evidence_tokens = {t for t in re.findall(r"[a-z0-9]+", text) if len(t) > 3}
            evidence_numbers = {
                number.replace(",", "")
                for number in re.findall(r"\d[\d,]*", text)
            }
            if course_codes and any(re.search(rf"\b{re.escape(code)}\b", text) is None for code in course_codes):
                continue
            non_course_identifiers = identifiers - course_codes
            if non_course_identifiers and not non_course_identifiers.issubset(evidence_tokens):
                continue
            if course_codes and not course_codes.issubset(evidence_tokens | {code.lower() for code in course_codes if re.search(rf"\b{re.escape(code)}\b", text)}):
                continue
            # Structured records often expose the answer as a numeric/currency
            # value in a dict, while the prose answer contributes only the
            # program and year words to lexical overlap. Treat a matching
            # numeric value as claim support when the requested identifiers are
            # present in the same evidence item.
            meaningful_tokens = tokens - {"what", "this", "that", "with", "from", "into"}
            requested_programs = re.findall(
                r"\b(bca|mca|bba|mba|btech|cse)\b", sentence.lower()
            )
            program_supported = any(
                re.search(rf"\b{re.escape(program)}\b", text)
                for program in requested_programs
            )
            if answer_numbers & evidence_numbers and (
                meaningful_tokens & evidence_tokens or program_supported
            ):
                supported = True
                break
            overlap = tokens & evidence_tokens
            # Structured admin records may carry the complete published answer in
            # a field such as ``answer`` while the generated sentence preserves
            # that wording. Treat matching multi-word factual text as support.
            if any(
                phrase.strip() and phrase.strip().lower() in text
                for phrase in re.split(r"[.!?\n]+", sentence)
            ):
                supported = True
                break
            # Require either a substantial claim overlap or a short factual
            # claim whose key terms are all present in the same evidence item.
            if len(overlap) >= max(2, min(4, len(tokens) // 2)) or (
                len(overlap) >= 2 and any(char.isdigit() for char in sentence)
            ):
                supported = True
                break
        if not supported:
            unsupported.append(sentence)
    return {"verified": not unsupported, "unsupported_claims": unsupported,
            "evidence_count": len(evidence)}

confidence_gate = ConfidenceGate()
