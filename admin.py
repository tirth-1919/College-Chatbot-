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
from fastapi.responses import FileResponse

# Ensure backend package can be imported from root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app.core.config import settings
from backend.app.core.database import Base, engine, SessionLocal
from backend.app.core.middleware import TraceAndSecurityMiddleware
from backend.app.scripts.seed_ait_data import seed_initial_ait_knowledge
from backend.app.scripts.migrate_sqlite import run_migrations

# Import Admin routers and health
from backend.app.api.v1.admin import admin_master_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.colleges import router as colleges_router

# Initialize database schema and migrations
run_migrations()
Base.metadata.create_all(bind=engine)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        seed_initial_ait_knowledge(db)
    finally:
        db.close()
    yield

# Create dedicated Admin App
admin_app = FastAPI(
    title=f"{settings.APP_NAME} — Admin Console",
    version=settings.APP_VERSION,
    description="Dedicated Admin Management Application for Ahmedabad Institute of Technology AI Assistant",
    lifespan=lifespan
)

# CORS configuration
admin_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

admin_app.add_middleware(TraceAndSecurityMiddleware)

# Ensure storage directories exist
os.makedirs(settings.IMAGE_STORAGE_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Static media storage
admin_app.mount("/storage/images", StaticFiles(directory=settings.IMAGE_STORAGE_DIR), name="images")
admin_app.mount("/storage/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Mount Admin APIs under /api/v1
admin_app.include_router(health_router, prefix="/api/v1")
admin_app.include_router(colleges_router, prefix="/api/v1")
admin_app.include_router(admin_master_router, prefix="/api/v1")

@admin_app.get("/health")
def admin_health():
    return {
        "status": "healthy",
        "service": "admin-application",
        "port": 8001,
        "institution": settings.INSTITUTION_NAME,
        "version": settings.APP_VERSION
    }

# Mount Admin Frontend Dist if built
admin_dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps", "admin-web", "dist")
if os.path.exists(admin_dist_dir):
    admin_app.mount("/assets", StaticFiles(directory=os.path.join(admin_dist_dir, "assets")), name="admin-assets")

    @admin_app.get("/{full_path:path}")
    async def serve_admin_frontend(full_path: str):
        file_path = os.path.join(admin_dist_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(admin_dist_dir, "index.html"))

def print_banner(port: int, dev: bool):
    print("=" * 72)
    print("[*] AHMEDABAD INSTITUTE OF TECHNOLOGY (AIT) - ADMIN CONSOLE")
    print("=" * 72)
    print(f"[*] Admin API Backend:  http://localhost:{port}/api/v1/admin")
    print(f"[*] Admin Health Check: http://localhost:{port}/health")
    if dev:
        print(f"[*] Admin Dev Portal:   http://localhost:5174 (Vite Live Reload)")
    else:
        print(f"[*] Admin Web Portal:   http://localhost:{port} (Self-Hosted)")
    print("=" * 72)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIT Admin Console Runner")
    parser.add_argument("--port", type=int, default=8001, help="Port to run Admin API on (default: 8001)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    parser.add_argument("--dev", action="store_true", help="Launch Vite frontend dev server in parallel")
    parser.add_argument("--check", action="store_true", help="Run sanity check and exit cleanly")
    args = parser.parse_args()

    if args.check:
        print("Admin application configuration sanity check passed.")
        sys.exit(0)

    print_banner(args.port, args.dev)

    if args.dev:
        admin_web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps", "admin-web")
        subprocess.Popen(["npm", "run", "dev"], cwd=admin_web_dir, shell=True)

    uvicorn.run(admin_app, host=args.host, port=args.port)
