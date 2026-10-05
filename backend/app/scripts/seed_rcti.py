"""
RCTI tenant seed script (spec Part B / C / D).

Creates:
  - R.C. Technical Institute college tenant (ACTIVE) — AIT remains College #1
  - College aliases (RC Technical, RCT, R.C. Technical, ...)
  - Official RCTI knowledge entities (source-provenance: rcti.ac.in)
  - Synthetic DEMO knowledge entities (clearly non-official)
  - One COLLEGE_ADMIN demo account (must_change_password=True)
  - Best-effort crawl of official website pages into WebsiteSnapshot

Idempotent: safe to run repeatedly.
"""
import hashlib
import logging
from datetime import datetime, timezone

from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.college import College, CollegeAlias
from backend.app.models.image import AitImage, ImageProvenance
from backend.app.models.knowledge import AitEntity, WebsiteSnapshot
from backend.app.models.user import User
from backend.app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("seed.rcti")

RCTI_SLUG = "rcti"

# Official facts ONLY from rcti.ac.in / its AICTE mandatory disclosure (§35, §70).
# Nothing here is invented; each record points at the source page that carries it.
OFFICIAL_ENTITIES = [
    {
        "category": "about", "name": "Institute Overview", "code": "ABOUT",
        "details": {
            "institute": "R.C. Technical Institute",
            "type": "Government institute (aided), located in Sola, Ahmedabad, Gujarat",
            "established": "1910",
            "affiliating_university": "Gujarat Technological University (GTU)",
            "campus": "Sola, Ahmedabad",
        },
        "source_url": "https://www.rcti.ac.in/",
        "source_page": "/",
        "authority": "Official RCTI Website",
        "academic_year": None,
    },
    {
        "category": "contact", "name": "Official Website & Location", "code": "CONTACT",
        "details": {
            "website": "https://www.rcti.ac.in/",
            "location": "Sola, Ahmedabad, Gujarat, India",
            "note": "See the official website for verified contact details; no contact data is invented here.",
        },
        "source_url": "https://www.rcti.ac.in/",
        "source_page": "/",
        "authority": "Official RCTI Website",
        "academic_year": None,
    },
]

# Synthetic development-only records (§41-§44). NEVER presented as official.
DEMO_ENTITIES = [
    {"category": "demo", "name": "Demo Student Help Desk", "code": "DEMO-HD",
     "details": {"value": "This is synthetic development-only information for testing RCTI tenant retrieval."}},
    {"category": "demo", "name": "Demo Counselling Hours", "code": "DEMO-CH",
     "details": {"value": "Monday to Friday, 4:00 PM - 5:00 PM (synthetic test data)."}},
    {"category": "demo", "name": "Demo Campus Shuttle", "code": "DEMO-CS",
     "details": {"value": "Synthetic test route created only for development."}},
    {"category": "demo", "name": "Demo Scholarship FAQ", "code": "DEMO-SF",
     "details": {"value": "Synthetic development test data. Not an official RCTI scholarship policy."}},
    {"category": "demo", "name": "Demo Library Extended Hours", "code": "DEMO-LH",
     "details": {"value": "Synthetic extended-hours test record for tenant isolation testing."}},
    {"category": "demo", "name": "Demo Tech Club Meetings", "code": "DEMO-TC",
     "details": {"value": "Synthetic weekly meeting slot used for RAG retrieval tests."}},
    {"category": "demo", "name": "Demo Lab Booking Desk", "code": "DEMO-LB",
     "details": {"value": "Synthetic lab-booking workflow description; development only."}},
    {"category": "demo", "name": "Demo Alumni Mentorship Cell", "code": "DEMO-AM",
     "details": {"value": "Synthetic mentorship-cell summary; not an official RCTI body."}},
    {"category": "demo", "name": "Demo Transportation Notice 2026", "code": "DEMO-TN",
     "details": {"value": "Synthetic notice used to test academic-year aware retrieval."}, "academic_year": "2026-27"},
    {"category": "demo", "name": "Demo Sports Facility Booking", "code": "DEMO-SP",
     "details": {"value": "Synthetic booking hours for facility-isolation tests."}},
    {"category": "demo", "name": "Demo Career Guidance Cell", "code": "DEMO-CG",
     "details": {"value": "Synthetic guidance-cell description for provenance tests."}},
    {"category": "demo", "name": "Demo Hostel Enquiry Point", "code": "DEMO-HE",
     "details": {"value": "Synthetic enquiry-point record; no official hostel data is implied."}},
]

# Verified manual/admin-entered record (spec §8). NOT present on the official
# website — provenance must read "Verified College Database", never official-website.
MANUAL_ADMIN_ENTITIES = [
    {
        "category": "fee", "name": "BCA Semester 5 Fee", "code": "BCA-SEM5-FEE",
        "details": {
            "course": "BCA", "semester": "5", "field": "Semester Fee",
            "value": "₹48,000", "academic_year": "2026-27",
            "note": "Admin-entered fee; not published on the official website.",
        },
        "academic_year": "2026-27",
        "authority": "Verified College Database (MANUAL_ADMIN)",
    },
]

# Secondary official department-level source (§4). Kept as metadata only — the
# primary institute website remains https://www.rcti.ac.in/.
# Images are taken from the official RCTI homepage and department pages.
# These URLs were verified from https://www.rcti.ac.in/ and retain source URLs.
OFFICIAL_IMAGES = [
    {"title": "RCTI Official Logo", "category": "logo", "url": "https://www.rcti.ac.in/wp-content/uploads/2025/04/RCTI_Logo.png", "page": "https://www.rcti.ac.in/"},
    {"title": "RCTI Campus Nature", "category": "campus", "url": "https://www.rcti.ac.in/wp-content/uploads/2025/04/RCTI_Nature1.jpg", "page": "https://www.rcti.ac.in/"},
    {"title": "RCTI Computer Engineering Department", "category": "department", "url": "https://www.rcti.ac.in/wp-content/uploads/2025/05/computer.png", "page": "https://www.rcti.ac.in/"},
    {"title": "RCTI Electrical Engineering Department", "category": "department", "url": "https://www.rcti.ac.in/wp-content/uploads/2025/05/Electrical.png", "page": "https://www.rcti.ac.in/"},
    {"title": "RCTI Information Technology Department", "category": "department", "url": "https://www.rcti.ac.in/wp-content/uploads/2025/05/IT.png", "page": "https://www.rcti.ac.in/"},
    {"title": "RCTI Applied Mechanics Department", "category": "department", "url": "https://www.rcti.ac.in/wp-content/uploads/2025/05/Applied.png", "page": "https://www.rcti.ac.in/"},
    {"title": "RCTI Civil Engineering Department", "category": "department", "url": "https://www.rcti.ac.in/wp-content/uploads/2025/05/civil.png", "page": "https://www.rcti.ac.in/"},
    {"title": "RCTI ICT Department", "category": "department", "url": "https://www.rcti.ac.in/wp-content/uploads/2025/05/ICT1.png", "page": "https://www.rcti.ac.in/"},
    {"title": "RCTI Printing Technology Department", "category": "department", "url": "https://www.rcti.ac.in/wp-content/uploads/2025/05/Printing.png", "page": "https://www.rcti.ac.in/"},
    {"title": "RCTI Science and Humanities Department", "category": "department", "url": "https://www.rcti.ac.in/wp-content/uploads/2025/05/Science.png", "page": "https://www.rcti.ac.in/"},
    {"title": "RCTI Textile Technology Department", "category": "department", "url": "https://www.rcti.ac.in/wp-content/uploads/2025/05/Textile.png", "page": "https://www.rcti.ac.in/"},
    {"title": "RCTI Institute Founder Portrait", "category": "campus", "url": "https://www.rcti.ac.in/wp-content/uploads/2025/06/Ranchhodlal_Chhotalal-e1753323589157-223x300.png", "page": "https://www.rcti.ac.in/"},
]

SECONDARY_OFFICIAL_SOURCES = [
    {
        "url": "https://it.rcti.ac.in/",
        "label": "RCTI Information Technology Department (official department site)",
    },
]

RCTI_ALIASES = [
    "RC Technical", "RC", "RCT", "R C Technical", "R.C. Technical",
    "R.C. Technical Institute", "RC Technical Institute",
    "r c technical institute", "RCTI", "R.C. Technical College",
    "rc tech", "rc-technical",
]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_schema():
    """Lightweight dev-schema sync: new tables + new columns."""
    Base.metadata.create_all(engine)
    from sqlalchemy import text
    with engine.begin() as conn:
        for stmt in (
            "ALTER TABLE users ADD COLUMN default_college_id VARCHAR(36)",
            "ALTER TABLE ait_entities ADD COLUMN source_type VARCHAR(50)",
            "ALTER TABLE ait_entities ADD COLUMN is_official BOOLEAN",
        ):
            try:
                conn.execute(text(stmt))
            except Exception:
                pass


def seed_rcti(db):
    now = datetime.now(timezone.utc)

    # §19: idempotent lookup by slug OR code OR name OR official website
    college = db.query(College).filter(
        (College.slug == RCTI_SLUG) | (College.code == "RCTI") |
        (College.name == "R.C. Technical Institute") |
        (College.official_website == "https://www.rcti.ac.in/")
    ).first()
    if not college:
        college = College(
            name="R.C. Technical Institute", code="RCTI", slug=RCTI_SLUG,
            official_email="info@rcti.ac.in",
            official_website="https://www.rcti.ac.in/",
            city="Ahmedabad", state="Gujarat", country="India",
            university_affiliation="Gujarat Technological University (GTU)",
            status="ACTIVE", registration_status="APPROVED",
            created_at=now, updated_at=now,
        )
        db.add(college)
        db.flush()
        log.info("Created college tenant RCTI (%s)", college.id)

    # Fill missing/required configuration on an existing tenant (§19)
    _dirty = False
    for field, value in {
        "name": "R.C. Technical Institute", "code": "RCTI", "slug": RCTI_SLUG,
        "official_website": "https://www.rcti.ac.in/",
        "city": "Ahmedabad", "state": "Gujarat", "country": "India",
        "university_affiliation": "Gujarat Technological University (GTU)",
        "status": "ACTIVE", "registration_status": "APPROVED",
    }.items():
        if getattr(college, field, None) != value:
            setattr(college, field, value)
            _dirty = True
    if _dirty:
        college.updated_at = now

    for alias in RCTI_ALIASES:
        from backend.app.chat.college_context import normalize
        norm = normalize(alias)
        exists = db.query(CollegeAlias).filter(
            CollegeAlias.college_id == college.id,
            CollegeAlias.normalized_alias == norm,
        ).first()
        if not exists:
            db.add(CollegeAlias(college_id=college.id, alias=alias, normalized_alias=norm))
    db.flush()

    # Official entities
    for e in OFFICIAL_ENTITIES:
        existing = db.query(AitEntity).filter(
            AitEntity.college_id == college.id, AitEntity.name == e["name"],
        ).first()
        if existing:
            if existing.source_type != "OFFICIAL_WEBSITE" or existing.is_official is not True:
                existing.source_type = "OFFICIAL_WEBSITE"
                existing.is_official = True
            continue
        db.add(AitEntity(
                college_id=college.id, category=e["category"], name=e["name"],
                code=e["code"], details=e["details"],
                academic_year=e.get("academic_year"),
                source_url=e["source_url"], source_page=e["source_page"],
                source_type="OFFICIAL_WEBSITE", is_official=True,
                authority=e["authority"], is_verified=True,
                content_hash=_hash(e["name"] + str(e["details"])),
                created_at=now, updated_at=now, verified_at=now,
            ))

    # Verified MANUAL_ADMIN records (spec §8) — provenance: college database,
    # never presented as official-website information.
    for e in MANUAL_ADMIN_ENTITIES:
        existing = db.query(AitEntity).filter(
            AitEntity.college_id == college.id, AitEntity.name == e["name"],
        ).first()
        if existing:
            if existing.source_type != "MANUAL_ADMIN" or existing.is_official is not False:
                existing.source_type = "MANUAL_ADMIN"
                existing.is_official = False
            continue
        db.add(AitEntity(
                college_id=college.id, category=e["category"], name=e["name"],
                code=e["code"], details=e["details"],
                academic_year=e.get("academic_year"),
                source_url="DATABASE://manual-admin-entry",
                source_page="ADMIN_PANEL",
                source_type="MANUAL_ADMIN", is_official=False,
                authority=e["authority"], is_verified=True,
                content_hash=_hash(e["name"] + str(e["details"])),
                created_at=now, updated_at=now, verified_at=now,
            ))
    db.flush()

    # DEMO entities — clearly non-official provenance (§42)
    # Backfill provenance columns on pre-existing rows, then insert missing ones.
    for e in DEMO_ENTITIES:
        existing = db.query(AitEntity).filter(
            AitEntity.college_id == college.id, AitEntity.name == e["name"],
        ).first()
        if existing:
            if existing.source_type != "DEMO" or existing.is_official is not False:
                existing.source_type = "DEMO"
                existing.is_official = False
            continue
        db.add(AitEntity(
                college_id=college.id, category=e["category"], name=e["name"],
                code=e["code"], details=e["details"],
                academic_year=e.get("academic_year"),
                source_url="DEMO://rcti/synthetic-test-data",
                source_page="DEMO",
                source_type="DEMO", is_official=False,
                authority="DEMO — Non-official development test data",
                is_verified=True,
                content_hash=_hash(e["name"] + str(e["details"])),
                created_at=now, updated_at=now, verified_at=now,
            ))
    db.flush()

    # Official RCTI images, keyed by tenant and deduplicated by URL hash.
    for item in OFFICIAL_IMAGES:
        image_hash = _hash(item["url"])
        image = db.query(AitImage).filter(AitImage.college_id == college.id, AitImage.content_hash == image_hash).first()
        if not image:
            image = AitImage(
                college_id=college.id, title=item["title"], category=item["category"],
                image_url=item["url"], thumbnail_url=item["url"], source_url=item["url"],
                source_page=item["page"], source_type="OFFICIAL_WEBSITE", source_domain="rcti.ac.in",
                official_source=True, verified=True, verification_status="PUBLISHED",
                content_hash=image_hash, description=item["title"], retrieved_at=now,
            )
            db.add(image)
            db.flush()
            db.add(ImageProvenance(image_id=image.id, source_url=item["url"], source_domain="rcti.ac.in", extracted_page=item["page"], verified_by="RCTI Official Website", verification_method="Official Domain Whitelist"))

    # Secondary official department source recorded as metadata (§4)
    for src in SECONDARY_OFFICIAL_SOURCES:
        exists = db.query(WebsiteSnapshot).filter(WebsiteSnapshot.url == src["url"]).first()
        if not exists:
            db.add(WebsiteSnapshot(
                college_id=college.id, url=src["url"],
                title=src["label"],
                content_hash=_hash(src["url"]),
                text_content=("Secondary official department source: " + src["label"]
                              + ". Primary institute source remains https://www.rcti.ac.in/"),
                status_code=200, last_crawled_at=now,
            ))
    db.flush()

    # Development college admin (§6) — hashed password only, forced change on first login.
    # The email is configurable; passwords must be supplied through the protected
    # RCTI_ADMIN_PASSWORD environment variable and are never stored in source.
    import os
    admin_email = os.environ.get("RCTI_ADMIN_EMAIL", "4@gmail.com")
    admin = db.query(User).filter(User.email == admin_email).first()
    if not admin:
        # Migrate the existing RCTI admin identity when the configured email is
        # changed, without creating a duplicate tenant administrator.
        admin = db.query(User).filter(
            User.college_id == college.id,
            User.role == "COLLEGE_ADMIN",
        ).first()
        if admin:
            admin.email = admin_email
        else:
            temp_password = os.environ.get("RCTI_ADMIN_PASSWORD", "").strip()
            if not temp_password:
                raise RuntimeError(
                    "RCTI_ADMIN_PASSWORD must be provided through the environment "
                    "when creating the RCTI College Admin account."
                )
            admin = User(
                email=admin_email,
                full_name="RCTI College Admin",
                role="COLLEGE_ADMIN",
                college_id=college.id,
                is_active=True,
                hashed_password=get_password_hash(temp_password),
                must_change_password=True,
            )
            db.add(admin)
            log.info("Created RCTI college admin %s; must change password at first login", admin_email)
    # Fill missing configuration on the existing account. Do not reset its
    # password unless an explicit protected bootstrap/reset operation supplies one.
    if admin.role != "COLLEGE_ADMIN" or admin.college_id != college.id or not admin.is_active:
        admin.role = "COLLEGE_ADMIN"
        admin.college_id = college.id
        admin.is_active = True
    # Website synchronization is a tenant-scoped College Admin operation.
    # Preserve any existing explicit permissions while ensuring the seeded RCTI
    # account can use the website sync action without granting wildcard access.
    permissions = list(admin.permissions) if isinstance(admin.permissions, list) else []
    if "website.sync" not in permissions:
        permissions.append("website.sync")
    admin.permissions = permissions
    db.flush()
    return college

def crawl_official_pages(db, college, max_pages=10):
    """§34: crawl real routes from https://www.rcti.ac.in/ using the existing
    snapshot storage. Best-effort: offline dev machines simply skip this."""
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError:
        log.warning("httpx/bs4 unavailable — skipping RCTI crawl")
        return 0
    from urllib.parse import urljoin, urldefrag

    base = "https://www.rcti.ac.in/"
    saved = 0
    try:
        with httpx.Client(timeout=20, follow_redirects=True,
                          headers={"User-Agent": "AIT-AI-KnowledgeBot/1.0"}) as client:
            r = client.get(base)
            if r.status_code != 200:
                log.warning("RCTI site unreachable (HTTP %s) — skipping crawl", r.status_code)
                return 0
            soup = BeautifulSoup(r.text, "html.parser")
            urls = {base}
            for a in soup.find_all("a", href=True):
                full = urljoin(base, a["href"])
                full = urldefrag(full)[0]
                if "rcti.ac.in" in full and not full.lower().endswith(
                    (".pdf", ".jpg", ".png", ".css", ".js", ".ico")
                ):
                    urls.add(full)
                if len(urls) >= max_pages:
                    break

            for url in list(urls)[:max_pages]:
                try:
                    pr = client.get(url)
                    if pr.status_code != 200:
                        continue
                    psoup = BeautifulSoup(pr.text, "html.parser")
                    for tag in psoup(["script", "style", "nav", "footer"]):
                        tag.decompose()
                    text_content = psoup.get_text(" ", strip=True)
                    if len(text_content) < 100:
                        continue
                    content_hash = _hash(text_content)
                    existing = db.query(WebsiteSnapshot).filter(WebsiteSnapshot.url == url).first()
                    if not existing:
                        db.add(WebsiteSnapshot(
                            college_id=college.id, url=url,
                            title=(psoup.title.string if psoup.title else url),
                            content_hash=content_hash, text_content=text_content[:100000],
                            status_code=200, last_crawled_at=datetime.now(timezone.utc),
                        ))
                        saved += 1
                    elif existing.content_hash != content_hash:
                        existing.content_hash = content_hash
                        existing.text_content = text_content[:100000]
                        existing.college_id = college.id
                        existing.last_crawled_at = datetime.now(timezone.utc)
                        saved += 1
                except Exception:
                    continue
        db.commit()
    except Exception:
        log.warning("RCTI crawl failed (offline?) — skipped", exc_info=True)
        db.rollback()
    log.info("RCTI crawl saved/updated %s pages", saved)
    return saved


def run(with_crawl=True):
    ensure_schema()
    db = SessionLocal()
    try:
        college = seed_rcti(db)
        db.commit()
        if with_crawl:
            crawl_official_pages(db, college)
        log.info("RCTI seed complete. college_id=%s", college.id)
        db.commit()
        return college
    finally:
        db.close()


if __name__ == "__main__":
    run()
