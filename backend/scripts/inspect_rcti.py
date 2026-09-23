import sqlite3
c = sqlite3.connect("backend/ait_assistant.db")
cur = c.cursor()
cid = "a607d280-e365-4fc3-b964-d6260983be89"
print("colleges:", list(cur.execute("select id, code, name, status from colleges")))
print("snapshots rcti:", cur.execute("select count(*) from website_snapshots where college_id=?", (cid,)).fetchone())
print("entities rcti:", cur.execute("select count(*) from ait_entities where college_id=?", (cid,)).fetchone())
print("ait entities:", list(cur.execute(
    "select count(*) from ait_entities e join colleges c on e.college_id=c.id where c.code='AIT'")))
print("snap urls:")
for (u,) in cur.execute("select url from website_snapshots where college_id=?", (cid,)):
    print("  ", u)
print("aliases:", list(cur.execute("select alias from college_aliases where college_id=?", (cid,))))
print("rcti admin:", list(cur.execute("select email, role from users where email like 'rc@%'")))
