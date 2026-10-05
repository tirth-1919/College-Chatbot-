"Focused Smart Upload section classification and confidence contract tests."""
from backend.app.api.v1.admin.smart_upload import _classify_content, _classify_sections, _normalize_confidence

def test_multi_section_document_produces_canonical_categories():
    text = (
        "Admission Process: complete the application.\n\n"
        "Admission Eligibility: passed 12th standard.\n\n"
        "Admission Documents: submit the marksheet.\n\n"
        "Admission Fees: BCA fee INR 32000.\n\n"
        "Courses and Programs: BCA is a three-year program.\n\n"
        "Scholarship: eligible students may apply.\n\n"
        "Hostel: accommodation subject to availability.\n\n"
        "Contact Information: contact the Admission Office.\n\n"
        "Entrance Exam: verify GUJCET requirement."
    )
    categories = {row["detected_category"] for row in _classify_sections("AIT_Smart_Upload_Test_Data_2026.pdf", text)}
    assert categories == {
        "admission_process", "admission_eligibility", "admission_documents", "admission_fees",
        "courses", "scholarships", "hostel", "admission_contact", "admission_entrance_exam",
    }


def test_semantic_categories_do_not_fall_into_departments():
    assert _classify_content("x.txt", "Required documents for admission")["detected_category"] == "admission_documents"
    assert _classify_content("x.txt", "BCA fee is INR 32000")["detected_category"] == "admission_fees"
    assert _classify_content("x.txt", "Computer Engineering Department")["detected_category"] == "departments"
    assert _classify_content("x.txt", "The admission information is published here")["detected_category"] != "departments"


def test_confidence_is_a_single_probability_contract():
    assert _normalize_confidence(0.85) == 0.85
    assert 0 <= _normalize_confidence(1) <= 1
    for value in (1.5, -0.2, 8500):
        try:
            _normalize_confidence(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid confidence accepted: {value}")
