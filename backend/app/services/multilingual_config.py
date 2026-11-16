"""Centralized Multilingual Configuration & Grounding Rules.

Defines supported languages (en, hi, gu), localization instructions,
and protected technical entities and acronyms that must never be translated.
"""

from typing import Dict, List, Set


class MultilingualConfig:
    """Centralized language settings for CampusAI College Chatbot."""

    SUPPORTED_LANGUAGES = ["en", "hi", "gu"]
    DEFAULT_LANGUAGE = "en"

    LANGUAGE_NAMES = {
        "en": "English",
        "hi": "Hindi (हिंदी)",
        "gu": "Gujarati (ગુજરાતી)",
    }

    # Technical abbreviations, proper nouns, and regulatory bodies that must NOT be translated
    PROTECTED_ENTITIES: Set[str] = {
        "AICTE", "UGC", "NAAC", "NBA", "GTU", "NIRF",
        "ACPC", "GUJCET", "JEE", "JEE Main", "NEET", "GATE", "CAT",
        "B.Tech", "B.E.", "M.Tech", "M.E.", "BCA", "MCA", "Diploma", "Ph.D",
        "FRC", "MYSY", "TFW", "TFWS", "SC", "ST", "SEBC", "EWS",
        "TPO", "HOD", "IEEE", "CSI", "NSS", "NCC",
        "CGPA", "SGPA", "CPI", "SPI",
        ".edu", ".in", ".ac.in", ".pdf", "http", "https", "www", "@",
    }

    SYSTEM_LANGUAGE_INSTRUCTIONS: Dict[str, str] = {
        "en": (
            "Respond in clear, formal English. "
            "Retain all official course names, dates, amounts, and citations verbatim."
        ),
        "hi": (
            "उत्तर शुद्ध, सरल और औपचारिक हिंदी (Devanagari script) में दें। "
            "तकनीकी शब्द (जैसे B.Tech, ACPC, GUJCET, FRC, MYSY, HOD, आदि), "
            "वेबसाइट लिंक (URLs) और दस्तावेज़ों के नामों का अनुवाद न करें; उन्हें मूल रूप में ही रखें।"
        ),
        "gu": (
            "જવાબ સ્પષ્ટ અને શિષ્ટ ગુજરાતી ભાષામાં આપો. "
            "તકનીકી પદો (જેમ કે B.Tech, ACPC, GUJCET, FRC, MYSY, ફી માળખું, વગેરે), "
            "સત્તાવાર વેબસાઇટ લિંક્સ (URLs) અને દસ્તાવેજોના નામોનો ભાષાંતર કર્યા વગર મૂળ સ્વરૂપમાં જ જાળવી રાખો."
        ),
    }

    FALLBACK_NO_INFO_MESSAGES: Dict[str, str] = {
        "en": (
            "I apologize, but no verified institutional record was found answering this question "
            "in the official college documents or published website. "
            "Please contact the campus admissions helpdesk for official guidance."
        ),
        "hi": (
            "क्षमा करें, आधिकारिक कॉलेज दस्तावेज़ों या वेबसाइट पर इस प्रश्न के संबंध में "
            "कोई सत्यापित जानकारी उपलब्ध नहीं है। "
            "कृपया आधिकारिक मार्गदर्शन हेतु कॉलेज हेल्पडेस्क से संपर्क करें।"
        ),
        "gu": (
            "માફ કરશો, સત્તાવાર કોલેજ દસ્તાવેજો અથવા વેબસાઇટ પર આ પ્રશ્ન સંબંધિત કોઈ "
            "ચકાસાયેલ માહિતી મળી નથી. "
            "કૃપા કરીને અધિકૃત માર્ગદર્શન માટે કોલેજ હેલ્પડેસ્કનો સંપર્ક કરો."
        ),
    }

    @classmethod
    def get_instruction(cls, lang: str) -> str:
        """Returns language-specific prompt guidance."""
        return cls.SYSTEM_LANGUAGE_INSTRUCTIONS.get(lang, cls.SYSTEM_LANGUAGE_INSTRUCTIONS["en"])

    @classmethod
    def get_language_instruction(cls, lang: str) -> str:
        """Alias for get_instruction."""
        return cls.get_instruction(lang)

    @classmethod
    def get_fallback_message(cls, lang: str) -> str:
        """Returns localized no-evidence fallback."""
        return cls.FALLBACK_NO_INFO_MESSAGES.get(lang, cls.FALLBACK_NO_INFO_MESSAGES["en"])

    @classmethod
    def get_no_reliable_info_message(cls, lang: str) -> str:
        """Alias for get_fallback_message."""
        return cls.get_fallback_message(lang)

    @classmethod
    def is_supported(cls, lang: str) -> bool:
        """Validates if language code is supported."""
        return lang.lower().strip() in cls.SUPPORTED_LANGUAGES


multilingual_config = MultilingualConfig()
