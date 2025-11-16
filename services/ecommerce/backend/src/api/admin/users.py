"""
관리자 회원 관리 API

관리자가 회원 목록을 조회하고 회원 상태를 관리할 수 있는 API 엔드포인트
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from src.models.user import User, UserRole, UserStatus
from src.models.base import get_db
from src.middleware.authorization import require_permission, Permission
from src.utils.exceptions import ResourceNotFoundError, ValidationError


router = APIRouter(prefix="/v1/admin/users", tags=["Admin - Users"])


# ===== Request/Response 스키마 =====


class UserListItemResponse(BaseModel):
    """회원 목록 항목 응답"""

    id: str
    email: str
    name: str
    role: str
    status: str
    created_at: str
    last_login_at: Optional[str]
    failed_login_attempts: int

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "customer@example.com",
                "name": "홍길동",
                "role": "customer",
                "status": "active",
                "created_at": "2025-11-14T10:00:00",
                "last_login_at": "2025-11-14T12:00:00",
                "failed_login_attempts": 0,
            }
        }


class UserListResponse(BaseModel):
    """회원 목록 응답"""

    users: List[UserListItemResponse]
    total_count: int
    page: int
    page_size: int

    class Config:
        json_schema_extra = {
            "example": {"users": [], "total_count": 500, "page": 1, "page_size": 20}
        }


class UserDetailResponse(BaseModel):
    """회원 상세 응답"""

    id: str
    email: str
    name: str
    role: str
    status: str
    created_at: str
    last_login_at: Optional[str]
    failed_login_attempts: int

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "customer@example.com",
                "name": "홍길동",
                "role": "customer",
                "status": "active",
                "created_at": "2025-11-14T10:00:00",
                "last_login_at": "2025-11-14T12:00:00",
                "failed_login_attempts": 0,
            }
        }


class UserStatusUpdateRequest(BaseModel):
    """회원 상태 수정 요청"""

    status: UserStatus = Field(..., description="새로운 회원 상태")

    class Config:
        json_schema_extra = {"example": {"status": "suspended"}}


class UserStatusUpdateResponse(BaseModel):
    """회원 상태 수정 응답"""

    id: str
    email: str
    old_status: str
    new_status: str
    updated_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "customer@example.com",
                "old_status": "active",
                "new_status": "suspended",
                "updated_at": "2025-11-14T12:00:00",
            }
        }


# ===== API 엔드포인트 =====


@router.get(
    "",
    response_model=UserListResponse,
    summary="회원 목록 조회",
    description="관리자가 모든 회원 목록을 조회합니다 (필터링 및 페이지네이션 지원).",
)
async def get_users(
    role: Optional[UserRole] = Query(None, description="회원 역할 필터"),
    status: Optional[UserStatus] = Query(None, description="회원 상태 필터"),
    email: Optional[str] = Query(None, description="이메일 검색 (부분 일치)"),
    name: Optional[str] = Query(None, description="이름 검색 (부분 일치)"),
    start_date: Optional[datetime] = Query(
        None, description="가입 시작 날짜 (ISO 8601 형식)"
    ),
    end_date: Optional[datetime] = Query(
        None, description="가입 종료 날짜 (ISO 8601 형식)"
    ),
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기 (최대 100)"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission(Permission.USER_READ_ALL)),
):
    """
    모든 회원 목록을 조회합니다.

    **필요 권한**: USER_READ_ALL

    **필터 옵션**:
    - role: 회원 역할 (customer, admin, security_team)
    - status: 회원 상태 (active, suspended, deleted)
    - email: 이메일 (부분 일치)
    - name: 이름 (부분 일치)
    - start_date: 가입 시작 날짜 (이 날짜 이후 가입한 회원)
    - end_date: 가입 종료 날짜 (이 날짜 이전 가입한 회원)

    **페이지네이션**:
    - page: 페이지 번호 (기본값: 1)
    - page_size: 페이지 크기 (기본값: 20, 최대: 100)

    **반환**:
    - users: 회원 목록
    - total_count: 전체 회원 개수
    - page: 현재 페이지
    - page_size: 페이지 크기
    """
    # 기본 쿼리
    query = select(User)

    # 필터 적용
    filters = []

    if role:
        filters.append(User.role == role)

    if status:
        filters.append(User.status == status)

    if email:
        filters.append(User.email.ilike(f"%{email}%"))

    if name:
        filters.append(User.name.ilike(f"%{name}%"))

    if start_date:
        filters.append(User.created_at >= start_date)

    if end_date:
        filters.append(User.created_at <= end_date)

    if filters:
        query = query.where(and_(*filters))

    # 전체 개수 조회
    count_query = select(func.count(User.id))
    if filters:
        count_query = count_query.where(and_(*filters))

    total_count_result = await db.execute(count_query)
    total_count = total_count_result.scalar()

    # 정렬 및 페이지네이션
    offset = (page - 1) * page_size
    query = query.order_by(User.created_at.desc()).limit(page_size).offset(offset)

    # 실행
    result = await db.execute(query)
    users = result.scalars().all()

    # 응답 생성
    user_list = [
        UserListItemResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            role=user.role.value,
            status=user.status.value,
            created_at=user.created_at.isoformat(),
            last_login_at=(
                user.last_login_at.isoformat() if user.last_login_at else None
            ),
            failed_login_attempts=user.failed_login_attempts,
        )
        for user in users
    ]

    return UserListResponse(
        users=user_list, total_count=total_count, page=page, page_size=page_size
    )


@router.get(
    "/{user_id}",
    response_model=UserDetailResponse,
    summary="회원 상세 조회",
    description="관리자가 특정 회원의 상세 정보를 조회합니다.",
)
async def get_user_detail(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission(Permission.USER_READ_ALL)),
):
    """
    특정 회원의 상세 정보를 조회합니다.

    **필요 권한**: USER_READ_ALL

    **반환**:
    - 회원 상세 정보

    **에러**:
    - 404: 회원을 찾을 수 없음
    """
    # 회원 조회
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise ResourceNotFoundError(detail=f"회원을 찾을 수 없습니다: {user_id}")

    return UserDetailResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role.value,
        status=user.status.value,
        created_at=user.created_at.isoformat(),
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        failed_login_attempts=user.failed_login_attempts,
    )


@router.patch(
    "/{user_id}/status",
    response_model=UserStatusUpdateResponse,
    summary="회원 상태 변경",
    description="관리자가 회원 상태를 변경합니다 (예: 정지, 활성화, 삭제).",
)
async def update_user_status(
    user_id: str,
    request: UserStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission(Permission.USER_UPDATE_ALL)),
):
    """
    회원 상태를 변경합니다.

    **필요 권한**: USER_UPDATE_ALL

    **입력**:
    - status: 새로운 회원 상태 (active, suspended, deleted)

    **허용되는 상태 전환**:
    - active → suspended (계정 정지)
    - active → deleted (계정 삭제)
    - suspended → active (정지 해제)
    - suspended → deleted (계정 삭제)

    **주의사항**:
    - deleted 상태로 변경하면 회원 정보는 유지되지만 로그인 불가
    - 실제 데이터 삭제는 별도의 배치 작업으로 처리
    - 자기 자신의 상태는 변경할 수 없음

    **반환**:
    - 수정된 회원 정보

    **에러**:
    - 404: 회원을 찾을 수 없음
    - 400: 잘못된 상태 전환 또는 자기 자신의 상태 변경 시도
    """
    # 회원 조회
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise ResourceNotFoundError(detail=f"회원을 찾을 수 없습니다: {user_id}")

    # 자기 자신의 상태 변경 방지
    if str(user.id) == str(current_user.id):
        raise ValidationError(detail="자기 자신의 상태는 변경할 수 없습니다.")

    old_status = user.status
    new_status = request.status

    # 상태 전환 검증
    valid_transitions = {
        UserStatus.ACTIVE: [UserStatus.SUSPENDED, UserStatus.DELETED],
        UserStatus.SUSPENDED: [UserStatus.ACTIVE, UserStatus.DELETED],
        UserStatus.DELETED: [],  # DELETED 상태에서는 다른 상태로 전환 불가
    }

    if new_status not in valid_transitions.get(old_status, []):
        raise ValidationError(
            detail=f"'{old_status.value}' 상태에서 '{new_status.value}'로 변경할 수 없습니다."
        )

    # 상태 변경
    user.status = new_status

    # 정지 또는 삭제 시 로그인 실패 횟수 초기화
    if new_status in [UserStatus.SUSPENDED, UserStatus.DELETED]:
        user.reset_failed_attempts()

    await db.commit()
    await db.refresh(user)

    return UserStatusUpdateResponse(
        id=str(user.id),
        email=user.email,
        old_status=old_status.value,
        new_status=user.status.value,
        updated_at=datetime.utcnow().isoformat(),
    )
