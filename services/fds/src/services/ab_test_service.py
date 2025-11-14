"""
A/B 테스트 서비스

FDS 평가 시 A/B 테스트 그룹 분할 및 결과 집계를 담당합니다.
"""

import hashlib
import logging
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.ab_test import ABTest, ABTestStatus

logger = logging.getLogger(__name__)


class ABTestService:
    """
    A/B 테스트 서비스

    거래를 A/B 그룹으로 분할하고 테스트 결과를 집계합니다.
    """

    def __init__(self, db: AsyncSession):
        """
        A/B 테스트 서비스 초기화

        Args:
            db: 데이터베이스 세션
        """
        self.db = db

    async def get_active_test(self, test_type: str = "rule") -> Optional[ABTest]:
        """
        현재 진행 중인 A/B 테스트를 조회합니다.

        Args:
            test_type: 테스트 유형 (rule, model, threshold, hybrid)

        Returns:
            Optional[ABTest]: 진행 중인 테스트, 없으면 None
        """
        try:
            # 진행 중인 테스트 조회 (status = RUNNING)
            query = (
                select(ABTest)
                .where(ABTest.status == ABTestStatus.RUNNING)
                .where(ABTest.test_type == test_type)
                .order_by(ABTest.start_time.desc())
                .limit(1)
            )

            result = await self.db.execute(query)
            test = result.scalar_one_or_none()

            if test:
                logger.debug(
                    f"진행 중인 A/B 테스트 발견: {test.name} (ID: {test.id}), "
                    f"split={test.traffic_split_percentage}%"
                )

            return test

        except Exception as e:
            logger.error(f"A/B 테스트 조회 실패: {e}", exc_info=True)
            return None

    def assign_group(
        self, test: ABTest, transaction_id: UUID
    ) -> str:
        """
        거래를 A/B 그룹 중 하나에 할당합니다.

        일관된 분할을 위해 transaction_id의 해시값을 사용합니다.
        동일한 거래 ID는 항상 동일한 그룹에 할당됩니다.

        Args:
            test: A/B 테스트
            transaction_id: 거래 ID

        Returns:
            str: 그룹 ('A' 또는 'B')
        """
        # transaction_id를 문자열로 변환 후 SHA-256 해시 생성
        hash_input = f"{test.id}:{transaction_id}".encode("utf-8")
        hash_value = hashlib.sha256(hash_input).hexdigest()

        # 해시값의 첫 8자를 정수로 변환 (0-4294967295)
        hash_int = int(hash_value[:8], 16)

        # 트래픽 분할 비율에 따라 그룹 할당
        # 예: traffic_split_percentage = 50 → 50% B, 50% A
        threshold = (test.traffic_split_percentage / 100) * 0xFFFFFFFF

        if hash_int < threshold:
            return "B"
        else:
            return "A"

    async def record_test_result(
        self,
        test: ABTest,
        group: str,
        is_true_positive: bool = False,
        is_false_positive: bool = False,
        is_false_negative: bool = False,
        evaluation_time_ms: Optional[float] = None,
    ) -> None:
        """
        A/B 테스트 결과를 기록합니다.

        Args:
            test: A/B 테스트
            group: 그룹 ('A' 또는 'B')
            is_true_positive: 정탐 여부
            is_false_positive: 오탐 여부
            is_false_negative: 미탐 여부
            evaluation_time_ms: 평가 소요 시간 (ms)
        """
        try:
            # 테스트 결과 집계 (ABTest 모델의 increment_transaction 메서드 사용)
            test.increment_transaction(
                group=group,
                is_true_positive=is_true_positive,
                is_false_positive=is_false_positive,
                is_false_negative=is_false_negative,
                evaluation_time_ms=evaluation_time_ms,
            )

            # 데이터베이스에 업데이트 (commit은 상위 레벨에서 수행)
            self.db.add(test)
            await self.db.flush()

            logger.debug(
                f"A/B 테스트 결과 기록: test={test.name}, group={group}, "
                f"TP={is_true_positive}, FP={is_false_positive}, FN={is_false_negative}, "
                f"time={evaluation_time_ms}ms"
            )

        except Exception as e:
            logger.error(f"A/B 테스트 결과 기록 실패: {e}", exc_info=True)
            # Fail-safe: 에러 발생 시에도 계속 진행 (A/B 테스트 실패가 FDS를 막으면 안됨)

    def get_group_config(self, test: ABTest, group: str) -> dict:
        """
        그룹의 설정을 가져옵니다.

        Args:
            test: A/B 테스트
            group: 그룹 ('A' 또는 'B')

        Returns:
            dict: 그룹 설정 (rule_id, model_id, 파라미터 등)
        """
        if group == "A":
            return test.group_a_config
        else:
            return test.group_b_config

    async def determine_fraud_label(
        self,
        transaction_id: UUID,
        risk_score: int,
        decision: str,
    ) -> Tuple[bool, bool, bool]:
        """
        거래의 실제 사기 여부를 판단하여 TP/FP/FN을 결정합니다.

        **주의**: 실제 프로덕션에서는 수동 검토 결과나 라벨링 데이터를 사용해야 합니다.
        현재는 간단한 휴리스틱으로 구현합니다.

        Args:
            transaction_id: 거래 ID
            risk_score: FDS 위험 점수
            decision: FDS 의사결정 (approve, additional_auth_required, blocked)

        Returns:
            Tuple[bool, bool, bool]: (is_true_positive, is_false_positive, is_false_negative)
                - is_true_positive: 실제 사기 거래를 정확히 탐지
                - is_false_positive: 정상 거래를 사기로 탐지 (오탐)
                - is_false_negative: 사기 거래를 탐지 못함 (미탐)
        """
        # TODO: Phase 6에서 실제 라벨링 데이터 사용
        # 현재는 간단한 휴리스틱 사용:
        # - 위험 점수 80 이상 → 사기로 간주 (실제로는 수동 검토 필요)
        # - 위험 점수 80 미만 → 정상으로 간주

        # 실제 사기 여부 (휴리스틱)
        is_actually_fraud = risk_score >= 80

        # TP/FP/FN 판단
        if decision in ["blocked", "additional_auth_required"]:
            # FDS가 사기로 탐지한 경우
            if is_actually_fraud:
                # 정탐 (True Positive)
                return (True, False, False)
            else:
                # 오탐 (False Positive)
                return (False, True, False)
        else:
            # FDS가 정상으로 판단한 경우
            if is_actually_fraud:
                # 미탐 (False Negative)
                return (False, False, True)
            else:
                # 정탐 (True Negative) - 하지만 TN은 별도로 추적하지 않음
                return (False, False, False)
