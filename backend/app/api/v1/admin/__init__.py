from fastapi import APIRouter
from backend.app.api.v1.admin.auth import router as auth_router
from backend.app.api.v1.admin.dashboard import router as dashboard_router
from backend.app.api.v1.admin.knowledge import router as knowledge_router
from backend.app.api.v1.admin.knowledge_categories import router as knowledge_categories_router
from backend.app.api.v1.admin.website import router as website_router
from backend.app.api.v1.admin.documents import router as documents_router
from backend.app.api.v1.admin.images import router as images_router
from backend.app.api.v1.admin.conflicts import router as conflicts_router
from backend.app.api.v1.admin.ai_control import router as ai_router
from backend.app.api.v1.admin.users import router as users_router
from backend.app.api.v1.admin.gaps_feedback import router as gaps_feedback_router
from backend.app.api.v1.admin.audit import router as security_router
from backend.app.api.v1.admin.settings import router as settings_router
from backend.app.api.v1.admin.monitoring import router as monitoring_router
from backend.app.api.v1.admin.automation import router as automation_router
from backend.app.api.v1.admin.alerts import router as alerts_router
from backend.app.api.v1.admin.evaluation import router as evaluation_router
from backend.app.api.v1.admin.maintenance import router as maintenance_router
from backend.app.api.v1.admin.colleges import router as colleges_router
from backend.app.api.v1.admin.smart_upload import router as smart_upload_router
from backend.app.api.v1.admin.change_requests import router as change_requests_router

admin_master_router = APIRouter(prefix="/admin")

admin_master_router.include_router(auth_router)
admin_master_router.include_router(dashboard_router)
admin_master_router.include_router(knowledge_router)
admin_master_router.include_router(knowledge_categories_router)
admin_master_router.include_router(website_router)
admin_master_router.include_router(documents_router)
admin_master_router.include_router(images_router)
admin_master_router.include_router(conflicts_router)
admin_master_router.include_router(ai_router)
admin_master_router.include_router(users_router)
admin_master_router.include_router(gaps_feedback_router)
admin_master_router.include_router(security_router)
admin_master_router.include_router(settings_router)
admin_master_router.include_router(monitoring_router)
admin_master_router.include_router(automation_router)
admin_master_router.include_router(alerts_router)
admin_master_router.include_router(evaluation_router)
admin_master_router.include_router(maintenance_router)
admin_master_router.include_router(colleges_router)
admin_master_router.include_router(smart_upload_router)
admin_master_router.include_router(change_requests_router)

