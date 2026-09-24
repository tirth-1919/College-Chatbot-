import os
import sys
import argparse
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

# Ensure backend package can be imported from root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app.core.config import settings
from backend.app.core.database import Base, engine, SessionLocal
from backend.app.core.middleware import TraceAndSecurityMiddleware
from backend.app.scripts.seed_ait_data import seed_initial_ait_knowledge
from backend.app.scripts.migrate_sqlite import run_migrations

# Import User routers
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.conversations import router as conversations_router
from backend.app.api.v1.chat import router as chat_router
from backend.app.api.v1.images import router as images_router
from backend.app.api.v1.files import router as files_router
from backend.app.api.v1.voice import router as voice_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.colleges import router as colleges_router
from backend.app.api.v1.user_college import router as user_college_router

# Initialize database schema and migrations
run_migrations()
Base.metadata.create_all(bind=engine)

# Create dedicated User App
user_app = FastAPI(
    title=f"{settings.APP_NAME} — User Portal",
    version=settings.APP_VERSION,
    description="Dedicated User Application for Ahmedabad Institute of Technology AI Assistant"
)

# P1-10 FIX: CORS with explicit allowed origins. Wildcard + credentials is a browser security violation.
user_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
)

user_app.add_middleware(TraceAndSecurityMiddleware)

# Ensure storage directories exist
os.makedirs(settings.IMAGE_STORAGE_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Mount public images directory only (campus photos served statically)
user_app.mount("/storage/images", StaticFiles(directory=settings.IMAGE_STORAGE_DIR), name="images")
# P0-4 FIX: /storage/uploads is NOT publicly mounted.
# Private user uploads are accessed via authenticated GET /api/v1/files/{file_id}/download

# Mount User APIs under /api/v1
user_app.include_router(health_router, prefix="/api/v1")
user_app.include_router(auth_router, prefix="/api/v1")
user_app.include_router(conversations_router, prefix="/api/v1")
user_app.include_router(chat_router, prefix="/api/v1")
user_app.include_router(images_router, prefix="/api/v1")
user_app.include_router(files_router, prefix="/api/v1")
user_app.include_router(voice_router, prefix="/api/v1")
user_app.include_router(colleges_router, prefix="/api/v1")
user_app.include_router(user_college_router, prefix="/api/v1")

@user_app.on_event("startup")
def user_startup():
    db = SessionLocal()
    try:
        seed_initial_ait_knowledge(db)
    finally:
        db.close()

@user_app.get("/health")
def user_health():
    return {
        "status": "healthy",
        "service": "user-application",
        "port": 8000,
        "institution": settings.INSTITUTION_NAME,
        "version": settings.APP_VERSION
    }

# Mount User Frontend Dist if built
user_dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps", "user-web", "dist")
if os.path.exists(user_dist_dir):
    user_app.mount("/assets", StaticFiles(directory=os.path.join(user_dist_dir, "assets")), name="user-assets")

    @user_app.get("/{full_path:path}")
    async def serve_user_frontend(full_path: str):
        # Never let the SPA fallback expose dotfiles, source files, or paths
        # outside the built frontend directory through the public user server.
        requested_path = full_path.replace("\\", "/")
        if any(part.startswith(".") for part in requested_path.split("/") if part):
            return Response(status_code=404)
        file_path = os.path.abspath(os.path.join(user_dist_dir, requested_path))
        dist_root = os.path.abspath(user_dist_dir)
        if not file_path.startswith(dist_root + os.sep) and file_path != dist_root:
            return Response(status_code=404)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(user_dist_dir, "index.html"))

def print_banner(port: int, dev: bool):
    print("=" * 72)
    print("[*] AHMEDABAD INSTITUTE OF TECHNOLOGY (AIT) - USER AI ASSISTANT")
    print("=" * 72)
    print(f"[*] User API Backend:  http://localhost:{port}/api/v1")
    print(f"[*] User Health Check: http://localhost:{port}/health")
    if dev:
        print(f"[*] User Dev Frontend: http://localhost:5173 (Vite Live Reload)")
    else:
        print(f"[*] User Web App:      http://localhost:{port} (Self-Hosted)")
    print("=" * 72)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIT User Application Runner")
    parser.add_argument("--port", type=int, default=8000, help="Port to run User API on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    parser.add_argument("--dev", action="store_true", help="Launch Vite frontend dev server in parallel")
    parser.add_argument("--check", action="store_true", help="Run sanity check and exit cleanly")
    args = parser.parse_args()

    if args.check:
        print("User application configuration sanity check passed.")
        sys.exit(0)

    print_banner(args.port, args.dev)

    if args.dev:
        user_web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps", "user-web")
        subprocess.Popen(["npm", "run", "dev"], cwd=user_web_dir, shell=True)

    uvicorn.run(user_app, host=args.host, port=args.port)

