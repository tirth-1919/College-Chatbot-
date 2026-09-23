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
    # §SPEC: location/address questions must reach the tenant's contact record
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
    def query_entities(cls, db: Session, query_text: str, category: Optional[str] = None,
                       college_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query verified entities matching program names, subjects, facilities, fees, etc.
        Implements multi-stage matching: exact phrase, cleaned phrase, and tokenized rank matching.
        CRITICAL (§17): when college_id is provided the query is tenant-filtered
        FIRST — records from other colleges can never be returned.
        """
        q = db.query(AitEntity).filter(AitEntity.is_verified == True)
        if college_id:
            q = q.filter(AitEntity.college_id == college_id)
        if category:
            q = q.filter(AitEntity.category == category)

        raw_clean = query_text.strip().lower()
        requested_years = re.findall(r"20\d{2}\s*[-/]\s*\d{2,4}", raw_clean)
        is_fee_query = any(w in raw_clean for w in ["fee", "fees", "tuition", "cost", "charge", "kitni", "ketli"])

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

        entities = [entity for entity in entities if year_specific_match(entity)]

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

            # Hard guard: a committee/governance query may only be answered by
            # committee-category entities. Facility/faculty/program matches
            # (e.g. "AIT Central Library" for "library chairman?") are wrong
            # answers, not weak matches — so exclude them outright. If no
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

            if score > 0:
                matched_candidates.append((score, e))

        # Sort by match score descending
        matched_candidates.sort(key=lambda x: x[0], reverse=True)
        return [cls._to_dict(e) for score, e in matched_candidates[:5]]


    @classmethod
    def query_website_snapshots(cls, db: Session, query_text: str,
                                college_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Queries official crawled website page snapshots with improved filtering.
        §18: tenant-scoped — only the resolved college's official pages."""
        tokens = cls.clean_search_tokens(query_text)
        sq = db.query(WebsiteSnapshot)
        if college_id:
            sq = sq.filter(WebsiteSnapshot.college_id == college_id)
        snapshots = sq.all()
        normalized_query = re.sub(r"[^a-z0-9 ]+", " ", query_text.lower())
        program_terms = [term for term in [
            "bca", "mca", "bba", "mba", "cse", "computer engineering",
            "information technology", "it engineering", "mechanical", "civil",
            "electrical", "electronics"
        ] if re.search(rf"\b{re.escape(term)}\b", normalized_query)]
        committee_terms = [t for t in re.findall(r"[a-z0-9]+", normalized_query)
                           if t not in STOPWORDS and t not in {"chairman", "chairperson", "head", "heads", "list", "members", "member", "all"}]
        is_section_query = any(t in normalized_query for t in ["committee", "council", "squad", "cell", "iqac"])
        is_intake_query = any(t in normalized_query for t in ["intake", "total student", "student intake", "number of courses"])
        is_catalog_query = "catalog" in normalized_query or ("academic" in normalized_query and "catalog" in normalized_query)
        if is_catalog_query and not is_section_query and not is_intake_query:
            # Return program entities for catalog queries
            program_entities = [cls._to_dict(e) for e in db.query(AitEntity).filter(
                AitEntity.category == "program", AitEntity.is_verified == True
            ).order_by(AitEntity.name.asc()).all()]
            # Transform program entities to snapshot format for consistency
            return [{
                "url": e.get("source_url", ""),
                "title": e.get("name", ""),
                "section_title": "Program",
                "text_content": str(e.get("details", {})),
                "content": str(e.get("details", {})),
                "source_domain": "aitindia.in",
                "authority": "Official AIT Knowledge Base",
                "verification_status": "Verified"
            } for e in program_entities]
        if not tokens:
            tokens = re.findall(r'[a-zA-Z0-9]+', query_text.lower())

        # §18: tenant-scoped — reuse the already-filtered snapshot set. Never widen
        # back to all snapshots or other colleges' pages could be returned.
        snapshots = [s for s in snapshots if s.college_id == college_id] if college_id else snapshots
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
            content_lower = s.text_content.lower()
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
            if len(s.text_content) < 100 and not is_committee_page:
                continue

            title_lower = (s.title or '').lower()
            url_lower = (s.url or '').lower()
            full_content_lower = f"{title_lower} {url_lower} {s.text_content}".lower()
            if program_terms and not any(
                re.search(rf"\b{re.escape(term)}\b", full_content_lower)
                for term in program_terms
            ):
                continue
            score = sum(1 for t in tokens if re.search(rf"\b{re.escape(t)}\b", full_content_lower))

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
            if score > 0:
                results.append((score, s))

        # §18/§30: provenance must belong to the college that owns the snapshot
        college_map = {}
        for s in snapshots:
            if s.college_id and s.college_id not in college_map:
                from backend.app.models.college import College as _College
                _c = db.query(_College).filter(_College.id == s.college_id).first()
                college_map[s.college_id] = _c

        results.sort(key=lambda x: x[0], reverse=True)
        response = []
        for score, s in results[:3]:
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
                "url": s.url,
                "title": s.title,
                "section_title": section_title,
                "text_content": content,
                "content": content,
                "source_domain": source_domain,
                "authority": authority,
                "verification_status": "Official source"
            })
        return response

    @classmethod
    def get_by_category(cls, db: Session, category: str,
                        college_id: Optional[str] = None) -> List[Dict[str, Any]]:
        q = db.query(AitEntity).filter(
            AitEntity.category == category,
            AitEntity.is_verified == True
        )
        if college_id:
            q = q.filter(AitEntity.college_id == college_id)
        entities = q.order_by(AitEntity.name.asc()).all()

        return [cls._to_dict(e) for e in entities]

    @classmethod
    def _to_dict(cls, e: AitEntity) -> Dict[str, Any]:
        return {
            "id": e.id,
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
