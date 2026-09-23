from fastapi import APIRouter
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.conversations import router as conversations_router
from backend.app.api.v1.chat import router as chat_router
from backend.app.api.v1.images import router as images_router
from backend.app.api.v1.files import router as files_router
from backend.app.api.v1.voice import router as voice_router
from backend.app.api.v1.health import router as health_router
from backend.app.chat.college_context import AMBIGUOUS_THRESHOLD  # noqa: F401 (re-exported for tests)
from backend.app.api.v1.colleges import router as colleges_router
from backend.app.api.v1.user_college import router as user_college_router
from backend.app.api.v1.admin import admin_master_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(colleges_router)
api_v1_router.include_router(user_college_router)
api_v1_router.include_router(conversations_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(images_router)
api_v1_router.include_router(files_router)
api_v1_router.include_router(voice_router)
api_v1_router.include_router(admin_master_router)


