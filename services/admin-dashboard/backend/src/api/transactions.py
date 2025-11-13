"""
거래 API 엔드포인트

거래 상세 정보 조회 및 분석 API입니다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import datetime
from uuid import UUID
from typing import Optional
import sys
import os

# FDS 모델 import를 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../.."))
from services.fds.src.models.transaction import (
    Transaction,
    RiskLevel,
    EvaluationStatus,
)
from services.fds.src.models.risk_factor import RiskFactor
from services.fds.src.models.review_queue import ReviewQueue

from src.database import get_db

router = APIRouter(prefix="/v1/transactions", tags=["Transactions"])


@router.get("/{transaction_id}")
async def get_transaction_detail(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    거래 상세 정보 조회

    특정 거래의 모든 정보를 조회합니다.
    FDS 평가 결과, 위험 요인, 검토 큐 정보 등을 포함합니다.

    Args:
        transaction_id: 거래 ID
        db: 데이터베이스 세션

    Returns:
        dict: 거래 상세 정보
            - transaction: 거래 기본 정보
            - risk_factors: 위험 요인 리스트
            - review_queue: 검토 큐 정보 (존재하는 경우)
            - user_history: 사용자 거래 이력 요약
    """

    # 거래 정보 조회
    transaction_query = select(Transaction).where(Transaction.id == transaction_id)
    transaction_result = await db.execute(transaction_query)
    transaction = transaction_result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=404, detail=f"거래를 찾을 수 없습니다: {transaction_id}"
        )

    # 위험 요인 조회
    risk_factors_query = select(RiskFactor).where(
        RiskFactor.transaction_id == transaction.id
    )
    risk_factors_result = await db.execute(risk_factors_query)
    risk_factors = risk_factors_result.scalars().all()

    # 검토 큐 정보 조회 (존재하는 경우)
    review_queue_query = select(ReviewQueue).where(
        ReviewQueue.transaction_id == transaction.id
    )
    review_queue_result = await db.execute(review_queue_query)
    review_queue = review_queue_result.scalar_one_or_none()

    # 사용자 거래 이력 요약
    user_history_query = select(
        func.count(Transaction.id).label("total_transactions"),
        func.count(Transaction.id)
        .filter(Transaction.risk_level == RiskLevel.HIGH)
        .label("high_risk_count"),
        func.count(Transaction.id)
        .filter(Transaction.evaluation_status == EvaluationStatus.BLOCKED)
        .label("blocked_count"),
        func.avg(Transaction.risk_score).label("avg_risk_score"),
    ).where(Transaction.user_id == transaction.user_id)

    user_history_result = await db.execute(user_history_query)
    user_history_row = user_history_result.fetchone()

    # 응답 데이터 구성
    response = {
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
        "review_queue": (
            {
                "id": str(review_queue.id),
                "status": review_queue.status.value,
                "decision": review_queue.decision.value
                if review_queue.decision
                else None,
                "assigned_to": str(review_queue.assigned_to)
                if review_queue.assigned_to
                else None,
                "review_notes": review_queue.review_notes,
                "added_at": review_queue.added_at.isoformat(),
                "reviewed_at": review_queue.reviewed_at.isoformat()
                if review_queue.reviewed_at
                else None,
            }
            if review_queue
            else None
        ),
        "user_history": {
            "total_transactions": user_history_row.total_transactions or 0,
            "high_risk_count": user_history_row.high_risk_count or 0,
            "blocked_count": user_history_row.blocked_count or 0,
            "avg_risk_score": (
                round(user_history_row.avg_risk_score, 2)
                if user_history_row.avg_risk_score
                else 0
            ),
        },
    }

    return response


@router.get("")
async def list_transactions(
    user_id: Optional[UUID] = Query(None, description="사용자 ID 필터"),
    risk_level: Optional[RiskLevel] = Query(None, description="위험 수준 필터"),
    evaluation_status: Optional[EvaluationStatus] = Query(
        None, description="평가 상태 필터"
    ),
    limit: int = Query(50, ge=1, le=100, description="최대 결과 수"),
    offset: int = Query(0, ge=0, description="오프셋"),
    db: AsyncSession = Depends(get_db),
):
    """
    거래 목록 조회

    필터 조건에 맞는 거래 목록을 조회합니다.

    Args:
        user_id: 사용자 ID 필터
        risk_level: 위험 수준 필터 (low/medium/high)
        evaluation_status: 평가 상태 필터
        limit: 최대 결과 수 (기본 50, 최대 100)
        offset: 페이지네이션 오프셋
        db: 데이터베이스 세션

    Returns:
        dict: 거래 목록
            - items: 거래 리스트
            - total: 전체 거래 수
            - limit: 요청한 limit
            - offset: 요청한 offset
    """

    # 기본 쿼리
    base_query = select(Transaction)

    # 필터 적용
    filters = []
    if user_id:
        filters.append(Transaction.user_id == user_id)
    if risk_level:
        filters.append(Transaction.risk_level == risk_level)
    if evaluation_status:
        filters.append(Transaction.evaluation_status == evaluation_status)

    if filters:
        base_query = base_query.where(and_(*filters))

    # 최신순 정렬
    base_query = base_query.order_by(Transaction.created_at.desc())

    # 전체 개수 조회
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 페이지네이션 적용
    items_query = base_query.limit(limit).offset(offset)
    items_result = await db.execute(items_query)
    transactions = items_result.scalars().all()

    # 응답 데이터 구성
    items = [
        {
            "id": str(transaction.id),
            "order_id": str(transaction.order_id),
            "user_id": str(transaction.user_id),
            "amount": float(transaction.amount),
            "risk_score": transaction.risk_score,
            "risk_level": transaction.risk_level.value,
            "evaluation_status": transaction.evaluation_status.value,
            "ip_address": transaction.ip_address,
            "device_type": transaction.device_type.value,
            "evaluation_time_ms": transaction.evaluation_time_ms,
            "created_at": transaction.created_at.isoformat(),
        }
        for transaction in transactions
    ]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {
            "user_id": str(user_id) if user_id else None,
            "risk_level": risk_level.value if risk_level else None,
            "evaluation_status": evaluation_status.value
            if evaluation_status
            else None,
        },
    }
