"""Master API v1 Router Aggregator."""

from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.colleges import router as colleges_router
from app.api.v1.users import router as users_router
from app.api.v1.memberships import router as memberships_router
from app.api.v1.chat import router as chat_router
from app.api.v1.super_admin import router as super_admin_router
from app.api.v1.college_admin import router as college_admin_router
from app.api.v1.college_registrations import router as college_registrations_router
from app.api.v1.support import router as support_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.admin_ai_providers import router as admin_ai_providers_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(colleges_router)
api_v1_router.include_router(college_registrations_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(memberships_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(support_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(feedback_router)
api_v1_router.include_router(super_admin_router)
api_v1_router.include_router(college_admin_router)
api_v1_router.include_router(admin_ai_providers_router)
