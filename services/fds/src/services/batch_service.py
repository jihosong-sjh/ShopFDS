"""
Batch Service for FDS

이 모듈은 FDS 배치 재평가 로직을 제공합니다.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


class BatchService:
    """FDS 배치 재평가 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def reevaluate_transactions(self, cutoff_time: datetime) -> Dict[str, Any]:
        """
        지난 기간의 거래를 재평가

        Args:
            cutoff_time: 재평가 시작 시간 (이 시간 이후의 거래만 재평가)

        Returns:
            Dict[str, Any]: 재평가 결과
        """
        try:
            logger.info(
                f"[BatchService] Starting transaction re-evaluation since {cutoff_time}"
            )

            # TODO: 실제 구현에서는 FDS evaluation history를 조회하여 재평가
            # 1. cutoff_time 이후의 모든 거래 조회
            # transactions = await self.db.execute(
            #     select(FDSEvaluationHistory)
            #     .where(FDSEvaluationHistory.evaluated_at >= cutoff_time)
            #     .order_by(FDSEvaluationHistory.evaluated_at)
            # )
            # transactions = transactions.scalars().all()

            # 2. 각 거래를 FDS 엔진으로 재평가
            # from src.engines.evaluation_engine import EvaluationEngine
            # evaluation_engine = EvaluationEngine()
            # for transaction in transactions:
            #     new_result = await evaluation_engine.evaluate(transaction)
            #     # 결과 비교 및 업데이트
            #     if new_result['risk_level'] != transaction.risk_level:
            #         logger.warning(
            #             f"Risk level changed for transaction {transaction.transaction_id}: "
            #             f"{transaction.risk_level} -> {new_result['risk_level']}"
            #         )
            #         # 재평가 결과 저장
            #         await self._save_reevaluation_result(transaction, new_result)

            # 플레이스홀더 결과
            evaluated_count = 0
            high_risk_count = 0
            false_positive_count = 0

            logger.info(f"[SUCCESS] Re-evaluated {evaluated_count} transactions")

            return {
                "success": True,
                "evaluated_count": evaluated_count,
                "high_risk_count": high_risk_count,
                "false_positive_count": false_positive_count,
                "cutoff_time": cutoff_time.isoformat(),
            }

        except Exception as exc:
            logger.error(f"[FAIL] Failed to re-evaluate transactions: {exc}")
            raise

    async def _save_reevaluation_result(
        self, original_transaction: Any, new_result: Dict[str, Any]
    ):
        """
        재평가 결과 저장

        Args:
            original_transaction: 원본 거래 객체
            new_result: 재평가 결과
        """
        # TODO: 재평가 결과를 데이터베이스에 저장
        # 1. FDSReevaluationHistory 테이블에 기록
        # 2. 위험도가 변경된 경우 알림 발송
        # 3. 통계 업데이트
        pass
