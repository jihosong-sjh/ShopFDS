"""
대시보드 API 엔드포인트

실시간 거래 통계 및 대시보드 데이터를 제공합니다.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
import sys
import os

# FDS 모델 정의 (로컬 복사)
from enum import Enum
from sqlalchemy import Column, String, Float, DateTime, JSON, Uuid, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class EvaluationStatus(str, Enum):
    APPROVED = "approved"
    DECLINED = "declined"
    REVIEW_REQUIRED = "review_required"

class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

# 실제 모델은 별도 테이블에서 조회
class Transaction:
    __tablename__ = "transactions"

class ReviewQueue:
    __tablename__ = "review_queue"

from src.database import get_db

router = APIRouter(prefix="/v1/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    time_range: str = Query(
        "24h",
        description="시간 범위 (1h, 24h, 7d, 30d)",
        regex="^(1h|24h|7d|30d)$",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    실시간 거래 통계 조회

    보안팀 대시보드에 표시할 주요 지표를 반환합니다.

    Args:
        time_range: 통계 기간 (1h, 24h, 7d, 30d)
        db: 데이터베이스 세션

    Returns:
        dict: 대시보드 통계 데이터
            - transaction_summary: 거래 요약 (총 거래 수, 승인/차단/검토 수)
            - risk_distribution: 위험도별 분포 (low/medium/high 비율)
            - review_queue_summary: 검토 큐 요약 (대기/진행중/완료 수)
            - avg_evaluation_time_ms: 평균 FDS 평가 시간 (ms)
            - recent_alerts: 최근 고위험 거래 알림
    """

    # 시간 범위에 따른 시작 시간 계산
    time_ranges = {
        "1h": timedelta(hours=1),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    start_time = datetime.utcnow() - time_ranges[time_range]

    # 1. 거래 요약 통계
    transaction_summary_query = select(
        func.count(Transaction.id).label("total"),
        func.count(Transaction.id)
        .filter(Transaction.evaluation_status == EvaluationStatus.APPROVED)
        .label("approved"),
        func.count(Transaction.id)
        .filter(Transaction.evaluation_status == EvaluationStatus.BLOCKED)
        .label("blocked"),
        func.count(Transaction.id)
        .filter(Transaction.evaluation_status == EvaluationStatus.MANUAL_REVIEW)
        .label("manual_review"),
    ).where(Transaction.created_at >= start_time)

    transaction_summary_result = await db.execute(transaction_summary_query)
    transaction_summary_row = transaction_summary_result.fetchone()

    transaction_summary = {
        "total": transaction_summary_row.total or 0,
        "approved": transaction_summary_row.approved or 0,
        "blocked": transaction_summary_row.blocked or 0,
        "manual_review": transaction_summary_row.manual_review or 0,
    }

    # 2. 위험도별 분포
    risk_distribution_query = (
        select(
            Transaction.risk_level,
            func.count(Transaction.id).label("count"),
        )
        .where(Transaction.created_at >= start_time)
        .group_by(Transaction.risk_level)
    )

    risk_distribution_result = await db.execute(risk_distribution_query)
    risk_distribution_rows = risk_distribution_result.fetchall()

    risk_distribution = {
        "low": 0,
        "medium": 0,
        "high": 0,
    }
    for row in risk_distribution_rows:
        risk_distribution[row.risk_level.value] = row.count

    # 3. 검토 큐 요약
    review_queue_summary_query = select(
        func.count(ReviewQueue.id).label("total"),
        func.count(ReviewQueue.id)
        .filter(ReviewQueue.status == ReviewStatus.PENDING)
        .label("pending"),
        func.count(ReviewQueue.id)
        .filter(ReviewQueue.status == ReviewStatus.IN_REVIEW)
        .label("in_review"),
        func.count(ReviewQueue.id)
        .filter(ReviewQueue.status == ReviewStatus.COMPLETED)
        .label("completed"),
    ).where(ReviewQueue.added_at >= start_time)

    review_queue_summary_result = await db.execute(review_queue_summary_query)
    review_queue_summary_row = review_queue_summary_result.fetchone()

    review_queue_summary = {
        "total": review_queue_summary_row.total or 0,
        "pending": review_queue_summary_row.pending or 0,
        "in_review": review_queue_summary_row.in_review or 0,
        "completed": review_queue_summary_row.completed or 0,
    }

    # 4. 평균 FDS 평가 시간
    avg_evaluation_time_query = select(
        func.avg(Transaction.evaluation_time_ms).label("avg_time")
    ).where(Transaction.created_at >= start_time)

    avg_evaluation_time_result = await db.execute(avg_evaluation_time_query)
    avg_evaluation_time_row = avg_evaluation_time_result.fetchone()
    avg_evaluation_time_ms = int(avg_evaluation_time_row.avg_time or 0)

    # 5. 최근 고위험 거래 알림 (최근 10건)
    recent_alerts_query = (
        select(Transaction)
        .where(
            and_(
                Transaction.risk_level == RiskLevel.HIGH,
                Transaction.created_at >= start_time,
            )
        )
        .order_by(Transaction.created_at.desc())
        .limit(10)
    )

    recent_alerts_result = await db.execute(recent_alerts_query)
    recent_alerts_rows = recent_alerts_result.scalars().all()

    recent_alerts = [
        {
            "transaction_id": str(alert.id),
            "user_id": str(alert.user_id),
            "order_id": str(alert.order_id),
            "amount": float(alert.amount),
            "risk_score": alert.risk_score,
            "ip_address": alert.ip_address,
            "created_at": alert.created_at.isoformat(),
            "evaluation_status": alert.evaluation_status.value,
        }
        for alert in recent_alerts_rows
    ]

    # 응답 반환
    return {
        "time_range": time_range,
        "generated_at": datetime.utcnow().isoformat(),
        "transaction_summary": transaction_summary,
        "risk_distribution": risk_distribution,
        "review_queue_summary": review_queue_summary,
        "avg_evaluation_time_ms": avg_evaluation_time_ms,
        "performance_status": ("good" if avg_evaluation_time_ms <= 100 else "degraded"),
        "recent_alerts": recent_alerts,
    }
