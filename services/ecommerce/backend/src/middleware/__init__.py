"""
미들웨어 패키지

인증, 권한, CORS, 로깅 등의 미들웨어를 제공합니다.
"""

from middleware.auth import (
    get_current_user,
    get_current_user_id,
    get_current_active_user,
    require_role,
    require_admin,
    require_security_team,
    AuthenticationError,
    AuthorizationError,
)

from middleware.authorization import (
    UserRole,
    Permission,
    RBACManager,
    require_permission,
    require_all_permissions,
    check_resource_ownership,
)

__all__ = [
    # 인증
    "get_current_user",
    "get_current_user_id",
    "get_current_active_user",
    "require_role",
    "require_admin",
    "require_security_team",
    "AuthenticationError",
    "AuthorizationError",
    # 권한
    "UserRole",
    "Permission",
    "RBACManager",
    "require_permission",
    "require_all_permissions",
    "check_resource_ownership",
]
