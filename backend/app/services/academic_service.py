"""Exact academic and approved-gallery lookup scoped to an active college."""
import re
import uuid
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import AcademicCourse, AcademicFee, CollegeGalleryImage
from app.models.college import College


def _norm(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _normalise_course_query(text: str) -> str:
    """Normalize common course-list spelling variants before intent matching."""
    text = _norm(text)
    aliases = {"cource": "course", "cources": "courses", "corse": "course", "corses": "courses"}
    return " ".join(aliases.get(token, token) for token in text.split())


def _is_course_listing_question(text: str) -> bool:
    tokens = set(text.split())
    asks_about_programs = bool(tokens & {"course", "courses", "program", "programs", "branch", "branches", "degree", "degrees", "diploma"})
    asks_for_list = bool(tokens & {"which", "what", "list", "all", "offer", "offers", "offered", "provide", "provides", "provided", "available", "show", "tell"})
    return asks_about_programs and asks_for_list


def _requested_semester(text: str):
    s = _norm(text)
    words = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8}
    m = re.search(r"\b(?:semester|sem)\s*(\d+)\b|\b(\d+)(?:st|nd|rd|th)?\s+semester\b", s)
    if m:
        return int(m.group(1) or m.group(2))
    for word, number in words.items():
        if word in s and ("semester" in s or "sem" in s):
            return number
    return None


def _course_match(text: str, courses):
    query = _norm(text)
    candidates = []
    for course in courses:
        names = [course.course_name, course.course_code or "", course.course_abbreviation or "", course.branch_name or ""]
        for alias in names:
            norm = _norm(alias)
            if norm and (norm in query or query in norm):
                candidates.append((len(norm), course))
    return max(candidates, key=lambda x: x[0])[1] if candidates else None


async def answer_structured_question(db: AsyncSession, college_id: uuid.UUID, prompt: str, context_query: str = ""):
    """Return a grounded response, or None when the prompt is outside this layer."""
    q = _normalise_course_query(prompt)
    context_norm = _normalise_course_query(context_query)
    fee_intent = any(word in q.split() for word in ("fee", "fees", "tuition", "cost", "charges"))
    course_terms = {"course", "courses", "program", "programs", "branch", "branches", "engineering", "diploma", "bca", "mca", "btech", "mtech", "bachelor", "master", "science", "pharmacy", "architecture", "design", "vocational", "computer", "civil", "mechanical", "electrical", "data", "cyber", "ai"}
    has_course_hint = bool((set(q.split()) | set(context_norm.split())) & course_terms)
    image_intent_terms = {
        "photo", "photos", "picture", "pictures", "image", "images", "gallery", "galleries",
        "event", "events", "campus", "library", "libraries", "laboratory", "laboratories", "lab", "labs",
        "hostel", "hostels", "canteen", "canteens", "auditorium", "auditoriums", "classroom", "classrooms",
        "entrance", "entrances", "sports", "sport", "festival", "festivals", "workshop", "workshops",
        "seminar", "seminars", "admission", "admissions", "admin", "faculty", "staff", "building",
        "buildings", "facility", "facilities", "looks",
    }
    image_intent = bool(set(q.split()) & image_intent_terms)
    if not has_course_hint and not image_intent and not ("show" in q.split() and any(x in q.split() for x in ("college", "building", "facility", "facilities"))):
        return None
    if fee_intent and not has_course_hint:
        return None
    courses = (await db.execute(select(AcademicCourse).where(
        AcademicCourse.college_id == college_id, AcademicCourse.active_status.is_(True),
        AcademicCourse.verification_status.in_(["APPROVED", "VERIFIED"]),
    ))).scalars().all()
    semester = _requested_semester(prompt)
    course = _course_match(q + " " + context_norm, courses)
    if fee_intent and course:
        fee_type = "SEMESTER" if semester else next((kind for term, kind in (
            ("tuition", "TUITION"), ("admission", "ADMISSION"), ("registration", "REGISTRATION"),
            ("examination", "EXAMINATION"), ("total", "TOTAL"),
        ) if term in q), None)
        if not fee_type:
            return None
        stmt = select(AcademicFee).where(
            AcademicFee.college_id == college_id,
            AcademicFee.course_id == course.id,
            AcademicFee.semester_number == semester if semester else AcademicFee.semester_number.is_(None),
            AcademicFee.fee_type == fee_type,
            AcademicFee.verification_status.in_(["APPROVED", "VERIFIED"]),
        ).order_by(AcademicFee.academic_year.desc().nullslast(), AcademicFee.effective_from.desc().nullslast())
        fee = (await db.execute(stmt)).scalars().first()
        if fee:
            amount = f"{fee.currency} {fee.fee_amount:,.0f}" if fee.currency != "INR" else f"₹{fee.fee_amount:,.0f}"
            year = f" · Academic year {fee.academic_year}" if fee.academic_year else ""
            college = await db.get(College, college_id)
            heading = f"{college.name} – " if college else ""
            detail = f"Semester {semester}" if semester else fee_type.title()
            text = f"**{heading}{course.course_name} {detail} Fee**\n\n**{amount}**{year}\n\nFee type: {fee.fee_type.title()} · Verification: {fee.verification_status.title()}"
            return {"message_text": text, "answer_source_type": "ADMIN_VERIFIED", "is_verified": True,
                    "source_citations": ([{"title": "College fee schedule", "source_type": "PDF", "page_number": fee.source_page}] if fee.source_document else [])}
        requested = f"Semester {semester}" if semester else fee_type.title()
        return {"message_text": f"I don't have a verified {requested} fee for {course.course_name} in this college's catalogue.",
                "answer_source_type": "NO_RELIABLE_INFORMATION", "is_verified": False, "source_citations": []}

    if course:
        requested_field = next((field for term, field in (("eligibility", "eligibility"), ("duration", "duration"), ("syllabus", "syllabus_information")) if term in q), None)
        if requested_field:
            value = getattr(course, requested_field)
            if not value:
                return {"message_text": f"No verified {requested_field.replace('_', ' ')} information is registered for {course.course_name} at this college.", "answer_source_type": "NO_RELIABLE_INFORMATION", "is_verified": False, "source_citations": []}
            return {"message_text": f"**{course.course_name} · {requested_field.replace('_', ' ').title()}**\n\n{value}", "answer_source_type": "ADMIN_VERIFIED", "is_verified": True, "source_citations": []}

    if _is_course_listing_question(q) or ("does this college" in q and any(x in q for x in ("course", "program", "branch", "degree", "diploma"))):
        if not courses:
            return {"message_text": "No approved courses are currently listed for this college.", "answer_source_type": "NO_RELIABLE_INFORMATION", "is_verified": False, "source_citations": []}
        lines = [f"• {c.course_name}" + (f" ({c.course_abbreviation})" if c.course_abbreviation else "") for c in courses]
        return {"message_text": "**Approved courses available at this college**\n\n" + "\n".join(lines),
                "answer_source_type": "ADMIN_VERIFIED", "is_verified": True, "source_citations": []}

    college = await db.get(College, college_id)
    college_aliases = [getattr(college, "name", ""), getattr(college, "short_name", "")] if college else []
    image_words = ("photo", "photos", "picture", "pictures", "image", "images", "gallery", "galleries", "event", "events", "campus", "library", "libraries", "laboratory", "laboratories", "lab", "labs", "hostel", "hostels", "canteen", "canteens", "auditorium", "auditoriums", "classroom", "classrooms", "entrance", "sports", "festival", "festivals", "workshop", "workshops", "seminar", "seminars", "admission", "admissions", "admin", "faculty", "building", "buildings", "facility", "facilities", "looks")
    asks_to_show_college = "show" in q.split() and any(_norm(alias) and _norm(alias) in q for alias in college_aliases)
    if any(x in q.split() for x in image_words) or asks_to_show_college or ("show" in q.split() and any(x in q.split() for x in ("college", "building", "facility", "facilities"))):
        category_aliases = (
            ({"admission", "admissions", "admin"}, "ADMISSIONS"),
            ({"library", "libraries"}, "LIBRARY"),
            ({"laboratory", "laboratories", "lab", "labs"}, "LABORATORY"),
            ({"hostel", "hostels"}, "HOSTEL"),
            ({"canteen", "canteens"}, "CANTEEN"),
            ({"auditorium", "auditoriums"}, "AUDITORIUM"),
            ({"classroom", "classrooms"}, "CLASSROOM"),
            ({"entrance", "entrances"}, "ENTRANCE"),
            ({"sports", "sport"}, "SPORTS"),
            ({"event", "events", "festival", "festivals", "workshop", "workshops", "seminar", "seminars"}, "EVENTS"),
            ({"department", "departments"}, "DEPARTMENT"),
            ({"faculty", "staff"}, "FACULTY"),
            ({"campus", "building", "buildings", "facility", "facilities"}, "CAMPUS"),
        )
        query_tokens = set(q.split())
        category = next((value for aliases, value in category_aliases if query_tokens & aliases), None)
        stmt = select(CollegeGalleryImage).where(
            CollegeGalleryImage.college_id == college_id,
            CollegeGalleryImage.is_active.is_(True),
            CollegeGalleryImage.verification_status.in_(["APPROVED", "VERIFIED"]),
        )
        if category == "EVENTS":
            stmt = stmt.where(or_(
                CollegeGalleryImage.image_category.in_(("EVENTS", "TECHNICAL_FESTIVAL", "CULTURAL_FESTIVAL", "WORKSHOP", "SEMINAR")),
                CollegeGalleryImage.event_name.is_not(None),
            ))
        elif category:
            stmt = stmt.where(CollegeGalleryImage.image_category == category)
        if category == "EVENTS":
            event_terms = [part for part in q.split() if part not in {
                "show", "display", "get", "view", "see", "find", "give", "me", "the", "college", "ait", "rcti",
                "event", "events", "festival", "festivals", "workshop", "workshops", "seminar", "seminars",
                "photo", "photos", "picture", "pictures", "image", "images", "gallery", "galleries",
                "all", "latest", "what", "which", "are", "is", "organized", "at", "this", "from", "of", "for", "in", "on",
            }]
            if event_terms:
                event_query = "%" + " ".join(event_terms) + "%"
                stmt = stmt.where(or_(
                    CollegeGalleryImage.event_name.ilike(event_query),
                    CollegeGalleryImage.image_title.ilike(event_query),
                    CollegeGalleryImage.image_description.ilike(event_query),
                ))
        images = (await db.execute(stmt.order_by(CollegeGalleryImage.created_at.desc()))).scalars().all()
        if not images:
            return {"message_text": "No verified photographs matching that request are currently available for this college.",
                    "answer_source_type": "NO_RELIABLE_INFORMATION", "is_verified": False, "source_citations": []}
        citations = [{"title": im.image_title, "source_type": "ADMIN_VERIFIED", "url": im.source_url,
                      "image_url": im.image_url, "image_category": im.image_category,
                      "image_description": im.image_description, "event_name": im.event_name,
                      "event_date": im.event_date.isoformat() if im.event_date else None}
                     for im in images]
        category_label = "Events" if category == "EVENTS" else "Admissions" if category == "ADMISSIONS" else category.title() if category else "College"
        return {"message_text": f"**Verified {category_label} Photographs**\n\nShowing all {len(images)} matching photograph(s) from this college.",
                "answer_source_type": "ADMIN_VERIFIED", "is_verified": True, "source_citations": citations}
    return None
