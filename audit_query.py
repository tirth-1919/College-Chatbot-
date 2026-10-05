import sqlite3, json
c = sqlite3.connect('file:backend/ait_assistant.db?mode=ro', uri=True)
c.row_factory = sqlite3.Row
cols = c.execute("select id,code,name from colleges where code in ('AIT','RCTI') order by code").fetchall()
out = {
 'colleges': [dict(x) for x in cols],
 'counts': {x['code']: c.execute('select count(*) n from knowledge_records where college_id=?',(x['id'],)).fetchone()['n'] for x in cols},
 'categories': [dict(x) for x in c.execute("select co.code,kc.name,kc.key,count(kr.id) n from knowledge_records kr join colleges co on co.id=kr.college_id join knowledge_categories kc on kc.id=kr.category_id where co.code in ('AIT','RCTI') group by co.code,kc.name,kc.key order by co.code,n desc").fetchall()]
}
rows = c.execute("select kr.id,co.code college,kc.name current_category,kr.title,kr.field_name,kr.value,kr.description,kr.metadata,kr.course,kr.academic_year,kr.status,kr.verified from knowledge_records kr join colleges co on co.id=kr.college_id join knowledge_categories kc on kc.id=kr.category_id where co.code in ('AIT','RCTI') order by co.code,kr.id").fetchall()
out['records'] = [dict(x) for x in rows]
print(json.dumps(out, ensure_ascii=False, indent=2))
