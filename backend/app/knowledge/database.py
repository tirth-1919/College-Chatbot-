import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, cast, String
from backend.app.models.knowledge import AitEntity, WebsiteSnapshot

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
    "teachers": ["faculty", "professor", "coordinator"],
    "teacher": ["faculty", "professor", "coordinator"],
    "professors": ["faculty", "professor"],
}

class KnowledgeDatabase:
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


    @classmethod
    def query_entities(cls, db: Session, query_text: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query verified AIT entities matching program names, subjects, facilities, fees, etc.
        Implements multi-stage matching: exact phrase, cleaned phrase, and tokenized rank matching.
        """
        q = db.query(AitEntity).filter(AitEntity.is_verified == True)
        if category:
            q = q.filter(AitEntity.category == category)

        raw_clean = query_text.strip().lower()

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

        if entities:
            return [cls._to_dict(e) for e in entities]

        # 2. Second attempt: Clean college stopwords (e.g. 'ait fees' -> 'fees')
        tokens = cls.clean_search_tokens(query_text)
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

        if entities:
            return [cls._to_dict(e) for e in entities]

        # 3. Third attempt: Individual token match across entities
        # E.g. for "bca fees", match entities containing "bca" and "fees"
        matched_candidates = []
        all_verified = q.all()

        is_faculty_query = any(w in raw_clean for w in ["who teaches", "faculty", "professor", "teacher", "sir", "madam", "hod", "coordinator", "padhave", "padhata"])
        is_fee_query = any(w in raw_clean for w in ["fee", "fees", "tuition", "cost", "charge", "kitni", "ketli"])
        is_placement_query = any(w in raw_clean for w in ["placement", "package", "recruiter", "recruiters", "tpo", "placed"])
        is_facility_query = any(w in raw_clean for w in ["library", "lab", "canteen", "sports", "facility", "facilities", "classroom", "ground"])
        is_admission_query = any(w in raw_clean for w in ["admission", "admissions", "apply", "form", "acpc", "dates", "schedule", "when to fill", "kab bharna", "kyare", "when is"])

        for e in all_verified:
            entity_blob = f"{e.name} {e.code or ''} {e.category} {str(e.details)}".lower()
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

            # Domain Category Boost
            if is_faculty_query and e.category == "faculty":
                score += 10
            elif is_placement_query and e.category == "placement":
                score += 10
            elif is_facility_query and e.category == "facility":
                score += 8
            elif is_fee_query and ("annual_fees" in str(e.details).lower() or "sem_fees" in str(e.details).lower()):
                score += 6
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

            if score > 0:
                matched_candidates.append((score, e))

        # Sort by match score descending
        matched_candidates.sort(key=lambda x: x[0], reverse=True)
        return [cls._to_dict(e) for score, e in matched_candidates[:5]]


    @classmethod
    def query_website_snapshots(cls, db: Session, query_text: str) -> List[Dict[str, Any]]:
        """Queries official crawled AIT website page snapshots."""
        tokens = cls.clean_search_tokens(query_text)
        if not tokens:
            tokens = re.findall(r'[a-zA-Z0-9]+', query_text.lower())

        snapshots = db.query(WebsiteSnapshot).all()
        results = []
        for s in snapshots:
            content_lower = f"{s.title or ''} {s.url} {s.text_content}".lower()
            score = sum(1 for t in tokens if t in content_lower)
            if score > 0:
                results.append((score, s))

        results.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "url": s.url,
                "title": s.title,
                "text_content": s.text_content,
                "source_domain": "aitindia.in"
            }
            for score, s in results[:3]
        ]

    @classmethod
    def get_by_category(cls, db: Session, category: str) -> List[Dict[str, Any]]:
        entities = db.query(AitEntity).filter(
            AitEntity.category == category,
            AitEntity.is_verified == True
        ).all()

        return [cls._to_dict(e) for e in entities]

    @classmethod
    def _to_dict(cls, e: AitEntity) -> Dict[str, Any]:
        return {
            "id": e.id,
            "name": e.name,
            "code": e.code,
            "category": e.category,
            "details": e.details,
            "source_url": e.source_url,
            "source_page": e.source_page,
            "authority": e.authority,
            "is_verified": e.is_verified,
            "verified_at": e.verified_at.isoformat() if e.verified_at else None
        }

knowledge_db = KnowledgeDatabase()
