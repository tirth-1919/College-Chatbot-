import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from backend.app.core.config import settings
from backend.app.core.database import Base, engine, SessionLocal
from backend.app.core.middleware import TraceAndSecurityMiddleware
from backend.app.api.v1.router import api_v1_router
from backend.app.scripts.seed_platform_infrastructure import seed_platform_infrastructure
from backend.app.scripts.migrate_sqlite import run_migrations

# Production schema ownership belongs exclusively to Alembic. The application
# never mutates a PostgreSQL schema at import/startup and never swallows a
# migration failure. Development/tests retain the SQLite compatibility path.
if settings.ENVIRONMENT.lower() not in ("production", "prod"):
    run_migrations()
    Base.metadata.create_all(bind=engine)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI FAQ College Chat Bot multi-college platform API"
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

# Mount public images directory (only verified tenant assets are stored here)
app.mount("/storage/images", StaticFiles(directory=settings.IMAGE_STORAGE_DIR), name="images")

frontend_dist = Path(__file__).resolve().parents[2] / "apps" / "user-web" / "dist"
frontend_public = frontend_dist
app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="frontend-assets")

@app.get("/ai-faq-college-chat-bot-icon.svg")
def frontend_logo_icon():
    return FileResponse(frontend_public / "ai-faq-college-chat-bot-icon.svg")

@app.get("/ai-faq-college-chat-bot-logo.svg")
def frontend_logo():
    return FileResponse(frontend_public / "ai-faq-college-chat-bot-logo.svg")



# P0-4 FIX: /storage/uploads is NO LONGER publicly mounted.
# Private user uploads are accessed via authenticated GET /api/v1/files/{file_id}/download

# Include master API router
app.include_router(api_v1_router)

@app.on_event("startup")
def startup_event():
    # Production releases run `alembic upgrade head` before starting the app.
    # SQLite development/test startup may retain its compatibility sync.
    if settings.ENVIRONMENT.lower() not in ("production", "prod"):
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
    frontend_index = frontend_dist / "index.html"
    return FileResponse(frontend_index)

@app.get("/health")
def health_check():
    # Liveness only: does not claim that dependencies are ready.
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "institution": settings.INSTITUTION_NAME,
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION
    }

@app.get("/ready")
def readiness_check():
    # Dependency readiness without exposing credentials or connection strings.
    checks = {"database": "unhealthy", "vector": "not_configured"}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            checks["database"] = "healthy"
            if engine.dialect.name == "postgresql":
                installed = connection.execute(text(
                    "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )).scalar()
                checks["vector"] = "healthy" if installed else "unhealthy"
    except Exception:
        # Do not return exception details, SQL, paths, or provider secrets.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail={"error_code": "DEPENDENCY_NOT_READY", "checks": checks})
    return {"status": "ready", "checks": checks, "version": settings.APP_VERSION}

@app.get("/api/v1/config/brand")
def get_brand_config():
    return {
        "institution_name": settings.INSTITUTION_NAME,
        "institution_short_name": settings.INSTITUTION_SHORT_NAME,
        "institution_url": settings.INSTITUTION_URL,
        "logo_url": None,
        "colors": {
            "primary": "#0b0a3e",
            "secondary": "#1a2345",
            "accent": "#f08518",
            "background": "#f8fafc",
            "text": "#0f172a"
        }
    }


