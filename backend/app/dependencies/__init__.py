"""Dependencies registry."""

from app.dependencies.auth import (
    get_current_user,
    get_current_active_user,
    require_role,
    require_college_admin,
    require_super_admin,
)
from app.dependencies.tenant import (
    get_requested_college_id,
    require_college_tenant_access,
)

__all__ = [
    "get_current_user",
    "get_current_active_user",
    "require_role",
    "require_college_admin",
    "require_super_admin",
    "get_requested_college_id",
    "require_college_tenant_access",
]

