"""
룰 관리 API

FDS 사기 탐지 룰의 생성, 수정, 삭제, 조회 엔드포인트를 제공합니다.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import get_db
from ..models.fraud_rule import FraudRule, RuleCategory

router = APIRouter(prefix="/v1/fds/rules", tags=["Rules"])


# === Pydantic Schemas ===


class RuleCreateRequest(BaseModel):
    """룰 생성 요청"""

    rule_name: str = Field(..., description="룰 이름", max_length=255)
    rule_category: RuleCategory = Field(
        ..., description="룰 카테고리 (payment/account/shipping)"
    )
    rule_description: Optional[str] = Field(None, description="룰 설명")
    rule_logic: Optional[dict] = Field(None, description="룰 실행 로직 (JSON)")
    risk_score: int = Field(..., description="룰 매칭 시 부여할 위험 점수", ge=0, le=100)
    is_active: bool = Field(True, description="활성화 여부")
    priority: int = Field(0, description="우선순위 (높을수록 먼저 실행)", ge=0, le=100)

    class Config:
        json_schema_extra = {
            "example": {
                "rule_name": "테스트 카드 사용 감지",
                "rule_category": "payment",
                "rule_description": "알려진 테스트 카드 번호를 사용한 거래를 차단합니다.",
                "rule_logic": {"type": "test_card_check", "action": "block"},
                "risk_score": 100,
                "is_active": True,
                "priority": 100,
            }
        }


class RuleUpdateRequest(BaseModel):
    """룰 수정 요청"""

    rule_name: Optional[str] = Field(None, description="룰 이름", max_length=255)
    rule_category: Optional[RuleCategory] = Field(None, description="룰 카테고리")
    rule_description: Optional[str] = Field(None, description="룰 설명")
    rule_logic: Optional[dict] = Field(None, description="룰 실행 로직 (JSON)")
    risk_score: Optional[int] = Field(None, description="위험 점수", ge=0, le=100)
    is_active: Optional[bool] = Field(None, description="활성화 여부")
    priority: Optional[int] = Field(None, description="우선순위", ge=0, le=100)

    class Config:
        json_schema_extra = {
            "example": {"risk_score": 90, "is_active": False, "priority": 50}
        }


class RuleResponse(BaseModel):
    """룰 응답"""

    rule_id: UUID
    rule_name: str
    rule_category: RuleCategory
    rule_description: Optional[str]
    rule_logic: Optional[dict]
    risk_score: int
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID]

    class Config:
        from_attributes = True


# === API Endpoints ===


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    request: RuleCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    새로운 사기 탐지 룰 생성

    **권한**: Admin 또는 Security Team

    **요청 본문**:
    - rule_name: 룰 이름 (필수, 최대 255자)
    - rule_category: 룰 카테고리 (필수, payment/account/shipping)
    - rule_description: 룰 설명 (선택)
    - rule_logic: 룰 실행 로직 JSON (선택)
    - risk_score: 위험 점수 (필수, 0-100)
    - is_active: 활성화 여부 (기본값: True)
    - priority: 우선순위 (기본값: 0, 높을수록 먼저 실행)

    **응답**:
    - 201 Created: 생성된 룰 정보
    - 400 Bad Request: 잘못된 요청 데이터
    """
    # FraudRule 객체 생성
    rule = FraudRule(
        rule_name=request.rule_name,
        rule_category=request.rule_category,
        rule_description=request.rule_description,
        rule_logic=request.rule_logic,
        risk_score=request.risk_score,
        is_active=request.is_active,
        priority=request.priority,
        # created_by는 인증 시스템 통합 후 설정
    )

    db.add(rule)
    await db.commit()
    await db.refresh(rule)

    return rule


@router.get("", response_model=List[RuleResponse])
async def list_rules(
    category: Optional[RuleCategory] = Query(None, description="룰 카테고리 필터"),
    is_active: Optional[bool] = Query(None, description="활성화 상태 필터"),
    skip: int = Query(0, description="건너뛸 개수", ge=0),
    limit: int = Query(100, description="조회할 최대 개수", ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """
    사기 탐지 룰 목록 조회

    **쿼리 파라미터**:
    - category: 룰 카테고리 필터 (payment/account/shipping, 선택)
    - is_active: 활성화 상태 필터 (true/false, 선택)
    - skip: 페이지네이션 오프셋 (기본값: 0)
    - limit: 최대 조회 개수 (기본값: 100, 최대: 1000)

    **응답**:
    - 200 OK: 룰 목록 (우선순위 역순 + 생성 일시 순)
    """
    query = select(FraudRule)

    # 필터 적용
    if category:
        query = query.where(FraudRule.rule_category == category)
    if is_active is not None:
        query = query.where(FraudRule.is_active == is_active)

    # 정렬: 우선순위 내림차순, 생성 일시 오름차순
    query = query.order_by(FraudRule.priority.desc(), FraudRule.created_at)

    # 페이지네이션
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    rules = result.scalars().all()

    return rules


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    특정 룰 상세 조회

    **경로 파라미터**:
    - rule_id: 룰 ID (UUID)

    **응답**:
    - 200 OK: 룰 상세 정보
    - 404 Not Found: 룰이 존재하지 않음
    """
    query = select(FraudRule).where(FraudRule.rule_id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule not found: {rule_id}",
        )

    return rule


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: UUID,
    request: RuleUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    룰 수정

    **권한**: Admin 또는 Security Team

    **경로 파라미터**:
    - rule_id: 룰 ID (UUID)

    **요청 본문**:
    - rule_name: 룰 이름 (선택)
    - rule_category: 룰 카테고리 (선택)
    - rule_description: 룰 설명 (선택)
    - rule_logic: 룰 실행 로직 JSON (선택)
    - risk_score: 위험 점수 (선택, 0-100)
    - is_active: 활성화 여부 (선택)
    - priority: 우선순위 (선택, 0-100)

    **응답**:
    - 200 OK: 수정된 룰 정보
    - 404 Not Found: 룰이 존재하지 않음
    """
    # 룰 조회
    query = select(FraudRule).where(FraudRule.rule_id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule not found: {rule_id}",
        )

    # 수정 사항 적용
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    rule.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(rule)

    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    룰 삭제

    **권한**: Admin 또는 Security Team

    **경로 파라미터**:
    - rule_id: 룰 ID (UUID)

    **응답**:
    - 204 No Content: 삭제 성공
    - 404 Not Found: 룰이 존재하지 않음

    **주의**: 이 작업은 되돌릴 수 없습니다.
    """
    # 룰 조회
    query = select(FraudRule).where(FraudRule.rule_id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule not found: {rule_id}",
        )

    # 룰 삭제
    await db.delete(rule)
    await db.commit()

    return None


@router.patch("/{rule_id}/toggle", response_model=RuleResponse)
async def toggle_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    룰 활성화/비활성화 토글

    **권한**: Admin 또는 Security Team

    **경로 파라미터**:
    - rule_id: 룰 ID (UUID)

    **응답**:
    - 200 OK: 토글된 룰 정보
    - 404 Not Found: 룰이 존재하지 않음
    """
    # 룰 조회
    query = select(FraudRule).where(FraudRule.rule_id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule not found: {rule_id}",
        )

    # 활성화 상태 토글
    rule.is_active = not rule.is_active
    rule.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(rule)

    return rule


@router.get("/stats/summary")
async def get_rule_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    룰 통계 요약

    **응답**:
    - total_rules: 전체 룰 수
    - active_rules: 활성화된 룰 수
    - by_category: 카테고리별 룰 수
    """
    # 전체 룰 수
    total_query = select(FraudRule)
    total_result = await db.execute(total_query)
    total_rules = len(total_result.scalars().all())

    # 활성화된 룰 수
    active_query = select(FraudRule).where(FraudRule.is_active)
    active_result = await db.execute(active_query)
    active_rules = len(active_result.scalars().all())

    # 카테고리별 룰 수
    by_category = {}
    for category in RuleCategory:
        category_query = select(FraudRule).where(FraudRule.rule_category == category)
        category_result = await db.execute(category_query)
        by_category[category.value] = len(category_result.scalars().all())

    return {
        "total_rules": total_rules,
        "active_rules": active_rules,
        "inactive_rules": total_rules - active_rules,
        "by_category": by_category,
    }
