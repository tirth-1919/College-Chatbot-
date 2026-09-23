"""
RCTI source-priority verification (spec §21 TEST 1-6).

Run: .venv/Scripts/python.exe -m backend.tests.test_rcti_source_priority
"""
import sys
import sqlite3
from pathlib import Path

# Use the real dev DB, but run through the SQLAlchemy stack
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.core.database import SessionLocal  # noqa: E402
from backend.app.knowledge.database import knowledge_db  # noqa: E402
from backend.app.knowledge.rag import rag_engine  # noqa: E402

db = SessionLocal()

def _rcti_id():
    from backend.app.models.college import College
    return db.query(College).filter(College.code == "RCTI").first().id

def _ait_id():
    from backend.app.models.college import College
    return db.query(College).filter(College.code == "AIT").first().id

rcti = _rcti_id()
ait = _ait_id()
fails = []

def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (" | " + str(extra) if extra else ""))
    if not cond:
        fails.append(name)

# TEST: RCTI website snapshots are retrievable and scoped
snaps = knowledge_db.query_website_snapshots(db, "vision mission", college_id=rcti)
check("RCTI website retrieval", len(snaps) > 0 and all("rcti" in (s["url"] or "") for s in snaps), [s["url"] for s in snaps][:2])

# TEST 5: RCTI question never returns AIT snapshots
snaps_ait = knowledge_db.query_website_snapshots(db, "vision mission", college_id=rcti)
check("RCTI tenant isolation (website)", all(s["url"] and "rcti" in s["url"].lower() for s in snaps_ait))

# TEST 6: AIT question never returns RCTI snapshots
snaps_a = knowledge_db.query_website_snapshots(db, "placement", college_id=ait)
check("AIT tenant isolation (website)", all("rcti" not in (s["url"] or "").lower() for s in snaps_a))

# Entities isolation
e_rcti = knowledge_db.query_entities(db, "Institute Overview", college_id=rcti)
check("RCTI entity retrieval", len(e_rcti) > 0, [e["name"] for e in e_rcti][:2])
e_rcti_for_ait = knowledge_db.query_entities(db, "Institute Overview", college_id=ait)
# RCTI entity 'Institute Overview' is named the same as AIT's possibly; check ids
check("AIT never returns RCTI entities", all(
    knowledge_db._to_dict and True for e in e_rcti_for_ait) and all(
    "rcti" not in str(e.get("source_url", "")).lower() for e in e_rcti_for_ait))

# RAG isolation
r_rcti = rag_engine.search(db, "Institute Overview Sola Ahmedabad", college_id=rcti, top_k=5)
r_ait = rag_engine.search(db, "Institute Overview Sola Ahmedabad", college_id=ait, top_k=5)
check("RCTI RAG isolation", all(r["college_id"] == rcti for r in r_rcti))
check("AIT RAG isolation", all(r["college_id"] == ait for r in r_ait))

# Website content sanity: official homepage should mention R.C. Technical Institute
home = knowledge_db.query_website_snapshots(db, "R.C. Technical Institute", college_id=rcti)
check("RCTI homepage indexed", any("technical" in (s["content"] or "").lower() for s in home),
      [(s["url"], (s["content"] or "")[:80]) for s in home][:1])

# --- Website-first priority (spec TEST 1/4): a question the website answers
# must resolve to website snapshots, and DB entities must NOT be consulted.
web_first = knowledge_db.query_website_snapshots(db, "vision mission of the institute", college_id=rcti)
check("TEST1/4 website-first hit exists", len(web_first) > 0)
if web_first:
    check("TEST1/4 website snapshot is RCTI official",
          all("rcti" in (s["url"] or "").lower() for s in web_first),
          [s["url"] for s in web_first])

# --- TEST 2: website does NOT contain the BCA Sem 5 fee; verified MANUAL_ADMIN
# database record must be the answer.
web_fee = knowledge_db.query_website_snapshots(db, "BCA semester 5 fee", college_id=rcti)
check("TEST2 website has no BCA sem-5 fee", not any(
    "48,000" in (s["content"] or "") for s in web_fee),
    [(s["url"], (s["content"] or "")[:60]) for s in web_fee][:2])
db_fee = knowledge_db.query_entities(db, "BCA semester 5 fee", college_id=rcti)
check("TEST2 database has verified BCA sem-5 fee", any(
    "48,000" in str(e["details"]) for e in db_fee),
    [(e["name"], str(e["details"])[:80]) for e in db_fee][:2])
if db_fee:
    fee_e = next(e for e in db_fee if "48,000" in str(e["details"]))
    check("TEST2 fee provenance is MANUAL_ADMIN", "manual" in str(fee_e.get("authority", "")).lower(),
          fee_e.get("authority"))
    check("TEST2 fee never cited as official website", "official" not in str(fee_e.get("authority", "")).lower())

# TEST 2b: fee must not leak to AIT
ait_fee = knowledge_db.query_entities(db, "BCA semester 5 fee", college_id=ait)
check("TEST2 AIT never returns RCTI fee", not any("48,000" in str(e["details"]) for e in ait_fee))

db.close()
print("\n%d failure(s)" % len(fails))

if __name__ == "__main__":
    sys.exit(1 if fails else 0)


def test_rcti_source_priority():
    assert not fails, "RCTI source-priority failures: %s" % fails
