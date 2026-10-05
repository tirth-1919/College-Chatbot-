from typing import List, Dict, Any, Optional
import re

def _terms(value):
    """Comparable whole words, including simple plural variants (not substrings)."""
    words = re.findall(r"[a-z0-9]+", str(value or "").lower())
    return {w[:-3] + "y" if w.endswith("ies") and len(w) > 4 else
            w[:-1] if w.endswith("s") and len(w) > 4 else w for w in words}


def evidence_relevance(item, spec):
    """Return a source-independent score, or None for an ineligible item.

    Structured subject fields take precedence over incidental words in a page
    body. A general page needs a strong subject signal, not a navigation link.
    """
    if spec is None or not spec.college_id or item.get("college_id") != spec.college_id:
        return None
    if item.get("verified") is False or str(item.get("status", "ACTIVE")).upper() != "ACTIVE":
        return None
    if item.get("source_type") in ("entity_db", *ADMIN_DB_SOURCE_TYPES) and item.get("verified") is not True:
        return None
    if item.get("source_type") == "website_snapshot" and item.get("active") is False:
        return None
    metadata = item.get("content") if isinstance(item.get("content"), dict) else {}
    if not metadata and isinstance(item.get("details"), dict):
        metadata = item.get("details")
    program = (
        item.get("program") or metadata.get("program") or metadata.get("course")
        or item.get("course")
    )
    expected = ResponseBuilder._program_family(spec.program) if spec.program else None
    actual = ResponseBuilder._program_family(program) if program else None
    general = str(program or "").lower() in {"", "all programs", "all courses", "general", "general program"}
    if expected and program and not general and (actual or _terms(program) != _terms(spec.program)) and actual != expected:
        return None
    # A named program in a record title is a program restriction even when its
    # structured course field is missing. Never treat body mentions as ownership.
    if expected and general and item.get("source_type") != "website_snapshot":
        title_family = ResponseBuilder._program_family(item.get("title"))
        if title_family and title_family != expected:
            return None
    year = str(item.get("academic_year") or metadata.get("academic_year") or "").replace(" ", "")
    if spec.academic_year and year and year != str(spec.academic_year).replace(" ", ""):
        return None
    subject = _terms(spec.category or spec.topic or spec.intent)
    canonical_topic = str(spec.topic or spec.category or "").strip()
    subject -= {"unknown", "general", "ait", "institutional"}
    topic_aliases = {
        "course": {"course", "program", "degree", "academic"},
        "program": {"course", "program", "degree", "academic"},
        "facilitie": {"facilitie", "facility", "amenitie", "resource"},
        "admission": {"admission", "application", "enrol"},
        "fee": {"fee", "fees", "tuition", "tuition_fee"},
        "fees": {"fee", "fees", "tuition", "tuition_fee"},
        "event": {"event", "events", "news", "announcement", "notice", "circular", "activity", "seminar", "workshop", "festival", "hackathon", "cultural", "calendar", "fest"},
    }
    identity = _terms(getattr(spec, "college_name", "") or "") | _terms(
        getattr(spec, "college_code", "") or "")
    question = _terms(spec.retrieval_text) - {
        "what", "which", "where", "available", "college", "students", "student",
        "at", "for", "the", "are", "is", "in", "of", "ait", "rcti", "and", "or",
    } - identity
    # Admission subtopics are children of the admission topic.  Preserve the
    # child as an additional generic subject signal so documents/eligibility
    # records can ground the parent topic without category-specific branches.
    if (str(spec.topic or spec.category or "").upper() == "ADMISSION"
            and spec.requested_field and _terms(spec.requested_field) & question):
        subject |= _terms(spec.requested_field)
    # A generic request for the institution's "facilities" has no single
    # subject, so the concrete facility in the question (library, hostel,
    # transportation, canteen, ...) supplies the constraint instead.
    #
    # P0.5: the ACTIVE COLLEGE'S OWN IDENTITY IS NEVER PART OF THE SUBJECT.
    # Every institutional question names the college, so leaving "Ahmedabad /
    # Institute / Technology" in the subject made any college-owned page look
    # relevant regardless of what it actually said. Identity is enforced by the
    # college_id hard check above; it must not also act as a topical signal.
    if subject & {"facilitie", "facility"}:
        concrete = _terms(spec.entity) | _terms(spec.facilities)
        # Do not expand a generic facilities request into every concrete
        # facility category.  Only an explicit entity/facility on the spec is
        # allowed to narrow the answer to Library, Hostel, Transport, etc.
        subject = concrete or (question - {"facilitie", "facility", "data", "science", "general"})
        if not subject:
            subject = question
    # A question about a topic the record set does not label (for example
    # scholarships) falls back to the question's own content words.
    # Query topic can be generic (e.g. FACULTY) while the spec's entity is the
    # requested subject (DBMS). Keep that entity as a required semantic term.
    # For specific recognized topics, it complements rather than replaces the
    # topic so unrelated faculty pages cannot pass.
    if spec.entity and _terms(spec.entity) & question:
        subject |= _terms(spec.entity)
    if subject and not (subject & question) and not _terms(canonical_topic) & {"event", "news", "announcement", "notice", "circular", "activity", "seminar", "workshop", "festival", "hackathon", "cultural", "calendar", "fest"}:
        fallback = question - {"facilitie", "facility", "data", "science", "general"}
        if fallback:
            subject = fallback
    if not subject:
        subject = question
    # A typographical normalization that preserves a canonical topic should not
    # require its canonical spelling to appear in the raw lexical carrier.
    if canonical_topic and canonical_topic.upper() not in {"UNKNOWN", "GENERAL", "INSTITUTIONAL"}:
        subject |= _terms(canonical_topic)
    # Canonical aliases provide a shared vocabulary to the generic relevance
    # calculation; they do not define category-specific answer handling.
    canonical_alias_terms = set().union(*(
        topic_aliases.get(term, set()) for term in _terms(canonical_topic)
    ))
    if canonical_alias_terms:
        subject = canonical_alias_terms | _terms(canonical_topic)
    if str(spec.topic or spec.category or "").upper() == "ADMISSION" and spec.requested_field:
        subject |= _terms(spec.requested_field)
    # A specific field is a subject signal, not merely an answer decoration.
    field = _terms(spec.requested_field)
    if (field and not (field & {"facilitie", "facility", "fee", "tuition", "tuition_fee"})
            and field & question):
        subject |= field
    if spec.entity and _terms(spec.entity) & question:
        subject |= _terms(spec.entity)
    if getattr(spec, "temporal_qualifier", None):
        subject -= {"latest", "recent", "current", "newest", "upcoming", "forthcoming"}
    category = _terms(item.get("category"))
    topic = _terms(item.get("topic"))
    field_terms = _terms(item.get("field") or (item.get("details") or {}).get("field_name") if isinstance(item.get("details"), dict) else item.get("field"))
    title = _terms(item.get("title") or item.get("name"))
    url = _terms(item.get("source_url") or (item.get("details") or {}).get("source_url") if isinstance(item.get("details"), dict) else item.get("source_url"))
    entity = _terms(item.get("entity"))
    body = _terms(" ".join(str(item.get(k) or "") for k in ("value", "content", "description", "summary", "answer")))
    if isinstance(item.get("details"), dict):
        body |= _terms(" ".join(
            str(v) for k, v in item["details"].items()
            if k in ("value", "content", "summary", "description", "answer") and isinstance(v, (str, int, float))
        ))
    elif isinstance(item.get("details"), str):
        # A snapshot's readable body lives in `details`. Excluding it made every
        # page look content-free, so a genuinely relevant official page could
        # never be selected by what it actually says.
        body |= _terms(item["details"])
    # Prefix families: admission_documents belongs to admission, but a fee
    # record cannot become facilities just because its value mentions campus.
    def related(a, b):
        return bool(a and b and (a & b or any(x.startswith(y + "_") or y.startswith(x + "_") for x in a for y in b)))

    # P0.3: a sub-topic is evidence for its parent topic, generically. An
    # `admission_documents` or `eligibility` record answers an "admission"
    # question, and an admission question is satisfied by any of its
    # sub-topics -- without any per-category branch. The relationship is
    # expressed once, as data, so new sub-topics need no new code.
    SUBTOPIC_PARENTS = ("ADMISSION",)
    wanted = {str(spec.category or spec.topic or spec.intent or "").lower().replace("-", "_")}
    for _parent in SUBTOPIC_PARENTS:
        if spec.requested_field or spec.subtopic:
            wanted.add(_parent.lower())
    label = {str(item.get("category") or "").lower().replace("-", "_")}
    category_hit = related(category, subject) or related(label, wanted)
    topic_hit = related(topic, subject)
    field_hit = related(field_terms, field) if field else False
    title_hit = related(title, subject)
    url_hit = related(url, subject)
    body_hit = related(body, subject) or bool(canonical_alias_terms & body)
    # P0.5: a record's `category` is a source-side LABEL, not a hard
    # constraint on the question's subject -- exactly like a page title. An
    # "About" page can list courses, a "program" record carries eligibility,
    # and a "faculty" record carries the subject being taught. The label is
    # therefore a ranking signal only; the hard constraints that remain are
    # college identity, program family, academic year and verification status.
    if subject and not (category_hit or topic_hit or title_hit or url_hit or field_hit or body_hit):
        return None
    # A website without a structured label needs the requested subject in its
    # title/URL, or a genuinely focused body (not a single menu/nav mention).
    if item.get("source_type") == "website_snapshot" and subject and not (category_hit or topic_hit or title_hit or url_hit):
        text = str(item.get("value") or (item.get("details") or "") or "").lower()
        hits = sum(len(re.findall(rf"\b{re.escape(term)}s?\b", text)) for term in subject if len(term) > 2)
        if hits < 2 and not related(_terms(text), subject):
            return None
    # Admission subtopics may be represented by structured keys (for example
    # `eligibility`) while the record's primary category is simply `program`.
    # Keep structured-key names as relevance signals without flattening them
    # into the answer text.
    structured_metadata = item.get("metadata")
    if isinstance(item.get("details"), dict):
        structured_metadata = {**item["details"], **(structured_metadata or {})} if isinstance(structured_metadata, dict) else item["details"]
    if isinstance(structured_metadata, dict):
        structured_keys = _terms(" ".join(str(k) for k in structured_metadata.keys()))
        if structured_keys & subject:
            body_hit = True
    # An unlabelled DB record needs a subject in its title, field or value.
    if not category and not topic and subject and not (title_hit or field_hit or body_hit):
        return None
    # P0.5: a body-only hit is evidence when the page CONTENT actually
    # discusses the subject, not when it merely names it once inside unrelated
    # navigation. Focus is measured generically: repeated mentions, or several
    # distinct subject terms.
    focused_body = False
    if body_hit:
        raw_text = " ".join(
            str(item.get(k) or "") for k in ("value", "content", "summary", "answer")
        )
        if isinstance(item.get("details"), dict):
            raw_text += " " + " ".join(
                str(v) for k, v in item["details"].items()
                if k in ("value", "content", "summary", "description", "answer")
                and isinstance(v, (str, int, float))
            )
        elif isinstance(item.get("details"), str):
            raw_text += " " + item["details"]
        raw_text = raw_text.lower()
        subject_terms = {t for t in subject if len(t) > 2}
        mentions = sum(
            len(re.findall(rf"\b{re.escape(t)}(?:s|es)?\b", raw_text))
            for t in subject_terms
        )
        covered = len({t for t in subject_terms if re.search(rf"\b{re.escape(t)}(?:s|es)?\b", raw_text)})
        focused_body = mentions >= 2 or covered >= 2
    if body_hit and not (category_hit or topic_hit or title_hit or url_hit or field_hit) and not focused_body:
        return None
    # A structured field can independently identify the requested subject even
    # when the parent record label (e.g. faculty/program) is broader.
    structured_topic_hit = bool(
        isinstance(item.get("details"), dict)
        and _terms(canonical_topic) & _terms(" ".join(item["details"].keys()))
    )
    if item.get("source_type") == "website_snapshot" and canonical_alias_terms:
        body_facets = _terms(" ".join(
            str(item.get(key) or "")
            for key in ("details", "content", "summary", "description", "value", "answer")
        ))
        substantive_terms = canonical_alias_terms - {"events", "activity", "calendar"}
        if not (substantive_terms & body_facets):
            return None
    # A generic source label is not enough to establish a match. For a body-only
    # candidate, require multiple distinct subject terms or repeated mentions.
    # Temporal words are ranking qualifiers, not required topic facets.
    subject -= {"latest", "recent", "current", "newest", "upcoming", "forthcoming"}
    # Normalize every evidence facet into one relevance representation. Metadata
    # and page dates can contribute, but a page label alone cannot establish
    # content relevance: the body must still substantiate the requested topic.
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else metadata
    evidence_text = " ".join(
        str(item.get(key) or "") for key in (
            "topic", "category", "title", "name", "source_url", "url",
            "summary", "description", "value", "answer",
        )
    )
    if isinstance(metadata, dict):
        evidence_text += " + " + " ".join(
            str(value) for value in metadata.values()
            if isinstance(value, (str, int, float))
        )
    evidence_terms = _terms(evidence_text)
    canonical_topic_hit = bool(_terms(canonical_topic) & evidence_terms)
    # A canonical topic plus real body-topic overlap, or a focused body with
    # multiple distinct subject concepts, handles typos and About-page facts
    # without treating incidental navigation/title words as evidence.
    topic_body_terms = _terms(" ".join(
        str(item.get(key) or "") for key in ("value", "summary", "description", "answer")
    ))
    for key in ("details", "content"):
        value = item.get(key)
        if isinstance(value, str):
            topic_body_terms |= _terms(value)
        elif isinstance(value, dict):
            topic_body_terms |= _terms(" ".join(
                str(v) for v in value.values() if isinstance(v, (str, int, float))
            ))
    metadata_terms = _terms(" ".join(
        str(value) for value in metadata.values() if isinstance(value, (str, int, float))
    )) if isinstance(metadata, dict) else set()
    topic_body_terms |= metadata_terms
    canonical_topic_terms = _terms(canonical_topic)
    topic_body_vocabulary = canonical_topic_terms | canonical_alias_terms
    topic_body_hit = bool(topic_body_vocabulary & topic_body_terms)
    if canonical_alias_terms:
        structured_topic_hit = structured_topic_hit or bool(
            canonical_alias_terms & (category | topic | title | url)
        )
        content_topic_hit = bool(canonical_alias_terms & topic_body_terms)
    else:
        content_topic_hit = False
    focused_subject_terms = subject & topic_body_terms
    semantic_match = bool(
        topic_body_hit or content_topic_hit or structured_topic_hit or len(focused_subject_terms) >= 2
        or (canonical_topic_hit and len(focused_subject_terms) >= 1)
        or ((category_hit or topic_hit) and body_hit)
        or ((title_hit or url_hit or field_hit) and body_hit)
    )
    if canonical_topic and not semantic_match:
        return None
    score = (30 * category_hit + 25 * topic_hit + 20 * title_hit +
             15 * url_hit + 12 * field_hit + 5 * body_hit +
             8 * related(entity, _terms(spec.entity)) +
             10 * bool(expected and actual == expected) +
             4 * bool(spec.academic_year and year == str(spec.academic_year).replace(" ", "")) +
             12 * canonical_topic_hit + 8 * topic_body_hit +
             4 * bool(canonical_topic_hit and semantic_match) +
             12 * structured_topic_hit)
    return score

# Admin knowledge-store source types that count as a database record.
ADMIN_DB_SOURCE_TYPES = ("ADMIN_VERIFIED", "ADMIN_UPLOAD", "ADMIN_MANAGED")

# P0.3: the GENERIC ordered list of fields that may carry an evidence item's
# answer text. This is data about where sources store their facts, not a
# per-category rule: any source that publishes its value in one of these fields
# normalises without code changes.
NORMALIZABLE_TEXT_FIELDS = (
    "value", "answer", "content", "summary", "description",
)

# Fields that identify a record rather than stating its facts. They are read
# for identity/subject matching only and must never become the answer text.
NORMALIZABLE_NON_TEXT_FIELDS = (
    "field", "field_name", "program", "academic_year",
)

class ResponseBuilder:
    @staticmethod
    def _program_family(value):
        """Map a program string onto a coarse family for mismatch checks.

        Delegates to the shared grounding helper so evidence normalization
        and grounding validation cannot disagree.
        """
        from backend.app.knowledge.grounding import ResponseBuilderProgramFamily

        return ResponseBuilderProgramFamily(value)

    @staticmethod
    def _is_general_program(value) -> bool:
        """
        True when a `course`/program label is institution-wide rather than a
        specific degree ("All Programs", "General", ...).

        Such a record must never be phrased as if it were about a program.
        """
        return _terms(value) <= {
            "all", "program", "programme", "course", "courses", "general",
            "any", "institution", "college", "university",
        }

    @staticmethod
    def _canonical_program(value):
        """
        Reduce a program label to its short canonical form.

        "BCA (Bachelor of Computer Applications)" -> "BCA"
        "Data Science"                              -> "Data Science"
        "R.C. Technical Institute"                   -> None (not a program)
        """
        if not value:
            return None
        text = str(value).split("(", 1)[0].strip()
        return text or None

    @staticmethod
    def evidence_matches_spec(item: Dict[str, Any], query_spec) -> bool:
        """
        P0.1: QuerySpec-based relevance / mismatch validation.

        Rejects evidence that would silently reinterpret the question:
          * evidence from ANOTHER college
          * a different program family (BCA -> BBA / BCA -> Data Science)
          * a record whose status was not ACTIVE
          * a record that is explicitly UNVERIFIED
        """
        if query_spec is None:
            return True
        expected_college = getattr(query_spec, "college_id", None)
        if expected_college:
            item_college = item.get("college_id")
            if item_college and item_college != expected_college:
                return False
        # Verification / status are NEVER downgraded by this stage.
        if item.get("verified") is False:
            return False
        if str(item.get("status") or "ACTIVE").upper() != "ACTIVE":
            return False
        if item.get("source_type") == "website_snapshot" and item.get("active") is False:
            return False
        expected_program = getattr(query_spec, "program", None)
        if expected_program:
            candidate = item.get("program") or item.get("course")
            if candidate:
                expected_family = ResponseBuilder._program_family(expected_program)
                candidate_family = ResponseBuilder._program_family(candidate)
                if expected_family and candidate_family and expected_family != candidate_family:
                    return False
        expected_year = getattr(query_spec, "academic_year", None)
        if expected_year:
            item_year = str(item.get("academic_year") or "")
            details = str(item.get("content") or item.get("description") or "")
            needle = str(expected_year).replace(" ", "")
            haystack = item_year.replace(" ", "")
            if needle not in haystack and needle not in details.replace(" ", ""):
                return False
        return True

    @classmethod
    def normalize_evidence(cls, evidence: List[Dict[str, Any]], query_spec=None) -> List[Dict[str, Any]]:
        # ------------------------------------------------------------------
        # P0.1: normalize_evidence receives the QuerySpec.
        #
        # Every normalized item retains the full evidence contract:
        #   source_type, source_record_id, college_id, college_name, title,
        #   category, topic, program, entity, academic_year, field, value,
        #   content, description, source_url, verified, status
        #
        # Mismatch validation is done against the QuerySpec -- never against
        # a re-parsed question.
        # ------------------------------------------------------------------
        normalized = []
        for item in evidence or []:
            details = item.get("details") or item.get("content") or ""
            metadata = details if isinstance(details, dict) else {}
            if isinstance(details, dict) and not details.get("content") and not details.get("value") and not details.get("answer"):
                details = dict(details)
                details["content"] = details.get("summary") or details.get("description") or ""
                metadata = details
            # P0.3: the normalizer must be able to read a record's answer text
            # from ANY of the generic fields a source may populate. Previously
            # only content/value/answer/summary/description were consulted, so
            # a record whose text lived in `metadata.content`, `field`,
            # `field_name`, `program` or `academic_year` normalised to an EMPTY
            # value and was silently dropped by the grounding gate.
            text = ""
            for _key in NORMALIZABLE_TEXT_FIELDS:
                candidate = metadata.get(_key) if metadata else None
                if candidate in (None, "") or isinstance(candidate, (dict, list, tuple, set)):
                    candidate = item.get(_key)
                if candidate in (None, "") or isinstance(candidate, (dict, list, tuple, set)):
                    continue
                text = str(candidate).strip()
                if text:
                    break
            # P0.3 (defect 1): `value` is preserved EXACTLY when it is the
            # only text a record carries. When a record publishes BOTH a short
            # `value`/`summary` label and a richer `content`/`answer` body (an
            # extracted document whose summary is a one-line label), the
            # complete published text must win -- otherwise the answer silently
            # drops the actual document requirements and shows only the label.
            longer = text
            for _key in NORMALIZABLE_TEXT_FIELDS:
                for _source in (metadata or {}, item):
                    candidate = _source.get(_key)
                    if candidate in (None, "") or isinstance(candidate, (dict, list, tuple, set)):
                        continue
                    candidate = str(candidate).strip()
                    if len(candidate) > len(longer):
                        longer = candidate
            # `metadata.content` is commonly a complete uploaded section while
            # `value`/`summary` is only its short preview. Treat the metadata
            # content as published factual text in the same generic candidate
            # pool, preserving all metadata in the normalized contract below.
            if metadata and isinstance(metadata.get("content"), str):
                candidate = metadata["content"].strip()
                if len(candidate) > len(longer):
                    longer = candidate
            if metadata and isinstance(metadata.get("content"), str) and metadata.get("content").strip():
                # The uploaded section is the complete factual source. Prefer it
                # over a short value even when the record carries a program label.
                text = metadata["content"].strip()
            text = longer
            # Ensure the factual value/content channel wins over a short label
            # or source summary when both are published on the same record.
            # Content remains separately preserved below as metadata/content.
            factual_body = metadata.get("content") if metadata else None
            if isinstance(factual_body, str) and len(factual_body.strip()) > len(str(text or "")):
                text = factual_body.strip()
            if item.get("source_type") == "website_snapshot":
                # A website page's readable body IS the page, not the flattened
                # metadata dictionary, so a related record cannot inherit the
                # page's unrelated stored sections.
                text = details if isinstance(details, str) else (metadata.get("content") or "")
            # P0.3: when a record publishes MANY structured fields (a program
            # record carrying eligibility, duration, fees, seats, curriculum),
            # the whole flattened bag is not the answer. Select the field the
            # question actually asked about, using the SAME generic relevance
            # mechanism, and answer with that field alone. This is field-level
            # selection, not a per-category answer branch.
            selected_detail = None
            if isinstance(details, dict) and query_spec is not None:
                selected_detail = cls._select_detail_field(details, item, query_spec)
                if selected_detail:
                    text = selected_detail
            # The record serializer retains the complete Smart Upload payload in
            # metadata.content. When there is no narrower structured field
            # selected, prefer the complete relevant section to a short preview.
            full_section = metadata.get("content") if metadata else None
            if not selected_detail and isinstance(full_section, str) and len(full_section.strip()) > len(str(text or "")):
                content_probe = dict(item, value=full_section, details=full_section)
                if query_spec is None or evidence_relevance(content_probe, query_spec) is not None:
                    text = full_section.strip()
            if isinstance(text, dict):
                structured_text = text
                text = ". ".join(
                    str(value).strip() for value in structured_text.values()
                    if isinstance(value, (str, int, float)) and str(value).strip()
                )
            if metadata and not text:
                text = ". ".join(str(value).strip() for value in metadata.values() if isinstance(value, (str, int, float)) and str(value).strip())
            if not text:
                text = item.get("value") or item.get("description")
            # P0.3: a record that publishes NOTHING in a text field can still
            # be identified by one of its identity fields. This is the last
            # resort ONLY -- a real value always wins above.
            if not text:
                for _key in NORMALIZABLE_NON_TEXT_FIELDS:
                    candidate = metadata.get(_key) if metadata else None
                    if candidate in (None, "") or isinstance(candidate, (dict, list, tuple, set)):
                        candidate = item.get(_key)
                    if candidate in (None, "") or isinstance(candidate, (dict, list, tuple, set)):
                        continue
                    text = str(candidate).strip()
                    if text:
                        break
            # A record may carry its text ONLY in `details` as a plain string.
            if not text and isinstance(details, str):
                text = details.strip()
            normalized_item = {
                "source_type": item.get("source_type"),
                "source_record_id": item.get("id") or item.get("source_record_id"),
                "college_id": item.get("college_id"),
                "college_name": item.get("college_name") or metadata.get("college_name"),
                "title": item.get("name") or item.get("title") or "",
                "category": item.get("category") or metadata.get("category"),
                "topic": item.get("topic") or metadata.get("topic"),
                "program": metadata.get("program") or metadata.get("course") or item.get("course") or item.get("program"),
                "entity": item.get("entity") or metadata.get("entity"),
                "academic_year": metadata.get("academic_year") or item.get("academic_year"),
                "field": metadata.get("field") or metadata.get("field_name") or item.get("field_name") or item.get("field"),
                "value": text,
                "content": details,
                "description": metadata.get("description") if metadata else item.get("description"),
                "answer": metadata.get("answer") if metadata else item.get("answer"),
                # Preserve source metadata as an independent EvidenceItem field;
                # keeping `content` as the usable answer text lets field
                # extraction and grounding see structured subtopic keys.
                "metadata": metadata,
                "source_url": item.get("source_url") or item.get("url") or "",
                "verified": item.get("verified", True),
                "status": item.get("status", "ACTIVE"),
                "authority": item.get("authority"),
                "section": item.get("section"),
                "summary": metadata.get("summary") or item.get("summary"),
                "active": item.get("active", True),
                "last_crawled_at": item.get("last_crawled_at") or metadata.get("last_crawled_at"),
                "created_at": item.get("created_at") or metadata.get("created_at"),
                "updated_at": item.get("updated_at") or metadata.get("updated_at"),
                "date": item.get("date") or metadata.get("date"),
                "event_date": item.get("event_date") or metadata.get("event_date"),
                "published_at": item.get("published_at") or metadata.get("published_at"),
                "publication_date": item.get("publication_date") or metadata.get("publication_date"),
                "relevance_score": item.get("relevance_score"),
            }
            if query_spec is not None and evidence_relevance(normalized_item, query_spec) is None:
                continue
            normalized.append(normalized_item)
        return normalized
    @classmethod
    def _select_detail_field(cls, details: Dict[str, Any], item: Dict[str, Any], query_spec):
        """
        Choose the ONE structured field of `details` that answers the question.

        Generic: every scalar field is scored with the shared
        `evidence_relevance` mechanism against the QuerySpec, and the best
        scoring field is returned. Returns None when the record has a single
        scalar field (no selection is possible or needed) or when no field is
        relevant, so the normal full-text behaviour is preserved.

        Only non-identity scalar fields of `details` are candidates.
        """
        scalars = {
            key: value for key, value in (details or {}).items()
            if isinstance(value, (str, int, float)) and str(value).strip()
            # P0.5: identity/metadata keys describe the record, they never
            # state its facts. A record storing {"field_name": "tuition_fee",
            # "course": "BCA", "value": "INR 32,000"} must answer with the
            # value, never with the label "tuition_fee" that merely repeats
            # the question.
            and key not in NORMALIZABLE_NON_TEXT_FIELDS
            and key not in ("course", "program", "category", "topic", "id")
        }
        if len(scalars) <= 1:
            return None
        base = {
            "source_type": item.get("source_type"),
            "college_id": item.get("college_id"),
            "title": item.get("name") or item.get("title") or "",
            "category": item.get("category") or (item.get("details") or {}).get("category"),
            "program": (item.get("details") or {}).get("course") or item.get("course"),
            "verified": item.get("verified", True),
            "status": item.get("status", "ACTIVE"),
            "active": item.get("active", True),
        }
        best_key, best_score = None, 0
        wanted_field = str(getattr(query_spec, "requested_field", "") or "").lower()
        wanted_subtopic = str(getattr(query_spec, "subtopic", "") or "").lower()
        # Query understanding may express a subtopic through a normalized field
        # (eligibility/tuition_fee) rather than setting `subtopic` directly.
        # Use the shared field vocabulary to match common stored key variants.
        field_aliases = {
            "eligibility": {"eligibility", "eligibility_criteria", "criteria", "qualification"},
            "admission_eligibility": {"eligibility", "eligibility_criteria", "criteria", "qualification"},
            "tuition_fee": {"fee", "fees", "annual_fee", "annual_fees", "semester_fee", "semester_fees"},
            "required_documents": {"documents", "admission_documents", "required_documents", "document_checklist"},
            "admission_documents": {"documents", "admission_documents", "required_documents", "document_checklist"},
        }
        exact_wanted = field_aliases.get(wanted_field, {wanted_field} if wanted_field else set())
        if wanted_subtopic:
            exact_wanted |= field_aliases.get(wanted_subtopic, {wanted_subtopic})
        if wanted_field:
            exact_wanted.add(wanted_field)
        if wanted_subtopic:
            exact_wanted.add(wanted_subtopic)
        if wanted_field == "eligibility":
            exact_wanted |= field_aliases["eligibility"]
        for key, value in scalars.items():
            # Generic storage keys carry answer text, not subtopic identity.
            # Let the full-content preference below resolve `value` versus
            # `content`; only semantic field names can narrow the answer.
            if str(key).lower() in {"value", "content", "summary", "description", "answer"}:
                continue
            # Prefer an exact structured field name when QuerySpec asks for a
            # specific subtopic (e.g. eligibility vs duration/fees/curriculum).
            key_normalized = re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")
            if exact_wanted and key_normalized in {v.replace(" ", "_") for v in exact_wanted}:
                best_key, best_score = key, 10_000
                continue
            if best_score >= 10_000:
                continue
            probe = dict(
                base,
                # The field's own name is a subject signal, exactly as a record
                # category would be for a titled record.
                field=key,
                category=key,
                topic=key,
                title=key,
                value=str(value),
                details=str(value),
                # The record's own fields are not competing evidence.
                **{"content": None, "description": None, "summary": None, "answer": None},
            )
            score = evidence_relevance(probe, query_spec)
            if score is not None and score > best_score:
                best_key, best_score = key, score
        if best_key is None:
            return None
        return str(scalars[best_key]).strip()

    @classmethod
    def build_grounded_answer(cls, evidence: List[Dict[str, Any]], query_spec=None, query: str = "") -> str:
        """
        P0.1: the answer is built from QuerySpec + normalized EvidenceItems.

        It does NOT need the raw question to determine program / category /
        year -- those come from `query_spec`.  The `query` argument is kept
        only for optional natural-language phrasing and is never used for
        semantic interpretation.

        There are deliberately NO category-specific branches here:
        no `if hostel`, `if library`, `if scholarship`, `if facilities`.
        Phrasing is generic and driven by the evidence item's own fields.
        """
        items = cls.normalize_evidence(evidence, query_spec=query_spec)
        query = query or " ".join(str(value) for value in (
            getattr(query_spec, "topic", None), getattr(query_spec, "requested_field", None),
            getattr(query_spec, "program", None),
        ) if value)

        temporal = bool(getattr(query_spec, "temporal_qualifier", None))
        def evidence_date(item):
            from datetime import datetime, timezone
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            candidates = [
                item.get("date"), item.get("event_date"), item.get("published_at"),
                item.get("publication_date"), item.get("last_crawled_at"),
                item.get("updated_at"), item.get("created_at"),
                metadata.get("date"), metadata.get("event_date"),
                metadata.get("published_at"), metadata.get("publication_date"),
            ]
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
            text = " ".join(
                str(item.get(key) or "") for key in ("value", "content", "summary", "description")
            )
            for match in re.finditer(
                r"\b(?:20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]20\d{2})\b",
                text,
            ):
                try:
                    parsed = datetime.fromisoformat(match.group(0).replace("/", "-"))
                    return parsed.replace(tzinfo=timezone.utc).timestamp()
                except (TypeError, ValueError, OverflowError):
                    continue
            return float("-inf")
        if temporal:
            items.sort(key=evidence_date, reverse=True)

        temporal = bool(getattr(query_spec, "temporal_qualifier", None))
        def evidence_date(item):
            from datetime import datetime, timezone
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            candidates = [
                item.get("event_date"), item.get("date"), item.get("published_at"),
                item.get("publication_date"), item.get("last_crawled_at"),
                item.get("updated_at"), item.get("created_at"),
                metadata.get("event_date"), metadata.get("date"),
                metadata.get("published_at"), metadata.get("publication_date"),
            ]
            for candidate in candidates:
                if not candidate:
                    continue
                try:
                    parsed = candidate if isinstance(candidate, datetime) else datetime.fromisoformat(str(candidate).replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    return parsed.timestamp()
                except (TypeError, ValueError, OverflowError):
                    continue
            published = " ".join(
                str(item.get(key) or "") for key in ("value", "content", "summary", "description")
            )
            for match in re.finditer(
                r"\b(?:20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]20\d{2})\b",
                published,
            ):
                try:
                    parsed = datetime.fromisoformat(match.group(0).replace("/", "-"))
                    return parsed.replace(tzinfo=timezone.utc).timestamp()
                except (TypeError, ValueError, OverflowError):
                    continue
            return float("-inf")
        if temporal:
            items.sort(key=evidence_date, reverse=True)

        facts = []
        for item in items:
            value = item.get("value")
            if isinstance(value, dict):
                structured_value = value
                value = structured_value.get("content") or structured_value.get("value") or structured_value.get("answer") or structured_value.get("summary")
                if not value:
                    scalar_values = [str(v).strip() for v in structured_value.values() if isinstance(v, (str, int, float)) and str(v).strip()]
                    value = ". ".join(scalar_values)
            if not value:
                value = item.get("description") or item.get("answer")
            if not value and item.get("title") and item.get("source_type") == "website_snapshot":
                value = item.get("title")
            if not value:
                continue
            value = str(value).strip()
            # Generic, category-agnostic phrasing driven by the EVIDENCE's own
            # program field (never by re-reading the question).
            # An admin DB record either carries source_type "entity_db" or
            # comes straight from the knowledge store with no source_type yet.
            is_db_record = item.get("source_type") in (
                None, "", "entity_db",
            ) or item.get("source_type") in ADMIN_DB_SOURCE_TYPES
            # P0.3 (defect 1): only a REAL college program is named in the
            # answer. A record scoped to "All Programs" (or any other
            # institution-wide label) is not about a program at all, and
            # decorating it produced "The recorded All Programs value is ...",
            # which (a) is not a college fact and (b) failed claim
            # verification, silently discarding a perfectly valid record.
            if is_db_record and item.get("program") and not cls._is_general_program(item["program"]):
                program = cls._canonical_program(item["program"])
                value = f"The recorded {program} value is {value}"
                if item.get("academic_year"):
                    value += f" for the {item['academic_year']} academic year"
                if not value.endswith((".", "!", "?")):
                    value += "."
            elif not value.endswith((".", "!", "?")):
                # Keep exactly one terminal sentence break, and never double it.
                value += "."
            if value and value.lower() not in {fact.lower() for fact in facts}:
                facts.append(value)
        if len(facts) > 1:
            facts = [fact for fact in facts if not any(
                fact.lower() != other.lower() and fact.lower() in other.lower()
                for other in facts
            )]
        if facts:
            return " ".join(facts)
        return ""

    @classmethod
    def build_verified_answer(cls, evidence: List[Dict[str, Any]], query_spec=None, query: str = "") -> str:
        # Compatibility alias for callers that need the generic grounded path.
        return cls.build_grounded_answer(evidence, query_spec=query_spec, query=query)

    @classmethod
    def build_blocks(
        cls,
        text_content: str,
        images: Optional[List[Dict[str, Any]]] = None,
        table_data: Optional[Dict[str, Any]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        provenance: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        blocks = []

        # 1. Main Text Block
        if text_content:
            blocks.append({
                "type": "text",
                "content": text_content
            })

        # 2. Real AIT Image Blocks (P0)
        if images:
            for img in images:
                blocks.append({
                    "type": "image",
                    "url": img.get("image_url", ""),
                    "thumbnail_url": img.get("thumbnail_url", ""),
                    "alt": img.get("title", "AIT Official Image"),
                    "title": img.get("title", ""),
                    "category": img.get("category", ""),
                    "source_url": img.get("source_url", ""),
                    "verified": img.get("verified", True)
                })

        # 3. Table Block
        if table_data:
            blocks.append({
                "type": "table",
                "data": table_data
            })

        # 4. Citations Block
        if citations:
            blocks.append({
                "type": "citation",
                "items": citations
            })

        # 5. Provenance Block (Clean user-facing attribution, no raw internal debugging)
        if provenance:
            blocks.append({
                "type": "provenance",
                "authority": provenance.get("authority", ""),
                "source_domain": provenance.get("source_domain"),
                "answer_status": provenance.get("answer_status"),
                "source_type": provenance.get("source_type"),
                "verified": provenance.get("verified", False),
                "source_context": provenance.get("source_context"),
                "source_label": provenance.get("source_label"),
                "source_url": provenance.get("source_url"),
                "verified_at": provenance.get("verified_at", "")
            })

        # 6. Suggested Follow-up Actions
        if suggestions:
            blocks.append({
                "type": "suggested_action",
                "items": suggestions
            })

        return blocks

    @classmethod
    def format_final_payload(
        cls,
        conversation_id: str,
        message_id: str,
        text_content: str,
        blocks: List[Dict[str, Any]],
        grounding_status: str = "verified"
    ) -> Dict[str, Any]:
        return {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "message": text_content,
            "blocks": blocks,
            "grounding_status": grounding_status
        }

response_builder = ResponseBuilder()
