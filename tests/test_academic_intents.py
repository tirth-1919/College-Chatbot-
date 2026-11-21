"""Unit coverage for fee-question normalization used by structured lookup."""
import pytest

from app.services.academic_service import _requested_semester, _course_match


@pytest.mark.parametrize(("question", "semester"), [
    ("What is BCA semester 1 fee?", 1),
    ("BCA sem 1 fees", 1),
    ("first semester BCA tuition", 1),
    ("What is BCA semester 2 fee?", 2),
    ("second semester fee", 2),
    ("sem 8 charges", 8),
])
def test_semester_phrasing(question, semester):
    assert _requested_semester(question) == semester


def test_course_lookup_accepts_abbreviation_and_full_name():
    class Course:
        course_name = "Bachelor of Computer Applications"
        course_code = ""
        course_abbreviation = "BCA"
        branch_name = None

    course = Course()
    assert _course_match("What is BCA fee", [course]) is course
    assert _course_match("Bachelor of Computer Applications semester 1", [course]) is course
