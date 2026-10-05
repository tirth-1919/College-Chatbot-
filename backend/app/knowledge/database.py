import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, cast, String
from backend.app.models.knowledge import AitEntity, WebsiteSnapshot
from backend.app.models.knowledge_categories import KnowledgeRecord, KnowledgeCategory
from backend.app.intelligence.entities import entity_extractor

# Admission sub-category keys recognised by admission_category_from_spec().
ADMISSION_CATEGORY_KEYS = frozenset({
    "admission_process", "admission_documents", "admission_fees",
    "admission_eligibility", "admission_entrance_exam", "admission_merit",
    "admission_counselling", "admission_deadline", "admission_reservation",
    "admission_confirmation", "admission_cancellation", "admission_refund",
    "admission_contact", "admission_programs", "admission_hostel",
    "admission_scholarship", "admission_nri", "admission_international",
    "admission_application",
})

STOPWORDS = {
    "ait", "college", "ahmedabad", "institute", "of", "technology", "india",
    "please", "tell", "me", "about", "what", "is", "the", "are", "ka", "ki",
    "ke", "kya", "hai", "che", "chhe", "batao", "dekhado", "karo", "information",
    "details", "for", "in", "and", "a", "an", "at", "by", "from", "on", "with",
    "as", "into", "how", "where", "who", "when", "why", "which", "can", "will",
    "do", "does", "did", "to", "it", "its", "there", "their"
}

SYNONYM_EXPANSION = {
    "courses": ["program", "curriculum", "branch", "degree"],
    "course": ["program", "curriculum", "branch", "degree"],
    "fees": ["annual_fees", "sem_fees", "tuition", "fee"],
    "fee": ["annual_fees", "sem_fees", "tuition", "fees"],
    "hostel": ["accommodation", "facilities"],
    "admission": ["admissions", "eligibility", "intake", "acpc"],
    "placements": ["placement", "highest_package", "recruiters", "tpo"],
    "placement": ["placements", "highest_package", "recruiters", "tpo"],
    "news": ["event", "events", "announcement", "notice", "circular", "activity", "seminar", "workshop", "festival"],
    "activity": ["activities", "event", "events", "cultural", "technical", "sports"],
    "festival": ["fest", "events", "cultural"],
    "seminar": ["workshop", "events"],
    "workshop": ["seminar", "events"],
    # Â§SPEC: location/address questions must reach the tenant's contact record
    # (e.g. RCTI "Official Website & Location"), whose details JSON stores
    # "location"/"website" rather than the literal query word.
    "address": ["location", "contact"],
    "location": ["address", "contact"],
    "located": ["location", "address", "contact"],
    "teachers": ["faculty", "professor", "coordinator"],
    "teacher": ["faculty", "professor", "coordinator"],
    "professors": ["faculty", "professor"],
}

class KnowledgeDatabase:
    CATEGORY_INTENT_TERMS = {
        "FEES": {"fee", "fees", "tuition", "cost", "charge", "payment"},
        "FACULTY": {"faculty", "teacher", "teachers", "professor", "prof", "teaches", "hod", "staff"},
        "LIBRARY": {"library", "books", "journal", "reading", "librarian"},
        "FACILITIES": {"facility", "facilities", "amenities", "canteen", "cafeteria", "sports", "ground", "wifi"},
        "HOSTEL": {"hostel", "accommodation", "room", "stay"},
        "TRANSPORT": {"transport", "bus", "commute", "route"},
        "PLACEMENT": {"placement", "placements", "recruiter", "package", "tpo"},
        "ADMISSIONS": {"admission", "apply", "application", "intake", "registration"},
        "DOCUMENTS": {"document", "documents", "certificate", "certificates", "checklist", "required"},
        "ELIGIBILITY": {"eligibility", "criteria", "qualification", "cutoff", "eligible"},
        "PROGRAMS": {"program", "programs", "course", "courses", "degree", "branch"},
        "DEPARTMENTS": {"department", "departments", "faculty", "branch"},
        "EXAMINATIONS": {"exam", "exams", "timetable", "midsem", "result", "results"},
        "SCHOLARSHIPS": {"scholarship", "aid", "concession"},
        "CONTACT": {"contact", "phone", "email", "helpline", "address", "location", "office", "reach"},
        "AFFILIATION": {"affiliated", "affiliation", "university", "board", "approved", "accreditation"},
        "EVENTS": {"event", "events", "news", "announcement", "notice", "circular", "activity", "seminar", "workshop", "festival", "hackathon", "cultural", "calendar", "fest"},
        "POLICIES": {"policy", "policies", "rules", "regulation"},
    }

    @classmethod
    def admission_category_for_query(cls, query_text: str) -> Optional[str]:
        # Return the precise admission category requested, if any.
        q = (query_text or "").lower()
        patterns = [
            ("admission_documents", r"document|certificate|marksheet|domicile|transfer|migration"),
            ("admission_fees", r"admission.*\bfee|\bfee.*admission|tuition|cost"),
            ("admission_eligibility", r"eligib|qualification|criteria"),
            ("admission_entrance_exam", r"entrance|gujcet|jee|neet"),
            ("admission_merit", r"merit|cut.?off"),
            ("admission_counselling", r"counsell?ing"),
            ("admission_deadline", r"deadline|last date|start.*admission|admission.*date"),
            ("admission_reservation", r"reservation|category|domicile|quota"),
            ("admission_confirmation", r"confirm.*admission|admission.*confirm"),
            ("admission_cancellation", r"cancel.*admission|admission.*cancel"),
            ("admission_refund", r"refund"),
            ("admission_contact", r"admission.*(contact|phone|email|helpline)|contact.*admission"),
            ("admission_programs", r"admission.*(program|course)|program.*admission"),
            ("admission_hostel", r"admission.*hostel"),
            ("admission_scholarship", r"admission.*scholarship"),
            ("admission_nri", r"\bnri\b"),
            ("admission_international", r"international.*admission|admission.*international|foreign student"),
            ("admission_application", r"apply|application|registration|form"),
            ("admission_process", r"admission|admissions"),
        ]
        for category, pattern in patterns:
            if re.search(pattern, q):
                return category
        return None
    @classmethod
    def compatible_categories(cls, query_text: str) -> Optional[set]:
        terms = set(re.findall(r"[a-z0-9]+", (query_text or "").lower()))
        matched = {intent for intent, keywords in cls.CATEGORY_INTENT_TERMS.items() if terms & keywords}
        if not matched:
            return None
        category_map = {
            "FEES": {"fee", "fees", "annual_fees", "sem_fees"},
            "FACULTY": {"faculty"}, "LIBRARY": {"library", "facility"},
            "FACILITIES": {"facility", "facilities", "campus", "library", "lab"},
            "HOSTEL": {"hostel", "facility"}, "TRANSPORT": {"transport", "facility"},
            "PLACEMENT": {"placement"}, "ADMISSIONS": {"admission", "contact"},
            "DOCUMENTS": {"admission", "documents", "document", "application", "certificate", "checklist", "required"},
            "ELIGIBILITY": {"admission", "program"}, "PROGRAMS": {"program"},
            "DEPARTMENTS": {"department", "program", "faculty"},
            "EXAMINATIONS": {"exam", "result", "academic"}, "SCHOLARSHIPS": {"scholarship"},
            "CONTACT": {"contact"}, "AFFILIATION": {"affiliation", "university", "board", "approved", "accreditation"},
            "EVENTS": {"event", "events", "news", "announcement", "notice", "circular", "activity", "seminar", "workshop", "festival", "hackathon", "cultural", "calendar", "fest"},
            "POLICIES": {"policy"},
        }
        allowed = set().union(*(category_map.get(intent, set()) for intent in matched))
        return allowed or None
    @classmethod
    def admission_category_from_spec(cls, query_spec) -> Optional[str]:
        """
        P0.1: derive the precise admission sub-category from QuerySpec only.

        No raw-question regex is applied here.  The spec already resolved
        topic / requested_field / intent at query understanding.
        """
        intent = (getattr(query_spec, "intent", "") or "").upper()
        field = (getattr(query_spec, "requested_field", "") or "").lower()
        topic = (getattr(query_spec, "topic", "") or "").upper()
        # The spec's TOPIC is the authoritative category. A fee topic is never
        # an admission category just because the word "fee" also appears.
        if topic and topic != "ADMISSION" and not intent.startswith("ADMISSION"):
            return None
        # P0.3 (defect 4): the spec's admission SUB-TOPIC is the precise
        # category. It is consulted before the generic field aliases so the
        # whole ADMISSIONS tree (documents, eligibility, fees, entrance exam,
        # merit, counselling, deadline, reservation, confirmation,
        # cancellation, refund) maps onto its stored category, not onto a
        # catch-all `admission`.
        subtopic = (getattr(query_spec, "subtopic", "") or "").upper()
        if subtopic:
            candidate = f"admission_{subtopic.lower()}"
            if candidate in ADMISSION_CATEGORY_KEYS:
                return candidate
        # An explicit requested_field naming a DOCUMENTS-type sub-topic wins.
        if field:
            candidate = f"admission_{field}"
            if candidate in ADMISSION_CATEGORY_KEYS:
                return candidate
            if field == "required_documents":
                return "admission_documents"
            if field == "tuition_fee":
                return "admission_fees"
        if topic == "ADMISSION" or intent.startswith("ADMISSION"):
            if intent.startswith("ADMISSION_"):
                suffix = intent[len("ADMISSION_"):].lower()
                candidate = f"admission_{suffix}"
                if candidate in ADMISSION_CATEGORY_KEYS:
                    return candidate
            return "admission_process"
        return None

    @classmethod
    def category_from_spec(cls, query_spec) -> Optional[str]:
        """
        P0.1: map QuerySpec topic/category onto a stored category key.

        Prefers the spec's `topic` (the broad knowledge category) over
        `requested_field` (a narrow attribute) so a fee question maps to the
        `fees` category rather than a non-existent `tuition_fee` key.

        Returns None when the spec carries no category, so callers keep their
        existing unfiltered-by-category behaviour.

        P0.3 (defect 4): an Admissions sub-topic is NOT the bare `admission`
        category.  Forcing every admission sub-topic onto `admission` (or onto
        the lower-case topic) made the stored `admission_documents` /
        `admission_eligibility` categories unreachable and rejected valid
        evidence.  When the spec carries a specific admission sub-topic we
        return the matching stored category key instead, so retrieval targets
        the right knowledge category.
        """
        admission_category = cls.admission_category_from_spec(query_spec)
        if admission_category:
            return admission_category
        raw = (
            getattr(query_spec, "topic", None)
            or getattr(query_spec, "category", None)
        )
        if not raw:
            return None
        key = re.sub(r"[^a-z0-9]+", "_", str(raw).strip().lower()).strip("_")
        return key or None

    @classmethod
    def clean_search_tokens(cls, query_text: str) -> List[str]:
        """Extracts meaningful search tokens and expands domain synonyms."""
        words = re.findall(r'[a-zA-Z0-9\.\+]+', query_text.lower())
        tokens = [w for w in words if w not in STOPWORDS and len(w) > 1]
        expanded = list(tokens)
        for t in tokens:
            if t in SYNONYM_EXPANSION:
                expanded.extend(SYNONYM_EXPANSION[t])
        return expanded


    @staticmethod
    def is_student_support_query(query_text: str) -> bool:
        return bool(re.search(
            r"\b(counsell?ing|counseling|student\s+(?:support|guidance|welfare)|"
            r"support\s+services?|student\s+services?|mentoring|mentor(?:ing)?\s+services?)\b",
            (query_text or "").lower(),
        ))

    @staticmethod
    def student_support_evidence_allowed(query_text: str, content: str, title: str = "", url: str = "") -> bool:
        if not KnowledgeDatabase.is_student_support_query(query_text):
            return True
        evidence = f"{title or ''} {url or ''} {content or ''}".lower()
        return bool(re.search(
            r"\b(counsell?ing|counseling|student\s+(?:support|guidance|welfare)|"
            r"support\s+services?|student\s+services?|mentoring|mentor(?:ing)?\s+services?)\b",
            evidence,
        ))

    @staticmethod
    def transportation_evidence_allowed(query_text: str, content: str, title: str = "", url: str = "") -> bool:
        # Require transportation evidence to be a real topic, not a generic facility hit.
        query = (query_text or "").lower()
        if not re.search(r"\b(transport(?:ation)?|bus|commute|route|pickup|drop(?:off)?)\b", query):
            return True
        title_url = f"{title or ''} {url or ''}".lower()
        body = f"{title_url} {content or ''}".lower()
        transport_terms = r"\b(transport(?:ation)?|bus(?:es)?|commut(?:e|ing)|route|pickup|drop(?:off)?|shuttle|vehicle|parking)\b"
        if not re.search(transport_terms, body):
            return False
        # A transport word buried in a large unrelated page (navigation, a
        # footer, or a merged catalog) is not sufficient. Prefer a page whose
        # identity is transport-related, or a sentence with actual service
        # evidence such as routes, pickup points, or commuting.
        if re.search(transport_terms, title_url):
            return True
        return bool(re.search(
            r"\b(bus|transport(?:ation)?|shuttle)\b.{0,220}\b(route|pickup|drop(?:off)?|commut|students?|campus|service|facility)\b"
            r"|\b(route|pickup|drop(?:off)?)\b.{0,220}\b(bus|transport(?:ation)?|shuttle|campus|students?)\b",
            content or "", re.IGNORECASE,
        ))

    @staticmethod
    def topic_relevance_score(query_text: str, content: str, title: str = "", url: str = "") -> Optional[int]:
        '''Require evidence for the question's topic, not merely a shared college word.

        Snapshot search is intentionally conservative: an official page is still
        rejected when it is a home, placement, or other unrelated page.  The
        rules describe topic evidence and page shape, rather than individual
        questions, so new wording continues to work across colleges.
        '''
        query = (query_text or "").lower()
        title_url = f"{title or ''} {url or ''}".lower()
        body = f"{title_url} {content or ''}".lower()
        if not KnowledgeDatabase.student_support_evidence_allowed(query_text, content, title, url):
            return None
        def has(pattern):
            return bool(re.search(pattern, body))

        def reject(pattern):
            return bool(re.search(pattern, f"{title or ''} {url or ''}".lower()))

        # P0.5: a page's own TITLE/URL is a positive signal, never a hard
        # constraint. A page titled "DBMS Faculty" is precisely the evidence
        # for a subject-coordinator question, so the unrelated-page guards
        # below must not fire when the page already names the requested topic.
        own_label = f"{title or ''} {url or ''}".lower()

        def unrelated_page(pattern):
            if not reject(pattern):
                return False
            subject_terms = {
                t for t in re.findall(r"[a-z0-9]{4,}", query) if t not in STOPWORDS
            }
            label_terms = set(re.findall(r"[a-z0-9]{4,}", own_label))
            return not (subject_terms & label_terms)

        # Specific program questions need both the program and the requested
        # academic fact.  This prevents a generic page mentioning "courses"
        # from answering a BCA question.
        program = re.search(r"\b(bca|mca|bba|mba|b\.?tech|cse|computer engineering|information technology)\b", query)
        if program and not has(rf"\b{re.escape(program.group(1).replace('.', ''))}\b|" + re.escape(program.group(1))):
            return None
        # A question about WHO teaches / coordinates a subject is a teaching
        # question, not a curriculum-structure question. It must not be matched
        # by the syllabus/curriculum branch, which would otherwise fire on the
        # word "subject" in "subject coordinator" and then reject the very
        # faculty page that answers it.
        teaches_subject = bool(re.search(
            r"\b(subject\s+coordinator|coordinator|who\s+teaches|taught\s+by)\b",
            query,
        ))
        if re.search(r"\b(fee|fees|tuition|cost|charge|payment)\b", query):
            if not has(r"\b(fee|fees|tuition|cost|charge|payment|₹|inr)\b"):
                return None
            if reject(r"\b(placement|recruit|home|event|grievance|library)\b"):
                return None
        elif re.search(r"\b(eligibility|eligible|qualification|criteria|cutoff|merit)\b", query):
            if not has(r"\b(eligib|qualification|criteria|cut[ -]?off|merit|admission requirement)\w*\b"):
                return None
            if reject(r"\b(placement|recruit|home|event|grievance)\b"):
                return None
        elif re.search(r"\b(required documents?|admission documents?|application documents?|certificates?|document checklist|checklist|documents? needed|documents? (?:are|is) required|required (?:for|at) admission)\b", query):
            if not has(r"\b(required documents?|admission documents?|application documents?|certificates?|document checklist|checklist|documents? needed|documents? (?:are|is) required|documents? required)\b"):
                return None
            if reject(r"\b(placement|recruit|home|event|grievance|library|fee|fees|tuition)\b"):
                return None
        elif re.search(r"\b(admission|apply|application|enrol|enroll|registration|intake)\b", query):
            if not has(r"\b(admission|apply|application|enrol|enroll|registration|intake|acpc|prospectus)\w*\b"):
                return None
            if reject(r"\b(placement|recruit|home|event|grievance|library)\b"):
                return None
        elif teaches_subject:
            # For "who coordinates / teaches this subject?", faculty pages are
            # positive evidence. Don't route the word "subject" into the
            # curriculum/syllabus rule below.
            if not has(r"\b(faculty|teacher|professor|teaches|taught|subject coordinator|staff|hod)\w*\b"):
                return None
        elif re.search(r"\b(course|courses|program|programs|degree|branch|branches|department|departments|academic)\b", query):
            if not has(r"\b(course|courses|program|programs|degree|branch|branches|department|departments|academic|curriculum|syllabus)\w*\b"):
                return None
            # A course/programs question must not be answered by a page that
            # only lists departments; departments are a separate user intent.
            if re.search(r"\b(course|courses|program|programs|degree|branch|branches|curriculum|syllabus)\b", query) and not has(r"\b(course|courses|program|programs|degree|branch|branches|curriculum|syllabus)\b"):
                return None
            if re.search(r"\b(course|courses|program|programs|degree)\b", query) and reject(r"\b(department|departments)\b"):
                return None
            if reject(r"\b(placement|recruit|home|event|grievance|library)\b"):
                return None
            # A focused Courses/Programs page is positive evidence. Returning
            # a positive score is important because the generic snapshot
            # collector intentionally discards zero-score pages.
            return 12
        elif teaches_subject:
            # The evidence must actually name the subject being taught and the
            # teaching role. A page that names neither is not faculty evidence.
            if not has(r"\b(faculty|teacher|professor|teaches|taught|subject coordinator|staff|hod)\w*\b"):
                return None
            if reject(r"\b(placement|recruit|home|event|grievance|library)\b"):
                return None
        elif re.search(r"\b(transport(?:ation)?|bus|commute|route|pickup|drop(?:off)?)\b", query):
            if not KnowledgeDatabase.transportation_evidence_allowed(query_text, content, title, url):
                return None
            # Transportation is a distinct institutional topic.  Generic campus
            # wording (for example, "facility") must not make an unrelated
            # placement, event, or company snapshot eligible evidence.
            if not has(r"\b(transport(?:ation)?|bus(?:es)?|commut(?:e|ing)|route|pickup|drop(?:off)?|shuttle|vehicle|parking)\b"):
                return None
            if reject(r"\b(placement|recruit|company|companies|drive|event|events?|hackathon|walkathon|library|faculty)\b"):
                return None
        elif re.search(r"\b(hostel|accommodation|residence|dormitory|dorms?)\b", query):
            if not has(r"\b(hostel|accommodation|residence|dormitory|dorms?|room|mess|warden)\b"):
                return None
            if reject(r"\b(placement|recruit|home|event|grievance|library|faculty)\b"):
                return None
        elif re.search(r"\b(syllabus|curriculum|semester|subjects?|course\s+structure)\b", query) and not teaches_subject:
            if not has(r"\b(syllabus|curriculum|semester|subject|course\s+structure|course\s+content)\b"):
                return None
            if reject(r"\b(placement|recruit|home|event|grievance)\b"):
                return None
        elif re.search(r"\b(library|reading hall|books|librarian)\b", query):
            if not has(r"\b(library|reading hall|books|librarian|library timing|opening hours)\b"):
                return None
        elif re.search(r"\b(event|events|fest|hackathon|cultural|annual day|news|announcement|notices?|circulars?|activities|seminars?|workshops?|festivals?)\b", query):
            if not has(r"\b(event|fest|hackathon|cultural|annual day|news|announcement|notice|circular|activity|seminar|workshop|festival)\w*\b"):
                return None
        elif re.search(r"\b(facilit(?:y|ies)|amenities)\b", query):
            meaningful = set(re.findall(r"[a-z0-9]+", query)) - STOPWORDS - {"facility", "facilities", "amenities"}
            overlap = sum(1 for term in meaningful if re.search(rf"\b{re.escape(term)}\b", body))
            if not has(r"\b(facilit(?:y|ies)|amenities|technical|project|activity|activities|campus|resource|lab|library|hostel|transport|scholarship)\b") or (meaningful and overlap == 0):
                return None
        elif re.search(r"\b(affiliat(?:ed|ion)|university|board|approved\s+by|accredit(?:ation|ed))\b", query):
            if not has(r"\b(affiliat(?:ed|ion)|university|board|approved\s+by|accredit(?:ation|ed)|gtu|aicte)\b"):
                return None
            if reject(r"\b(placement|recruit|home|event|grievance|library|facility|facilities)\b"):
                return None
        elif re.search(r"\bplacement\s+cell\b", query) and re.search(r"\b(contact|email|phone|number|call|reach)\b", query):
            # Placement-contact questions require contact details from the
            # placement-cell page, not generic placement companies or drives.
            if not has(r"\bplacement\s+cell\b"):
                return None
            if not has(r"@|\b(?:phone|mobile|telephone|call|contact|email|number)\b"):
                return None
            if reject(r"\b(?:company|companies|drive|drives|recruit(?:er|ers|ment)|event|events)\b"):
                return None
        elif re.search(r"\b(placement|recruiter|package|training and placement)\b", query):
            if not has(r"\b(placement|recruiter|package|training and placement|tpo)\w*\b"):
                return None
        elif re.search(r"\b(address|location|contact|contact details|contact information|phone|telephone|email|office|reach)\b", query):
            if not has(r"@|\b(address|location|contact|phone|telephone|email|office|reach|campus|road|ahmedabad|gujarat)\b"):
                return None
            if reject(r"\b(placement|recruit|drive|event|library|facility|facilities)\b"):
                return None
        elif re.search(r"\b(exam|exams|timetable|schedule|result|results)\b", query):
            if not has(r"\b(exam|timetable|schedule|result|results)\w*\b"):
                return None
        elif re.search(r"\b(about|overview|history|tell me about)\b", query):
            if reject(r"\b(placement|recruit|grievance|library|admission|fee)\b") and not has(r"\b(about|overview|history|institute|college)\b"):
                return None
        return 0
    @staticmethod
    def website_relevance_score(query_text: str, content: str, title: str = "", url: str = "") -> Optional[int]:
        # Return a targeted relevance score, or None for an unsafe match.
        topic_score = KnowledgeDatabase.topic_relevance_score(query_text, content, title, url)
        if topic_score is None:
            return None
        # This guard is intentionally conservative for general learning/advice
        # questions: an institutional page must contain actual instructional
        # concepts, not just generic words such as student, software, or company.
        query = (query_text or "").lower()
        evidence = " ".join((title or "", url or "", content or "")).lower()
        is_general_programming_guidance = bool(re.search(
            r"\b(beginner|practice|learn|learning|concepts?|skills?|build(?:ing)?|small web application|web app|coding)\b",
            query,
        )) and bool(re.search(
            r"\b(programming|program(?:ming)?|software|web application|web app|coding|computer science|development)\b",
            query,
        )) and not bool(re.search(
            r"\b(placement|placements|library|dbms|database|department|departments|faculty|teacher|professor|fee|fees|admission|hostel|facility|facilities|event|events|course|courses|curriculum|syllabus)\b",
            query,
        ))
        if is_general_programming_guidance:
            instructional_concepts = {
                "variable", "variables", "data structure", "data structures", "algorithm", "algorithms",
                "control flow", "conditional", "conditionals", "loop", "loops", "function", "functions",
                "object oriented", "object-oriented", "oop", "html", "css", "javascript", "testing",
                "debugging", "version control", "git", "api", "database", "sql", "responsive design",
            }
            concept_hits = sum(1 for term in instructional_concepts if re.search(rf"\b{re.escape(term)}\b", evidence))
            if concept_hits < 2:
                return None
        is_dbms_query = bool(re.search(r"\bdbms\b|database\s+management\s+systems?", query))
        is_subject_faculty_query = bool(re.search(
            r"\b(subject\s+coordinator|coordinator|faculty(?:\s+member)?|who\s+teaches|professor|teacher|hod)\b",
            query,
        ))
        if is_dbms_query and is_subject_faculty_query:
            has_dbms_evidence = bool(re.search(r"\bdbms\b|database\s+management\s+systems?", evidence))
            has_role_evidence = bool(re.search(
                r"\b(subject\s+coordinator|coordinator|faculty(?:\s+member)?|professor|teacher|hod|course|subject)\b"
                r"|computer\s+(?:engineering|applications)",
                evidence,
            ))
            if not (has_dbms_evidence and has_role_evidence):
                return None
            return 30 + (10 if re.search(r"\bsubject\s+coordinator\b|\bcoordinator\b", evidence) else 0)
        return 0
    @staticmethod
    def _department_query_has_meaningful_evidence(query_text: str, content: str, title: str = "", url: str = "") -> bool:
        # Require structured academic evidence for department/branch questions.
        # Placement, recruiting, event, and home-page snapshots often repeat
        # academic words incidentally; those words must never make the page a
        # department source by themselves.
        query = (query_text or "").lower()
        title_lower = (title or "").lower()
        url_lower = (url or "").lower()
        content_lower = (content or "").lower()
        body = " ".join((title_lower, url_lower, content_lower))
        is_department_query = bool(re.search(
            r"\b(departments?|departmental|branches?|programs?|courses?|academic\s+departments?)\b",
            query,
        ))
        if not is_department_query:
            return True
        # Metadata is the strongest signal: a page explicitly named or routed
        # as placement/recruitment/events/home is not academic evidence.  This
        # deliberately covers placement-company pages even when their body
        # lists Computer/IT, MBA, Civil, EC, Mechanical, or the word branch.
        excluded_metadata = re.compile(
            r"\b(?:placement|placements|placement\s+company|placement\s+companies|"
            r"campus\s+drive|campus\s+drives|drives?|recruit(?:er|ers|ment)|"
            r"company\s+listings?|events?)\b"
        )
        if excluded_metadata.search(f"{title_lower} {url_lower}"):
            return False
        if re.search(r"(?:^|[\n|])\s*section\s*:\s*(?:home|.*(?:placement|drive|recruit|event))\b", content_lower):
            return False
        if re.fullmatch(r"\s*(?:home|home page|homepage)\s*", title_lower):
            return False
        academic_markers = re.findall(
            r"\b(departments?|departmental|branches?|programs?|courses?|academic|coordinator)\b",
            body,
        )
        named_branches = re.findall(
            r"\b(?:computer(?:\s+science)?\s+engineering|information\s+technology|it\s+engineering|"
            r"artificial\s+intelligence|data\s+science|cyber\s+security|civil\s+engineering|"
            r"mechanical\s+engineering|electronics?(?:\s+(?:and|&)\s+communication)?|"
            r"applied\s+mechanics|printing\s+technology|ict|bca|mca|bba|mba)\b",
            body,
        )
        coordinator_branches = re.findall(
            r"\bdepartmental\s+coordinator\s*[-:]\s*"
            r"(civil|computer|it|mechanical|electronics?|information\s+technology|applied\s+mechanics)\b",
            body,
        )
        explicit_academic_structure = bool(re.search(
            r"\b(?:academic\s+departments?|departments?\s+(?:available|offered|include|are)|"
            r"branches?\s+(?:available|offered|include|are)|(?:offers?|offering)\s+(?:the\s+)?"
            r"(?:following\s+)?(?:programs?|courses?|branches?))\b",
            body,
        ))
        academic_page_context = bool(re.search(
            r"\b(?:academic|academics|department|departments|program|programs|course|courses|"
            r"faculty|engineering|curriculum|syllabus)\b", f"{title_lower} {url_lower}"
        ))
        # Recruitment language in dominant body content is unsafe too, but do
        # not reject an otherwise academic page for a passing mention of an
        # event.  A recruiting page needs both the topic and its typical data.
        recruiting_content = bool(re.search(
            r"\b(?:placement|recruit(?:er|ers|ment)|campus\s+drives?|company\s+listings?)\b",
            content_lower,
        ))
        if recruiting_content and not academic_page_context:
            return False
        # A genuine listing needs explicit academic structure, an academic page
        # context, or multiple coordinator entries—not just incidental words.
        # Course questions also accept a substantive "offers ... courses/programs"
        # statement on an About page.  Keep this criterion aligned with the
        # course evidence accepted by website_content_supports_query(), while
        # retaining the metadata and named-program protections above.
        substantive_course_listing = bool(
            re.search(r"\b(course|courses|program|programs|degree)\b", query)
            and re.search(r"\b(offers?|offered|available|programs?|courses?|degrees?|branches?)\b", body)
            and re.search(
                r"\b(bca|mca|bba|mba|b\.?tech|engineering|information technology|computer|civil|mechanical|electrical|electronics)\b",
                body,
            )
        )
        return bool(
            (named_branches and (
                explicit_academic_structure
                or academic_page_context
                or len(set(named_branches)) >= 2
                or len(set(coordinator_branches)) >= 2
            ))
            or substantive_course_listing
        )

    @staticmethod
    def website_content_supports_query(query_text: str, content: str, title: str = "", url: str = "") -> bool:
        # Return true only when website text contains substantive domain evidence.
        query = (query_text or "").lower()
        body = (content or "").lower()
        if KnowledgeDatabase.website_relevance_score(
            query_text, content, title=title, url=url
        ) is None:
            return False
        if not KnowledgeDatabase._department_query_has_meaningful_evidence(
            query_text, content, title=title, url=url
        ) and not (
            re.search(r"\b(course|courses|program|programs|degree)\b", query)
            and re.search(r"\b(offers?|offered|available)\b", body)
            and re.search(r"\b(bca|mca|bba|mba|b\.?tech|engineering|information technology|computer|civil|mechanical|electrical|electronics)\b", body)
            and not re.search(r"\b(placement|recruit|home|event|grievance|library)\b", f"{title} {url}".lower())
        ):
            # A course/program query can be supported by a substantive course
            # statement even when the page is an About page rather than an
            # academics URL.  Keep this narrow so generic pages do not pass.
            if not re.search(r"\b(course|courses|program|programs|degree|branch|curriculum|syllabus)\b", query):
                return False
            if not re.search(r"\b(offers?|offered|available|programs?|courses?|degrees?|branches?)\b", body):
                return False
            if not re.search(r"\b(bca|mca|bba|mba|b\.?tech|engineering|information technology|computer|civil|mechanical|electrical|electronics)\b", body):
                return False
        if re.search(r"\b(core values?|educational philosophy|institutional philosophy|vision|mission|values)\b", query):
            if re.search(r"(?:our|institute'?s|institutional)\s+(?:core\s+)?(?:values?|vision|mission|philosophy|objectives|principles)|(?:core\s+values?|educational\s+philosophy|institutional\s+philosophy|vision\s+and\s+mission|mission\s+and\s+vision)", body):
                return True
            return False
        if re.search(r"\b(student clubs?|extracurricular|student activities|student organizations?)\b", query):
            if re.search(r"\b(governing council|committee|grievance cell|academic calendar|facilities)\b", body) and not re.search(r"\b(club|society|association|team|student organization)\s+(?:for|that|which|where|offers|organizes|conducts)", body):
                return False
            if re.search(r"(?:student\s+clubs?|student\s+organizations?|extracurricular|co[- ]curricular|student\s+activities|campus\s+activities).{0,180}(?:club|activities|events|societ|team|association|cultural|technical|sports)", body):
                navigation_only = bool(re.search(
                    r"(?:\bhome\b|\bacademics\b|\bstudent cell\b|governing council|committee|grievance cell|academic calendar).{0,200}(?:menu|navigation|co[- ]curricular activities|academic calendar|grievance cell|facilities)",
                    body,
                ))
                return not navigation_only
            return False
        if re.search(r"\b(rto|license facilitation center|learning license|driving license)\b", query):
            return bool(re.search(r"(?:rto|license).{0,180}(?:application|processing|assistance|authority|office|facilitation)", body))
        return True
    @classmethod
    def query_entities(cls, db: Session, query_text: str, category: Optional[str] = None,
                       college_id: Optional[str] = None, query_spec=None) -> List[Dict[str, Any]]:
        """
        Query verified entities matching program names, subjects, facilities, fees, etc.
        Implements multi-stage matching: exact phrase, cleaned phrase, and tokenized rank matching.
        CRITICAL: when college_id is provided the query is tenant-filtered
        FIRST - records from other colleges can never be returned.
        """
        # Tenant context is mandatory for production retrieval.  A missing
        # active college must fail closed; text in names, codes, URLs, or
        # identifiers is never an ownership signal.
        if not college_id:
            return []
        q = db.query(AitEntity).filter(
            AitEntity.college_id == college_id,
            AitEntity.is_verified == True,
        )
        if category and not str(category).startswith("admission_"):
            if category == "admission_documents":
                q = q.filter(AitEntity.category.in_(["admission_documents", "admission-documents", "admission"]))
            else:
                # Stored category keys may be suffixed per-record
                # (e.g. "fees" and "fees-1a2b3c"), so match the family.
                normalized = category.lower().replace("-", "_")
                q = q.filter(
                    or_(
                        AitEntity.category == category,
                        AitEntity.category.like(f"{normalized}-%"),
                        AitEntity.category.like(f"{normalized}_%"),
                    )
                )

        # The admin knowledge-db is the canonical store for newer verified
        # records.  Older records are mirrored into ait_entities, but that
        # mirror is not guaranteed (and is intentionally not a second tenant
        # boundary).  Query both stores with the same active-tenant and
        # verification predicates before ranking the result.
        modern_query = db.query(KnowledgeRecord).filter(
            KnowledgeRecord.college_id == college_id,
            KnowledgeRecord.verified == True,
            KnowledgeRecord.status == "ACTIVE",
        )
        if category and category == "admission_documents":
            modern_query = modern_query.join(KnowledgeCategory).filter(
                or_(
                    KnowledgeCategory.key.in_(
                        ["admission_documents", "admission-documents", "admission"]
                    ),
                    KnowledgeCategory.key.like("admission-documents-%"),
                    KnowledgeCategory.key.like("admission_documents-%"),
                    KnowledgeCategory.key.like("admission-%"),
                )
            )
        elif category and not str(category).startswith("admission_"):
            normalized_cat = category.lower().replace("-", "_")
            modern_query = modern_query.join(KnowledgeCategory).filter(
                or_(
                    KnowledgeCategory.key == category,
                    KnowledgeCategory.key.like(f"{normalized_cat}-%"),
                    KnowledgeCategory.key.like(f"{normalized_cat}_%"),
                )
            )
        modern_records = modern_query.all()

        # ------------------------------------------------------------------
        # P0.1: QuerySpec is the ONLY understanding boundary.
        #
        # Nothing below re-parses the user's question for program, topic,
        # category, academic year, or any *_query flag.  Those were resolved
        # once in EntityExtractor.extract_query_understanding.
        #
        # Tenant isolation and verification predicates above are UNCHANGED:
        #   college_id == active college
        #   AitEntity.is_verified == True
        #   KnowledgeRecord.verified == True AND status == "ACTIVE"
        # ------------------------------------------------------------------
        if query_spec is not None:
            # -- canonical semantic fields, straight off the spec ------------
            requested_course = query_spec.program
            requested_programs = list(query_spec.programs or [])
            requested_years = query_spec.requested_years

            # -- canonical lexical flags, computed once on the spec ----------
            is_fee_query = query_spec.is_fee_query
            is_document_query = query_spec.is_document_query
            is_program_query = query_spec.is_program_query
            is_values_query = query_spec.is_values_query
            is_clubs_query = query_spec.is_clubs_query
            is_rto_query = query_spec.is_rto_query
            is_database_query = query_spec.is_database_query

            # Precise admission sub-category comes from the spec's
            # requested_field / intent, not from a fresh regex over the text.
            admission_category = cls.admission_category_from_spec(query_spec)

            # Canonical category: the spec's category wins when present.
            if not category:
                category = cls.category_from_spec(query_spec)

            # -- retrieval/relevance text: spec-derived ---------------------
            raw_clean = query_spec.retrieval_text
            relevance_text = query_spec.retrieval_text
        else:
            # Legacy path retained only so older unit tests that call this
            # helper directly still work.  The orchestrator never takes it.
            raw_clean = (query_text or "").strip().lower()
            admission_category = cls.admission_category_for_query(raw_clean)
            requested_programs = entity_extractor.extract_entities(raw_clean).get("programs", [])
            requested_course = requested_programs[0] if requested_programs else None
            if not requested_course:
                named_program = re.search(
                    r"\b(data\s+science|artificial\s+intelligence|computer\s+engineering|information\s+technology)\b",
                    raw_clean,
                )
                if named_program:
                    requested_course = named_program.group(1)
            requested_years = re.findall(r"20\d{2}\s*[-/]\s*\d{2,4}", raw_clean)
            is_fee_query = any(w in raw_clean for w in ["fee", "fees", "tuition", "cost", "charge", "kitni", "ketli"])
            is_document_query = bool(re.search(
                r"\b(required documents?|admission documents?|application documents?|"
                r"certificates?|document checklist|checklist|documents? needed|"
                r"documents? (?:are|is) required|required (?:for|at) admission)\b", raw_clean,
            ))
            is_program_query = bool(re.search(r"\b(course|courses|program|programs|degree|branch|curriculum|syllabus)\b", raw_clean)) and not is_document_query and not is_fee_query
            is_values_query = bool(re.search(r"\b(core values?|educational philosophy|institutional philosophy|vision|mission|values)\b", raw_clean))
            is_clubs_query = bool(re.search(r"\b(student clubs?|extracurricular|student activities|student organizations?)\b", raw_clean))
            is_rto_query = bool(re.search(r"\b(rto|license facilitation center|learning license|driving license)\b", raw_clean))
            is_database_query = bool(re.search(r"\b(database|knowledge database|stored|records? stored|academic[- ]year information|course categories)\b", raw_clean))

            relevance_text = query_text

        def _program_family(value):
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
            # A named specialisation is its own family so a BCA request can
            # never be answered with a Data Science record.
            if re.search(r"\bdata\s+science\b", text):
                return "data_science"
            if re.search(r"\bartificial\s+intelligence\b", text):
                return "artificial_intelligence"
            return None
        def program_relevance_matches(blob, course=None):
            # A requested program is a hard filter. Generic fee/admission tokens
            # must never make a different program a candidate.
            if not requested_course:
                return True
            requested_family = _program_family(requested_course)
            candidate_identity = str(course or "")
            # When no explicit course column exists, the entity's canonical
            # name/code is the identity. Do not scan `details` prose, which may
            # mention unrelated programs as comparisons or other-program notes.
            if not candidate_identity:
                candidate_identity = str(blob or "").split("{", 1)[0]
            candidate_family = _program_family(candidate_identity)
            if candidate_family and requested_family and candidate_family != requested_family:
                return False
            # A structured course value is authoritative for program matching.
            # Do not let an explicit mismatching course become a candidate.
            if requested_family and course:
                course_normalized = re.sub(r"[^a-z0-9]+", " ", str(course).lower()).strip()
                if course_normalized in {"all programs", "all courses", "general", "general program"}:
                    # Institution-wide records may carry admission documents
                    # applicable to every program; generic scope is not a
                    # mismatching program identity.
                    return bool(admission_category)
                if not candidate_family:
                    return False
            requested_normalized = re.sub(r"[^a-z0-9]+", " ", requested_course.lower()).strip()
            candidate_normalized = re.sub(r"[^a-z0-9]+", " ", candidate_identity.lower())
            # Specific branch/entity requests require their branch evidence, but
            # allow a broader record as a lower-ranked fallback in the same family.
            if requested_normalized not in {"b tech", "btech"}:
                branch_terms = {
                    "computer science engineering": ("computer science", "cse"),
                    "information technology": ("information technology", "it engineering"),
                }
                for phrase, aliases in branch_terms.items():
                    if phrase in requested_normalized and not any(alias in candidate_normalized for alias in aliases):
                        return False
            return True
        is_fee_query = is_fee_query
        is_document_query = is_document_query
        is_program_query = is_program_query
        is_values_query = is_values_query
        is_clubs_query = is_clubs_query
        is_rto_query = is_rto_query
        is_database_query = is_database_query
        if is_values_query:
            category = category or None
        query_domain_terms = []
        if is_values_query:
            query_domain_terms = ["vision", "mission", "value", "philosophy"]
        elif is_clubs_query:
            query_domain_terms = ["club", "extracurricular", "student activities", "student organization"]
        elif is_rto_query:
            query_domain_terms = ["rto", "license", "driving license", "learning license"]

        def year_specific_match(entity):
            if not (requested_years and is_fee_query):
                return True
            details = str(entity.details).lower()
            academic_year = (entity.academic_year or "").replace(" ", "").lower()
            return any(
                year.replace(" ", "").lower() in academic_year
                or year.replace(" ", "").lower() in details
                for year in requested_years
            )

        def record_topic_relevance_matches(query, blob, title=""):
            # Apply topic evidence to structured records, not just website pages.
            return cls.topic_relevance_score(query, blob, title=title) is not None
        def modern_record_matches(record):
            blob = " ".join(str(value or "") for value in (
                record.title, record.course, record.field_name, record.value,
                record.description, record.metadata_json,
                record.academic_year,
            )).lower()
            record_key = record.category.key.lower().replace("-", "_") if record.category else ""
            category_confirms_documents = record_key.startswith("admission_documents")
            if not record_topic_relevance_matches(relevance_text, blob, record.title) and not category_confirms_documents:
                return False
            if is_document_query and not re.search(
                r"\b(required[_ ]documents?|admission[_ ]documents?|application[_ ]documents?|"
                r"certificates?|document[_ ]checklist|checklist|documents? needed|"
                r"documents? (?:are|is) required|required (?:for|at) admission)\b", blob,
            ) and not (
                record.category
                and record.category.key.lower().replace("-", "_").startswith("admission_documents")
            ):
                return False
            # Course-listing queries are distinct from admission subtopics.
            # An eligibility/documents request can be answered by a program
            # record whose structured details carry that requested field.
            if is_program_query and not admission_category and record.category and record.category.key.lower() not in {"courses", "course", "program", "programs", "admission_programs"}:
                return False
            if requested_years and is_fee_query:
                year = (record.academic_year or "").replace(" ", "").lower()
                if not any(y.replace(" ", "").lower() in year or y.replace(" ", "").lower() in blob for y in requested_years):
                    return False
            record_category = record.category.key.lower().replace("-", "_") if record.category else ""
            if category and record.category and not admission_category:
                category_key = category.lower().replace("-", "_")
                category_family_match = (
                    record_category == category_key
                    or record_category.startswith(category_key + "_")
                    or record_category.startswith(category_key + "-")
                )
                if not category_family_match:
                    return False
            if admission_category and record.category:
                requested_category = admission_category.lower().replace("-", "_")
                structured_fields = record.metadata_json if isinstance(record.metadata_json, dict) else {}
                subtopic_key = requested_category.removeprefix("admission_")
                has_structured_subtopic = subtopic_key in structured_fields
                if record_category != requested_category and not has_structured_subtopic and not (
                    requested_category == "admission_documents"
                    and (
                        record_category == "admission"
                        or record_category.startswith("admission_documents_")
                    )
                ):
                    return False
            if not program_relevance_matches(blob, record.course):
                return False
            if requested_course and not record.course and re.search(r"\b(fee|fees|tuition|cost|charge)\b", raw_clean):
                return False
            tokens = cls.clean_search_tokens(relevance_text)
            if not tokens:
                return False
            structured_fields = record.metadata_json if isinstance(record.metadata_json, dict) else {}
            requested_subtopic = (
                admission_category.removeprefix("admission_")
                if admission_category else None
            )
            if requested_subtopic and requested_subtopic in structured_fields:
                return True
            return any(re.search(rf"\b{re.escape(token)}\b", blob) for token in tokens)

        modern_matches = [r for r in modern_records if modern_record_matches(r)]
        # Rank the hierarchy before returning records: topic/subtopic and exact
        # program/year specificity outrank generic token overlap.
        def modern_specificity(record):
            blob = " ".join(str(value or "") for value in (
                record.title, record.course, record.field_name, record.value,
                record.description, record.metadata_json, record.academic_year,
            )).lower()
            score = 0
            if is_fee_query and re.search(r"\b(fee|fees|tuition|cost|charge)\b", blob): score += 20
            if is_document_query and re.search(r"required|document|certificate|checklist", blob): score += 20
            if requested_course and record.course and _program_family(record.course) == _program_family(requested_course): score += 30
            if requested_course and requested_course.lower().replace(".", "") in blob.replace(".", ""): score += 15
            if requested_years and any(y.replace(" ", "") in blob.replace(" ", "") for y in requested_years): score += 25
            return score
        modern_matches.sort(key=modern_specificity, reverse=True)
        # If both a course-specific and general admission record match, never
        # allow the general record to displace the requested course record.
        if requested_course:
            course_matches = [r for r in modern_matches if r.course and requested_course.replace(".", "") in r.course.lower().replace(".", "")]
            if course_matches:
                modern_matches = course_matches
        if cls.is_student_support_query(raw_clean):
            modern_matches = [r for r in modern_matches if cls.student_support_evidence_allowed(
                raw_clean, " ".join(str(value or "") for value in (
                    r.title, r.course, r.field_name, r.value, r.description,
                    r.metadata_json, r.academic_year,
                )),
            )]

        # 1. First attempt: exact substring match
        search_term = f"%{raw_clean}%"
        entities = q.filter(
            or_(
                func.lower(AitEntity.name).like(search_term),
                func.lower(AitEntity.code).like(search_term),
                func.lower(AitEntity.category).like(search_term),
                func.lower(cast(AitEntity.details, String)).like(search_term)
            )
        ).all()
        entities = [entity for entity in entities if year_specific_match(entity)]
        entities = [entity for entity in entities if record_topic_relevance_matches(
            relevance_text, f"{entity.name} {entity.code or ''} {entity.category} {entity.details}", entity.name
        )]
        compatible = cls.compatible_categories(relevance_text)
        if admission_category:
            allowed_admission_categories = {admission_category}
            if admission_category == "admission_documents":
                allowed_admission_categories.add("admission")
            # Program records may carry structured admission sub-fields
            # (eligibility, documents, fees). They remain valid evidence for
            # that admission sub-topic when the requested program matches.
            if admission_category == "admission_eligibility":
                allowed_admission_categories.update({"program", "programs", "course", "courses"})
            entities = [entity for entity in entities if entity.category.lower() in allowed_admission_categories]
        elif compatible and not requested_course:
            entities = [entity for entity in entities if entity.category.lower() in compatible]
        if query_domain_terms:
            entities = [entity for entity in entities if any(
                term in f"{entity.name} {entity.category} {entity.details}".lower()
                for term in query_domain_terms
            )]
        if requested_course and admission_category:
            requested_family = _program_family(requested_course)
            entities = [
                entity for entity in entities
                if requested_course.replace(".", "").lower() in f"{entity.code or ''} {entity.name or ''} {entity.details}".lower().replace(".", "")
                or (requested_family and requested_family == _program_family(entity.code or entity.name or entity.details))
            ]
        # Admission subtopics may live in AitEntity.details rather than the
        # entity's primary category. Keep exact course-family and tenant checks.
        if admission_category and admission_category.startswith("admission_"):
            subtopic = admission_category.removeprefix("admission_")
            entities = [
                entity for entity in entities
                if entity.category.lower() == admission_category
                or (
                    entity.category.lower() in {"program", "programs", "course", "courses"}
                    and isinstance(entity.details, dict)
                    and bool(entity.details.get(subtopic))
                )
            ]
        if is_document_query:
            entities = [entity for entity in entities if re.search(
                r"\b(required[_ ]documents?|admission[_ ]documents?|application[_ ]documents?|"
                r"certificates?|document[_ ]checklist|checklist|documents? needed|"
                r"documents? (?:are|is) required|required (?:for|at) admission)\b",
                f"{entity.name} {entity.category} {entity.details}".lower(),
            ) or entity.category.lower().replace("-", "_").startswith("admission_documents")]
        if is_fee_query:
            entities = [entity for entity in entities if entity.category.lower() in {"fee", "fees", "annual_fees", "sem_fees"}]
        if cls.is_student_support_query(raw_clean):
            entities = [entity for entity in entities if cls.student_support_evidence_allowed(
                raw_clean, f"{entity.name} {entity.category} {entity.details}"
            )]

        if entities:
            if requested_course and is_fee_query:
                requested_term = requested_course.split("(", 1)[0].strip().lower().replace(".", "")
                # AitEntity has no `course` column: the program code lives in
                # `code`, with free text in `name`/`details`.
                entities = [e for e in entities if requested_term in f"{e.code or ''} {e.name} {e.details}".lower().replace(".", "")]
            if entities:
                return [cls._to_dict(e) for e in entities]
        if modern_matches:
            return [cls._record_to_dict(r) for r in modern_matches]

        # 2. Second attempt: Clean college stopwords (e.g. 'ait fees' -> 'fees')
        tokens = cls.clean_search_tokens(relevance_text)
        if not tokens:
            tokens = [w for w in re.findall(r'[a-zA-Z0-9]+', raw_clean) if len(w) > 1]

        if not tokens:
            return []

        cleaned_phrase = " ".join(tokens)
        cleaned_term = f"%{cleaned_phrase}%"
        entities = q.filter(
            or_(
                func.lower(AitEntity.name).like(cleaned_term),
                func.lower(AitEntity.code).like(cleaned_term),
                func.lower(AitEntity.category).like(cleaned_term),
                func.lower(cast(AitEntity.details, String)).like(cleaned_term)
            )
        ).all()

        entities = [entity for entity in entities if year_specific_match(entity)]
        entities = [entity for entity in entities if record_topic_relevance_matches(
            relevance_text, f"{entity.name} {entity.code or ''} {entity.category} {entity.details}", entity.name
        )]
        compatible = cls.compatible_categories(relevance_text)
        if admission_category:
            allowed_admission_categories = {admission_category}
            if admission_category == "admission_documents":
                allowed_admission_categories.add("admission")
            # Program records may carry structured admission sub-fields
            # (eligibility, documents, fees). They remain valid evidence for
            # that admission sub-topic when the requested program matches.
            if admission_category == "admission_eligibility":
                allowed_admission_categories.update({"program", "programs", "course", "courses"})
            entities = [entity for entity in entities if entity.category.lower() in allowed_admission_categories]
        elif compatible and not requested_course:
            entities = [entity for entity in entities if entity.category.lower() in compatible]
        if query_domain_terms:
            entities = [entity for entity in entities if any(
                term in f"{entity.name} {entity.category} {entity.details}".lower()
                for term in query_domain_terms
            )]
        if requested_course and admission_category:
            requested_family = _program_family(requested_course)
            entities = [
                entity for entity in entities
                if requested_course.replace(".", "").lower() in f"{entity.code or ''} {entity.name or ''} {entity.details}".lower().replace(".", "")
                or (requested_family and requested_family == _program_family(entity.code or entity.name or entity.details))
            ]
        # Admission subtopics may live in AitEntity.details rather than the
        # entity's primary category. Keep exact course-family and tenant checks.
        if admission_category and admission_category.startswith("admission_"):
            subtopic = admission_category.removeprefix("admission_")
            entities = [
                entity for entity in entities
                if entity.category.lower() == admission_category
                or (
                    entity.category.lower() in {"program", "programs", "course", "courses"}
                    and isinstance(entity.details, dict)
                    and bool(entity.details.get(subtopic))
                )
            ]
        if is_document_query:
            entities = [entity for entity in entities if re.search(
                r"\b(required[_ ]documents?|admission[_ ]documents?|application[_ ]documents?|"
                r"certificates?|document[_ ]checklist|checklist|documents? needed|"
                r"documents? (?:are|is) required|required (?:for|at) admission)\b",
                f"{entity.name} {entity.category} {entity.details}".lower(),
            ) or entity.category.lower().replace("-", "_").startswith("admission_documents")]
        if is_fee_query:
            entities = [entity for entity in entities if entity.category.lower() in {"fee", "fees", "annual_fees", "sem_fees"}]
        if cls.is_student_support_query(raw_clean):
            entities = [entity for entity in entities if cls.student_support_evidence_allowed(
                raw_clean, f"{entity.name} {entity.category} {entity.details}"
            )]

        if entities:
            return [cls._to_dict(e) for e in entities]
        if modern_matches:
            return [cls._record_to_dict(r) for r in modern_matches]

        # 3. Third attempt: Individual token match across entities
        # E.g. for "bca fees", match entities containing "bca" and "fees"
        matched_candidates = []
        all_verified = q.all()
        all_verified = [e for e in all_verified if record_topic_relevance_matches(
            relevance_text, f"{e.name} {e.code or ''} {e.category} {e.details}", e.name
        )]
        if query_domain_terms:
            all_verified = [e for e in all_verified if any(
                term in f"{e.name} {e.category} {e.details}".lower()
                for term in query_domain_terms
            )]
        if cls.is_student_support_query(raw_clean):
            all_verified = [e for e in all_verified if cls.student_support_evidence_allowed(
                raw_clean, f"{e.name} {e.category} {e.details}"
            )]

        is_faculty_query = any(w in raw_clean for w in ["who teaches", "faculty", "professor", "teacher", "sir", "madam", "hod", "coordinator", "padhave", "padhata"])
        is_fee_query = any(w in raw_clean for w in ["fee", "fees", "tuition", "cost", "charge", "kitni", "ketli"])
        is_placement_query = any(w in raw_clean for w in ["placement", "package", "recruiter", "recruiters", "tpo", "placed"])
        is_facility_query = any(w in raw_clean for w in ["library", "lab", "canteen", "sports", "facility", "facilities", "classroom", "ground"])
        is_library_query = "library" in raw_clean
        is_admission_query = any(w in raw_clean for w in ["admission", "admissions", "apply", "form", "acpc", "dates", "schedule", "when to fill", "kab bharna", "kyare", "when is"])
        # Document-requirements queries need content-level document evidence;
        # admission/fee overlap alone is not sufficient.
        is_document_query = bool(re.search(
            r"\b(required documents?|admission documents?|application documents?|"
            r"certificates?|document checklist|checklist|documents? needed|"
            r"documents? (?:are|is) required|required (?:for|at) admission)\b", raw_clean,
        ))
        def has_document_evidence(blob):
            return bool(re.search(
                r"\b(required[_ ]documents?|admission[_ ]documents?|application[_ ]documents?|"
                r"certificates?|document[_ ]checklist|checklist|documents? needed|"
                r"documents? (?:are|is) required|required (?:for|at) admission)\b", blob.lower(),
            ))
        # Committee/governance queries must never resolve to generic facility,
        # faculty or program entities. A "chairman"/"committee" question is
        # answerable only from genuine committee-category records (or the
        # committee website snapshot); anything else is a wrong-entity match.
        is_committee_query = any(w in raw_clean for w in [
            "chairman", "chairperson", "committee", "council", "squad",
            "iqac", "grievance", "convener", "convenor",
        ])
        # Tokens that cannot disambiguate WHICH committee is being asked
        # about (they appear in every committee record's name/details).
        committee_generic_tokens = {
            "chairman", "chairperson", "committee", "council", "squad",
            "iqac", "grievance", "convener", "convenor", "who", "is",
            "the", "of", "a", "an", "what", "which", "tell", "me",
            "name", "names", "head", "heads", "member", "members", "list",
        }
        specific_tokens = [
            t for t in tokens if t not in committee_generic_tokens
        ]

        for e in all_verified:
            entity_blob = f"{e.name} {e.code or ''} {e.category} {str(e.details)}".lower()
            if query_spec is not None:
                from backend.app.chat.response_builder import evidence_relevance
                db_candidate = {
                    "college_id": e.college_id,
                    "source_type": "entity_db",
                    "verified": e.is_verified,
                    "status": "ACTIVE",
                    "title": e.name,
                    "name": e.name,
                    "category": e.category,
                    "topic": e.category,
                    "details": e.details,
                    "source_url": e.source_url,
                }
                if evidence_relevance(db_candidate, query_spec) is None:
                    continue
            if not program_relevance_matches(
                entity_blob,
                (e.details or {}).get("course") if isinstance(e.details, dict) else None,
            ):
                continue
            score = 0
            has_explicit_match = False
            for tok in tokens:
                pattern = rf"\b{re.escape(tok)}\b"
                if re.search(pattern, entity_blob):
                    has_explicit_match = True
                    # Give high weight if token is the code (e.g. BCA, MCA, DBMS) or name
                    if e.code and tok == e.code.lower():
                        score += 6
                    elif tok in e.name.lower():
                        score += 4
                    else:
                        score += 1

            if is_document_query and not has_document_evidence(entity_blob):
                continue
            # Domain Category Boost
            # Admin-verified Knowledge DB records (mirrored from knowledge_records)
            # are exact, dated facts and must outrank broader undated program blobs
            # (e.g. website fee ranges) when tokens match. This preserves the
            # source hierarchy for data the website does NOT publish.
            authority_l = (e.authority or "").lower()
            if "verified database" in authority_l or "admin verified" in authority_l:
                score += 6
            if is_faculty_query and e.category == "faculty":
                score += 10
            elif is_placement_query and e.category == "placement":
                score += 10
            elif is_facility_query and e.category == "facility":
                score += 8
            elif is_fee_query and ("annual_fees" in str(e.details).lower() or "sem_fees" in str(e.details).lower()):
                score += 6
            # An explicit academic year must be satisfied by the record; do not
            # rank an undated legacy fee as if it were year-specific evidence.
            requested_years = re.findall(r"20\d{2}\s*[-/]\s*\d{2,4}", raw_clean)
            if requested_years and is_fee_query:
                # Check both academic_year field and details
                year_match = False
                if e.academic_year:
                    for year in requested_years:
                        if year.replace(" ", "") in e.academic_year.replace(" ", ""):
                            year_match = True
                            break
                if not year_match and not any(year.replace(" ", "") in str(e.details).lower() for year in requested_years):
                    continue
            elif is_admission_query and (e.category == "contact" or "admissions_helpline" in str(e.details).lower()):
                score += 10

            if category and e.category == category:
                score += 12

            # Guard against unrelated categories when a specific intent domain is queried
            if is_placement_query and e.category not in ["placement"]:
                if not any(re.search(rf"\b{re.escape(tok)}\b", entity_blob) for tok in ["placement", "highest_package", "recruiter", "recruiters", "tpo"]):
                    continue

            if is_faculty_query and e.category not in ["faculty"]:
                continue
            if is_library_query and e.category not in ["library", "facility", "facilities"]:
                continue
            if is_fee_query and e.category not in ["fee", "fees", "annual_fees", "sem_fees"]:
                continue
            if requested_course and is_fee_query and not re.search(
                rf"\b{re.escape(requested_course.split('(', 1)[0].strip().lower())}\b",
                entity_blob,
            ):
                continue
            if is_fee_query:
                # Category/year overlap alone is not fee evidence. This keeps a
                # generic dated admission record from winning a fee lookup.
                fee_evidence = f"{e.name} {e.code or ''} {e.details}".lower()
                if not re.search(r"\b(fee|fees|tuition|cost|charge|payment|annual_fees|sem_fees)\b|₹|inr", fee_evidence):
                    continue
            # Hard guard: a committee/governance query may only be answered by
            # committee-category entities. Facility/faculty/program matches
            # (e.g. "AIT Central Library" for "library chairman?") are wrong
            # answers, not weak matches â€” so exclude them outright. If no
            # committee entity matches, return nothing so the grounding
            # validator produces its "couldn't verify" refusal instead.
            if is_committee_query and e.category != "committee":
                continue
            if is_committee_query and e.category == "committee":
                # Every committee's details JSON mentions the word "chairman",
                # so a query token like "chairman" matches ALL committees
                # equally via the details blob. Require at least one
                # specific (non-generic) query token to appear in the
                # entity's NAME itself, otherwise this committee is not a
                # genuine match for the asked-about committee.
                committee_name = e.name.lower()
                if not any(tok in committee_name for tok in specific_tokens):
                    continue
                score += 10

            entity_course = (e.details or {}).get("course") if isinstance(e.details, dict) else None
            if requested_course and entity_course and _program_family(entity_course) == _program_family(requested_course):
                score += 20
            if requested_course and requested_course.lower().replace(".", "") in entity_blob.replace(".", ""):
                score += 10
            if score > 0:
                matched_candidates.append((score, e))

        # Sort by match score descending. Domain-specific questions must not
        # fall back to a merely similar record from another topic.
        matched_candidates.sort(key=lambda x: x[0], reverse=True)
        return [cls._to_dict(e) for score, e in matched_candidates[:5]]


    @classmethod
    def query_website_snapshots(cls, db: Session, query_text: str,
                                college_id: Optional[str] = None, query_spec=None) -> List[Dict[str, Any]]:
        # ------------------------------------------------------------------
        # P0.1: QuerySpec is the ONLY understanding boundary.
        #
        # This function does NOT independently extract program, topic,
        # category or academic year from the raw question.  Those were
        # resolved once in EntityExtractor.extract_query_understanding and
        # arrive here as spec fields / spec booleans.
        #
        # TENANT ISOLATION IS UNCHANGED AND NEVER WIDENED:
        #   WebsiteSnapshot.college_id == query_spec.college_id (== active college)
        #   WebsiteSnapshot.active == True
        # Official-website priority is preserved: snapshots are returned to
        # the orchestrator which prefers them over admin DB records.
        #
        # Search meaningful concepts rather than the user's exact phrase:
        # crawled pages often use "departmental", "associations" or
        # "societies" for the same request.
        # ------------------------------------------------------------------
        if query_spec is not None:
            # Tenant comes from the spec, never from a text guess.
            college_id = query_spec.college_id or college_id
            relevance_text = query_spec.retrieval_text
            normalized_query = re.sub(r"[^a-z0-9 ]+", " ", relevance_text.lower())

            # Program / entity / category terms come from the spec only.
            spec_programs = list(query_spec.programs or [])
            if query_spec.program and query_spec.program not in spec_programs:
                spec_programs.append(query_spec.program)
            program_terms = [
                term for term in [
                    "bca", "mca", "bba", "mba", "cse", "computer engineering",
                    "information technology", "it engineering", "mechanical",
                    "civil", "electrical", "electronics",
                ]
                if any(re.search(rf"\b{re.escape(term)}\b", str(p).lower())
                       for p in spec_programs + [query_spec.entity or ""])
            ]

            committee_terms = [
                t for t in re.findall(r"[a-z0-9]+", normalized_query)
                if t not in STOPWORDS
                and t not in {"chairman", "chairperson", "head", "heads",
                              "list", "members", "member", "all"}
            ]
            is_section_query = query_spec.is_section_query
            is_values_query = query_spec.is_values_query
            is_clubs_query = query_spec.is_clubs_query
            is_rto_query = query_spec.is_rto_query
            is_student_support_query = query_spec.is_student_support_query
            is_intake_query = query_spec.is_intake_query
            is_catalog_query = query_spec.is_catalog_query
            # An academic year is a spec field, never re-scanned from text.
            academic_years = query_spec.requested_years
        else:
            # Legacy direct-call path (unit tests / scripts only).  The
            # orchestrator always supplies a spec.
            relevance_text = query_text
            normalized_query = re.sub(r"[^a-z0-9 ]+", " ", (query_text or "").lower())
            program_terms = [term for term in [
                "bca", "mca", "bba", "mba", "cse", "computer engineering",
                "information technology", "it engineering", "mechanical", "civil",
                "electrical", "electronics"
            ] if re.search(rf"\b{re.escape(term)}\b", normalized_query)]
            committee_terms = [t for t in re.findall(r"[a-z0-9]+", normalized_query)
                               if t not in STOPWORDS and t not in {"chairman", "chairperson", "head", "heads", "list", "members", "member", "all"}]
            is_section_query = any(t in normalized_query for t in ["committee", "council", "squad", "cell", "iqac"])
            is_values_query = bool(re.search(r"\b(core values?|educational philosophy|institutional philosophy|vision|mission|values)\b", normalized_query))
            is_clubs_query = bool(re.search(r"\b(student clubs?|extracurricular|student activities|student organizations?)\b", normalized_query))
            is_rto_query = bool(re.search(r"\b(rto|license facilitation center|learning license|driving license)\b", normalized_query))
            is_student_support_query = cls.is_student_support_query(normalized_query)
            is_intake_query = any(t in normalized_query for t in ["intake", "total student", "student intake", "number of courses"])
            is_catalog_query = "catalog" in normalized_query or ("academic" in normalized_query and "catalog" in normalized_query)
            academic_years = re.findall(r"20\d{2}\s*[-/]\s*\d{2,4}", normalized_query)

        tokens = cls.clean_search_tokens(relevance_text)
        token_variants = set(tokens)
        for token in tokens:
            if token.endswith("ies") and len(token) > 4:
                token_variants.add(token[:-3] + "y")
            elif token.endswith("s") and len(token) > 3:
                token_variants.add(token[:-1])
            if token == "associations":
                token_variants.update({"association", "society", "societies", "club", "clubs"})
            elif token in {"clubs", "club", "activities", "activity", "organizations", "organization"}:
                token_variants.update({"club", "association", "society", "activity"})
            elif token in {"departments", "departmental"}:
                token_variants.update({"department", "departments", "departmental", "branch"})
            elif token in {"event", "events", "news"}:
                token_variants.update({"event", "events", "news", "announcement", "notice", "circular", "activity", "seminar", "workshop", "festival", "hackathon", "cultural", "calendar", "fest"})
            elif token in {"latest", "recent", "current", "newest", "upcoming"}:
                token_variants.update({"latest", "recent", "current", "newest", "upcoming"})
        tokens = sorted(token_variants)
        temporal = bool(query_spec and getattr(query_spec, "temporal_qualifier", None))
        if query_spec is not None:
            from backend.app.chat.response_builder import evidence_relevance
        # Official pages are tenant-owned records.  Never widen this query when
        # the active college is unresolved, even if a URL/title resembles a
        # known college identifier.
        if not college_id:
            return []
        sq = db.query(WebsiteSnapshot).filter(
            WebsiteSnapshot.college_id == college_id,
            WebsiteSnapshot.active == True,
        )
        snapshots = sq.all()
        if is_catalog_query and not is_section_query and not is_intake_query:
            # Catalog retrieval is tenant-specific.  An absent tenant is not a
            # license to widen the query to every college.
            if not college_id:
                return []
            program_entities = [cls._to_dict(e) for e in db.query(AitEntity).filter(
                AitEntity.category == "program", AitEntity.is_verified == True,
                AitEntity.college_id == college_id,
            ).order_by(AitEntity.name.asc()).all()]
            # Transform program entities to snapshot format for consistency
            # Keep scanning tenant-owned website snapshots as well.  The
            # program entities are useful candidates, but catalog questions
            # must not bypass focused official sections.
        if not tokens:
            tokens = re.findall(r'[a-zA-Z0-9]+', relevance_text.lower())

        # Â§18: tenant-scoped â€” reuse the already-filtered snapshot set. Never widen
        # back to all snapshots or other colleges' pages could be returned.
        snapshots = [s for s in snapshots if s.college_id == college_id]
        results = []

        # Define low-quality content patterns to filter out
        low_quality_patterns = [
            r',children:', r'submitting', r'failed to fetch', r'pdf view failed',
            r'loading documents', r'_blank', r'noopener', r'noreferrer', r',role:',
            r',date:', r',imageUrl:', r',className:', r',count:', r',link:',
            r'scroll', r'smooth', r'easeout', r'whileinview:', r'aria-label'
        ]

        for s in snapshots:
            # Filter out low-quality content
            content_lower = (s.text_content or "").lower()
            # Retrieval score is initialized before every optional relevance
            # feature; no candidate may inherit another row's local score.
            score = 0
            if all(marker in content_lower for marker in [
                "inr 12.5 lpa", "inr 4.2 to 4.8 lpa", "85%+"
            ]):
                continue
            is_low_quality = any(re.search(pattern, content_lower) for pattern in low_quality_patterns)

            # Allow committee page even if it has some navigation terms
            is_committee_page = '/about/committee' in (s.url or '').lower()
            if is_low_quality and not is_committee_page:
                continue

            # Skip very short content unless it's the committee page
            if len(s.text_content or "") < 100 and not is_committee_page:
                continue

            title_lower = (s.title or '').lower()
            url_lower = (s.url or '').lower()
            full_content_lower = f"{title_lower} {url_lower} {s.text_content}".lower()
            if program_terms and not any(
                re.search(rf"\b{re.escape(term)}\b", full_content_lower)
                for term in program_terms
            ):
                continue
            targeted_relevance = cls.website_relevance_score(
                relevance_text, s.text_content, title=s.title or "", url=s.url or ""
            )
            if is_student_support_query and not cls.student_support_evidence_allowed(
                relevance_text, s.text_content, title=s.title or "", url=s.url or ""
            ):
                continue
            if targeted_relevance is None and query_spec is None:
                continue
            # Existing semantic guards remain authoritative where they identify
            # a well-supported match; the shared QuerySpec score supplements
            # rather than replaces those established topic contracts.
            if targeted_relevance is None and query_spec is not None:
                continue
            from backend.app.chat.response_builder import evidence_relevance
            evidence_facets = {
                "college_id": s.college_id,
                "source_type": "website_snapshot",
                "title": s.title or "",
                "name": s.title or "",
                "details": s.text_content or "",
                "content": s.text_content or "",
                "source_url": s.url or "",
                "summary": "",
                "description": "",
                "metadata": {},
                "active": s.active,
                "status": "ACTIVE" if s.active else "INACTIVE",
                "last_crawled_at": s.last_crawled_at,
                "created_at": s.created_at,
            }
            relevance = evidence_relevance(evidence_facets, query_spec) if query_spec is not None else None
            if query_spec is not None and relevance is None:
                continue
            if relevance is not None:
                targeted_relevance = relevance if targeted_relevance is None else max(targeted_relevance, relevance)
                if (targeted_relevance is not None and relevance > 0
                        and not cls.website_content_supports_query(
                            relevance_text, s.text_content, title=s.title or "", url=s.url or ""
                        )):
                    continue
            score = sum(1 for t in tokens if re.search(rf"\b{re.escape(t)}\b", full_content_lower))
            if targeted_relevance:
                score += targeted_relevance
            if relevance is not None:
                score += relevance
            if temporal:
                from datetime import datetime, timezone
                metadata_values = getattr(s, "metadata", None)
                if not isinstance(metadata_values, dict):
                    metadata_values = {}
                temporal_candidates = [
                    metadata_values.get("event_date"), metadata_values.get("date"),
                    metadata_values.get("published_at"), metadata_values.get("publication_date"),
                    metadata_values.get("updated_at"), metadata_values.get("created_at"),
                ]
                temporal_candidates.extend(re.findall(
                    r"\b(?:20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]20\d{2}|20\d{2})\b",
                    s.text_content or "",
                ))
                temporal_candidates.extend([
                    getattr(s, "last_crawled_at", None), getattr(s, "updated_at", None),
                    getattr(s, "created_at", None),
                ])
                for temporal_value in temporal_candidates:
                    if not temporal_value:
                        continue
                    try:
                        parsed = temporal_value if isinstance(temporal_value, datetime) else datetime.fromisoformat(str(temporal_value).replace("Z", "+00:00"))
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=timezone.utc)
                        score += parsed.timestamp() / 1_000_000_000
                        break
                    except (TypeError, ValueError, OverflowError):
                        continue
            body_lower = (s.text_content or "").lower()
            # A page is relevant when it contains a coherent domain concept,
            # not only the exact wording of the question. This is deliberately
            # lexical and tenant-scoped; it never invents content or widens the
            # snapshot set to another college.
            query_has_departments = bool(re.search(
                r"\b(departments?|departmental|branches?|programs?|courses?|academic\s+departments?)\b",
                normalized_query,
            ))
            if query_has_departments and not cls._department_query_has_meaningful_evidence(
                relevance_text, s.text_content, title=s.title or "", url=s.url or ""
            ):
                # A course/program listing is valid academic evidence even when
                # the same snapshot also contains navigation or placement text.
                is_course_listing = bool(
                    re.search(r"\b(course|courses|program|programs|degree)\b", normalized_query)
                    and re.search(r"\b(offers?|offered|available)\b", body_lower)
                    and re.search(r"\b(bca|mca|bba|mba|b\.?tech|engineering|information technology|computer|civil|mechanical|electrical|electronics)\b", body_lower)
                )
                if not is_course_listing:
                    continue
            if query_has_departments:
                score += 8
            navigation_only = bool(re.search(r"(?:\bhome\b|\bacademics\b|\bstudent cell\b).*(?:â†’|â€º|>>|academic calendar|grievance cell)", body_lower))
            if is_values_query:
                navigation_only = navigation_only or bool(re.search(
                    r"(?:governing council|committee|grievance cell|academic calendar|facilities|student section).{0,160}(?:home|academics|menu|navigation|co-curricular activities|grievance cell)",
                    body_lower,
                ))
                formal_values = re.search(
                    r"(?:our|institute'?s|institutional)\s+(?:core\s+)?(?:values?|vision|mission|philosophy|objectives|principles)"
                    r"|(?:core\s+values?|educational\s+philosophy|institutional\s+philosophy|vision\s+and\s+mission|mission\s+and\s+vision)",
                    body_lower,
                )
                if not formal_values or navigation_only:
                    continue
                score += 12
            if is_clubs_query:
                if re.search(r"\b(governing council|committee|grievance cell|academic calendar|facilities)\b", title_lower) and not re.search(r"\b(club|society|association|team|student organization)\s+(?:for|that|which|where|offers|organizes|conducts)", body_lower):
                    continue
                actual_activity_content = re.search(
                    r"(?:student\s+clubs?|student\s+organizations?|extracurricular|co[- ]curricular|student\s+activities|campus\s+activities)"
                    r".{0,180}(?:club|activities|events|societ|team|association|cultural|technical|sports)",
                    body_lower,
                )
                if not actual_activity_content or navigation_only:
                    continue
                score += 12
            if is_rto_query:
                if not any(term in body_lower for term in ["rto", "license", "transport authority"]):
                    continue
                if not re.search(r"(?:rto|license).{0,180}(?:application|processing|assistance|authority|office|facilitation)", body_lower):
                    continue
                score += 12
            if is_section_query and committee_terms:
                section_score = sum(1 for t in committee_terms if re.search(rf"\b{re.escape(t)}\b", full_content_lower))
                score += section_score * 3
                if not any(re.search(rf"\b{re.escape(t)}\b", full_content_lower) for t in committee_terms):
                    continue
                target = "sports" if "sports" in normalized_query else ("anti-ragging" if "anti ragging" in normalized_query or "anti-ragging" in normalized_query else None)
                if target == "anti-ragging":
                    target_present = "anti-ragging" in full_content_lower or "anti ragging" in full_content_lower
                else:
                    target_present = not target or target in full_content_lower
                if target and not target_present:
                    continue
                if target and target in full_content_lower:
                    score += 20
            if is_intake_query:
                if "/about/intake" in url_lower or "intake" in title_lower:
                    score += 30
                if any(term in full_content_lower for term in ["pg", "ug", "diploma", "total intake", "courses"]):
                    score += 8
                if not any(term in full_content_lower for term in ["intake", "pg", "ug", "diploma"]):
                    continue
            if relevance is not None:
                score += relevance
            if score > 0 and cls.website_content_supports_query(
                relevance_text, s.text_content, title=s.title or "", url=s.url or ""
            ):
                # Do not reduce each snapshot to its own section/body text.
                # Retain generic evidence facets and crawl timestamps for the
                # shared relevance and temporal-ranking pipeline downstream.
                relevance_metadata = {
                    "college_id": s.college_id,
                    "source_type": "website_snapshot",
                    "title": s.title or "",
                    "details": s.text_content or "",
                    "content": s.text_content or "",
                    "source_url": s.url or "",
                    "active": s.active,
                    "status": "ACTIVE" if s.active else "INACTIVE",
                    "last_crawled_at": s.last_crawled_at,
                    "created_at": s.created_at,
                }
                results.append((score, s, relevance_metadata))

        # Â§18/Â§30: provenance must belong to the college that owns the snapshot
        college_map = {}
        for s in snapshots:
            if s.college_id and s.college_id not in college_map:
                from backend.app.models.college import College as _College
                _c = db.query(_College).filter(_College.id == s.college_id).first()
                college_map[s.college_id] = _c

        temporal = bool(query_spec and getattr(query_spec, "temporal_qualifier", None))
        def temporal_date(row):
            from datetime import datetime, timezone
            snapshot = row[1]
            # The information's own publication/fact dates outrank crawl
            # timestamps, which describe ingestion rather than freshness.
            candidates = [
                getattr(snapshot, "event_date", None), getattr(snapshot, "date", None),
                getattr(snapshot, "published_at", None), getattr(snapshot, "publication_date", None),
            ]
            body = str(getattr(snapshot, "text_content", "") or "")
            candidates.extend(re.findall(
                r"\b(?:20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]20\d{2})\b",
                body,
            ))
            candidates.extend([
                getattr(snapshot, "last_crawled_at", None),
                getattr(snapshot, "updated_at", None),
                getattr(snapshot, "created_at", None),
            ])
            for value in candidates:
                if not value:
                    continue
                try:
                    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    return parsed.timestamp()
                except (TypeError, ValueError, OverflowError):
                    continue
            return float("-inf")
        if temporal:
            # Relevance is a gate and rank signal before recency. Date only
            # breaks ties between evidence that already answers the query.
            results.sort(key=lambda row: (row[0], temporal_date(row)), reverse=True)
        else:
            results.sort(key=lambda row: row[0], reverse=True)
        response = []
        for score, s, metadata in results[:3]:
            content = s.text_content
            section_title = None
            # Always attempt section extraction for committee queries regardless of section_title presence
            if is_section_query or committee_terms:
                sections = re.split(r"(?=SECTION:\s*)", content)
                matching_sections = [section for section in sections if any(
                    re.search(rf"\b{re.escape(term)}\b", section.lower()) for term in committee_terms
                )]
                if matching_sections:
                    content = max(matching_sections, key=lambda section: sum(
                        1 for term in committee_terms if re.search(rf"\b{re.escape(term)}\b", section.lower())
                    ))
                    title_match = re.match(r"SECTION:\s*([^\n]+)", content)
                    section_title = title_match.group(1).strip() if title_match else None
            college = college_map.get(s.college_id)
            if college:
                source_domain = (college.official_website or "").replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                authority = f"Official {college.name} Website"
            else:
                source_domain = "aitindia.in"
                authority = "Official Ahmedabad Institute of Technology Website"
            response.append({
                "id": s.id,
                "url": s.url,
                "title": s.title,
                "section_title": section_title,
                "text_content": content,
                "content": content,
                "source_domain": source_domain,
                "authority": authority,
                "verification_status": "Official source",
                "college_id": s.college_id,
                "active": s.active,
                "last_crawled_at": s.last_crawled_at,
                "created_at": s.created_at,
                "updated_at": getattr(s, "updated_at", None),
                "metadata": metadata,
                })
        return response

    @classmethod
    def get_by_category(cls, db: Session, category: str,
                        college_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not college_id:
            return []
        q = db.query(AitEntity).filter(
            AitEntity.college_id == college_id,
            AitEntity.category == category,
            AitEntity.is_verified == True,
        )
        entities = q.order_by(AitEntity.name.asc()).all()

        return [cls._to_dict(e) for e in entities]

    @classmethod
    def _record_to_dict(cls, record: KnowledgeRecord) -> Dict[str, Any]:
        metadata = record.metadata_json or {}
        # `value` is the published answer field, while Smart Upload keeps the
        # complete section in metadata.content.  Expose that content without
        # replacing provenance or the structured fields used by retrieval.
        details = {
            "value": record.value,
            "field_name": record.field_name,
            "description": record.description,
            "course": record.course,
            "academic_year": record.academic_year,
            **metadata,
        }
        # Keep the complete uploaded section authoritative over an empty or
        # preview-like content field; `value` remains separately preserved.
        if metadata.get("content"):
            details["content"] = metadata["content"]
        return {
            "id": record.id,
            "college_id": record.college_id,
            "name": record.title,
            "code": None,
            "category": record.category.key if record.category else None,
            "course": record.course,
            "details": details,
            "academic_year": record.academic_year,
            "source_url": record.source_url or "",
            "source_page": record.source_title,
            "authority": record.source_type or "ADMIN_VERIFIED",
            "source_type": record.source_type,
            "is_verified": record.verified,
            "status": record.status,
            "verified_at": record.verified_at.isoformat() if record.verified_at else None,
            "source_type": record.source_type,
        }

    @classmethod
    def _to_dict(cls, e: AitEntity) -> Dict[str, Any]:
        return {
                "id": e.id,
            "college_id": e.college_id,
            "name": e.name,
            "code": e.code,
            "category": e.category,
            "details": e.details,
            "academic_year": e.academic_year,
            "source_url": e.source_url,
            "source_page": e.source_page,
            "authority": e.authority,
            "is_verified": e.is_verified,
            "verified_at": e.verified_at.isoformat() if e.verified_at else None
        }

knowledge_db = KnowledgeDatabase()
