"""
역할 기반 접근 제어 (RBAC) 미들웨어

사용자 역할에 따른 권한 관리 및 접근 제어를 제공합니다.
"""

from enum import Enum
from typing import List, Set
from fastapi import Depends
from src.middleware.auth import get_current_user


class UserRole(str, Enum):
    """
    사용자 역할 정의

    각 역할은 특정 권한을 가지며, 상위 역할은 하위 역할의 권한을 포함합니다.
    """

    CUSTOMER = "customer"  # 일반 고객
    ADMIN = "admin"  # 관리자 (상품, 주문 관리)
    SECURITY_TEAM = "security_team"  # 보안팀 (FDS 관리)
    SUPER_ADMIN = "super_admin"  # 최고 관리자 (모든 권한)


class Permission(str, Enum):
    """
    권한 정의

    세분화된 권한 단위로, 각 역할이 가질 수 있는 권한을 정의합니다.
    """

    # 상품 관련
    PRODUCT_READ = "product:read"
    PRODUCT_CREATE = "product:create"
    PRODUCT_UPDATE = "product:update"
    PRODUCT_DELETE = "product:delete"

    # 주문 관련
    ORDER_READ_OWN = "order:read:own"  # 본인 주문만 조회
    ORDER_READ_ALL = "order:read:all"  # 모든 주문 조회
    ORDER_CREATE = "order:create"
    ORDER_UPDATE = "order:update"
    ORDER_CANCEL = "order:cancel"

    # 사용자 관리
    USER_READ_OWN = "user:read:own"  # 본인 정보만 조회
    USER_READ_ALL = "user:read:all"  # 모든 사용자 조회
    USER_UPDATE_OWN = "user:update:own"
    USER_UPDATE_ALL = "user:update:all"
    USER_DELETE = "user:delete"

    # FDS 관련
    FDS_VIEW_DASHBOARD = "fds:view:dashboard"
    FDS_MANAGE_RULES = "fds:manage:rules"
    FDS_REVIEW_TRANSACTIONS = "fds:review:transactions"
    FDS_APPROVE_BLOCKED = "fds:approve:blocked"

    # 시스템 관리
    SYSTEM_CONFIG = "system:config"
    SYSTEM_LOGS = "system:logs"


# 역할별 권한 매핑
ROLE_PERMISSIONS: dict[UserRole, Set[Permission]] = {
    UserRole.CUSTOMER: {
        Permission.PRODUCT_READ,
        Permission.ORDER_READ_OWN,
        Permission.ORDER_CREATE,
        Permission.ORDER_CANCEL,
        Permission.USER_READ_OWN,
        Permission.USER_UPDATE_OWN,
    },
    UserRole.ADMIN: {
        Permission.PRODUCT_READ,
        Permission.PRODUCT_CREATE,
        Permission.PRODUCT_UPDATE,
        Permission.PRODUCT_DELETE,
        Permission.ORDER_READ_ALL,
        Permission.ORDER_UPDATE,
        Permission.USER_READ_ALL,
        Permission.USER_UPDATE_ALL,
    },
    UserRole.SECURITY_TEAM: {
        Permission.PRODUCT_READ,
        Permission.ORDER_READ_ALL,
        Permission.USER_READ_ALL,
        Permission.FDS_VIEW_DASHBOARD,
        Permission.FDS_MANAGE_RULES,
        Permission.FDS_REVIEW_TRANSACTIONS,
        Permission.FDS_APPROVE_BLOCKED,
        Permission.SYSTEM_LOGS,
    },
    UserRole.SUPER_ADMIN: set(Permission),  # 모든 권한
}


class RBACManager:
    """
    역할 기반 접근 제어 관리 클래스
    """

    @staticmethod
    def get_user_permissions(role: UserRole) -> Set[Permission]:
        """
        사용자 역할에 따른 권한 목록 반환

        Args:
            role: 사용자 역할

        Returns:
            Set[Permission]: 권한 집합
        """
        return ROLE_PERMISSIONS.get(role, set())

    @staticmethod
    def has_permission(user_role: UserRole, required_permission: Permission) -> bool:
        """
        사용자가 특정 권한을 가지고 있는지 확인

        Args:
            user_role: 사용자 역할
            required_permission: 필요한 권한

        Returns:
            bool: 권한 보유 여부
        """
        user_permissions = RBACManager.get_user_permissions(user_role)
        return required_permission in user_permissions

    @staticmethod
    def has_any_permission(
        user_role: UserRole, required_permissions: List[Permission]
    ) -> bool:
        """
        사용자가 여러 권한 중 하나라도 가지고 있는지 확인 (OR 조건)

        Args:
            user_role: 사용자 역할
            required_permissions: 필요한 권한 목록

        Returns:
            bool: 권한 보유 여부
        """
        user_permissions = RBACManager.get_user_permissions(user_role)
        return any(perm in user_permissions for perm in required_permissions)

    @staticmethod
    def has_all_permissions(
        user_role: UserRole, required_permissions: List[Permission]
    ) -> bool:
        """
        사용자가 모든 권한을 가지고 있는지 확인 (AND 조건)

        Args:
            user_role: 사용자 역할
            required_permissions: 필요한 권한 목록

        Returns:
            bool: 권한 보유 여부
        """
        user_permissions = RBACManager.get_user_permissions(user_role)
        return all(perm in user_permissions for perm in required_permissions)


def require_permission(*permissions: Permission):
    """
    특정 권한을 요구하는 데코레이터 팩토리

    Args:
        *permissions: 필요한 권한 목록 (OR 조건)

    Returns:
        Callable: FastAPI 의존성 함수

    Example:
        ```python
        @app.post("/products")
        async def create_product(
            current_user = Depends(require_permission(Permission.PRODUCT_CREATE))
        ):
            return {"message": "상품이 생성되었습니다."}
        ```
    """

    async def permission_checker(current_user=Depends(get_current_user)):
        # TODO: User 모델 생성 후 주석 해제
        # user_role = UserRole(current_user.role)
        #
        # if not RBACManager.has_any_permission(user_role, list(permissions)):
        #     raise AuthorizationError(
        #         detail=f"이 작업을 수행하려면 다음 권한 중 하나가 필요합니다: {', '.join(p.value for p in permissions)}"
        #     )

        # 임시: 권한 체크 생략
        return current_user

    return permission_checker


def require_all_permissions(*permissions: Permission):
    """
    모든 권한을 요구하는 데코레이터 팩토리 (AND 조건)

    Args:
        *permissions: 필요한 권한 목록 (모두 필요)

    Returns:
        Callable: FastAPI 의존성 함수
    """

    async def permission_checker(current_user=Depends(get_current_user)):
        # TODO: User 모델 생성 후 주석 해제
        # user_role = UserRole(current_user.role)
        #
        # if not RBACManager.has_all_permissions(user_role, list(permissions)):
        #     raise AuthorizationError(
        #         detail=f"이 작업을 수행하려면 모든 권한이 필요합니다: {', '.join(p.value for p in permissions)}"
        #     )

        return current_user

    return permission_checker


def check_resource_ownership(
    resource_user_id: str, current_user_id: str, allow_admin: bool = True
) -> bool:
    """
    리소스 소유권 확인

    사용자가 본인의 리소스에만 접근하도록 제한합니다.

    Args:
        resource_user_id: 리소스 소유자 ID
        current_user_id: 현재 사용자 ID
        allow_admin: 관리자 접근 허용 여부

    Returns:
        bool: 접근 허용 여부

    Example:
        ```python
        @app.get("/orders/{order_id}")
        async def get_order(
            order_id: str,
            current_user = Depends(get_current_user),
            db: AsyncSession = Depends(get_db)
        ):
            order = await get_order_from_db(order_id, db)
            if not check_resource_ownership(order.user_id, current_user.id):
                raise AuthorizationError(detail="본인의 주문만 조회할 수 있습니다.")
            return order
        ```
    """
    # TODO: User 모델 생성 후 주석 해제
    # if allow_admin and current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
    #     return True

    return resource_user_id == current_user_id


# 편의성을 위한 사전 정의된 권한 체커
require_product_create = require_permission(Permission.PRODUCT_CREATE)
require_product_update = require_permission(Permission.PRODUCT_UPDATE)
require_order_read_all = require_permission(Permission.ORDER_READ_ALL)
require_fds_dashboard = require_permission(Permission.FDS_VIEW_DASHBOARD)
require_fds_manage = require_permission(Permission.FDS_MANAGE_RULES)
require_system_admin = require_all_permissions(Permission.SYSTEM_CONFIG)
