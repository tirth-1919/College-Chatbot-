import re
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
@dataclass
class QuerySpec:
    'The one canonical query contract shared by the chat pipeline.'
    college_id: Optional[str] = None
    college_name: Optional[str] = None
    intent: Optional[str] = None
    category: Optional[str] = None
    topic: Optional[str] = None
    program: Optional[str] = None
    entity: Optional[str] = None
    academic_year: Optional[str] = None
    requested_field: Optional[str] = None
    route: Optional[str] = None
    confidence: Optional[float] = None
    # ------------------------------------------------------------------
    # P0.1 QuerySpec consolidation.
    #
    # Everything downstream of query understanding reads these fields.
    # No stage after this one may re-derive intent / category / topic /
    # program / entity / academic_year from the raw question.
    #
    # `raw_question` is an *opaque lexical carrier* used only for:
    #   * retrieval relevance scoring (match ranking, not interpretation)
    #   * natural-language phrasing in the final answer
    # It must never be a source of semantic fields.
    # ------------------------------------------------------------------
    raw_question: Optional[str] = None
    # Full multi-value views kept on the spec so downstream stages never
    # re-run entity extraction.
    programs: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    facilities: Optional[List[str]] = None
    subjects: Optional[List[str]] = None
    faculty_names: Optional[List[str]] = None
    semester: Optional[Any] = None

    @property
    def subtopic(self):
        return self.requested_field

    @property
    def field(self):
        return self.requested_field

    # ------------------------------------------------------------------
    # Lexical flag accessors.  These are computed ONCE, here, from the raw
    # question.  Downstream code reads the boolean; it never re-scans text.
    # ------------------------------------------------------------------
    @property
    def _haystack(self) -> str:
        return (self.raw_question or "").lower()

    def _has(self, pattern: str) -> bool:
        return bool(re.search(pattern, self._haystack))

    def _has_any(self, words) -> bool:
        return any(w in self._haystack for w in words)

    @property
    def has_temporal_qualifier(self) -> bool:
        return self.temporal_qualifier is not None
    @property
    def is_greeting_phrase(self) -> bool:
        greetings = {
            "hi", "hello", "hey", "hy", "hyy", "hiii", "hii", "greetings",
            "good morning", "good afternoon", "good evening",
        }
        normalized = re.sub(r"[^a-z0-9 ]", " ", self._haystack).strip()
        return normalized in greetings

    @property
    def is_visual_request(self) -> bool:
        return self._has_any([
            "show me", "campus photo", "library photo", "lab photo",
            "view of", "how it look",
        ]) and self._has_any([
            "campus", "library", "lab", "classroom", "canteen", "sports",
            "ground", "building",
        ])

    @property
    def is_user_file_request(self) -> bool:
        return self._has_any([
            "my file", "this pdf", "uploaded document", "attached",
            "this image", "in my doc",
        ])

    @property
    def is_general_learning_guidance(self) -> bool:
        return bool(re.search(
            r"\b(beginner|practice|learn|learning|concepts?|skills?|build(?:ing)?|before|how to)\b",
            self._haystack,
        )) and bool(re.search(
            r"\b(programming|coding|software|web application|web app|development|developer)\b",
            self._haystack,
        )) and not self._has(
            r"\b(placement|official|faculty|teacher|professor|fee|fees|admission|"
            r"eligibility|library|department|departments|syllabus|curriculum|"
            r"course|courses)\b"
        )

    @property
    def is_fee_query(self) -> bool:
        return self._has_any(["fee", "fees", "tuition", "cost", "charge", "kitni", "ketli"])

    @property
    def is_document_query(self) -> bool:
        return self._has(
            r"\b(required documents?|admission documents?|application documents?|"
            r"certificates?|document checklist|checklist|documents? needed|"
            r"documents? (?:are|is) required|required (?:for|at) admission)\b"
        )

    @property
    def is_program_query(self) -> bool:
        return self._has(
            r"\b(course|courses|program|programs|degree|branch|curriculum|syllabus)\b"
        ) and not self.is_document_query and not self.is_fee_query

    @property
    def is_values_query(self) -> bool:
        return self._has(
            r"\b(core values?|educational philosophy|institutional philosophy|vision|mission|values)\b"
        )

    @property
    def is_clubs_query(self) -> bool:
        return self._has(r"\b(student clubs?|extracurricular|student activities|student organizations?)\b")

    @property
    def is_rto_query(self) -> bool:
        return self._has(r"\b(rto|license facilitation center|learning license|driving license)\b")

    @property
    def is_database_query(self) -> bool:
        return self._has(
            r"\b(database|knowledge database|stored|records? stored|"
            r"academic[- ]year information|course categories)\b"
        )

    @property
    def is_transport_query(self) -> bool:
        return self._has_any([
            "transport", "transportation", "bus", "buses", "commute",
            "commuting", "route", "routes", "pickup", "pick up",
            "drop-off", "drop off", "shuttle", "vehicle", "vehicles",
            "parking",
        ])

    @property
    def is_section_query(self) -> bool:
        return self._has_any(["committee", "council", "squad", "cell", "iqac"])

    @property
    def is_student_support_query(self) -> bool:
        return self._has(
            r"(support\s+services?|student\s+services?|mentoring|"
            r"mentor(?:ing)?\s+services?)\b"
        )

    @property
    def is_catalog_query(self) -> bool:
        return "catalog" in self._haystack and not self.is_section_query and not self.is_intake_query

    @property
    def is_intake_query(self) -> bool:
        return self._has_any(["intake", "total student", "student intake", "number of courses"])

    @property
    def is_placement_query(self) -> bool:
        return self._has_any([
            "placement", "placements", "highest package", "average package",
            "placement rate", "recruiter", "recruiters",
            "training and placement", "placement cell",
            "companies visiting", "placement department",
        ])

    @property
    def is_committee_query(self) -> bool:
        return self._has_any([
            "committee", "council", "squad", "iqac", "grievance",
            "chairman", "chairperson",
        ])

    @property
    def is_courses_listing_query(self) -> bool:
        return self._has_any([
            "catalog", "courses", "programs", "program list",
            "academic catalog",
        ])

    @property
    def has_strong_institutional_keyword(self) -> bool:
        return self._has_any([
            "fees", "fee", "admission", "admissions", "placement",
            "placements", "faculty", "professor", "hod", "principal",
            "hostel", "gtu", "ahmedabad institute", "canteen", "library",
            "sports ground", "iqac", "grievance", "counselling",
            "counseling", "student support", "student guidance",
            "student welfare", "mentoring",
        ])

    @property
    def has_weak_institutional_keyword(self) -> bool:
        return self._has_any([
            "college", "campus", "committee", "council", "squad",
            "chairman", "chairperson",
        ])

    @property
    def has_ait_mention(self) -> bool:
        return self._has(r"\bait\b")

    @property
    def has_semantic_signal(self) -> bool:
        """True when the spec carries a real semantic field (not raw text)."""
        return bool(self.program or self.entity or self.topic or self.requested_field)

    @property
    def keywords(self):
        return [w for w in re.findall(r"[a-z0-9]+", self._haystack) if len(w) > 1]

    @property
    def synonyms(self):
        return sorted({
            syn
            for word in self.keywords
            for syn in EntityExtractor.SYNONYMS.get(word, [])
        })

    @property
    def requested_years(self) -> List[str]:
        return [self.academic_year] if self.academic_year else []

    @property
    def temporal_qualifier(self) -> Optional[str]:
        "Temporal ranking intent, normalized once at QuerySpec construction."
        raw = (self.raw_question or "").lower()
        if re.search(r"\b(upcoming|forthcoming)\b", raw):
            return "upcoming"
        if re.search(r"\b(latest|recent|current|newest|lateset)\b", raw):
            return "latest"
        return None

    @property
    def retrieval_text(self) -> str:
        """Canonical retrieval/lexical text derived from spec fields only."""
        parts = [
            self.topic,
            self.requested_field,
            self.program,
            self.entity,
            self.academic_year,
            *(self.programs or []),
            *(self.topics or []),
            *(self.facilities or []),
        ]
        # Keep the resolved fields first, then retain the original wording as a
        # lexical ranking carrier.  Downstream code may use this for evidence
        # matching, but never for re-interpreting identity fields.
        lexical = self.raw_question or ""
        return " ".join(str(p) for p in parts if p) + (f" {lexical}" if lexical else "")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# Backward-compatible name for callers that only need the older parsed shape.
QueryUnderstanding = QuerySpec

class EntityExtractor:
    PROGRAMS = {
        "bca": "BCA (Bachelor of Computer Applications)",
        "data science": "Data Science",
        "data science & analytics": "Data Science",
        "artificial intelligence": "Artificial Intelligence",
        "computer applications": "BCA (Bachelor of Computer Applications)",
        "business administration": "BBA (Bachelor of Business Administration)",
        "mca": "MCA (Master of Computer Applications)",
        "bba": "BBA (Bachelor of Business Administration)",
        "mba": "MBA (Master of Business Administration)",
        "btech": "B.Tech",
        "b.tech": "B.Tech",
        "b tech": "B.Tech",
        "bachelor of technology": "B.Tech",
        "b.tech cse": "B.Tech Computer Science & Engineering",
        "btech cse": "B.Tech Computer Science & Engineering",
        "b tech cse": "B.Tech Computer Science & Engineering",
        "computer science engineering": "B.Tech Computer Science & Engineering",
        "computer science & engineering": "B.Tech Computer Science & Engineering",
        "cse": "B.Tech Computer Science & Engineering",
        "computer engineering": "B.Tech Computer Engineering",
        "ce": "B.Tech Computer Engineering",
        "b.tech it": "B.Tech Information Technology",
        "btech it": "B.Tech Information Technology",
        "information technology": "B.Tech Information Technology",
        "b tech it": "B.Tech Information Technology",
        "bachelor of computer applications": "BCA (Bachelor of Computer Applications)",
        "bachelor of business administration": "BBA (Bachelor of Business Administration)",
        "it branch": "B.Tech Information Technology",
        "it department": "B.Tech Information Technology",
        "it engineering": "B.Tech Information Technology",
        "mechanical": "B.Tech Mechanical Engineering",
        "civil": "B.Tech Civil Engineering",
        "electrical": "B.Tech Electrical Engineering",
        "ec": "B.Tech Electronics & Communication Engineering"
    }

    SUBJECTS = {
        "dbms": "Database Management Systems",
        "database": "Database Management Systems",
        "dsa": "Data Structures & Algorithms",
        "data structures": "Data Structures & Algorithms",
        "os": "Operating Systems",
        "operating system": "Operating Systems",
        "cn": "Computer Networks",
        "computer networks": "Computer Networks",
        "java": "Java Programming",
        "python": "Python Programming",
        "ai": "Artificial Intelligence",
        "machine learning": "Machine Learning",
        "se": "Software Engineering",
        "toc": "Theory of Computation",
        "coa": "Computer Organization & Architecture"
    }

    FACILITIES = {
        "central library": "Central Library",
        "library": "Central Library",
        "computer lab": "Computer Laboratories",
        "lab": "Laboratories",
        "canteen": "Cafeteria & Canteen",
        "sports ground": "Sports Ground",
        "sports": "Sports Ground & Gymnasium",
        "gym": "Sports Ground & Gymnasium",
        "smart class": "Smart Classrooms",
        "smart classroom": "Smart Classrooms",
        "classroom": "Smart Classrooms",
        "campus": "AIT Campus",
        "auditorium": "College Auditorium"
    }

    TOPICS = {
        "fees": "FEES",
        "fee": "FEES",
        "tuition": "FEES",
        "admission": "ADMISSION",
        "admissions": "ADMISSION",
        "eligibility": "ELIGIBILITY",
        "placement": "PLACEMENT",
        "placements": "PLACEMENT",
        "package": "PLACEMENT",
        "faculty": "FACULTY",
        "professor": "FACULTY",
        "library": "LIBRARY",
        "lab": "LAB",
        "canteen": "FACILITIES",
        "sports": "FACILITIES",
        "contact": "CONTACT",
        "address": "LOCATION",
        "hostel": "HOSTEL",
        "hostels": "HOSTEL",
        "accommodation": "HOSTEL",
        "dormitory": "HOSTEL",
        "transport": "TRANSPORT",
        "transportation": "TRANSPORT",
        "bus": "TRANSPORT",
        "commute": "TRANSPORT",
        "scholarship": "SCHOLARSHIP",
        "scholarships": "SCHOLARSHIP",
        "financial aid": "SCHOLARSHIP",
        "concession": "SCHOLARSHIP",
        "facilities": "FACILITIES",
        "facility": "FACILITIES",
        "canteen": "FACILITIES",
        "sports": "FACILITIES",
        "transportation facilities": "TRANSPORT",
        "library facilities": "LIBRARY",
        "event": "EVENTS",
        "events": "EVENTS",
        "fest": "EVENTS",
        "cultural": "EVENTS",
        "calendar": "EVENTS",
        "news": "EVENTS",
        "announcement": "EVENTS",
        "announcements": "EVENTS",
        "event": "EVENTS",
        "events": "EVENTS",
        "notice": "EVENTS",
        "notices": "EVENTS",
        "circular": "EVENTS",
        "circulars": "EVENTS",
        "activity": "EVENTS",
        "activities": "EVENTS",
        "activity": "EVENTS",
        "seminar": "EVENTS",
        "seminars": "EVENTS",
        "workshop": "EVENTS",
        "workshops": "EVENTS",
        "festival": "EVENTS",
        "festivals": "EVENTS",
        "techfest": "EVENTS",
        "hackathon": "EVENTS",
        "course": "COURSES",
        "courses": "COURSES",
        "program": "COURSES",
        "programs": "COURSES",
        "degree": "COURSES",
    }

    # P0.3 TOPIC_PRIORITY: several institutional topics can legitimately match
    # one question ("What library facilities are available?" -> library AND
    # facilities).  Topic detection must therefore be EXPLICIT rather than
    # dependent on dict iteration order, otherwise the same question can be
    # routed to a different knowledge category between releases.
    #
    # The ordering below expresses specificity: a concrete institutional topic
    # (hostel, library, transport, scholarship, ...) always wins over a generic
    # one (facilities, campus).  It is a topic/sub-topic relationship, not an
    # answer branch.
    TOPIC_PRIORITY = (
        "FEES",
        "ELIGIBILITY",
        "PLACEMENT",
        "EVENTS",
        "FACULTY",
        "SCHOLARSHIP",
        "HOSTEL",
        "LIBRARY",
        "LAB",
        "CONTACT",
        "LOCATION",
        "TRANSPORT",
        "COURSES",
        "FACILITIES",
    )

    @classmethod
    def select_topic(cls, topics) -> Optional[str]:
        """Pick the single most specific topic from the extracted set."""
        candidates = [t for t in (topics or []) if t]
        if not candidates:
            return None
        for preferred in cls.TOPIC_PRIORITY:
            if preferred in candidates:
                return preferred
        return candidates[0]

    # ------------------------------------------------------------------
    # P0.3: the ADMISSIONS topic tree.
    #
    #   Admissions
    #     |-- Process, Eligibility, Documents, Fees, Entrance Exam, Merit,
    #     |   Counselling, Deadline, Reservation, Confirmation,
    #     |   Cancellation, Refund
    #
    # A question naming any of these sub-topics IS an Admissions question.
    # Declaring the relationship here (data, not control flow) lets the
    # generic relevance gate recognise the parent topic without a per-category
    # answer branch anywhere downstream.
    # ------------------------------------------------------------------
    ADMISSION_SUBTOPICS = {
        "DOCUMENTS": r"\b(documents?|certificates?|marksheet|marksheets|domicile|transcript|transfer certificate|migration certificate|papers?)\b",
        "ELIGIBILITY": r"\b(eligib\w*|qualification|criteria|qualifying|cut\s*-?\s*off|minimum\s+qualification)\b",
        "FEES": r"\b(fee|fees|tuition|cost|charge|payment)\b",
        "ENTRANCE_EXAM": r"\b(entrance|entrance\s+exam|gujcet|jee|neet|test\s+exam|exam\s+pattern)\b",
        "MERIT": r"\b(merit|cut\s*-?\s*off|rank|reservation|reservation\s+policy|quota)\b",
        "COUNSELLING": r"\b(counsell\w*|counseling|counselling)\b",
        "DEADLINE": r"\b(deadline|last\s+date|closing\s+date|dates?)\b",
        "RESERVATION": r"\b(reservation|quota|category\s+based\s+reservation|domicile\s+based)\b",
        "CONFIRMATION": r"\b(confirm\w*|confirmation|accept\s+offer|offer\s+letter)\b",
        "CANCELLATION": r"\b(cancel\w*|cancellation|withdraw\w*|withdrawal)\b",
        "REFUND": r"\b(refund)\b",
        "PROCESS": r"\b(process|procedure|how\s+to\s+apply|apply|application|steps)\b",
    }

    # Most specific sub-topics first: a question about entrance exams must not
    # be classified as a generic PROCESS question, and DOCUMENTS must outrank
    # the bare word "required".
    ADMISSION_SUBTOPIC_ORDER = (
        "ENTRANCE_EXAM", "MERIT", "DOCUMENTS", "ELIGIBILITY", "FEES",
        "COUNSELLING", "DEADLINE", "RESERVATION", "CONFIRMATION",
        "CANCELLATION", "REFUND", "PROCESS",
    )

    @classmethod
    def select_admission_subtopic(cls, text: str) -> Optional[str]:
        """
        Return the admission sub-topic named by `text`, or None.

        The sub-topic is only recognised when the question is genuinely about
        admissions -- either it says so, or it names a program/degree, which is
        how the form "What documents are required for BCA?" is understood.
        """
        raw = (text or "").lower()
        if not raw:
            return None
        mentions_admission = bool(re.search(
            r"\b(admission|admissions|admit|applying|application|apply|enroll\w*|"
            r"registration|joining|entrance|counsell\w*)\b", raw
        ))
        mentions_program = bool(re.search(
            r"\b(bca|bba|mca|mba|b\.?tech|bachelor|master|degree|course|program\w*)\b", raw
        ))
        # A program name alone is sufficient for admission subtopics whose
        # meaning is unambiguous (documents/eligibility), but not for fees:
        # "BCA fee" is a fee query, not an admission-fee query.
        for subtopic in cls.ADMISSION_SUBTOPIC_ORDER:
            if not re.search(cls.ADMISSION_SUBTOPICS[subtopic], raw):
                continue
            if subtopic == "FEES" and not mentions_admission:
                continue
            if not (mentions_admission or mentions_program):
                return None
            return subtopic
        return None
        return None

    SUBTOPICS = {
        "required documents": ("ADMISSION", "DOCUMENTS", "REQUIRED_DOCUMENTS"),
        "admission documents": ("ADMISSION", "DOCUMENTS", "REQUIRED_DOCUMENTS"),
        "documents": ("ADMISSION", "DOCUMENTS", "REQUIRED_DOCUMENTS"),
        "certificates": ("ADMISSION", "DOCUMENTS", "REQUIRED_DOCUMENTS"),
        "eligibility": ("ADMISSION", "ELIGIBILITY", "ELIGIBILITY"),
        "tuition": ("FEES", "FEES", "TUITION_FEE"),
        "fee": ("FEES", "FEES", "TUITION_FEE"),
        "fees": ("FEES", "FEES", "TUITION_FEE"),
        "cost": ("FEES", "FEES", "TUITION_FEE"),
        "charges": ("FEES", "FEES", "OTHER_FEE"),
        "syllabus": ("ACADEMICS", "ACADEMICS", "SYLLABUS"),
        "faculty": ("ACADEMICS", "ACADEMICS", "FACULTY"),
        "hostel": ("CAMPUS", "CAMPUS", "HOSTEL"),
        "transport": ("CAMPUS", "CAMPUS", "TRANSPORT"),
        "library": ("CAMPUS", "CAMPUS", "LIBRARY"),
        "placement": ("PLACEMENT", "PLACEMENT", "PLACEMENT"),
    }

    SYNONYMS = {
        "fee": ["fee", "fees", "tuition", "cost", "charges"],
        "fees": ["fee", "fees", "tuition", "cost", "charges"],
        "document": ["document", "documents", "papers", "certificates"],
        "documents": ["document", "documents", "papers", "certificates"],
        "event": ["event", "events", "news", "announcement", "notice", "circular", "activity", "seminar", "workshop", "festival"],
        "events": ["event", "events", "news", "announcement", "notice", "circular", "activity", "seminar", "workshop", "festival"],
        "admission": ["admission", "admissions", "enrollment", "enrolment"],
    }

    ORDINAL_SEMESTERS = {
        "1": 1, "1st": 1, "first": 1, "one": 1, "pehelu": 1, "pehla": 1,
        "2": 2, "2nd": 2, "second": 2, "two": 2, "biju": 2, "doosra": 2,
        "3": 3, "3rd": 3, "third": 3, "three": 3, "triju": 3, "teesra": 3,
        "4": 4, "4th": 4, "fourth": 4, "four": 4, "chothu": 4, "chautha": 4,
        "5": 5, "5th": 5, "fifth": 5, "five": 5, "paanchmu": 5, "paanchva": 5,
        "6": 6, "6th": 6, "sixth": 6, "six": 6, "chhatthu": 6, "chhattha": 6,
        "7": 7, "7th": 7, "seventh": 7, "seven": 7, "saatmu": 7, "saatva": 7,
        "8": 8, "8th": 8, "eighth": 8, "eight": 8, "aathmu": 8, "aathva": 8
    }

    @classmethod
    def extract_query_understanding(cls, text: str, college_id: Optional[str] = None,
                                    intent: Optional[str] = None) -> QuerySpec:
        "Build the canonical QuerySpec at the query-understanding boundary."
        raw = (text or "").lower()
        raw = re.sub(r"\blateset\b", "latest", raw)
        raw = re.sub(r"\bevnts?\b", "events", raw)
        entities = cls.extract_entities(raw)
        # A research field or a generic area of study is not necessarily a
        # college program. Keep unambiguous degree codes (BCA, BBA, etc.)
        # while requiring an explicit program/degree reference for broad fields.
        if not re.search(r"\b(program|programme|degree|course|speciali[sz]ation)\s+(?:in|of|for)?\s*(?:data science|artificial intelligence)\b|\b(data science|artificial intelligence)\s+(?:program|programme|degree|course|speciali[sz]ation)\b|\b(?:fee|fees|tuition|admission)\s+(?:for|of|in)\s+(?:the\s+)?(?:data science|artificial intelligence)\b|\b(?:data science|artificial intelligence)\s+(?:fee|fees|tuition|admission)\b", raw):
            entities["programs"] = [p for p in entities["programs"] if p not in ("Data Science", "Artificial Intelligence")]
        program = entities["programs"][0] if entities["programs"] else None
        # P0.3: explicit topic selection. "What library facilities are
        # available?" matches BOTH library and facilities; the specific topic
        # must win so the question is answered from library evidence.
        topic = cls.select_topic(entities["topics"])
        subtopic = field = None
        for phrase, (sub_intent, sub_topic, sub_name) in sorted(cls.SUBTOPICS.items(), key=lambda x: -len(x[0])):
            if re.search(rf"\b{re.escape(phrase)}\b", raw):
                intent = intent or sub_intent
                topic = topic or sub_topic
                if sub_topic == "DOCUMENTS":
                    topic = sub_topic
                subtopic = sub_name
                field = sub_name
                break
        if not subtopic and topic == "ADMISSION" and re.search(r"\b(papers?|needed|required|certificates?)\b", raw):
            subtopic, field = "REQUIRED_DOCUMENTS", "REQUIRED_DOCUMENTS"
        # P0.3 (defect 4): a general ADMISSION sub-topic relationship. Asking
        # about documents, eligibility, fees, an entrance exam, merit,
        # counselling, a deadline, reservation, confirmation, cancellation or
        # a refund is asking about ADMISSIONS, so the spec must carry BOTH the
        # parent topic and the specific sub-topic. This is data about the
        # topic tree -- not a per-category answer branch.
        if topic == "EVENTS":
            intent = intent or "EVENT"
        admission_subtopic = cls.select_admission_subtopic(raw)
        if admission_subtopic:
            # The parent topic is authoritative whenever one of its children
            # is requested. This also handles "eligibility criteria for BCA"
            # where the word admission is omitted but the degree makes the
            # admissions context explicit. Preserve the explicit subtopic even
            # when an older alias already populated requested_field.
            topic = "ADMISSION"
            subtopic, field = admission_subtopic, admission_subtopic
        if subtopic == "DOCUMENTS":
            subtopic = "REQUIRED_DOCUMENTS"
            field = "REQUIRED_DOCUMENTS"
        year_match = re.search(r"20\d{2}\s*[-/]\s*\d{2,4}", raw)
        keywords = [w for w in re.findall(r"[a-z0-9]+", raw) if len(w) > 1]
        synonyms = sorted({syn for word in keywords for syn in cls.SYNONYMS.get(word, [])})
        entity = (entities["subjects"] or entities["facilities"] or entities["faculty"] or [None])[0]
        return QuerySpec(
            college_id=college_id, intent=intent, category=topic, topic=topic,
            program=program, entity=entity,
            requested_field=field,
            academic_year=year_match.group(0).replace(" ", "") if year_match else None,
            confidence=None,
            raw_question=text or "",
            programs=list(entities["programs"]),
            topics=list(entities["topics"]),
            facilities=list(entities["facilities"]),
            subjects=list(entities["subjects"]),
            faculty_names=list(entities["faculty"]),
            semester=entities["semester"],
        )

    @classmethod
    def build_query_spec_from_legacy(
        cls,
        text: str,
        intent_info: Optional[Dict[str, Any]] = None,
        entities: Optional[Dict[str, Any]] = None,
        college_id: Optional[str] = None,
    ) -> QuerySpec:
        """
        P0.1 COMPATIBILITY BOUNDARY (single point).

        Converts the legacy (text, intent_info, entities, college_id) tuple
        into the canonical QuerySpec exactly once, then that legacy shape is
        discarded.  Callers must use the returned spec for every downstream
        decision; nothing may keep both representations alive.

        This exists only so old call sites keep working during the migration.
        It performs NO new interpretation beyond merging the already-computed
        legacy fields onto the spec.
        """
        intent_info = intent_info or {}
        entities = entities or {}
        intent = intent_info.get("intent")
        spec = cls.extract_query_understanding(
            text, college_id=college_id, intent=intent,
        )
        spec.confidence = intent_info.get("confidence")

        # Merge legacy multi-value entity bags onto the spec so no downstream
        # stage ever needs the raw dict again.
        for key, attr in (
            ("programs", "programs"), ("topics", "topics"),
            ("facilities", "facilities"), ("subjects", "subjects"),
            ("faculty", "faculty_names"),
        ):
            legacy_values = list(entities.get(key) or [])
            if not legacy_values:
                continue
            current = list(getattr(spec, attr) or [])
            for value in legacy_values:
                if value not in current:
                    current.append(value)
            setattr(spec, attr, current)

        if entities.get("semester") and not spec.semester:
            spec.semester = entities.get("semester")
        if not spec.topic and spec.topics:
            spec.topic = spec.topics[0]
        if not spec.category and spec.topic:
            spec.category = spec.topic
        if not spec.program and spec.programs:
            spec.program = spec.programs[0]
        if not spec.entity and (spec.subjects or spec.facilities or spec.faculty_names):
            spec.entity = (
                spec.subjects or spec.facilities or spec.faculty_names
            )[0]
        return spec

    @classmethod
    def extract_entities(cls, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        extracted = {
            "programs": [],
            "subjects": [],
            "facilities": [],
            "topics": [],
            "semester": None,
            "faculty": []
        }

        # 1. Match Programs (longest aliases first; standalone pronoun 'it' is never a program)
        for key in sorted(cls.PROGRAMS, key=len, reverse=True):
            val = cls.PROGRAMS[key]
            pattern = rf"\b{re.escape(key)}\b"
            if re.search(pattern, text_lower):
                if val not in extracted["programs"]:
                    extracted["programs"].append(val)

        # 2. Match Subjects
        for key, val in cls.SUBJECTS.items():
            pattern = rf"\b{re.escape(key)}\b"
            if re.search(pattern, text_lower):
                if val not in extracted["subjects"]:
                    extracted["subjects"].append(val)

        # 3. Match Facilities
        for key, val in cls.FACILITIES.items():
            pattern = rf"\b{re.escape(key)}\b"
            if re.search(pattern, text_lower):
                if val not in extracted["facilities"]:
                    extracted["facilities"].append(val)

        # 4. Match Topics
        for key, val in cls.TOPICS.items():
            pattern = rf"\b{re.escape(key)}\b"
            if re.search(pattern, text_lower):
                if val not in extracted["topics"]:
                    extracted["topics"].append(val)

        # 5. Match Semesters: "sem 2", "semester 2", "2nd sem", "bca sem 2 na subjects"
        sem_match = re.search(r"\b(?:sem|semester)\s*([0-9]|1st|2nd|3rd|4th|5th|6th|7th|8th|first|second|third|fourth|fifth|sixth|seventh|eighth)\b", text_lower)
        if not sem_match:
            sem_match = re.search(r"\b([0-9]|1st|2nd|3rd|4th|5th|6th|7th|8th|first|second|third|fourth|fifth|sixth|seventh|eighth|pehelu|biju|triju|chothu)\s*(?:sem|semester)\b", text_lower)
        
        if sem_match:
            term = sem_match.group(1)
            extracted["semester"] = cls.ORDINAL_SEMESTERS.get(term, term)

        # 6. Match Professor / Faculty mentions
        prof_match = re.findall(r"\b(?:prof\.|professor|dr\.|mr\.|mrs\.|ms\.)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\b", text, re.IGNORECASE)
        if prof_match:
            extracted["faculty"].extend(prof_match)

        return extracted

entity_extractor = EntityExtractor()
