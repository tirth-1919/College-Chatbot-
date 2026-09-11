import re
from typing import Dict, Any

class LanguageEngine:
    # Common Gujarati words in Latin script (Gujlish)
    GUJLISH_KEYWORDS = {
        "ketli", "ketla", "ketlu", "che", "kya", "chhe", "nathi", "aave", "aavse", "karvu",
        "padhave", "kon", "ma", "na", "ni", "nu", "kem", "mate", "joie", "aapo",
        "kaal", "aaje", "bol", "saaru", "badha", "su", "shu", "kyare", "kyathi", "bhai",
        "batao", "dekhado", "karo", "malse", "madse", "chhe", "chho"
    }

    # Common Hindi words in Latin script (Hinglish)
    HINGLISH_KEYWORDS = {
        "kitni", "kitna", "kitne", "hai", "kaha", "kahan", "nahi", "aata", "padhate", "kaun",
        "mein", "ka", "ki", "ke", "kaise", "kare", "chahiye", "batao", "bataiye", "kab",
        "bharna", "bharo", "milega", "hoga", "kaisa", "kaisi", "kaise", "kisko",
        "aaj", "kya", "kyun", "sab", "hoga", "hota", "hoti", "hote", "bhai", "dost"
    }


    @classmethod
    def detect_language(cls, text: str) -> Dict[str, Any]:
        text_clean = text.strip()
        if not text_clean:
            return {"language": "en", "confidence": 1.0, "script": "latin"}

        # Check for Gujarati script (Unicode range U+0A80 to U+0AFF)
        gujarati_chars = len(re.findall(r'[\u0A80-\u0AFF]', text_clean))
        # Check for Devanagari script (Hindi, U+0900 to U+097F)
        devanagari_chars = len(re.findall(r'[\u0900-\u097F]', text_clean))
        total_alpha = len(re.findall(r'\w', text_clean)) or 1

        if gujarati_chars / total_alpha > 0.3:
            return {"language": "gu", "confidence": round(gujarati_chars / total_alpha, 2), "script": "gujarati"}
        
        if devanagari_chars / total_alpha > 0.3:
            return {"language": "hi", "confidence": round(devanagari_chars / total_alpha, 2), "script": "devanagari"}

        # Check Latin-script transliterated languages
        tokens = set(re.findall(r'\b[a-zA-Z]+\b', text_clean.lower()))
        gujlish_matches = tokens.intersection(cls.GUJLISH_KEYWORDS)
        hinglish_matches = tokens.intersection(cls.HINGLISH_KEYWORDS)

        if len(gujlish_matches) > 0 and len(gujlish_matches) >= len(hinglish_matches):
            return {
                "language": "gujlish",
                "canonical_lang": "gu",
                "confidence": 0.85,
                "script": "latin",
                "detected_markers": list(gujlish_matches)
            }

        if len(hinglish_matches) > 0:
            return {
                "language": "hinglish",
                "canonical_lang": "hi",
                "confidence": 0.85,
                "script": "latin",
                "detected_markers": list(hinglish_matches)
            }

        return {"language": "en", "confidence": 0.95, "script": "latin"}

language_engine = LanguageEngine()
