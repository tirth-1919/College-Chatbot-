"""Institutional Knowledge Category Classifier Service.

Classifies college pages, documents, and chunks into 15 standardized academic domains:
1. ADMISSIONS
2. COURSES
3. FEES
4. SCHOLARSHIPS
5. EXAMINATIONS
6. RESULTS
7. ACADEMIC_CALENDAR
8. FACILITIES
9. HOSTEL
10. LIBRARY
11. PLACEMENT
12. CONTACT
13. RULES
14. DEPARTMENTS
15. OTHER
"""

import re
from typing import Dict, List, Optional, Tuple


class KnowledgeClassifierService:
    """Classifies educational institutional content into 15 domain categories."""

    VALID_CATEGORIES = [
        "ADMISSIONS",
        "COURSES",
        "FEES",
        "SCHOLARSHIPS",
        "EXAMINATIONS",
        "RESULTS",
        "ACADEMIC_CALENDAR",
        "FACILITIES",
        "HOSTEL",
        "LIBRARY",
        "PLACEMENT",
        "CONTACT",
        "RULES",
        "DEPARTMENTS",
        "OTHER",
    ]

    # Keyword dictionary with category weightings
    TAXONOMY: Dict[str, Dict[str, float]] = {
        "FEES": {
            "fee": 2.0, "tuition": 2.5, "frc": 2.0, "semester fee": 3.0,
            "cost": 1.2, "payment": 1.5, "demand draft": 2.0, "refund": 1.8,
            "caution money": 2.5, "deposit": 1.5, "challan": 2.0, "dues": 1.5,
            "late fee": 2.5, "receipt": 1.5, "fee structure": 3.0,
        },
        "ADMISSIONS": {
            "admission": 2.5, "eligibility": 2.0, "application": 1.8, "apply online": 2.5,
            "cutoff": 2.0, "merit list": 2.5, "counseling": 2.0, "acpc": 3.0,
            "gujcet": 2.5, "jee main": 2.0, "intake": 1.8, "seat matrix": 2.5,
            "documents required": 2.0, "management quota": 2.5, "prospectus": 2.0,
        },
        "SCHOLARSHIPS": {
            "scholarship": 3.0, "mysy": 3.0, "freeship": 2.5, "financial aid": 2.5,
            "tuition waiver": 3.0, "tfw": 2.5, "stipend": 2.0, "fellowship": 2.0,
            "post matric": 2.5, "digital gujarat": 3.0, "national scholarship": 2.5,
        },
        "COURSES": {
            "curriculum": 2.5, "syllabus": 2.5, "b.tech": 2.0, "b.e.": 2.0,
            "m.tech": 2.0, "diploma": 2.0, "degree": 1.8, "credit": 1.8,
            "course": 1.5, "undergraduate": 2.0, "postgraduate": 2.0, "ph.d": 2.0,
            "semester": 1.5, "electives": 2.0, "program": 1.2,
        },
        "DEPARTMENTS": {
            "department": 2.5, "faculty": 2.0, "head of department": 3.0, "hod": 3.0,
            "professor": 2.0, "associate professor": 2.5, "assistant professor": 2.5,
            "computer engineering": 2.5, "mechanical engineering": 2.5,
            "civil engineering": 2.5, "electrical engineering": 2.5, "information technology": 2.5,
            "staff": 1.5, "dean": 2.0, "principal": 2.0,
        },
        "PLACEMENT": {
            "placement": 3.0, "recruitment": 2.5, "highest package": 3.0, "average package": 3.0,
            "ctc": 2.5, "lpa": 2.5, "campus drive": 2.5, "internship": 2.0,
            "tpo": 3.0, "training and placement": 3.0, "recruiter": 2.5, "companies visited": 2.5,
        },
        "HOSTEL": {
            "hostel": 3.0, "mess": 2.5, "accommodation": 2.0, "dormitory": 2.5,
            "room rent": 2.5, "warden": 3.0, "curfew": 2.0, "boarding": 2.0,
            "resident": 1.5, "dining": 2.0, "sharing room": 2.5,
        },
        "LIBRARY": {
            "library": 3.0, "books": 2.0, "journals": 2.0, "librarian": 3.0,
            "reading room": 2.5, "e-resources": 2.5, "digital library": 3.0,
            "borrowing": 2.0, "catalogue": 2.0, "circulation": 2.0,
        },
        "EXAMINATIONS": {
            "examination": 2.5, "exam": 2.0, "mid semester": 2.5, "end semester": 2.5,
            "time table": 2.5, "hall ticket": 3.0, "exam schedule": 3.0, "invigilation": 2.0,
            "backlog": 2.5, "re-assessment": 2.5, "re-checking": 2.5,
        },
        "RESULTS": {
            "result": 2.5, "marksheet": 3.0, "grade": 2.0, "cgpa": 2.5, "sgpa": 2.5,
            "transcript": 2.5, "percentage": 1.8, "rank list": 2.5, "passed": 1.5,
            "provisional certificate": 2.5,
        },
        "ACADEMIC_CALENDAR": {
            "academic calendar": 3.5, "commencement": 2.5, "vacation": 2.0, "term dates": 2.5,
            "holidays": 2.0, "orientation": 2.0, "working days": 2.0, "schedule": 1.5,
        },
        "FACILITIES": {
            "campus": 1.5, "laboratory": 2.0, "lab": 1.5, "sports": 2.0, "gymnasium": 2.5,
            "canteen": 2.5, "cafeteria": 2.5, "auditorium": 2.5, "wifi": 2.0, "transport": 2.0,
            "bus facility": 2.5, "medical center": 2.5,
        },
        "CONTACT": {
            "contact us": 3.0, "telephone": 2.0, "phone": 1.8, "email": 1.8, "helpline": 2.5,
            "address": 2.0, "location": 1.8, "inquiry": 2.0, "office hours": 2.5,
        },
        "RULES": {
            "rules": 2.0, "regulations": 2.0, "anti-ragging": 3.0, "discipline": 2.0,
            "attendance": 2.5, "code of conduct": 3.0, "grievance": 2.5, "policy": 1.8,
            "committee": 1.8,
        },
    }

    @classmethod
    def classify_text(
        cls,
        text: str,
        heading: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> Tuple[str, float, List[str]]:
        """Classifies content into one of the 15 categories.

        Returns:
            Tuple of (category_name, confidence_score, matched_keywords)
        """
        if not text and not heading:
            return "OTHER", 0.0, []

        scores: Dict[str, float] = {cat: 0.0 for cat in cls.TAXONOMY}
        matches: Dict[str, List[str]] = {cat: [] for cat in cls.TAXONOMY}

        # Build combined corpus with weighted signals
        search_corpus = text.lower()
        heading_corpus = (heading or "").lower()
        url_corpus = (source_url or "").lower()

        # 1. Evaluate taxonomy keyword matches
        for cat, keywords in cls.TAXONOMY.items():
            for kw, weight in keywords.items():
                kw_lower = kw.lower()

                # Strongest signal: keyword in URL
                if kw_lower in url_corpus:
                    scores[cat] += weight * 3.0
                    matches[cat].append(f"url:{kw}")

                # High signal: keyword in section heading
                if kw_lower in heading_corpus:
                    scores[cat] += weight * 2.5
                    matches[cat].append(f"heading:{kw}")

                # Standard signal: keyword occurrence in body text
                count = len(re.findall(r"\b" + re.escape(kw_lower) + r"\b", search_corpus))
                if count > 0:
                    # Log-damped frequency to avoid 1 word dominating
                    freq_multiplier = min(3.0, 1.0 + 0.5 * (count - 1))
                    scores[cat] += weight * freq_multiplier
                    matches[cat].append(kw)

        # 2. Pick top-scoring category
        best_cat = "OTHER"
        best_score = 0.0

        for cat, score in scores.items():
            if score > best_score:
                best_score = score
                best_cat = cat

        # 3. Normalize confidence between 0.0 and 1.0
        # A score of >= 10.0 gives high confidence (>0.90)
        if best_score < 1.0:
            return "OTHER", 0.20, []

        confidence = round(min(0.99, best_score / (best_score + 3.0)), 2)
        top_tags = list(set(matches[best_cat]))[:5]

        return best_cat, confidence, top_tags


classifier_service = KnowledgeClassifierService()

