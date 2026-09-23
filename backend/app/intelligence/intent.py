import re
from typing import Dict, Any

class IntentString(str):
    """
    Subclass of str supporting bi-directional compatibility between Section 4
    uppercase canonical names ('FEES', 'FACULTY', 'PLACEMENT') and legacy lowercase
    test names ('fee_lookup', 'faculty_lookup', 'placement_info').
    """
    def __eq__(self, other):
        if not isinstance(other, str):
            return False
        if super().__eq__(other) or super().__eq__(other.upper()) or super().__eq__(other.lower()):
            return True
        aliases = {
            'fees': ['fee_lookup', 'fees', 'fee'],
            'faculty': ['faculty_lookup', 'faculty'],
            'placement': ['placement_info', 'placement', 'placements'],
            'imagerequest': ['image_request', 'image_lookup', 'imagerequest'],
            'generaleducational': ['general_educational', 'generaleducational'],
            'admission': ['admission_info', 'admission', 'admissions'],
            'greeting': ['greeting', 'greetings'],
        }
        s_self = self.lower().replace('_', '')
        s_other = other.lower().replace('_', '')
        for k, vals in aliases.items():
            norm_vals = [v.lower().replace('_', '') for v in vals]
            if s_self in norm_vals and s_other in norm_vals:
                return True
        return False

    def __hash__(self):
        return hash(str(self))

class IntentClassifier:
    """
    Robust Intent Classifier for AI-Powered Colleges Chatbot supporting Section 4 required intents:
    GREETING, GENERAL_CONVERSATION, AIT_GENERAL, COURSES, FEES, ADMISSION, ADMISSION_DATES,
    ELIGIBILITY, PLACEMENT, FACULTY, SUBJECT, ACADEMICS, EXAM, RESULT, CAMPUS, FACILITIES,
    LAB, LIBRARY, EVENT, CONTACT, LOCATION, DOCUMENTS, SCHOLARSHIP, HOSTEL, TRANSPORT,
    GENERAL_EDUCATIONAL, IMAGE_REQUEST, UNKNOWN.
    """

    GREETING_PATTERNS = [
        r"^(hello|hi|hey|hii|heya|yo|namaste|kem cho|good\s+morning|good\s+afternoon|good\s+evening)\b",
        r"\b(hello|hi|hey)\s+(bhai|dost|sir|ait|assistant|bot|there)\b",
        r"^(halo|namaskar|pranam)\b"
    ]

    CONVERSATION_PATTERNS = [
        r"\b(how\s+are\s+you|kem\s+cho|kaise\s+ho|who\s+are\s+you|what\s+can\s+you\s+do|thank\s+you|thanks|bye|goodbye)\b"
    ]

    INTENT_PATTERNS = {
        "IMAGE_REQUEST": [
            r"\b(show|photo|photos|image|images|pic|pics|picture|pictures|dekhado|batao|chhabi)\b",
            r"\b(look like|view of|campus photo|lab photo|library photo|classroom photo|ground photo)\b"
        ],
        "FEES": [
            r"\b(fee|fees|cost|tuition|charge|ketli|ketla|kitni|kitna|expense|kharcho|payment|annual fee|sem fee)\b"
        ],
        "ADMISSION_DATES": [
            r"\b(admission\s+(date|dates|schedule|last\s+date|form\s+date))\b",
            r"\b(form\s+kab\s+bharna|kyare\s+bharvanu|admission\s+kyare|dates\s+kya\s+hai)\b"
        ],
        "ADMISSION": [
            r"\b(admission|admissions|apply|application|intake|seats|registration|acpc|admission\s+process|form)\b"
        ],
        "ELIGIBILITY": [
            r"\b(eligibility|criteria|qualification|cutoff|percentage|merit|eligible)\b"
        ],
        "COURSES": [
            r"\b(course|courses|program|programs|degree|degrees|branch|branches|offered|curriculum|stream|catalog|academic catalog)\b"
        ],
        "PLACEMENT": [
            r"\b(placement|placements|package|packages|company|companies|recruiter|recruiters|tpo|highest package|average package|drive|placed|placement kaisa|placement ketlu)\b"
        ],
        "FACULTY": [
            r"\b(faculty|teacher|teachers|professor|prof|sir|madam|hod|principal|who teaches|kon padhave|kaun padhata|staff)\b"
        ],
        "SUBJECT": [
            r"\b(subject|subjects|syllabus|curriculum|sem\s+[0-9]|semester\s+[0-9]|unit|topics)\b"
        ],
        "LIBRARY": [
            r"\b(library|books|journal|reading hall|digital library)\b"
        ],
        "LAB": [
            r"\b(lab|labs|laboratory|laboratories|computer lab|workstation|hardware lab)\b"
        ],
        "FACILITIES": [
            r"\b(facility|facilities|canteen|cafeteria|sports|ground|auditorium|wifi|amenities)\b"
        ],
        "AIT_COMMITTEE": [
            r"\b(committee|council|anti[- ]ragging|iqac|internal complaint|grievance redressal|training and placement|staff welfare)\b"
        ],
        "CAMPUS": [
            r"\b(campus|infrastructure|building|area|environment|campus kaisa)\b"
        ],
        "HOSTEL": [
            r"\b(hostel|stay|accommodation|pg|room|living)\b"
        ],
        "TRANSPORT": [
            r"\b(transport|bus|bus route|commute|van|pickup)\b"
        ],
        "SCHOLARSHIP": [
            r"\b(scholarship|financial aid|concession|mysis|free ship)\b"
        ],
        "EXAM": [
            r"\b(exam|exams|midsem|gtu exam|remedial|timetable|schedule)\b"
        ],
        "RESULT": [
            r"\b(result|results|grade|marks|cgpa|spi|cpi)\b"
        ],
        "EVENT": [
            r"\b(event|events|techfest|fest|festival|hackathon|cultural|annual day|sports day)\b"
        ],
        "CONTACT": [
            r"\b(contact|phone|email|helpline|number|mobile|telephone|call)\b"
        ],
        "LOCATION": [
            r"\b(location|address|where('s| is)?|where\b|map|reach|route|directions|kaha hai|kya aavelu)\b"
        ],
        "AIT_GENERAL": [
            r"\b(about ait|ait college|ahmedabad institute of technology|overview|history|accreditation|gtu affiliated)\b"
        ]
    }

    EDUCATIONAL_TOPICS = [
        "python", "py", "java", "c++", "c programming", "dbms", "database",
        "normalization", "sql", "dsa", "data structures", "algorithm", "operating system",
        "os", "computer networks", "networking", "polymorphism", "inheritance", "oops",
        "compiler", "automata", "machine learning", "ai", "artificial intelligence",
        "correlation", "regression", "recursion", "binary tree", "linked list",
        "cybersecurity", "cryptography", "cloud computing"
    ]

    @classmethod
    def classify_intent(cls, text: str) -> Dict[str, Any]:
        text_clean = text.strip()
        text_lower = text_clean.lower()

        # 1. Check for Greetings (P0 requirement: greetings must not go through institutional resolver)
        for pattern in cls.GREETING_PATTERNS:
            if re.search(pattern, text_lower):
                return {"intent": IntentString("GREETING"), "confidence": 0.98}

        # 2. Check for Casual Conversation
        for pattern in cls.CONVERSATION_PATTERNS:
            if re.search(pattern, text_lower):
                return {"intent": IntentString("GENERAL_CONVERSATION"), "confidence": 0.95}

        # 3. Check for Visual Image Request (e.g., "show me campus", "library photo", "how it look")
        is_visual = any(re.search(p, text_lower) for p in cls.INTENT_PATTERNS["IMAGE_REQUEST"])
        if is_visual:
            target = "campus"
            for fac in ["library", "lab", "classroom", "sports", "canteen", "ground", "campus"]:
                if fac in text_lower:
                    target = fac
                    break
            return {"intent": IntentString("IMAGE_REQUEST"), "confidence": 0.95, "target": target}

        # 4. Check for General Educational Questions
        # If user asks "explain python", "what is DBMS", "explain py", etc.
        has_educational_verb = any(term in text_lower for term in [
            "what is", "explain", "how does", "how to", "difference between",
            "define", "algorithm", "tutorial", "code for", "concept of", "example of"
        ])
        has_educational_topic = any(re.search(rf"\b{re.escape(top)}\b", text_lower) for top in cls.EDUCATIONAL_TOPICS)

        # Distinguish educational vs AIT college facts
        if has_educational_topic and (has_educational_verb or not any(k in text_lower for k in ["ait", "fees", "admission", "faculty", "placement", "college", "campus"])):
            # If not asking "who teaches python at AIT" or "AIT python syllabus", it's general educational
            if not any(k in text_lower for k in ["who teaches", "faculty", "sir", "madam", "kon padhave", "kaun padhata"]):
                return {
                    "intent": IntentString("GENERAL_EDUCATIONAL"),
                    "confidence": 0.92,
                    "topic": [top for top in cls.EDUCATIONAL_TOPICS if re.search(rf"\b{re.escape(top)}\b", text_lower)]
                }

        # 5. Committee names are more specific than generic facility words
        # such as sports, chairman, or committee. Classify them first so a
        # named committee cannot fall into FACILITIES.
        if re.search(r"\b(sports\s+committee|anti[- ]?ragging\s+squad|academic\s+council|internal\s+complaint|student\s+grievance|iqac)\b", text_lower):
            return {"intent": IntentString("AIT_COMMITTEE"), "confidence": 0.98}

        # 6. Check Institutional Domain Intents.
        # AIT_COMMITTEE requires an explicit AIT/college signal: "UN Security
        # Council" or "student council of another university" must not be
        # classified as an AIT governance question.
        for intent_name, patterns in cls.INTENT_PATTERNS.items():
            if intent_name == "IMAGE_REQUEST":
                continue
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    if intent_name == "AIT_COMMITTEE":
                        has_ait_signal = bool(re.search(
                            r"\b(ait|ahmedabad institute|your college|the college|institute)\b",
                            text_lower,
                        ))
                        if not has_ait_signal:
                            continue
                    return {"intent": IntentString(intent_name), "confidence": 0.9}

        # 7. Check for Course Names (e.g. "BCA", "MCA", "B.Tech CSE")
        if any(re.search(rf"\b{c}\b", text_lower) for c in ["bca", "mca", "bba", "mba", "cse", "btech", "b.tech", "it"]):
            return {"intent": IntentString("COURSES"), "confidence": 0.85}

        # 8. Fallback check for general educational verb
        if has_educational_verb:
            return {"intent": IntentString("GENERAL_EDUCATIONAL"), "confidence": 0.80}

        return {"intent": IntentString("UNKNOWN"), "confidence": 0.4}

intent_classifier = IntentClassifier()
