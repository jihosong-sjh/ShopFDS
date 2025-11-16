"""
룰 관리 API 엔드포인트

보안팀이 FDS 탐지 룰을 동적으로 추가/수정/삭제할 수 있는 API를 제공합니다.
코드 배포 없이 데이터베이스를 통해 룰을 즉시 활성화할 수 있습니다.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# FDS 모델 임포트 (상대 경로가 아닌 절대 경로 사용)
import sys
import os

# FDS 서비스 경로를 Python 경로에 추가
fds_service_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../fds/src")
)
if fds_service_path not in sys.path:
    sys.path.insert(0, fds_service_path)

from models.detection_rule import DetectionRule, RuleType
from src.database import get_db

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/rules", tags=["Rules"])


# --- Pydantic Schemas ---


class RuleCondition(BaseModel):
    """룰 조건 스키마 (JSON 형식)"""

    # Velocity 룰
    window_seconds: Optional[int] = Field(
        None, description="시간 윈도우 (초)", ge=1, le=86400
    )
    max_transactions: Optional[int] = Field(None, description="최대 거래 횟수", ge=1, le=100)
    scope: Optional[str] = Field(
        None, description="적용 범위 (ip_address, user_id, card_bin)"
    )

    # Threshold 룰
    field: Optional[str] = Field(None, description="비교할 필드 (amount 등)")
    operator: Optional[str] = Field(None, description="비교 연산자 (gt, gte, lt, lte, eq)")
    value: Optional[float] = Field(None, description="임계값")

    # Blacklist 룰
    type: Optional[str] = Field(
        None, description="블랙리스트 유형 (ip, email_domain, card_bin)"
    )
    values: Optional[List[str]] = Field(None, description="블랙리스트 값 목록")

    # Location 룰
    max_distance_km: Optional[float] = Field(
        None, description="최대 거리 (km)", ge=0, le=10000
    )

    # Time Pattern 룰
    start_hour: Optional[int] = Field(None, description="시작 시간 (0-23)", ge=0, le=23)
    end_hour: Optional[int] = Field(None, description="종료 시간 (0-23)", ge=0, le=23)

    # Device Pattern 룰
    max_devices: Optional[int] = Field(None, description="최대 디바이스 수", ge=1, le=10)


class RuleCreateRequest(BaseModel):
    """룰 생성 요청"""

    name: str = Field(..., description="룰 이름", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="룰 설명")
    rule_type: str = Field(..., description="룰 유형")
    condition: dict = Field(..., description="룰 조건 (JSON 형식)")
    risk_score_weight: int = Field(50, description="위험 점수 가중치 (0-100)", ge=0, le=100)
    is_active: bool = Field(True, description="활성화 여부")
    priority: int = Field(50, description="우선순위 (0-100, 높을수록 먼저 평가)", ge=0, le=100)

    @validator("rule_type")
    def validate_rule_type(cls, v):
        """룰 유형 검증"""
        valid_types = [rt.value for rt in RuleType]
        if v not in valid_types:
            raise ValueError(
                f"Invalid rule_type. Must be one of: {', '.join(valid_types)}"
            )
        return v


class RuleUpdateRequest(BaseModel):
    """룰 수정 요청"""

    name: Optional[str] = Field(None, description="룰 이름", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="룰 설명")
    condition: Optional[dict] = Field(None, description="룰 조건 (JSON 형식)")
    risk_score_weight: Optional[int] = Field(
        None, description="위험 점수 가중치 (0-100)", ge=0, le=100
    )
    is_active: Optional[bool] = Field(None, description="활성화 여부")
    priority: Optional[int] = Field(None, description="우선순위 (0-100)", ge=0, le=100)


class RuleResponse(BaseModel):
    """룰 응답"""

    id: str
    name: str
    description: Optional[str]
    rule_type: str
    condition: dict
    risk_score_weight: int
    is_active: bool
    priority: int
    created_by: Optional[str]
    times_triggered: int
    last_triggered_at: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class RuleListResponse(BaseModel):
    """룰 목록 응답"""

    total: int
    rules: List[RuleResponse]


# --- API Endpoints ---


@router.get("/", response_model=RuleListResponse, summary="룰 목록 조회")
async def list_rules(
    rule_type: Optional[str] = Query(None, description="룰 유형 필터"),
    is_active: Optional[bool] = Query(None, description="활성화 상태 필터"),
    skip: int = Query(0, description="건너뛸 개수", ge=0),
    limit: int = Query(100, description="조회할 개수", ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """
    FDS 탐지 룰 목록을 조회합니다.

    **필터링 옵션**:
    - `rule_type`: 특정 룰 유형만 조회 (예: velocity, threshold)
    - `is_active`: 활성화 상태로 필터링 (true: 활성화만, false: 비활성화만)

    **정렬**: 우선순위 내림차순, 생성일 기준
    """
    try:
        # 기본 쿼리
        query = select(DetectionRule)

        # 필터 적용
        if rule_type:
            query = query.where(DetectionRule.rule_type == rule_type)

        if is_active is not None:
            query = query.where(DetectionRule.is_active == is_active)

        # 정렬: 우선순위 내림차순, 생성일 기준
        query = query.order_by(
            DetectionRule.priority.desc(), DetectionRule.created_at.desc()
        )

        # 전체 개수 조회
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 페이지네이션 적용
        query = query.offset(skip).limit(limit)

        # 룰 조회
        result = await db.execute(query)
        rules = result.scalars().all()

        return RuleListResponse(
            total=total, rules=[RuleResponse(**rule.to_dict()) for rule in rules]
        )

    except Exception as e:
        logger.error(f"룰 목록 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="룰 목록 조회 중 오류가 발생했습니다.",
        )


@router.get("/{rule_id}", response_model=RuleResponse, summary="룰 상세 조회")
async def get_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    특정 FDS 탐지 룰의 상세 정보를 조회합니다.

    **응답**:
    - 룰의 모든 정보 (조건, 트리거 통계 포함)
    """
    try:
        # 룰 조회
        query = select(DetectionRule).where(DetectionRule.id == rule_id)
        result = await db.execute(query)
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"룰을 찾을 수 없습니다: {rule_id}",
            )

        return RuleResponse(**rule.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"룰 상세 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="룰 상세 조회 중 오류가 발생했습니다.",
        )


@router.post(
    "/",
    response_model=RuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새 룰 생성",
)
async def create_rule(
    request: RuleCreateRequest,
    db: AsyncSession = Depends(get_db),
    # TODO: current_user: User = Depends(get_current_user),
):
    """
    새로운 FDS 탐지 룰을 생성합니다.

    **주의**:
    - 룰 이름은 고유해야 합니다.
    - 룰 조건은 rule_type에 따라 필수 필드가 다릅니다.

    **예시 조건**:
    - **Velocity**: `{"window_seconds": 300, "max_transactions": 3, "scope": "ip_address"}`
    - **Threshold**: `{"field": "amount", "operator": "gt", "value": 500000}`
    - **Blacklist**: `{"type": "ip", "values": ["1.2.3.4", "5.6.7.8"]}`
    """
    try:
        # 룰 이름 중복 확인
        existing_query = select(DetectionRule).where(DetectionRule.name == request.name)
        existing_result = await db.execute(existing_query)
        existing_rule = existing_result.scalar_one_or_none()

        if existing_rule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"이미 존재하는 룰 이름입니다: {request.name}",
            )

        # 새 룰 생성
        new_rule = DetectionRule(
            name=request.name,
            description=request.description,
            rule_type=RuleType(request.rule_type),
            condition=request.condition,
            risk_score_weight=request.risk_score_weight,
            is_active=request.is_active,
            priority=request.priority,
            # created_by=current_user.id,  # TODO: 인증 구현 후 활성화
        )

        # 룰 조건 검증
        if not new_rule.validate_condition():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"룰 조건이 유효하지 않습니다. rule_type={request.rule_type}에 필요한 필드를 확인하세요.",
            )

        db.add(new_rule)
        await db.commit()
        await db.refresh(new_rule)

        logger.info(f"새 룰 생성 완료: {new_rule.name} (ID: {new_rule.id})")

        return RuleResponse(**new_rule.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"룰 생성 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="룰 생성 중 오류가 발생했습니다.",
        )


@router.put("/{rule_id}", response_model=RuleResponse, summary="룰 수정")
async def update_rule(
    rule_id: UUID,
    request: RuleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    # TODO: current_user: User = Depends(get_current_user),
):
    """
    기존 FDS 탐지 룰을 수정합니다.

    **주의**:
    - rule_type은 수정할 수 없습니다 (새 룰을 생성하세요).
    - 룰 이름 변경 시 중복 확인을 수행합니다.
    """
    try:
        # 룰 조회
        query = select(DetectionRule).where(DetectionRule.id == rule_id)
        result = await db.execute(query)
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"룰을 찾을 수 없습니다: {rule_id}",
            )

        # 룰 이름 변경 시 중복 확인
        if request.name and request.name != rule.name:
            existing_query = select(DetectionRule).where(
                DetectionRule.name == request.name
            )
            existing_result = await db.execute(existing_query)
            existing_rule = existing_result.scalar_one_or_none()

            if existing_rule:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"이미 존재하는 룰 이름입니다: {request.name}",
                )

        # 수정 사항 적용
        if request.name is not None:
            rule.name = request.name
        if request.description is not None:
            rule.description = request.description
        if request.condition is not None:
            rule.condition = request.condition
        if request.risk_score_weight is not None:
            rule.risk_score_weight = request.risk_score_weight
        if request.is_active is not None:
            rule.is_active = request.is_active
        if request.priority is not None:
            rule.priority = request.priority

        # 룰 조건 검증
        if request.condition is not None and not rule.validate_condition():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"룰 조건이 유효하지 않습니다. rule_type={rule.rule_type}에 필요한 필드를 확인하세요.",
            )

        await db.commit()
        await db.refresh(rule)

        logger.info(f"룰 수정 완료: {rule.name} (ID: {rule.id})")

        return RuleResponse(**rule.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"룰 수정 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="룰 수정 중 오류가 발생했습니다.",
        )


@router.patch("/{rule_id}/toggle", response_model=RuleResponse, summary="룰 활성화/비활성화 토글")
async def toggle_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    # TODO: current_user: User = Depends(get_current_user),
):
    """
    FDS 탐지 룰의 활성화 상태를 토글합니다.

    **동작**:
    - 현재 `is_active=true` → `is_active=false`로 변경 (비활성화)
    - 현재 `is_active=false` → `is_active=true`로 변경 (활성화)

    **효과**:
    - 비활성화된 룰은 FDS 평가 시 로드되지 않습니다.
    - 코드 배포 없이 즉시 적용됩니다 (룰 엔진 캐시 갱신).
    """
    try:
        # 룰 조회
        query = select(DetectionRule).where(DetectionRule.id == rule_id)
        result = await db.execute(query)
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"룰을 찾을 수 없습니다: {rule_id}",
            )

        # 활성화 상태 토글
        old_status = rule.is_active
        rule.is_active = not rule.is_active

        await db.commit()
        await db.refresh(rule)

        logger.info(
            f"룰 상태 변경 완료: {rule.name} (ID: {rule.id}), "
            f"{old_status} -> {rule.is_active}"
        )

        return RuleResponse(**rule.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"룰 토글 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="룰 상태 변경 중 오류가 발생했습니다.",
        )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, summary="룰 삭제")
async def delete_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    # TODO: current_user: User = Depends(get_current_user),
):
    """
    FDS 탐지 룰을 삭제합니다.

    **주의**:
    - 룰을 삭제하면 복구할 수 없습니다.
    - 대신 `is_active=false`로 비활성화하는 것을 권장합니다.
    """
    try:
        # 룰 조회
        query = select(DetectionRule).where(DetectionRule.id == rule_id)
        result = await db.execute(query)
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"룰을 찾을 수 없습니다: {rule_id}",
            )

        # 룰 삭제
        await db.delete(rule)
        await db.commit()

        logger.info(f"룰 삭제 완료: {rule.name} (ID: {rule.id})")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"룰 삭제 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="룰 삭제 중 오류가 발생했습니다.",
        )
