import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.core.config import settings
from backend.app.core.database import Base, engine, SessionLocal
from backend.app.core.middleware import TraceAndSecurityMiddleware
from backend.app.api.v1.router import api_v1_router
from backend.app.scripts.seed_ait_data import seed_initial_ait_knowledge
from backend.app.scripts.migrate_sqlite import run_migrations

# Run column migrations if needed and initialize database schema
run_migrations()
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Ahmedabad Institute of Technology (AIT) AI Assistant API"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits local dev frontends on any port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Security and Tracing Middleware
app.add_middleware(TraceAndSecurityMiddleware)

# Ensure storage directories exist
os.makedirs(settings.IMAGE_STORAGE_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Mount local storage as static files
app.mount("/storage/images", StaticFiles(directory=settings.IMAGE_STORAGE_DIR), name="images")
app.mount("/storage/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include master API router
app.include_router(api_v1_router)

@app.on_event("startup")
def startup_event():
    # Pre-seed verified AIT institutional knowledge and images if database is fresh
    db = SessionLocal()
    try:
        seed_initial_ait_knowledge(db)
    finally:
        db.close()

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
