"""Platform-default knowledge categories.

Descriptions are GENERIC (no college-specific wording — the platform is
multi-tenant and the product name is ``AI FAQ College Chat Bot``). Each
tenant college gets its OWN copy of these categories provisioned
idempotently via ``provision_default_categories`` — the same logical
category (e.g. ``Fees``) exists independently per college.
"""

DEFAULT_CATEGORIES = [
    {
        "key": "fees",
        "name": "Fees",
        "description": "College fee and payment information",
    },
    {
        "key": "faculty",
        "name": "Faculty",
        "description": "College faculty and staff information",
    },
    {
        "key": "courses",
        "name": "Courses",
        "description": "College course and program information",
    },
    {
        "key": "admissions",
        "name": "Admissions",
        "description": "College admission process information",
    },
    {
        "key": "departments",
        "name": "Departments",
        "description": "College department information",
    },
    {
        "key": "placement",
        "name": "Placement",
        "description": "College placement information",
    },
    {
        "key": "academic_calendar",
        "name": "Academic Calendar",
        "description": "College academic calendar information",
    },
    {
        "key": "scholarships",
        "name": "Scholarships",
        "description": "College scholarship information",
    },
    {
        "key": "facilities",
        "name": "Facilities",
        "description": "College campus facility information",
    },
    {
        "key": "library",
        "name": "Library",
        "description": "College library information",
    },
    {
        "key": "hostel",
        "name": "Hostel",
        "description": "College hostel information",
    },
    {
        "key": "transport",
        "name": "Transport",
        "description": "College transport information",
    },
    {
        "key": "events",
        "name": "Events",
        "description": "College event information",
    },
    {
        "key": "examinations",
        "name": "Examinations",
        "description": "College examination information",
    },
    {
        "key": "general",
        "name": "General",
        "description": "General college information",
    },
]

# Keys that uploads are classified into (same source of truth as above).
DEFAULT_KEYS = [spec["key"] for spec in DEFAULT_CATEGORIES]

GENERAL_KEY = "general"
