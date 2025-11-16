"""
검토 큐 API 엔드포인트

차단된 고위험 거래를 검토하고 승인/차단 결정을 내리는 API입니다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field
import sys
import os

# FDS 모델 import를 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../.."))
from services.fds.src.models.transaction import (
    Transaction,
    EvaluationStatus,
)
from services.fds.src.models.review_queue import (
    ReviewQueue,
    ReviewStatus,
    ReviewDecision,
)
from services.fds.src.models.risk_factor import RiskFactor

from src.database import get_db

router = APIRouter(prefix="/v1/review-queue", tags=["Review Queue"])


# Pydantic 스키마
class ReviewDecisionRequest(BaseModel):
    """검토 결정 요청"""

    decision: ReviewDecision = Field(..., description="검토 결과 (approve/block/escalate)")
    notes: Optional[str] = Field(None, description="검토 메모 (최대 1000자)", max_length=1000)
    reviewer_id: UUID = Field(..., description="검토 담당자 ID")


class ReviewQueueItem(BaseModel):
    """검토 큐 항목 응답"""

    id: str
    transaction_id: str
    status: ReviewStatus
    decision: Optional[ReviewDecision]
    assigned_to: Optional[str]
    review_notes: Optional[str]
    added_at: str
    reviewed_at: Optional[str]
    transaction: dict  # 거래 정보 (간략)


@router.get("")
async def get_review_queue(
    status: Optional[ReviewStatus] = Query(
        None, description="검토 상태 필터 (pending/in_review/completed)"
    ),
    limit: int = Query(50, ge=1, le=100, description="최대 결과 수"),
    offset: int = Query(0, ge=0, description="오프셋"),
    db: AsyncSession = Depends(get_db),
):
    """
    검토 큐 목록 조회

    차단된 고위험 거래 목록을 조회합니다.
    보안팀이 수동으로 검토해야 할 거래들을 확인할 수 있습니다.

    Args:
        status: 검토 상태 필터 (None이면 전체)
        limit: 최대 결과 수 (기본 50, 최대 100)
        offset: 페이지네이션 오프셋
        db: 데이터베이스 세션

    Returns:
        dict: 검토 큐 목록
            - items: 검토 큐 항목 리스트
            - total: 전체 항목 수
            - limit: 요청한 limit
            - offset: 요청한 offset
    """

    # 기본 쿼리
    base_query = select(ReviewQueue).join(
        Transaction, ReviewQueue.transaction_id == Transaction.id
    )

    # 상태 필터 적용
    if status:
        base_query = base_query.where(ReviewQueue.status == status)

    # 최신순 정렬
    base_query = base_query.order_by(ReviewQueue.added_at.desc())

    # 전체 개수 조회
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 페이지네이션 적용
    items_query = base_query.limit(limit).offset(offset)
    items_result = await db.execute(items_query)
    review_queue_items = items_result.scalars().all()

    # 응답 데이터 구성
    items = []
    for item in review_queue_items:
        # Transaction 정보 조회
        transaction_query = select(Transaction).where(
            Transaction.id == item.transaction_id
        )
        transaction_result = await db.execute(transaction_query)
        transaction = transaction_result.scalar_one_or_none()

        if not transaction:
            continue

        items.append(
            {
                "id": str(item.id),
                "transaction_id": str(item.transaction_id),
                "status": item.status.value,
                "decision": item.decision.value if item.decision else None,
                "assigned_to": str(item.assigned_to) if item.assigned_to else None,
                "review_notes": item.review_notes,
                "added_at": item.added_at.isoformat(),
                "reviewed_at": item.reviewed_at.isoformat()
                if item.reviewed_at
                else None,
                "transaction": {
                    "order_id": str(transaction.order_id),
                    "user_id": str(transaction.user_id),
                    "amount": float(transaction.amount),
                    "risk_score": transaction.risk_score,
                    "risk_level": transaction.risk_level.value,
                    "ip_address": transaction.ip_address,
                    "device_type": transaction.device_type.value,
                    "created_at": transaction.created_at.isoformat(),
                },
            }
        )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/{review_queue_id}/approve")
async def approve_or_block_transaction(
    review_queue_id: UUID,
    request: ReviewDecisionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    차단 해제/승인 API

    검토 큐에 있는 거래에 대해 최종 결정을 내립니다.
    - approve: 오탐으로 판단, 거래 승인
    - block: 정탐으로 판단, 차단 유지
    - escalate: 추가 조사 필요, 상위 에스컬레이션

    Args:
        review_queue_id: 검토 큐 ID
        request: 검토 결정 요청 (decision, notes, reviewer_id)
        db: 데이터베이스 세션

    Returns:
        dict: 검토 결과
            - review_queue_id: 검토 큐 ID
            - transaction_id: 거래 ID
            - decision: 최종 결정
            - status: 검토 상태
            - reviewed_at: 검토 완료 시간
    """

    # 검토 큐 항목 조회
    review_queue_query = select(ReviewQueue).where(ReviewQueue.id == review_queue_id)
    review_queue_result = await db.execute(review_queue_query)
    review_queue = review_queue_result.scalar_one_or_none()

    if not review_queue:
        raise HTTPException(
            status_code=404, detail=f"검토 큐 항목을 찾을 수 없습니다: {review_queue_id}"
        )

    # 이미 완료된 검토인지 확인
    if review_queue.status == ReviewStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="이미 검토가 완료된 항목입니다.")

    # 거래 정보 조회
    transaction_query = select(Transaction).where(
        Transaction.id == review_queue.transaction_id
    )
    transaction_result = await db.execute(transaction_query)
    transaction = transaction_result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=f"거래를 찾을 수 없습니다: {review_queue.transaction_id}",
        )

    # 검토 완료 처리
    review_queue.complete_review(decision=request.decision, notes=request.notes)
    review_queue.assigned_to = request.reviewer_id

    # 결정에 따라 거래 상태 업데이트
    if request.decision == ReviewDecision.APPROVE:
        transaction.evaluation_status = EvaluationStatus.APPROVED
    elif request.decision == ReviewDecision.BLOCK:
        transaction.evaluation_status = EvaluationStatus.BLOCKED
    elif request.decision == ReviewDecision.ESCALATE:
        transaction.evaluation_status = EvaluationStatus.MANUAL_REVIEW

    # 변경사항 저장
    try:
        await db.commit()
        await db.refresh(review_queue)
        await db.refresh(transaction)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"검토 결과 저장 실패: {str(e)}")

    return {
        "review_queue_id": str(review_queue.id),
        "transaction_id": str(review_queue.transaction_id),
        "decision": review_queue.decision.value,
        "status": review_queue.status.value,
        "reviewed_at": review_queue.reviewed_at.isoformat(),
        "transaction_status": transaction.evaluation_status.value,
        "message": f"검토가 완료되었습니다. 결정: {request.decision.value}",
    }


@router.get("/{review_queue_id}")
async def get_review_queue_detail(
    review_queue_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    검토 큐 항목 상세 조회

    Args:
        review_queue_id: 검토 큐 ID
        db: 데이터베이스 세션

    Returns:
        dict: 검토 큐 항목 상세 정보
    """

    # 검토 큐 항목 조회
    review_queue_query = select(ReviewQueue).where(ReviewQueue.id == review_queue_id)
    review_queue_result = await db.execute(review_queue_query)
    review_queue = review_queue_result.scalar_one_or_none()

    if not review_queue:
        raise HTTPException(
            status_code=404, detail=f"검토 큐 항목을 찾을 수 없습니다: {review_queue_id}"
        )

    # 거래 정보 조회
    transaction_query = select(Transaction).where(
        Transaction.id == review_queue.transaction_id
    )
    transaction_result = await db.execute(transaction_query)
    transaction = transaction_result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=f"거래를 찾을 수 없습니다: {review_queue.transaction_id}",
        )

    # 위험 요인 조회
    risk_factors_query = select(RiskFactor).where(
        RiskFactor.transaction_id == transaction.id
    )
    risk_factors_result = await db.execute(risk_factors_query)
    risk_factors = risk_factors_result.scalars().all()

    return {
        "id": str(review_queue.id),
        "transaction_id": str(review_queue.transaction_id),
        "status": review_queue.status.value,
        "decision": review_queue.decision.value if review_queue.decision else None,
        "assigned_to": str(review_queue.assigned_to)
        if review_queue.assigned_to
        else None,
        "review_notes": review_queue.review_notes,
        "added_at": review_queue.added_at.isoformat(),
        "reviewed_at": review_queue.reviewed_at.isoformat()
        if review_queue.reviewed_at
        else None,
        "transaction": {
            "id": str(transaction.id),
            "order_id": str(transaction.order_id),
            "user_id": str(transaction.user_id),
            "amount": float(transaction.amount),
            "risk_score": transaction.risk_score,
            "risk_level": transaction.risk_level.value,
            "evaluation_status": transaction.evaluation_status.value,
            "ip_address": transaction.ip_address,
            "user_agent": transaction.user_agent,
            "device_type": transaction.device_type.value,
            "geolocation": transaction.geolocation,
            "evaluation_time_ms": transaction.evaluation_time_ms,
            "created_at": transaction.created_at.isoformat(),
            "evaluated_at": transaction.evaluated_at.isoformat()
            if transaction.evaluated_at
            else None,
        },
        "risk_factors": [
            {
                "id": str(factor.id),
                "factor_type": factor.factor_type,
                "factor_score": factor.factor_score,
                "description": factor.description,
                "metadata": factor.metadata,
            }
            for factor in risk_factors
        ],
    }
