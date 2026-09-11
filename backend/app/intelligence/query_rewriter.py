import re
from typing import Dict, Any

class QueryRewriter:
    SLANG_MAP = {
        # Gujarati/Gujlish mappings
        r"\bketli che\b": "what is the fee",
        r"\bketli chhe\b": "what is the fee",
        r"\bketla che\b": "what is the fee",
        r"\bketlu che\b": "how much is",
        r"\bkyare che\b": "when is",
        r"\bkyare bharvanu\b": "when to fill",
        r"\bkon padhave che\b": "who teaches",
        r"\bkon che\b": "who is",
        r"\bcollege ma library che\b": "is there a library in college",
        r"\bher office kya che\b": "where is her office",
        r"\bkya che\b": "where is",
        r"\bkya aavelu che\b": "where is located",
        r"\bna subjects\b": "curriculum subjects",
        r"\bna syllabus\b": "syllabus",
        r"\bni fees\b": "fees structure",
        r"\bdekhado\b": "show me",
        r"\bbatao\b": "show me",

        # Hindi/Hinglish mappings
        r"\bkitni hai\b": "what is",
        r"\bkitna hai\b": "what is",
        r"\bkaisa hai\b": "how is",
        r"\bkaise hai\b": "how is",
        r"\bkab bharna\b": "when to fill and submit",
        r"\bkab bharna hai\b": "when to fill and submit",
        r"\bkab start hoga\b": "when does it start",
        r"\bkaun padhata hai\b": "who teaches",
        r"\bkaha hai\b": "where is",
        r"\bki fees\b": "fees structure",
        r"\bke subjects\b": "curriculum subjects",

        # Technical/Subject Abbreviations
        r"\bexplain py\b": "explain python programming",
        r"\bwhat is py\b": "what is python",
        r"\bintro to py\b": "introduction to python",
        r"\bplcmnt\b": "placement",
        r"\badmsn\b": "admission",
        r"\bhod\b": "head of department",
        r"\btpo\b": "training and placement officer cell",
    }

    @classmethod
    def rewrite_query(cls, text: str, detected_lang: str) -> Dict[str, Any]:
        normalized = text
        for pattern, replacement in cls.SLANG_MAP.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        # Normalize redundant spaces
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return {
            "original_query": text,
            "normalized_query": normalized,
            "is_rewritten": normalized.lower() != text.lower().strip()
        }

query_rewriter = QueryRewriter()

