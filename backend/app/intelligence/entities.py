import re
from typing import Dict, Any, List

class EntityExtractor:
    PROGRAMS = {
        "bca": "BCA (Bachelor of Computer Applications)",
        "mca": "MCA (Master of Computer Applications)",
        "bba": "BBA (Bachelor of Business Administration)",
        "mba": "MBA (Master of Business Administration)",
        "b.tech cse": "B.Tech Computer Science & Engineering",
        "btech cse": "B.Tech Computer Science & Engineering",
        "cse": "B.Tech Computer Science & Engineering",
        "computer engineering": "B.Tech Computer Engineering",
        "ce": "B.Tech Computer Engineering",
        "b.tech it": "B.Tech Information Technology",
        "btech it": "B.Tech Information Technology",
        "information technology": "B.Tech Information Technology",
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
        "transport": "TRANSPORT"
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

        # 1. Match Programs (ensuring standalone pronoun 'it' is NEVER matched as B.Tech IT)
        for key, val in cls.PROGRAMS.items():
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
