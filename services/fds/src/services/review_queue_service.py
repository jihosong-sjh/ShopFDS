"""
ReviewQueue 서비스

고위험 거래를 검토 큐에 자동 추가하고 관리하는 서비스
"""

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..models.review_queue import ReviewQueue, ReviewStatus, ReviewDecision
from ..models.transaction import Transaction, EvaluationStatus

logger = logging.getLogger(__name__)


class ReviewQueueService:
    """
    ReviewQueue 서비스

    고위험 거래를 검토 큐에 자동 추가하고,
    보안팀의 검토 프로세스를 지원합니다.
    """

    def __init__(self, db: AsyncSession):
        """
        서비스 초기화

        Args:
            db: 데이터베이스 세션
        """
        self.db = db

    async def add_to_review_queue(self, transaction_id: UUID) -> Optional[ReviewQueue]:
        """
        고위험 거래를 검토 큐에 자동 추가

        Args:
            transaction_id: 거래 ID

        Returns:
            Optional[ReviewQueue]: 생성된 ReviewQueue 엔트리 (이미 존재하면 None)

        Raises:
            ValueError: 거래가 존재하지 않는 경우
        """
        try:
            # 1. 거래 존재 확인
            result = await self.db.execute(
                select(Transaction).where(Transaction.id == transaction_id)
            )
            transaction = result.scalar_one_or_none()

            if transaction is None:
                raise ValueError(f"거래를 찾을 수 없습니다: {transaction_id}")

            # 2. 이미 검토 큐에 있는지 확인
            result = await self.db.execute(
                select(ReviewQueue).where(ReviewQueue.transaction_id == transaction_id)
            )
            existing_queue = result.scalar_one_or_none()

            if existing_queue:
                logger.info(
                    f"거래가 이미 검토 큐에 있습니다: transaction_id={transaction_id}, "
                    f"queue_id={existing_queue.id}"
                )
                return None

            # 3. 검토 큐에 추가
            review_queue = ReviewQueue(
                transaction_id=transaction_id,
                status=ReviewStatus.PENDING,
                added_at=datetime.utcnow(),
            )

            self.db.add(review_queue)
            await self.db.commit()
            await self.db.refresh(review_queue)

            # 4. 거래 상태 업데이트 (BLOCKED -> MANUAL_REVIEW)
            transaction.evaluation_status = EvaluationStatus.MANUAL_REVIEW
            await self.db.commit()

            logger.info(
                f"거래를 검토 큐에 추가했습니다: transaction_id={transaction_id}, "
                f"queue_id={review_queue.id}, risk_score={transaction.risk_score}"
            )

            return review_queue

        except IntegrityError as e:
            await self.db.rollback()
            logger.warning(
                f"검토 큐 추가 중 중복 에러: transaction_id={transaction_id}, error={str(e)}"
            )
            return None

        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"검토 큐 추가 중 에러: transaction_id={transaction_id}, error={str(e)}",
                exc_info=True,
            )
            raise

    async def assign_reviewer(self, queue_id: UUID, reviewer_id: UUID) -> ReviewQueue:
        """
        검토 담당자 할당

        Args:
            queue_id: 검토 큐 ID
            reviewer_id: 검토 담당자 사용자 ID

        Returns:
            ReviewQueue: 업데이트된 검토 큐 엔트리

        Raises:
            ValueError: 검토 큐가 존재하지 않는 경우
        """
        result = await self.db.execute(
            select(ReviewQueue).where(ReviewQueue.id == queue_id)
        )
        review_queue = result.scalar_one_or_none()

        if review_queue is None:
            raise ValueError(f"검토 큐를 찾을 수 없습니다: {queue_id}")

        # 담당자 할당 및 상태 변경
        review_queue.assign_to_reviewer(reviewer_id)
        await self.db.commit()
        await self.db.refresh(review_queue)

        logger.info(f"검토 담당자 할당: queue_id={queue_id}, reviewer_id={reviewer_id}")

        return review_queue

    async def complete_review(
        self,
        queue_id: UUID,
        decision: ReviewDecision,
        notes: Optional[str] = None,
    ) -> ReviewQueue:
        """
        검토 완료 처리

        Args:
            queue_id: 검토 큐 ID
            decision: 검토 결과 (approve/block/escalate)
            notes: 검토 메모

        Returns:
            ReviewQueue: 업데이트된 검토 큐 엔트리

        Raises:
            ValueError: 검토 큐가 존재하지 않는 경우
        """
        result = await self.db.execute(
            select(ReviewQueue).where(ReviewQueue.id == queue_id)
        )
        review_queue = result.scalar_one_or_none()

        if review_queue is None:
            raise ValueError(f"검토 큐를 찾을 수 없습니다: {queue_id}")

        # 검토 완료 처리
        review_queue.complete_review(decision, notes)
        await self.db.commit()
        await self.db.refresh(review_queue)

        logger.info(
            f"검토 완료: queue_id={queue_id}, decision={decision}, "
            f"review_time={review_queue.review_time_seconds}s"
        )

        return review_queue

    async def get_pending_reviews(
        self, limit: int = 50, offset: int = 0
    ) -> list[ReviewQueue]:
        """
        검토 대기 중인 항목 조회

        Args:
            limit: 조회할 최대 항목 수
            offset: 조회 시작 위치

        Returns:
            list[ReviewQueue]: 검토 대기 중인 항목 목록
        """
        result = await self.db.execute(
            select(ReviewQueue)
            .where(ReviewQueue.status == ReviewStatus.PENDING)
            .order_by(ReviewQueue.added_at.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(result.scalars().all())

    async def get_in_review(
        self, reviewer_id: Optional[UUID] = None, limit: int = 50, offset: int = 0
    ) -> list[ReviewQueue]:
        """
        검토 진행 중인 항목 조회

        Args:
            reviewer_id: 검토 담당자 ID (None이면 전체)
            limit: 조회할 최대 항목 수
            offset: 조회 시작 위치

        Returns:
            list[ReviewQueue]: 검토 진행 중인 항목 목록
        """
        query = select(ReviewQueue).where(ReviewQueue.status == ReviewStatus.IN_REVIEW)

        if reviewer_id:
            query = query.where(ReviewQueue.assigned_to == reviewer_id)

        query = query.order_by(ReviewQueue.added_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_review_by_transaction(
        self, transaction_id: UUID
    ) -> Optional[ReviewQueue]:
        """
        특정 거래의 검토 큐 엔트리 조회

        Args:
            transaction_id: 거래 ID

        Returns:
            Optional[ReviewQueue]: 검토 큐 엔트리 (없으면 None)
        """
        result = await self.db.execute(
            select(ReviewQueue).where(ReviewQueue.transaction_id == transaction_id)
        )
        return result.scalar_one_or_none()
