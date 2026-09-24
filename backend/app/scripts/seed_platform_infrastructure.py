"""
Platform Infrastructure Seeding (Multi-College Safe)

This module seeds ONLY platform-level infrastructure:
- AI providers and model registry
- Feature flags
- Optional Super Admin bootstrap (if ADMIN_BOOTSTRAP_PASSWORD is set)
- Demo users (development/test only)

It does NOT seed:
- College-specific knowledge (courses, faculty, fees, facilities)
- College-specific images
- College-specific categories
- NULL-tenant knowledge
- AIT-specific data

College-specific data must be provisioned during college registration/approval.
"""
import os
import warnings
from sqlalchemy.orm import Session
from backend.app.models.user import User
from backend.app.models.admin_system import (
    AiProviderConfig,
    AiModelRegistry,
    AiQuota,
    FeatureFlag,
    SystemPrompt,
    PromptVersion,
)
from backend.app.core.config import settings
from backend.app.core.security import get_password_hash, generate_totp_secret


# Demo credentials for development/demo environments only
_DEMO_PASSWORD = os.getenv("DEMO_USER_PASSWORD", "1")
_DEMO_USER_2_PASSWORD = os.getenv("DEMO_USER_2_PASSWORD", "2")
_DEMO_USER_3_PASSWORD = os.getenv("DEMO_USER_3_PASSWORD", "3")


def seed_platform_infrastructure(db: Session):
    """
    Seed platform-level infrastructure only.
    Safe for production multi-college deployment.
    """
    
    # 1. Seed Super Admin User if ADMIN_BOOTSTRAP_PASSWORD is configured
    super_admin = db.query(User).filter(User.email == "admin@platform.aifaq.bot").first()
    if not super_admin:
        bootstrap_password = settings.ADMIN_BOOTSTRAP_PASSWORD
        if not bootstrap_password:
            warnings.warn(
                "ADMIN_BOOTSTRAP_PASSWORD is not set. No super-admin will be auto-created. "
                "Set this env var to bootstrap the admin account on first run, or create manually.",
                RuntimeWarning,
                stacklevel=2
            )
        else:
            mfa_secret = generate_totp_secret()
            admin_user = User(
                email="admin@platform.aifaq.bot",
                hashed_password=get_password_hash(bootstrap_password),
                full_name="Platform Super Administrator",
                role="SUPER_ADMIN",
                is_active=True,
                is_verified=True,
                mfa_enabled=True,
                mfa_secret=mfa_secret,
                permissions=["*"]
            )
            db.add(admin_user)
            db.commit()

            # Write bootstrap file
            bootstrap_file = ".admin_bootstrap.txt"
            try:
                with open(bootstrap_file, "w") as bf:
                    bf.write("AI FAQ COLLEGE CHAT BOT — PLATFORM ADMIN BOOTSTRAP\n")
                    bf.write("=" * 50 + "\n")
                    bf.write(f"Email:       admin@platform.aifaq.bot\n")
                    bf.write(f"Password:    (set via ADMIN_BOOTSTRAP_PASSWORD env var)\n")
                    bf.write(f"TOTP Secret: {mfa_secret}\n")
                    bf.write("\nScan the TOTP secret with Google Authenticator or Authy.\n")
                    bf.write("Delete this file after setup. It is gitignored.\n")
                print("[PLATFORM] Super-admin account created. TOTP secret written to .admin_bootstrap.txt")
                print("[PLATFORM] Scan .admin_bootstrap.txt with your authenticator app and delete the file.")
            except Exception as write_err:
                print(f"[PLATFORM] WARNING: Admin bootstrap file could not be written: {write_err}")
                print("[PLATFORM] Admin account created but TOTP secret must be retrieved from the database.")

    # 1b. Seed demo/dev-only accounts (never in production)
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
            print("[PLATFORM] Demo student account seeded (credentials not printed).")

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
            print("[PLATFORM] Second demo account (College Admin) seeded.")

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
            print("[PLATFORM] Third demo account (Super Admin) seeded.")

    # 2. Seed AI Providers and Model Registry
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
        p_openai = AiProviderConfig(
            provider_name="openai",
            display_name="OpenAI Provider",
            priority=4,
            api_key_env="OPENAI_API_KEY",
            is_allowed_for_private_data=False,
            is_allowed_for_documents=True,
            is_allowed_for_images=True
        )
        p_anthropic = AiProviderConfig(
            provider_name="anthropic",
            display_name="Anthropic Claude Provider",
            priority=5,
            api_key_env="ANTHROPIC_API_KEY",
            is_allowed_for_private_data=False,
            is_allowed_for_documents=True,
            is_allowed_for_images=False
        )
        p_ollama = AiProviderConfig(
            provider_name="ollama",
            display_name="Local Ollama Inference",
            priority=6,
            base_url="http://localhost:11434",
            is_allowed_for_private_data=True,
            is_allowed_for_documents=True,
            is_allowed_for_images=False
        )
        db.add_all([p_gemini, p_groq, p_openrouter, p_openai, p_anthropic, p_ollama])
        db.flush()

        # Gemini models
        gemini_models = [
            ("gemini-3.7-flash", "Gemini 3.7 Flash (Primary)", 1),
            ("gemini-3.8-flash", "Gemini 3.8 Flash (Fallback 1)", 2),
            ("gemini-3.6-flash", "Gemini 3.6 Flash (Fallback 2)", 3),
            ("gemini-3.5-flash", "Gemini 3.5 Flash (Fallback 3)", 4),
            ("gemini-flash-latest", "Gemini Flash Latest (Fallback 4)", 5),
            ("gemini-3.5-flash-lite", "Gemini 3.5 Flash Lite (Fallback 5)", 6),
            ("gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite (Fallback 6)", 7),
            ("gemini-flash-lite-latest", "Gemini Flash Lite Latest (Fallback 7)", 8),
            ("gemini-2.5-flash", "Gemini 2.5 Flash (Fallback 8)", 9),
            ("gemini-2.5-flash-lite", "Gemini 2.5 Flash Lite (Fallback 9)", 10),
        ]
        for identifier, display, prio in gemini_models:
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

        # Groq models
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

        # OpenRouter models
        openrouter_models = [
            ("google/gemma-4-31b-it:free", "Gemma 4 31B IT (OpenRouter Free 1)", 1),
            ("inclusionai/ling-3.0-flash-vl:free", "Ling 3.0 Flash VL (OpenRouter Free 2)", 2),
            ("nvidia/nemotron-3-super-120b-a12b:free", "Nemotron 3 Super 120B (OpenRouter Free 3)", 3),
            ("thinkingmachines/inkling-small:free", "Inkling Small (OpenRouter Free 4)", 4),
            ("google/gemma-4-26b-a4b-it:free", "Gemma 4 26B A4B IT (OpenRouter Free 5)", 5),
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

        # OpenAI, Anthropic, Ollama
        db.add(AiModelRegistry(
            provider_id=p_openai.id,
            model_identifier="gpt-4o-mini",
            display_name="GPT-4o Mini (OpenAI)",
            priority=1,
            supports_text=True,
            supports_vision=True,
            supports_documents=True,
            supports_streaming=True,
            context_limit=128000,
            free_tier_status="PAID"
        ))
        db.add(AiModelRegistry(
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
        ))
        db.add(AiModelRegistry(
            provider_id=p_ollama.id,
            model_identifier="llama3",
            display_name="Llama 3 Local",
            priority=1,
            supports_text=True,
            supports_vision=False,
            supports_documents=True,
            supports_streaming=True,
            context_limit=8192,
            free_tier_status="NOT_APPLICABLE"
        ))

        db.commit()
        print("[PLATFORM] AI Providers and Model Registry seeded successfully.")

    # 3. Idempotent backfill for existing databases
    _PRIORITY_CHAIN = {
        "gemini": 1, "groq": 2, "openrouter": 3,
        "openai": 4, "anthropic": 5, "ollama": 6,
    }
    existing_provider_names = {
        p.provider_name.lower(): p for p in db.query(AiProviderConfig).all()
    }
    for name, prio in _PRIORITY_CHAIN.items():
        provider = existing_provider_names.get(name)
        if provider and provider.priority != prio:
            provider.priority = prio
    db.commit()

    # 4. Seed Feature Flags
    if db.query(FeatureFlag).count() == 0:
        flags = [
            ("IMAGE_ANSWERS", "Verified Official Campus Image Rendering", True),
            ("VOICE", "Multilingual Voice Input & Synthesis (EN, GU, HI)", True),
            ("RAG", "Authoritative Institutional RAG Search", True),
            ("AI_FAILOVER", "Autonomous Multi-Provider Circuit Breaker & Fallback", True),
            ("WEBSITE_SYNC", "Automated Website Crawler & Change Detection", True),
            ("SEMANTIC_CACHE", "Redis-Powered Semantic Query Cache", True),
            ("NEW_CHAT_UI", "Production ChatGPT-Style Glassmorphic Interface", True)
        ]
        for key, name, enabled in flags:
            ff = FeatureFlag(key=key, name=name, is_enabled=enabled, updated_by="System Initializer")
            db.add(ff)
        db.commit()
        print("[PLATFORM] Feature Flags seeded successfully.")

    # 5. Seed Generic System Prompt
    if db.query(SystemPrompt).count() == 0:
        generic_prompt_content = """You are an AI assistant for a multi-college information platform.

Your role:
- Answer questions about the specific college in the current conversation context
- Provide accurate information based on verified college knowledge
- Never share information across different colleges (strict tenant isolation)
- Be helpful, professional, and student-focused
- Support multiple languages (English, Gujarati, Hindi)

Important:
- College-specific information must come from the active college's knowledge base
- If you don't have verified information, clearly state that
- Never assume or fabricate college-specific details
- Respect the tenant boundary - each college's data is private"""

        sp = SystemPrompt(
            slug="platform_system_prompt",
            name="Multi-College Platform Master Prompt",
            description="Generic platform-level prompt for multi-college assistant",
            active_version_number=1
        )
        db.add(sp)
        db.flush()

        pv = PromptVersion(
            prompt_id=sp.id,
            version_number=1,
            content=generic_prompt_content,
            change_reason="Initial platform-level system prompt",
            is_active=True,
            created_by="System Initializer"
        )
        db.add(pv)
        db.commit()
        print("[PLATFORM] Generic system prompt seeded successfully.")

    print("[PLATFORM] Platform infrastructure initialization complete.")
