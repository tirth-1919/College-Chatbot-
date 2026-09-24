import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.core.config import settings
from backend.app.core.database import Base, engine, SessionLocal
from backend.app.core.middleware import TraceAndSecurityMiddleware
from backend.app.api.v1.router import api_v1_router
from backend.app.scripts.seed_platform_infrastructure import seed_platform_infrastructure
from backend.app.scripts.migrate_sqlite import run_migrations

# Run column migrations if needed and initialize database schema
run_migrations()
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Ahmedabad Institute of Technology (AIT) AI Assistant API"
)

# P1-10 FIX: CORS must use explicit allowed origins. Wildcard + allow_credentials is a browser security violation.
# Configure CORS_ORIGINS in .env to include your frontend URLs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
)

# Custom Security and Tracing Middleware
app.add_middleware(TraceAndSecurityMiddleware)

# Ensure storage directories exist
os.makedirs(settings.IMAGE_STORAGE_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Mount public images directory (only verified AIT campus images are stored here)
app.mount("/storage/images", StaticFiles(directory=settings.IMAGE_STORAGE_DIR), name="images")
# P0-4 FIX: /storage/uploads is NO LONGER publicly mounted.
# Private user uploads are accessed via authenticated GET /api/v1/files/{file_id}/download

# Include master API router
app.include_router(api_v1_router)

@app.on_event("startup")
def startup_event():
    from backend.app.scripts.migrate_sqlite import run_migrations
    run_migrations()
    # Seed platform-level infrastructure only (multi-college safe)
    # Does NOT seed AIT-specific tenant data
    db = SessionLocal()
    try:
        seed_platform_infrastructure(db)
    finally:
        db.close()

@app.get("/")
def root_check():
    """Basic service information for deployment smoke checks."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "message": "API is running. See /docs for the interactive API documentation.",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "institution": settings.INSTITUTION_NAME,
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION
    }

@app.get("/api/v1/config/brand")
def get_brand_config():
    return {
        "institution_name": settings.INSTITUTION_NAME,
        "institution_short_name": settings.INSTITUTION_SHORT_NAME,
        "institution_url": settings.INSTITUTION_URL,
        "logo_url": "https://www.aitindia.in/images/Ait-logo.webp",
        "colors": {
            "primary": "#0b0a3e",
            "secondary": "#1a2345",
            "accent": "#f08518",
            "background": "#f8fafc",
            "text": "#0f172a"
        }
    }
