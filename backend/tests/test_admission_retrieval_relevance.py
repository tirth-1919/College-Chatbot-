"""
Regression tests for BCA admission eligibility retrieval relevance.

Verifies that a query for BCA eligibility:
1. Returns the BCA program entity (with 10+2 eligibility info).
2. Does NOT return MCA, B.Tech, contact, or fee entities.

These tests run without a live backend using the filter logic directly.
"""
import re
import pytest


def _apply_eligibility_filter(retrieved_entities, programs_list):
    """Mirrors the admission_eligibility post-retrieval filter in orchestrator.py."""
    eligibility_kw = re.compile(
        r"\b(eligib|qualification|criteria|10\+2|hsc|12th|percentage|aggregate|pass|require)\b",
        re.IGNORECASE,
    )
    excluded_categories = {"contact", "fees", "fee", "annual_fees", "sem_fees"}

    _elig_programs = programs_list or []
    _course_tokens = []
    if _elig_programs:
        _raw_prog = _elig_programs[0]
        _acronym = re.split(r"[\s(]", _raw_prog)[0].lower()
        _course_tokens.append(_acronym)
        _paren_m = re.search(r"\(([^)]+)\)", _raw_prog)
        if _paren_m:
            _course_tokens.append(_paren_m.group(1).lower())

    course_match_re = (
        re.compile(
            r"\b(" + "|".join(re.escape(t) for t in _course_tokens) + r")\b",
            re.IGNORECASE,
        )
        if _course_tokens else None
    )

    known_acronyms = {"b.tech", "btech", "mca", "mba", "bba", "bca"}
    req_norm = {t.replace(".", "") for t in _course_tokens}
    other_courses = {c for c in known_acronyms if c.replace(".", "") not in req_norm}
    other_course_re = re.compile(
        r"\b(" + "|".join(re.escape(c) for c in other_courses if c) + r")\b",
        re.IGNORECASE,
    ) if (_course_tokens and other_courses) else None

    filtered = []
    for e in retrieved_entities:
        cat = e.get("category", "").lower().replace("-", "_")
        if cat in excluded_categories:
            continue
        details_str = str(e.get("details", {}))
        name_str = str(e.get("name", ""))
        combined = f"{name_str} {details_str}"
        if not eligibility_kw.search(details_str):
            continue
        if course_match_re and not course_match_re.search(combined):
            continue
        if other_course_re and other_course_re.search(name_str):
            continue
        filtered.append(e)
    return filtered


REAL_ENTITIES = [
    {"name": "AIT Official Contact Information", "category": "contact",
     "details": {"address": "Ahmedabad Institute of Technology", "phone": "+91-79-29702271"}},
    {"name": "BCA Semester 1 Fee", "category": "fees", "details": {"fee": 15000}},
    {"name": "B.Tech Computer Science & Engineering", "category": "program",
     "details": {"eligibility": "10+2 with Physics, Mathematics, Chemistry with GUJCET / JEE",
                 "duration": "4 years", "seats": 60}},
    {"name": "BCA (Bachelor of Computer Applications)", "category": "program",
     "details": {"eligibility": "10+2 with English and Mathematics / Business Maths / Statistics",
                 "duration": "3 years", "seats": 60}},
    {"name": "MCA (Master of Computer Applications)", "category": "program",
     "details": {"eligibility": "BCA / B.Sc (IT/CS) or equivalent graduate degree with 50% aggregate",
                 "duration": "2 years", "seats": 30}},
]

BCA_PROGRAMS = ["BCA (Bachelor of Computer Applications)"]


def test_bca_eligibility_only_bca_entity_kept():
    result = _apply_eligibility_filter(REAL_ENTITIES, BCA_PROGRAMS)
    names = [e["name"] for e in result]
    assert "BCA (Bachelor of Computer Applications)" in names


def test_bca_eligibility_contact_excluded():
    result = _apply_eligibility_filter(REAL_ENTITIES, BCA_PROGRAMS)
    names = [e["name"] for e in result]
    assert "AIT Official Contact Information" not in names


def test_bca_eligibility_fees_excluded():
    result = _apply_eligibility_filter(REAL_ENTITIES, BCA_PROGRAMS)
    names = [e["name"] for e in result]
    assert "BCA Semester 1 Fee" not in names


def test_bca_eligibility_mca_excluded():
    result = _apply_eligibility_filter(REAL_ENTITIES, BCA_PROGRAMS)
    names = [e["name"] for e in result]
    assert "MCA (Master of Computer Applications)" not in names


def test_bca_eligibility_btech_excluded():
    result = _apply_eligibility_filter(REAL_ENTITIES, BCA_PROGRAMS)
    names = [e["name"] for e in result]
    assert "B.Tech Computer Science & Engineering" not in names


def test_bca_eligibility_result_count_is_one():
    result = _apply_eligibility_filter(REAL_ENTITIES, BCA_PROGRAMS)
    assert len(result) == 1, f"Expected 1 entity, got {len(result)}: {[e['name'] for e in result]}"


def test_no_course_keeps_all_programs_with_eligibility():
    result = _apply_eligibility_filter(REAL_ENTITIES, [])
    names = [e["name"] for e in result]
    assert "AIT Official Contact Information" not in names
    assert "BCA Semester 1 Fee" not in names
    assert len(result) == 3


def test_acronym_extraction_from_full_program_name():
    raw = "BCA (Bachelor of Computer Applications)"
    acronym = re.split(r"[\s(]", raw)[0].lower()
    assert acronym == "bca"
    m = re.search(r"\(([^)]+)\)", raw)
    assert m and m.group(1).lower() == "bachelor of computer applications"


def test_full_expansion_matches_db_entity_name():
    raw = "BCA (Bachelor of Computer Applications)"
    acronym = re.split(r"[\s(]", raw)[0].lower()
    m = re.search(r"\(([^)]+)\)", raw)
    tokens = [acronym]
    if m:
        tokens.append(m.group(1).lower())
    regex = re.compile(r"\b(" + "|".join(re.escape(t) for t in tokens) + r")\b", re.IGNORECASE)
    assert regex.search("Bachelor of Computer Applications")
    assert regex.search("BCA program")

