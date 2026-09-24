"""
Test Production Startup Behavior

Verifies that production startup does NOT seed AIT-specific tenant data
and follows the multi-college architecture.
"""
import pytest
from sqlalchemy.orm import Session
from backend.app.models.college import College
from backend.app.models.user import User
from backend.app.models.knowledge import AitEntity
from backend.app.models.knowledge_categories import KnowledgeCategory
from backend.app.models.image import AitImage
from backend.app.models.admin_system import AiProviderConfig, FeatureFlag, SystemPrompt
from backend.app.scripts.seed_platform_infrastructure import seed_platform_infrastructure
from backend.app.core.config import settings


def test_production_startup_no_ait_knowledge(db: Session):
    """
    Production startup must NOT create AIT-specific knowledge records.
    """
    # Run platform infrastructure seeding
    seed_platform_infrastructure(db)
    
    # Check: No AIT entity knowledge should exist
    ait_entities = db.query(AitEntity).filter(AitEntity.college_id == None).all()
    ait_named_entities = db.query(AitEntity).filter(
        AitEntity.name.ilike("%Ahmedabad Institute%")
    ).all()
    
    assert len(ait_entities) == 0, "Production startup created NULL-tenant knowledge"
    assert len(ait_named_entities) == 0, "Production startup created AIT-specific knowledge"


def test_production_startup_no_ait_college(db: Session):
    """
    Production startup must NOT auto-create AIT as a default college.
    
    Note: Existing databases may have AIT from migrations. This tests that
    seed_platform_infrastructure() does not create it.
    """
    # Count colleges before seeding
    colleges_before = db.query(College).count()
    
    seed_platform_infrastructure(db)
    
    # Count colleges after seeding
    colleges_after = db.query(College).count()
    
    # Platform infrastructure should not create any colleges
    assert colleges_after == colleges_before, \
        f"Production startup created {colleges_after - colleges_before} college(s)"


def test_production_startup_no_global_categories(db: Session):
    """
    Production startup must NOT create global/NULL-tenant categories.
    Categories must be college-specific.
    """
    seed_platform_infrastructure(db)
    
    # Check: No NULL-tenant categories
    global_categories = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.college_id == None
    ).all()
    
    assert len(global_categories) == 0, "Production startup created global categories"


def test_production_startup_no_ait_images(db: Session):
    """
    Production startup must NOT create AIT campus images.
    """
    seed_platform_infrastructure(db)
    
    # Check: No AIT images
    ait_images = db.query(AitImage).filter(
        AitImage.college_id == None
    ).all()
    
    assert len(ait_images) == 0, "Production startup created NULL-tenant images"


def test_production_startup_no_demo_users_in_production(db: Session, monkeypatch):
    """
    Demo users must NOT be created when ENVIRONMENT=production.
    """
    # Count demo users before seeding
    demo_users_before = db.query(User).filter(
        User.email.in_(["1@gmail.com", "2@gmail.com", "3@gmail.com"])
    ).count()
    
    # Simulate production environment
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SEED_DEMO_USER", True)
    
    seed_platform_infrastructure(db)
    
    # Count demo users after seeding
    demo_users_after = db.query(User).filter(
        User.email.in_(["1@gmail.com", "2@gmail.com", "3@gmail.com"])
    ).count()
    
    # Should not create new demo users in production
    assert demo_users_after == demo_users_before, \
        f"Production startup created {demo_users_after - demo_users_before} demo user(s)"


def test_production_startup_creates_platform_infrastructure(db: Session):
    """
    Production startup MUST create platform-level infrastructure:
    - AI providers
    - Feature flags
    - System prompts
    """
    seed_platform_infrastructure(db)
    
    # Check: AI providers exist
    providers = db.query(AiProviderConfig).all()
    assert len(providers) > 0, "No AI providers seeded"
    
    # Check: Feature flags exist
    flags = db.query(FeatureFlag).all()
    assert len(flags) > 0, "No feature flags seeded"
    
    # Check: System prompts exist
    prompts = db.query(SystemPrompt).all()
    assert len(prompts) > 0, "No system prompts seeded"
    
    # Verify generic prompt content (not AIT-specific)
    for prompt in prompts:
        assert "Ahmedabad Institute" not in prompt.name, "System prompt contains AIT branding"
        assert "AIT" not in prompt.slug, "System prompt slug contains AIT"


def test_production_startup_super_admin_requires_password(db: Session, monkeypatch):
    """
    Super Admin must NOT be created without ADMIN_BOOTSTRAP_PASSWORD.
    """
    # Delete existing super admin to test fresh creation
    db.query(User).filter(User.email == "admin@platform.aifaq.bot").delete()
    db.commit()
    
    # Clear bootstrap password
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_PASSWORD", None)
    
    seed_platform_infrastructure(db)
    
    # Check: No super admin created
    super_admin = db.query(User).filter(
        User.role == "SUPER_ADMIN",
        User.email == "admin@platform.aifaq.bot"
    ).first()
    
    assert super_admin is None, "Super admin created without bootstrap password"


def test_production_startup_super_admin_with_password(db: Session, monkeypatch):
    """
    Super Admin SHOULD be created when ADMIN_BOOTSTRAP_PASSWORD is set.
    """
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_PASSWORD", "SecurePassword123!")
    
    seed_platform_infrastructure(db)
    
    # Check: Super admin created
    super_admin = db.query(User).filter(
        User.role == "SUPER_ADMIN",
        User.email == "admin@platform.aifaq.bot"
    ).first()
    
    assert super_admin is not None, "Super admin not created with bootstrap password"
    assert super_admin.is_active, "Super admin not active"
    assert super_admin.is_verified, "Super admin not verified"
    assert super_admin.mfa_enabled, "Super admin MFA not enabled"


def test_production_startup_platform_neutral_branding(db: Session):
    """
    System prompts created by platform infrastructure must use platform-neutral branding.
    
    Note: Existing databases may have old AIT prompts. This tests new prompts created
    by seed_platform_infrastructure().
    """
    # Delete any existing prompts to test fresh seeding
    db.query(SystemPrompt).delete()
    db.commit()
    
    # Seed platform infrastructure
    seed_platform_infrastructure(db)
    
    prompts = db.query(SystemPrompt).all()
    
    for prompt in prompts:
        # Get active version content
        active_version = [v for v in prompt.versions if v.is_active]
        if active_version:
            content = active_version[0].content
            
            # Must NOT contain AIT-specific references
            assert "Ahmedabad Institute of Technology" not in content, \
                "System prompt contains AIT-specific branding"
            assert "aitindia.in" not in content, \
                "System prompt contains AIT website"


def test_production_startup_idempotent(db: Session):
    """
    Running production startup multiple times must be safe (idempotent).
    """
    # Run first time
    seed_platform_infrastructure(db)
    
    first_provider_count = db.query(AiProviderConfig).count()
    first_flag_count = db.query(FeatureFlag).count()
    
    # Run second time
    seed_platform_infrastructure(db)
    
    second_provider_count = db.query(AiProviderConfig).count()
    second_flag_count = db.query(FeatureFlag).count()
    
    # Counts should remain stable
    assert first_provider_count == second_provider_count, "Provider count changed on re-run"
    assert first_flag_count == second_flag_count, "Feature flag count changed on re-run"


def test_development_startup_allows_demo_users(db: Session, monkeypatch):
    """
    Demo users SHOULD be created in development when SEED_DEMO_USER=true.
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "SEED_DEMO_USER", True)
    
    seed_platform_infrastructure(db)
    
    # Check: Demo users created
    demo_users = db.query(User).filter(
        User.email.in_(["1@gmail.com", "2@gmail.com", "3@gmail.com"])
    ).all()
    
    assert len(demo_users) > 0, "Demo users not created in development"
