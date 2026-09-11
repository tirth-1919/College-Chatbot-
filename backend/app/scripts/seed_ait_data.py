import hashlib
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.models.user import User
from backend.app.models.knowledge import AitEntity, AitKnowledgeVersion, WebsiteSnapshot
from backend.app.models.image import AitImage, ImageProvenance
from backend.app.models.admin_system import (
    AiProviderConfig,
    AiModelRegistry,
    AiQuota,
    FeatureFlag,
    SystemPrompt,
    PromptVersion,
    KnowledgeConflict
)
from backend.app.images.crawler import ait_image_crawler
from backend.app.core.security import get_password_hash
from backend.app.ai.prompts import AIT_SYSTEM_PROMPT

def seed_initial_ait_knowledge(db: Session):
    # 1. Seed Super Admin User if not exists
    super_admin = db.query(User).filter(User.email == "admin@aitindia.in").first()
    if not super_admin:
        admin_user = User(
            email="admin@aitindia.in",
            hashed_password=get_password_hash("Admin@AIT2026!"),
            full_name="AIT Super Administrator",
            role="SUPER_ADMIN",
            is_active=True,
            is_verified=True,
            mfa_enabled=True,
            mfa_secret="DEMO2FASECRETKEY",
            permissions=["*"]
        )
        db.add(admin_user)
        db.commit()
        print("Pre-seeded AIT Super Administrator (admin@aitindia.in / Admin@AIT2026!) with 2FA enabled.")

    # 2. Seed AI Providers and Model Registry if not exists
    if db.query(AiProviderConfig).count() == 0:
        p_gemini = AiProviderConfig(
            provider_name="gemini",
            display_name="Google Gemini Provider",
            priority=1,
            api_key_env="GEMINI_API_KEY",
            is_allowed_for_private_data=False,
            is_allowed_for_documents=True,
            is_allowed_for_images=True
        )
        p_openai = AiProviderConfig(
            provider_name="openai",
            display_name="OpenAI Provider",
            priority=2,
            api_key_env="OPENAI_API_KEY",
            is_allowed_for_private_data=False,
            is_allowed_for_documents=True,
            is_allowed_for_images=True
        )
        p_anthropic = AiProviderConfig(
            provider_name="anthropic",
            display_name="Anthropic Claude Provider",
            priority=3,
            api_key_env="ANTHROPIC_API_KEY",
            is_allowed_for_private_data=False,
            is_allowed_for_documents=True,
            is_allowed_for_images=False
        )
        p_ollama = AiProviderConfig(
            provider_name="ollama",
            display_name="Local Ollama Inference",
            priority=4,
            base_url="http://localhost:11434",
            is_allowed_for_private_data=True,
            is_allowed_for_documents=True,
            is_allowed_for_images=False
        )
        db.add_all([p_gemini, p_openai, p_anthropic, p_ollama])
        db.flush()

        # Models
        m_gemini_flash = AiModelRegistry(
            provider_id=p_gemini.id,
            model_identifier="gemini-3.6-flash",
            display_name="Gemini 3.6 Flash (Primary Verified)",
            priority=1,
            supports_text=True,
            supports_vision=True,
            supports_documents=True,
            supports_streaming=True,
            context_limit=1000000
        )
        m_gpt4o_mini = AiModelRegistry(
            provider_id=p_openai.id,
            model_identifier="gpt-4o-mini",
            display_name="GPT-4o Mini (OpenAI Secondary)",
            priority=3,
            supports_text=True,
            supports_vision=True,
            supports_documents=True,
            supports_streaming=True,
            context_limit=128000
        )
        m_claude = AiModelRegistry(
            provider_id=p_anthropic.id,
            model_identifier="claude-3-5-sonnet-20240620",
            display_name="Claude 3.5 Sonnet",
            priority=4,
            supports_text=True,
            supports_vision=True,
            supports_documents=True,
            supports_streaming=True,
            context_limit=200000
        )
        m_ollama = AiModelRegistry(
            provider_id=p_ollama.id,
            model_identifier="llama3",
            display_name="Llama 3 Local (Private On-Prem)",
            priority=5,
            supports_text=True,
            supports_vision=False,
            supports_documents=True,
            supports_streaming=True,
            context_limit=8192
        )
        db.add_all([m_gemini_flash, m_gpt4o_mini, m_claude, m_ollama])
        db.flush()

        # Quotas
        for m in [m_gemini_flash, m_gpt4o_mini, m_claude, m_ollama]:
            quota = AiQuota(
                model_id=m.id,
                quota_type="requests_per_day",
                limit_amount=15000,
                used_amount=120,
                remaining_amount=14880,
                source="PROVIDER_REPORTED" if "gemini" in m.model_identifier else "ESTIMATED"
            )
            db.add(quota)
        db.commit()
        print("Pre-seeded AI Providers, Model Registry, and Quotas successfully.")

    # 3. Seed Feature Flags if not exists
    if db.query(FeatureFlag).count() == 0:
        flags = [
            ("IMAGE_ANSWERS", "Verified Official AIT Campus Image Rendering", True),
            ("VOICE", "Multilingual Voice Input & Synthesis (EN, GU, HI)", True),
            ("RAG", "Authoritative Institutional RAG Search", True),
            ("AI_FAILOVER", "Autonomous Multi-Provider Circuit Breaker & Fallback", True),
            ("WEBSITE_SYNC", "Automated aitindia.in Crawler & Change Detection", True),
            ("SEMANTIC_CACHE", "Redis-Powered Semantic Query Cache", True),
            ("NEW_CHAT_UI", "Production ChatGPT-Style Glassmorphic Interface", True)
        ]
        for key, name, enabled in flags:
            ff = FeatureFlag(key=key, name=name, is_enabled=enabled, updated_by="System Initializer")
            db.add(ff)
        db.commit()
        print("Pre-seeded Feature Flags successfully.")

    # 4. Seed System Prompts if not exists
    if db.query(SystemPrompt).count() == 0:
        sp = SystemPrompt(
            slug="ait_system_prompt",
            name="AIT Institutional Assistant Master Prompt",
            description="Authoritative master instructions governing grounding, institutional accuracy, and tone.",
            active_version_number=1
        )
        db.add(sp)
        db.flush()

        pv = PromptVersion(
            prompt_id=sp.id,
            version_number=1,
            content=AIT_SYSTEM_PROMPT,
            change_reason="Initial baseline institutional system prompt",
            is_active=True,
            created_by="System Initializer"
        )
        db.add(pv)
        db.commit()
        print("Pre-seeded System Prompt versions successfully.")

    # 5. Check if institutional knowledge is already seeded
    if db.query(AitEntity).count() > 0:
        return


    entities = [
        # Programs & Fees
        {
            "category": "program",
            "name": "BCA (Bachelor of Computer Applications)",
            "code": "BCA",
            "details": {
                "duration": "3 Years (6 Semesters)",
                "annual_fees": "INR 45,000 to 52,000 per year",
                "sem_fees": "INR 22,500 to 26,000 per semester",
                "eligibility": "10+2 with English and Mathematics / Business Maths / Statistics",
                "intake": 120,
                "curriculum": ["Sem 1: C Programming, CS Fundamentals", "Sem 2: DBMS, Data Structures, Web Design", "Sem 3: OOP with Java, OS", "Sem 4: Python, Computer Networks", "Sem 5: Fullstack Web, AI", "Sem 6: Major Project & Internship"]
            },
            "source_url": "https://www.aitindia.in/departments/computer-apps/bca",
            "source_page": "/departments/computer-apps/bca"
        },
        {
            "category": "program",
            "name": "MCA (Master of Computer Applications)",
            "code": "MCA",
            "details": {
                "duration": "2 Years (4 Semesters)",
                "annual_fees": "INR 72,000 to 78,000 per year",
                "eligibility": "BCA / B.Sc (IT/CS) or equivalent graduate degree with 50% aggregate",
                "intake": 60,
                "curriculum": ["Sem 1: Advanced Algorithms, Cloud Computing", "Sem 2: Machine Learning, Advanced DBMS", "Sem 3: Mobile Application Dev, DevOps", "Sem 4: Industrial Project"]
            },
            "source_url": "https://www.aitindia.in/departments/computer-apps/mca",
            "source_page": "/departments/computer-apps/mca"
        },
        {
            "category": "program",
            "name": "B.Tech Computer Science & Engineering",
            "code": "B.Tech CSE",
            "details": {
                "duration": "4 Years (8 Semesters)",
                "annual_fees": "INR 78,000 per year (as per ACPC / Fee Regulatory Committee)",
                "eligibility": "10+2 with Physics, Mathematics, Chemistry with GUJCET / JEE",
                "intake": 180,
                "affiliated_university": "Gujarat Technological University (GTU)"
            },
            "source_url": "https://www.aitindia.in/departments/computer-eng",
            "source_page": "/departments/computer-eng"
        },
        {
            "category": "program",
            "name": "B.Tech Information Technology",
            "code": "B.Tech IT",
            "details": {
                "duration": "4 Years (8 Semesters)",
                "annual_fees": "INR 78,000 per year",
                "eligibility": "10+2 with Physics, Mathematics, Chemistry with GUJCET / JEE",
                "intake": 120
            },
            "source_url": "https://www.aitindia.in/departments/it",
            "source_page": "/departments/it"
        },
        {
            "category": "program",
            "name": "BBA (Bachelor of Business Administration)",
            "code": "BBA",
            "details": {
                "duration": "3 Years",
                "annual_fees": "INR 40,000 to 45,000 per year",
                "eligibility": "10+2 any stream"
            },
            "source_url": "https://www.aitindia.in/departments/management/bba",
            "source_page": "/departments/management/bba"
        },
        {
            "category": "program",
            "name": "MBA (Master of Business Administration)",
            "code": "MBA",
            "details": {
                "duration": "2 Years",
                "annual_fees": "INR 75,000 per year",
                "specializations": ["Finance", "Marketing", "Human Resources", "Information Systems"]
            },
            "source_url": "https://www.aitindia.in/departments/management/mba",
            "source_page": "/departments/management/mba"
        },

        # Faculty
        {
            "category": "faculty",
            "name": "Prof. Anjali Sharma",
            "code": "FAC-CSE-01",
            "details": {
                "designation": "Assistant Professor & Subject Coordinator",
                "department": "Computer Engineering & Computer Applications",
                "subjects_taught": ["Database Management Systems (DBMS)", "Advanced Database Systems"],
                "office_location": "Block B, Room 204, Second Floor, Academic Complex",
                "email": "anjali.sharma@aitindia.in",
                "experience": "9 Years"
            },
            "source_url": "https://www.aitindia.in/departments/computer-eng",
            "source_page": "/departments/computer-eng"
        },
        {
            "category": "faculty",
            "name": "Dr. Rajesh Patel",
            "code": "FAC-CSE-02",
            "details": {
                "designation": "Professor & Head of Department",
                "department": "Computer Engineering",
                "subjects_taught": ["Data Structures & Algorithms", "Theory of Computation"],
                "office_location": "Block B, Room 101, Ground Floor",
                "email": "rajesh.patel@aitindia.in"
            },
            "source_url": "https://www.aitindia.in/departments/computer-eng",
            "source_page": "/departments/computer-eng"
        },

        # Facilities
        {
            "category": "facility",
            "name": "AIT Central Library",
            "code": "FACILITY-LIB",
            "details": {
                "timings": "8:30 AM to 5:30 PM (Monday to Saturday)",
                "collection": "Over 25,000 printed volumes, IEEE digital access, DELNET e-journals",
                "location": "First Floor, Administrative & Central Library Block",
                "facilities": "Digital Library zone with 40 computer terminals, Reading Hall capacity of 200+ students"
            },
            "source_url": "https://www.aitindia.in/facilities/library",
            "source_page": "/facilities/library"
        },
        {
            "category": "facility",
            "name": "AIT High-Tech Computer Laboratories",
            "code": "FACILITY-LAB",
            "details": {
                "labs_count": "10+ Air-Conditioned Laboratories",
                "workstations": "500+ Intel Core i7 / i5 Systems",
                "networking": "High-Speed 1 Gbps Fiber-Optic Leased Line Backbone",
                "software": "Linux, Windows 11, Oracle, Python, Android Studio, Docker, MATLAB",
                "location": "Block A & Block B, Floors 1 through 3"
            },
            "source_url": "https://www.aitindia.in/facilities/computer-lab",
            "source_page": "/facilities/computer-lab"
        },
        {
            "category": "facility",
            "name": "AIT Smart Classrooms",
            "code": "FACILITY-CLASSROOM",
            "details": {
                "features": "Interactive digital smart boards, ceiling projectors, acoustic sound systems, Wi-Fi connectivity",
                "capacity": "70 students per lecture hall"
            },
            "source_url": "https://www.aitindia.in/facilities/smart-classes",
            "source_page": "/facilities/smart-classes"
        },
        {
            "category": "facility",
            "name": "AIT Sports Grounds & Gymnasium",
            "code": "FACILITY-SPORTS",
            "details": {
                "outdoor_sports": "Cricket Ground, Football Field, Volleyball Court, Basketball Court",
                "indoor_sports": "Table Tennis, Badminton, Chess, Carrom",
                "gym": "Equipped student fitness gym"
            },
            "source_url": "https://www.aitindia.in/facilities/sports-ground",
            "source_page": "/facilities/sports-ground"
        },
        {
            "category": "facility",
            "name": "AIT Campus Cafeteria & Canteen",
            "code": "FACILITY-CANTEEN",
            "details": {
                "menu": "Vegetarian North Indian, South Indian, Gujarati snacks, fast food, and beverages",
                "timings": "8:00 AM to 6:00 PM",
                "hygiene": "FSSAI compliant hygienic kitchen"
            },
            "source_url": "https://www.aitindia.in/facilities/canteen",
            "source_page": "/facilities/canteen"
        },

        # Placements
        {
            "category": "placement",
            "name": "AIT Training & Placement Cell",
            "code": "TPO",
            "details": {
                "highest_package": "INR 12.5 LPA",
                "average_package": "INR 4.2 to 4.8 LPA",
                "top_recruiters": ["TCS", "Infosys", "Wipro", "Capgemini", "Cognizant", "Gateway Group", "TatvaSoft", "eInfochips", "Zeus Learning"],
                "placement_rate": "85%+ eligible students placed annually"
            },
            "source_url": "https://www.aitindia.in/placement/cell",
            "source_page": "/placement/cell"
        },

        # Contact Info
        {
            "category": "contact",
            "name": "AIT Official Contact Information",
            "code": "CONTACT",
            "details": {
                "address": "Ahmedabad Institute of Technology, Nr. Vasantnagar Township, Gota-Ognaj Road, Ahmedabad - 380060, Gujarat, India",
                "phone": "+91-79-29702271 / 29702272",
                "admissions_helpline": "+91 90999 51160",
                "email": "info@aitindia.in",
                "website": "https://www.aitindia.in"
            },
            "source_url": "https://www.aitindia.in/contact",
            "source_page": "/contact"
        }
    ]

    for item in entities:
        content_hash = hashlib.sha256(str(item["details"]).encode('utf-8')).hexdigest()
        entity = AitEntity(
            category=item["category"],
            name=item["name"],
            code=item.get("code"),
            details=item["details"],
            source_url=item["source_url"],
            source_page=item["source_page"],
            content_hash=content_hash,
            is_verified=True
        )
        db.add(entity)
        db.flush()

        version = AitKnowledgeVersion(
            entity_id=entity.id,
            version=1,
            payload=item["details"],
            status="PUBLISHED",
            content_hash=content_hash
        )
        db.add(version)

    # Seed verified official images
    discovered_images = ait_image_crawler.discover_official_images()
    for img_item in discovered_images:
        existing = db.query(AitImage).filter(AitImage.content_hash == img_item["content_hash"]).first()
        if not existing:
            img = AitImage(
                title=img_item["title"],
                category=img_item["category"],
                image_url=img_item["image_url"],
                thumbnail_url=img_item["thumbnail_url"],
                source_url=img_item["source_url"],
                source_page=img_item["source_page"],
                source_domain=img_item["source_domain"],
                verified=img_item["verified"],
                content_hash=img_item["content_hash"],
                description=img_item["description"]
            )
            db.add(img)
            db.flush()

            prov = ImageProvenance(
                image_id=img.id,
                source_url=img_item["source_url"],
                source_domain=img_item["source_domain"],
                extracted_page=img_item["source_page"]
            )
            db.add(prov)

    db.commit()
    print("Pre-seeded verified AIT institutional knowledge and official media successfully!")
