"""
Idempotent seed for the dynamic Knowledge Database categories.
Running it twice must NOT create duplicates (checks unique key first).
"""
from sqlalchemy.orm import Session

from backend.app.models.knowledge_categories import KnowledgeCategory

INITIAL_CATEGORIES = [
    ("Course Information", "course", "AIT course and program information", "📘", 1),
    ("Admission", "admission", "AIT admission process, eligibility and dates", "📝", 2),
    ("Fees", "fees", "AIT fee structure per course and academic year", "💰", 3),
    ("Subjects", "subjects", "GTU/AIT subject and syllabus information", "📚", 4),
    ("Academic Structure", "academic-structure", "Departments, degrees and academic hierarchy", "🏛️", 5),
    ("Academic Calendar", "academic-calendar", "Academic calendar dates and schedules", "📅", 6),
    ("Examination", "examination", "Examination rules, dates and patterns", "🧪", 7),
    ("Faculty", "faculty", "AIT faculty and staff information", "👩‍🏫", 8),
    ("Laboratories", "laboratories", "AIT laboratory and equipment details", "🔬", 9),
    ("Internship", "internship", "AIT internship information", "💼", 10),
    ("Projects", "projects", "Student project information", "🛠️", 11),
    ("Placement", "placement", "AIT placement statistics and process", "📈", 12),
    ("Student Procedures", "student-procedures", "Student procedures and processes", "🧾", 13),
    ("Scholarships", "scholarships", "AIT scholarship and financial-aid information", "🎓", 14),
    ("General AIT Information", "general", "General AIT institutional information", "ℹ️", 15),
    ("Committees", "committees", "AIT committees and governance bodies", "🤝", 16),
    ("Campus", "campus", "AIT campus information", "🏢", 17),
    ("Library", "library", "AIT library information", "📖", 18),
    ("Sports", "sports", "AIT sports facilities and activities", "⚽", 19),
    ("Canteen", "canteen", "AIT canteen information", "🍽️", 20),
    ("Events", "events", "AIT events and activities", "🎉", 21),
    ("Facilities", "facilities", "AIT campus facilities", "🏫", 22),
]


def seed_knowledge_categories(db: Session, college_id: str = None) -> int:
    """Idempotent: only inserts categories whose key does not already exist for this college."""
    q = db.query(KnowledgeCategory.key)
    if college_id:
        q = q.filter(KnowledgeCategory.college_id == college_id)
    existing_keys = {k for (k,) in q.all()}
    
    q_names = db.query(KnowledgeCategory.name)
    if college_id:
        q_names = q_names.filter(KnowledgeCategory.college_id == college_id)
    existing_names = {n for (n,) in q_names.all()}

    created = 0
    for name, key, description, icon, order in INITIAL_CATEGORIES:
        if key in existing_keys or name in existing_names:
            continue
        db.add(KnowledgeCategory(
            name=name, key=key, description=description,
            icon=icon, display_order=order, status="ACTIVE",
            college_id=college_id
        ))
        created += 1
    if created:
        db.commit()
    return created
