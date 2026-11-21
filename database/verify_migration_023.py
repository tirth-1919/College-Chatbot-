"""Quick verification: list all colleges table columns after migration 023."""
import asyncio, os, sys
from pathlib import Path

env_file = Path(__file__).resolve().parent.parent / ".env"
db_url = ""
for line in env_file.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line.startswith("DATABASE_URL="):
        db_url = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

asyncpg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

EXPECTED = [
    "short_name", "cover_image_url", "institution_type", "established_year",
    "website_url", "address_line1", "address_line2", "city", "district",
    "state", "country", "postal_code", "maps_url", "latitude", "longitude",
    "admission_email", "examination_email", "placement_email",
    "admission_helpline", "alternate_phone", "working_hours",
    "affiliated_university", "recognized_by", "aicte_approval",
    "ugc_recognition", "naac_grade", "nba_accreditation",
    "accreditation_validity", "approval_document_url", "short_description",
    "about_text", "vision", "mission", "leader_name", "leader_designation",
    "linkedin_url", "instagram_url", "facebook_url", "youtube_url",
    "twitter_url", "favicon_url", "primary_brand_color",
    "secondary_brand_color", "draft_profile",
]

async def run():
    import asyncpg
    conn = await asyncpg.connect(asyncpg_url)
    rows = await conn.fetch(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name='colleges' ORDER BY ordinal_position"
    )
    await conn.close()
    existing = {r["column_name"] for r in rows}
    missing = [c for c in EXPECTED if c not in existing]
    print(f"Total columns: {len(rows)}")
    if missing:
        print(f"MISSING ({len(missing)}): {missing}")
        sys.exit(1)
    else:
        print(f"ALL {len(EXPECTED)} new columns present. ✓")

asyncio.run(run())
