import re
import bleach
from typing import Tuple

class InputSanitizer:
    # Patterns common to adversarial prompt injection attempts
    PROMPT_INJECTION_PATTERNS = [
        r"ignore (all )?(previous|prior) (instructions|prompts|rules)",
        r"you are now in developer mode",
        r"system override",
        r"reveal your system prompt",
        r"tell me your hidden instructions",
        r"disregard the institution guidelines"
    ]

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        # Strip dangerous HTML tags
        cleaned = bleach.clean(text, tags=[], strip=True)
        return cleaned.strip()

    @classmethod
    def inspect_prompt_injection(cls, text: str) -> Tuple[bool, str]:
        text_lower = text.lower()
        for pattern in cls.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                return True, "Potential prompt injection flag detected."
        return False, "CLEAN"

sanitizer = InputSanitizer()
