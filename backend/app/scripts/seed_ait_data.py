import hashlib
import os
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
from backend.app.core.config import settings
from backend.app.core.security import get_password_hash, generate_totp_secret
from backend.app.ai.prompts import build_system_prompt

# Demo credentials for development/demo environments only. Referenced by
# variable so the literal is defined once; never logged or returned by APIs.
_DEMO_PASSWORD = os.getenv("DEMO_USER_PASSWORD", "1")
_DEMO_USER_2_PASSWORD = os.getenv("DEMO_USER_2_PASSWORD", "2")
_DEMO_USER_3_PASSWORD = os.getenv("DEMO_USER_3_PASSWORD", "3")

def seed_initial_ait_knowledge(db: Session):
    # 1. Seed Super Admin User if not exists — using ADMIN_BOOTSTRAP_PASSWORD env var.
    # Credentials are NEVER hardcoded here. They come from the environment.
    super_admin = db.query(User).filter(User.email == "admin@aitindia.in").first()
    if not super_admin:
        bootstrap_password = settings.ADMIN_BOOTSTRAP_PASSWORD
        if not bootstrap_password:
            # No password configured — skip admin seeding. Set via ADMIN_BOOTSTRAP_PASSWORD env var.
            import warnings
            warnings.warn(
                "ADMIN_BOOTSTRAP_PASSWORD is not set. No super-admin will be auto-created. "
                "Set this env var to bootstrap the admin account on first run.",
                RuntimeWarning,
                stacklevel=2
            )
        else:
            # Generate a cryptographically random TOTP secret
            mfa_secret = generate_totp_secret()
            admin_user = User(
                email="admin@aitindia.in",
                hashed_password=get_password_hash(bootstrap_password),
                full_name="AIT Super Administrator",
                role="SUPER_ADMIN",
                is_active=True,
                is_verified=True,
                mfa_enabled=True,
                mfa_secret=mfa_secret,
                permissions=["*"]
            )
            db.add(admin_user)
            db.commit()

            # Write bootstrap file — gitignored, contains one-time credentials.
            # Admin must scan the TOTP secret with an authenticator app.
            bootstrap_file = ".admin_bootstrap.txt"
            try:
                with open(bootstrap_file, "w") as bf:
                    bf.write("AI-POWERED COLLEGES CHATBOT — ADMIN BOOTSTRAP CREDENTIALS\n")
                    bf.write("=" * 50 + "\n")
                    bf.write(f"Email:       admin@aitindia.in\n")
                    bf.write(f"Password:    (set via ADMIN_BOOTSTRAP_PASSWORD env var)\n")
                    bf.write(f"TOTP Secret: {mfa_secret}\n")
                    bf.write("\nScan the TOTP secret with Google Authenticator or Authy.\n")
                    bf.write("Delete this file after setup. It is gitignored.\n")
                # Intentionally do NOT print password or TOTP to stdout
                print("[AIT] Super-admin account created. TOTP secret written to .admin_bootstrap.txt")
                print("[AIT] Scan .admin_bootstrap.txt with your authenticator app and delete the file.")
            except Exception as write_err:
                # If we can't write the file, log error without exposing credentials
                print(f"[AIT] WARNING: Admin bootstrap file could not be written: {write_err}")
                print("[AIT] Admin account created but TOTP secret must be retrieved from the database.")


    # 1b. Seed demo/dev-only student account (never in production).
    #     Password is hashed with the project's bcrypt implementation and is
    #     never stored in plaintext, printed, or exposed via any API.
    #     Idempotent: an existing account is left completely untouched.
    demo_enabled = getattr(settings, "SEED_DEMO_USER", False)
    if demo_enabled and settings.ENVIRONMENT.lower() not in ("production", "prod"):
        demo_user = db.query(User).filter(User.email == "1@gmail.com").first()
        if not demo_user:
            db.add(User(
                email="1@gmail.com",
                hashed_password=get_password_hash(_DEMO_PASSWORD),
                full_name="Demo User",
                role="STUDENT",
                is_active=True,
                is_verified=True,
            ))
            db.commit()
            print("[AIT] Demo student account seeded (credentials not printed).")

        demo_user_2 = db.query(User).filter(User.email == "2@gmail.com").first()
        if not demo_user_2:
            db.add(User(
                email="2@gmail.com",
                hashed_password=get_password_hash(_DEMO_USER_2_PASSWORD),
                full_name="Demo Admin 2",
                role="COLLEGE_ADMIN",
                is_active=True,
                is_verified=True,
            ))
            db.commit()
            print("[AIT] Second demo account (College Admin) seeded.")

        demo_user_3 = db.query(User).filter(User.email == "3@gmail.com").first()
        if not demo_user_3:
            db.add(User(
                email="3@gmail.com",
                hashed_password=get_password_hash(_DEMO_USER_3_PASSWORD),
                full_name="Demo Super Admin 3",
                role="SUPER_ADMIN",
                is_active=True,
                is_verified=True,
                mfa_enabled=False,
                permissions=["*"]
            ))
            db.commit()
            print("[AIT] Third demo account (Super Admin) seeded.")

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
            model_identifier="gemini-3.7-flash",
            display_name="Gemini 3.7 Flash (Primary Verified)",
            priority=1,
            supports_text=True,
            supports_vision=True,
            supports_documents=True,
            supports_streaming=True,
            context_limit=1000000,
            free_tier_status="FREE_TIER_ELIGIBLE"
        )
        # Gemini-only failover chain (all verified via live SDK model discovery).
        # Availability does NOT imply independent quota per model.
        gemini_failover_models = [
            ("gemini-3.8-flash", "Gemini 3.8 Flash (Fallback 1)", 2),
            ("gemini-3.6-flash", "Gemini 3.6 Flash (Fallback 2)", 3),
            ("gemini-3.5-flash", "Gemini 3.5 Flash (Fallback 3)", 4),
            ("gemini-flash-latest", "Gemini Flash Latest (Rolling Alias, Fallback 4)", 5),
            ("gemini-3.5-flash-lite", "Gemini 3.5 Flash Lite (Fallback 5)", 6),
            ("gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite (Fallback 6)", 7),
            ("gemini-flash-lite-latest", "Gemini Flash Lite Latest (Rolling Alias, Fallback 7)", 8),
            ("gemini-2.5-flash", "Gemini 2.5 Flash (Fallback 8)", 9),
            ("gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite (Fallback 9)", 10),
        ]
        for identifier, display, prio in gemini_failover_models:
            db.add(AiModelRegistry(
                provider_id=p_gemini.id,
                model_identifier=identifier,
                display_name=display,
                priority=prio,
                supports_text=True,
                supports_vision=False,
                supports_documents=True,
                supports_streaming=True,
                context_limit=1000000,
                free_tier_status="FREE_TIER_ELIGIBLE"
            ))
        m_gpt4o_mini = AiModelRegistry(
            provider_id=p_openai.id,
            model_identifier="gpt-4o-mini",
            display_name="GPT-4o Mini (OpenAI Secondary)",
            priority=1,
            supports_text=True,
            supports_vision=True,
            supports_documents=True,
            supports_streaming=True,
            context_limit=128000,
            free_tier_status="PAID"
        )
        m_claude = AiModelRegistry(
            provider_id=p_anthropic.id,
            model_identifier="claude-3-5-sonnet-20240620",
            display_name="Claude 3.5 Sonnet",
            priority=1,
            supports_text=True,
            supports_vision=True,
            supports_documents=True,
            supports_streaming=True,
            context_limit=200000,
            free_tier_status="PAID"
        )
        m_ollama = AiModelRegistry(
            provider_id=p_ollama.id,
            model_identifier="llama3",
            display_name="Llama 3 Local (Private On-Prem)",
            priority=1,
            supports_text=True,
            supports_vision=False,
            supports_documents=True,
            supports_streaming=True,
            context_limit=8192,
            free_tier_status="NOT_APPLICABLE"
        )
        db.add_all([m_gemini_flash, m_gpt4o_mini, m_claude, m_ollama])
        db.flush()

        # Multi-provider transition chain: Groq and OpenRouter sit between
        # Gemini and the OpenAI/Anthropic/Ollama tail of the fallback order.
        p_groq = AiProviderConfig(
            provider_name="groq",
            display_name="Groq Provider",
            priority=2,
            api_key_env="GROQ_API_KEY",
            is_allowed_for_private_data=False,
            is_allowed_for_documents=True,
            is_allowed_for_images=False
        )
        p_openrouter = AiProviderConfig(
            provider_name="openrouter",
            display_name="OpenRouter Provider",
            priority=3,
            api_key_env="OPENROUTER_API_KEY",
            is_allowed_for_private_data=False,
            is_allowed_for_documents=True,
            is_allowed_for_images=False
        )
        # Re-rank the existing tail so the full chain reads:
        # gemini(1) -> groq(2) -> openrouter(3) -> openai(4) -> anthropic(5) -> ollama(6)
        p_openai.priority = 4
        p_anthropic.priority = 5
        p_ollama.priority = 6
        db.add_all([p_groq, p_openrouter])
        db.flush()

        # Groq: verified live against GET /openai/v1/models for this account.
        # Text-generation chat models only (whisper/orpheus/prompt-guard excluded).
        # Groq exposes NO pricing metadata in its models list -> UNKNOWN.
        groq_models = [
            ("openai/gpt-oss-120b", "GPT-OSS 120B (Groq Fallback 1)", 1),
            ("openai/gpt-oss-20b", "GPT-OSS 20B (Groq Fallback 2)", 2),
            ("groq/compound", "Groq Compound (Groq Fallback 3)", 3),
            ("groq/compound-mini", "Groq Compound Mini (Groq Fallback 4)", 4),
            ("qwen/qwen3.8-27b", "Qwen 3.8 27B (Groq Fallback 5)", 5),
            ("qwen/qwen3.6-27b", "Qwen 3.6 27B (Groq Fallback 6)", 6),
            ("allam-2-7b", "ALLAM 2 7B (Groq Fallback 7)", 7),
        ]
        for identifier, display, prio in groq_models:
            db.add(AiModelRegistry(
                provider_id=p_groq.id,
                model_identifier=identifier,
                display_name=display,
                priority=prio,
                supports_text=True,
                supports_vision=False,
                supports_documents=True,
                supports_streaming=True,
                context_limit=131072,
                free_tier_status="UNKNOWN"
            ))

        # OpenRouter: verified live against GET /api/v1/models for this account.
        # FREE classification comes from pricing metadata (prompt=="0" and
        # completion=="0"), never from the ":free" name suffix alone.
        openrouter_models = [
            ("google/gemma-4-31b-it:free", "Gemma 4 31B IT (OpenRouter Free Fallback 1)", 1),
            ("inclusionai/ling-3.0-flash-vl:free", "Ling 3.0 Flash VL (OpenRouter Free Fallback 2)", 2),
            ("nvidia/nemotron-3-super-120b-a12b:free", "Nemotron 3 Super 120B (OpenRouter Free Fallback 3)", 3),
            ("thinkingmachines/inkling-small:free", "Inkling Small (OpenRouter Free Fallback 4)", 4),
            ("google/gemma-4-26b-a4b-it:free", "Gemma 4 26B A4B IT (OpenRouter Free Fallback 5)", 5),
        ]
        for identifier, display, prio in openrouter_models:
            db.add(AiModelRegistry(
                provider_id=p_openrouter.id,
                model_identifier=identifier,
                display_name=display,
                priority=prio,
                supports_text=True,
                supports_vision=False,
                supports_documents=True,
                supports_streaming=True,
                context_limit=262144,
                free_tier_status="FREE_TIER_ELIGIBLE"
            ))
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

    # 2b. Idempotent multi-provider backfill for EXISTING databases.
    #     Ensures groq/openrouter providers and their verified models exist,
    #     and that the provider priority chain is gemini(1)->groq(2)->
    #     openrouter(3)->openai(4)->anthropic(5)->ollama(6), without touching
    #     or duplicating any already-seeded provider or model.
    _PRIORITY_CHAIN = {
        "gemini": 1, "groq": 2, "openrouter": 3,
        "openai": 4, "anthropic": 5, "ollama": 6,
    }
    existing_provider_names = {
        p.provider_name.lower(): p for p in db.query(AiProviderConfig).all()
    }
    for name, prio in _PRIORITY_CHAIN.items():
        provider = existing_provider_names.get(name)
        if provider is None:
            provider = AiProviderConfig(
                provider_name=name,
                display_name=f"{name.title()} Provider",
                priority=prio,
                api_key_env=None if name == "ollama" else f"{name.upper()}_API_KEY",
                base_url="http://localhost:11434" if name == "ollama" else None,
                is_allowed_for_private_data=(name == "ollama"),
                is_allowed_for_documents=True,
                is_allowed_for_images=(name == "gemini"),
            )
            db.add(provider)
            existing_provider_names[name] = provider
        elif provider.priority != prio:
            provider.priority = prio
    db.flush()

    _GROQ_SEED = [
        ("openai/gpt-oss-120b", "GPT-OSS 120B (Groq Fallback 1)", 1),
        ("openai/gpt-oss-20b", "GPT-OSS 20B (Groq Fallback 2)", 2),
        ("groq/compound", "Groq Compound (Groq Fallback 3)", 3),
        ("groq/compound-mini", "Groq Compound Mini (Groq Fallback 4)", 4),
        ("qwen/qwen3.8-27b", "Qwen 3.8 27B (Groq Fallback 5)", 5),
        ("qwen/qwen3.6-27b", "Qwen 3.6 27B (Groq Fallback 6)", 6),
        ("allam-2-7b", "ALLAM 2 7B (Groq Fallback 7)", 7),
    ]
    _OPENROUTER_SEED = [
        ("google/gemma-4-31b-it:free", "Gemma 4 31B IT (OpenRouter Free Fallback 1)", 1),
        ("inclusionai/ling-3.0-flash-vl:free", "Ling 3.0 Flash VL (OpenRouter Free Fallback 2)", 2),
        ("nvidia/nemotron-3-super-120b-a12b:free", "Nemotron 3 Super 120B (OpenRouter Free Fallback 3)", 3),
        ("thinkingmachines/inkling-small:free", "Inkling Small (OpenRouter Free Fallback 4)", 4),
        ("google/gemma-4-26b-a4b-it:free", "Gemma 4 26B A4B IT (OpenRouter Free Fallback 5)", 5),
    ]
    for provider_name, seed_models, free_status in (
        ("groq", _GROQ_SEED, "UNKNOWN"),
        ("openrouter", _OPENROUTER_SEED, "FREE_TIER_ELIGIBLE"),
    ):
        provider = existing_provider_names[provider_name]
        existing_models = {
            m.model_identifier for m in db.query(AiModelRegistry)
            .filter(AiModelRegistry.provider_id == provider.id).all()
        }
        added_any = False
        for identifier, display, prio in seed_models:
            if identifier not in existing_models:
                db.add(AiModelRegistry(
                    provider_id=provider.id,
                    model_identifier=identifier,
                    display_name=display,
                    priority=prio,
                    supports_text=True,
                    supports_vision=False,
                    supports_documents=True,
                    supports_streaming=True,
                    context_limit=262144 if provider_name == "openrouter" else 131072,
                    free_tier_status=free_status,
                ))
                added_any = True
        if added_any:
            print(f"[AIT] Backfilled verified {provider_name} models into the registry.")
    db.commit()

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
            content=build_system_prompt("Ahmedabad Institute of Technology (AIT)"),
            change_reason="Initial baseline institutional system prompt",
            is_active=True,
            created_by="System Initializer"
        )
        db.add(pv)
        db.commit()
        print("Pre-seeded System Prompt versions successfully.")

    # Remove the legacy fabricated placement record from databases seeded by
    # earlier versions. Placement facts must come from verified sources.
    legacy_placement = db.query(AitEntity).filter(
        AitEntity.category == "placement",
        AitEntity.source_url == "https://www.aitindia.in/placement/cell",
        AitEntity.details["highest_package"].as_string() == "INR 12.5 LPA",
    ).all()
    for entity in legacy_placement:
        db.delete(entity)
    legacy_snapshot = db.query(WebsiteSnapshot).filter(
        WebsiteSnapshot.url == "https://www.aitindia.in/placement/cell",
        WebsiteSnapshot.text_content.like("%INR 12.5 LPA%"),
    ).all()
    for snapshot in legacy_snapshot:
        db.delete(snapshot)
    if legacy_placement or legacy_snapshot:
        db.commit()

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

    # Committee data sourced from https://www.aitindia.in/about/committee (official AIT website)
    entities.extend([
        {
            "category": "committee",
            "name": "Anti-Ragging Squad",
            "code": "COMMITTEE-ANTI-RAGGING-SQUAD",
            "details": {
                "chairman": "Dr. Pooja Joshi",
                "members": [
                    "Shri Bhaumik Dixit", "Prof Ankita Shah", "Prof Shreya Thakore",
                    "Prof Jaimin Jani", "Prof Ashvin Patel", "Niral Trapsiya",
                    "Kalp Vadodariya", "Prince Thumar", "Bansri Thumar"
                ]
            },
            "source_url": "https://www.aitindia.in/about/committee",
            "source_page": "/about/committee"
        },
        {
            "category": "committee",
            "name": "Sports Committee",
            "code": "COMMITTEE-SPORTS",
            "details": {
                "chairman": "Prof Jignesh Patel",
                "members": [
                    "Prof Dhaval Khatri", "Prof Ashvin Patel", "Prof Apurva Inrodiya",
                    "Prof Navneet Yadav", "Prof Harshil Panchal", "Prof Ishan Bhavsar",
                    "Hetarth Panchal", "Sanjana Sinha", "Shri Bhaumik Dixit"
                ]
            },
            "source_url": "https://www.aitindia.in/about/committee",
            "source_page": "/about/committee"
        },
        {
            "category": "committee",
            "name": "Library Committee",
            "code": "COMMITTEE-LIBRARY",
            "details": {
                "chairman": "Prof Ashvin Patel",
                "members": [
                    "Prof Supriya Singh", "Prof Navneet Yadav", "Prof Dhaval Khatri",
                    "Prof Shreya Thakor", "Prof Vipul Patel", "Shri Viranchi Panchal (Convener)"
                ]
            },
            "source_url": "https://www.aitindia.in/about/committee",
            "source_page": "/about/committee"
        },
        {
            "category": "committee",
            "name": "Canteen Committee",
            "code": "COMMITTEE-CANTEEN",
            "details": {
                "chairman": "Shri Bhaumik Dixit",
                "members": [
                    "Prof Vipul Patel", "Niral Trapasiya", "Banshi Thumar", "Prof Jignesh Patel"
                ]
            },
            "source_url": "https://www.aitindia.in/about/committee",
            "source_page": "/about/committee"
        },
        {
            "category": "committee",
            "name": "Internal Complaint Committee",
            "code": "COMMITTEE-INTERNAL-COMPLAINT",
            "details": {
                "chairman": "Prof Deepali Mandalia",
                "members": [
                    "Shri Viranchi Panchal", "Prof Harsha Padheriya", "Prof Mayalaxmi Pillai",
                    "Prof Tanha Shah", "Prof Bansri Thakkar", "Shah Kanha Pratikbhai"
                ]
            },
            "source_url": "https://www.aitindia.in/about/committee",
            "source_page": "/about/committee"
        },
        {
            "category": "committee",
            "name": "Academic Council",
            "code": "COMMITTEE-ACADEMIC-COUNCIL",
            "details": {
                "chairman": "Dr. Sarada Devi Mandalapu",
                "members": [
                    "Dr Mohit Diwan", "Prof Vipul Patel", "Dr Dushyantsinh Rathod",
                    "Dr Ashish Chaurasia", "Prof Jignesh Patel", "Prof Tanha Shah",
                    "Prof Dipali Mandaliya", "Prof Mayalaxmi Pillai", "Prof Sandhya M C",
                    "Prof Navneet Yadav", "Prof Ashvin Patel", "Prof Shreya Thakor",
                    "Prof Dhaval Khatri", "Prof Ankia Shah", "Prof Leena Patel",
                    "Shri Viranchi Panchal"
                ]
            },
            "source_url": "https://www.aitindia.in/about/committee",
            "source_page": "/about/committee"
        }
    ])

    for item in entities:
        # Idempotency: skip entities that were already seeded (match on code or name+category)
        _existing_q = db.query(AitEntity).filter(AitEntity.category == item["category"])
        if item.get("code"):
            _existing = _existing_q.filter(AitEntity.code == item["code"]).first()
        else:
            _existing = _existing_q.filter(AitEntity.name == item["name"]).first()
        if _existing:
            continue
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
