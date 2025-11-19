"""
T108-T109: 룰 관리 및 A/B 테스트 통합 검증

이 테스트는 다음 시나리오를 검증합니다:
T108: 새 룰 추가 및 즉시 적용 검증
T109: A/B 테스트 실행 및 결과 집계 검증

테스트 접근법:
- 실제 서비스 API를 사용하지 않고 내부 로직을 단위 테스트
- RuleEngine의 동적 룰 로딩 메커니즘 검증
- A/B 테스트 서비스의 그룹 할당 및 결과 집계 검증
"""

import pytest
import uuid
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.engines.rule_engine import RuleEngine, TransactionContext, RuleEvaluationResult
from src.models.detection_rule import DetectionRule, RuleType
from src.models.ab_test import ABTest, ABTestStatus
from src.services.ab_test_service import ABTestService


@pytest.mark.asyncio
class TestT108RuleDynamicLoading:
    """
    T108: 새 룰 추가 및 즉시 적용 검증

    보안팀이 새로운 탐지 룰을 추가하면, 코드 배포 없이
    FDS 평가 엔진이 즉시 해당 룰을 로드하고 적용하는지 검증합니다.
    """

    async def test_rule_cache_invalidation_and_reload(self):
        """
        Step 1: 룰 캐시 무효화 및 재로드 검증

        시나리오:
        1. 초기 룰 세트 로드
        2. 새 룰 추가 (mock DB에)
        3. 캐시 무효화 (invalidate_cache)
        4. 재로드 시 새 룰이 포함되는지 확인
        """
        # Mock 데이터베이스 및 Redis
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        # 초기 룰 세트 (빈 상태)
        initial_rules = []

        # Mock DB execute 결과 설정
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = initial_rules
        mock_db.execute.return_value = mock_result

        # RuleEngine 초기화
        rule_engine = RuleEngine(mock_db, mock_redis)

        # Step 1: 초기 룰 로드
        loaded_rules_1 = await rule_engine.load_active_rules()
        assert len(loaded_rules_1) == 0
        print("Step 1 (T108): 초기 룰 로드 - 0개")

        # Step 2: 새 룰 추가 (mock)
        new_rule = DetectionRule(
            id=uuid.uuid4(),
            name="고액 거래 탐지 (200만원 이상)",
            description="200만원 이상의 고액 거래를 탐지합니다",
            rule_type=RuleType.THRESHOLD,
            condition={"field": "amount", "operator": "gte", "value": 2000000},
            risk_score_weight=50,
            is_active=True,
            priority=100,
            created_by="admin",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # DB에 새 룰 추가 (mock)
        updated_rules = [new_rule]
        mock_result_2 = MagicMock()
        mock_result_2.scalars.return_value.all.return_value = updated_rules
        mock_db.execute.return_value = mock_result_2

        print(f"Step 2 (T108): 새 룰 추가 완료 - {new_rule.name}")

        # Step 3: 캐시 무효화
        rule_engine.invalidate_cache()
        assert rule_engine._rule_cache == []
        assert rule_engine._cache_timestamp is None
        print("Step 3 (T108): 캐시 무효화 완료")

        # Step 4: 재로드 (새 룰 포함)
        loaded_rules_2 = await rule_engine.load_active_rules(force_reload=True)
        assert len(loaded_rules_2) == 1
        assert loaded_rules_2[0].id == new_rule.id
        assert loaded_rules_2[0].name == new_rule.name
        print(f"Step 4 (T108): 재로드 완료 - {len(loaded_rules_2)}개 룰 로드")

        # Step 5: 룰 세부 정보 확인
        loaded_rule = loaded_rules_2[0]
        assert loaded_rule.rule_type == RuleType.THRESHOLD
        assert loaded_rule.is_active is True
        assert loaded_rule.condition["value"] == 2000000
        print("Step 5 (T108): 새 룰 검증 완료")

    async def test_rule_priority_ordering(self):
        """
        Step 2: 룰 우선순위 순서 검증

        시나리오:
        1. 여러 우선순위의 룰 생성
        2. RuleEngine이 우선순위 순으로 정렬하는지 확인
        """
        # Mock DB 및 Redis
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        # 여러 우선순위의 룰 생성
        rules = [
            DetectionRule(
                id=uuid.uuid4(),
                name="낮은 우선순위 룰",
                rule_type=RuleType.THRESHOLD,
                condition={"field": "amount", "operator": "gte", "value": 1000000},
                risk_score_weight=30,
                is_active=True,
                priority=10,
                created_by="admin",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            DetectionRule(
                id=uuid.uuid4(),
                name="높은 우선순위 룰",
                rule_type=RuleType.BLACKLIST,
                condition={"type": "ip", "values": ["1.2.3.4"]},
                risk_score_weight=90,
                is_active=True,
                priority=100,
                created_by="admin",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            DetectionRule(
                id=uuid.uuid4(),
                name="중간 우선순위 룰",
                rule_type=RuleType.VELOCITY,
                condition={
                    "window_seconds": 300,
                    "max_transactions": 3,
                    "scope": "ip_address",
                },
                risk_score_weight=50,
                is_active=True,
                priority=50,
                created_by="admin",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]

        # Mock DB 결과 (이미 우선순위 순으로 정렬됨 - SQL ORDER BY 시뮬레이션)
        sorted_rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sorted_rules
        mock_db.execute.return_value = mock_result

        # RuleEngine 초기화 및 룰 로드
        rule_engine = RuleEngine(mock_db, mock_redis)
        loaded_rules = await rule_engine.load_active_rules()

        # 우선순위 순서 확인
        priorities = [r.priority for r in loaded_rules]
        expected_order = [100, 50, 10]

        assert priorities == expected_order, f"우선순위 정렬 오류: {priorities}"
        print(f"Step 1 (T108): 룰 우선순위 검증 - {priorities} (예상: {expected_order})")

    async def test_disabled_rule_not_loaded(self):
        """
        Step 3: 비활성화된 룰이 로드되지 않는지 검증

        시나리오:
        1. 활성/비활성 룰 혼합 생성
        2. RuleEngine이 활성 룰만 로드하는지 확인
        """
        # Mock DB 및 Redis
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        # 활성 룰
        active_rule = DetectionRule(
            id=uuid.uuid4(),
            name="활성 룰",
            rule_type=RuleType.THRESHOLD,
            condition={"field": "amount", "operator": "gte", "value": 1000000},
            risk_score_weight=50,
            is_active=True,
            priority=100,
            created_by="admin",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 비활성 룰 (로드되지 않아야 함)
        inactive_rule = DetectionRule(
            id=uuid.uuid4(),
            name="비활성 룰",
            rule_type=RuleType.VELOCITY,
            condition={
                "window_seconds": 300,
                "max_transactions": 3,
                "scope": "user_id",
            },
            risk_score_weight=60,
            is_active=False,  # 비활성화
            priority=50,
            created_by="admin",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Mock DB 결과 (활성 룰만 반환 - SQL WHERE 시뮬레이션)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [active_rule]
        mock_db.execute.return_value = mock_result

        # RuleEngine 초기화 및 룰 로드
        rule_engine = RuleEngine(mock_db, mock_redis)
        loaded_rules = await rule_engine.load_active_rules()

        # 비활성 룰이 로드되지 않았는지 확인
        assert len(loaded_rules) == 1
        assert loaded_rules[0].id == active_rule.id
        assert all(r.id != inactive_rule.id for r in loaded_rules)

        print("Step 1 (T108): 비활성 룰 제외 검증 완료 - 활성 룰만 1개 로드")


@pytest.mark.asyncio
class TestT109ABTestIntegration:
    """
    T109: A/B 테스트 실행 및 결과 집계 검증

    보안팀이 A/B 테스트를 설정하면, FDS 평가 엔진이 자동으로 거래를
    A/B 그룹으로 분할하고 결과를 집계하는지 검증합니다.
    """

    async def test_ab_test_group_assignment_consistency(self):
        """
        Step 1: A/B 테스트 그룹 할당 일관성 검증

        시나리오:
        1. A/B 테스트 생성 (50% 트래픽 분할)
        2. 동일한 transaction_id에 대해 여러 번 그룹 할당
        3. 항상 동일한 그룹이 할당되는지 확인 (일관성)
        """
        # Mock DB
        mock_db = AsyncMock()

        # A/B 테스트 생성 (50% 트래픽 분할)
        test = ABTest(
            id=uuid.uuid4(),
            name="룰 A/B 테스트",
            description="새로운 고액 거래 탐지 룰 테스트",
            test_type="rule",
            status=ABTestStatus.RUNNING,
            traffic_split_percentage=50,  # 50% A, 50% B
            group_a_config={"rule_id": str(uuid.uuid4())},
            group_b_config={"rule_id": str(uuid.uuid4())},
            start_time=datetime.utcnow(),
        )

        # ABTestService 초기화
        ab_test_service = ABTestService(mock_db)

        # 동일한 transaction_id에 대해 그룹 할당 (10회 반복)
        transaction_id = uuid.uuid4()
        groups = []

        for i in range(10):
            group = ab_test_service.assign_group(test, transaction_id)
            groups.append(group)

        # 모든 할당 결과가 동일한지 확인
        assert len(set(groups)) == 1, f"그룹 할당 불일치: {groups}"
        print(
            f"Step 1 (T109): 그룹 할당 일관성 검증 - transaction {transaction_id} → 그룹 {groups[0]} (10회 반복 동일)"
        )

    async def test_ab_test_traffic_split_distribution(self):
        """
        Step 2: A/B 테스트 트래픽 분할 비율 검증

        시나리오:
        1. A/B 테스트 생성 (50% 트래픽 분할)
        2. 1000개의 거래 ID 생성 및 그룹 할당
        3. A/B 그룹 비율이 대략 50:50인지 확인
        """
        # Mock DB
        mock_db = AsyncMock()

        # A/B 테스트 생성 (50% B 그룹)
        test = ABTest(
            id=uuid.uuid4(),
            name="50-50 분할 테스트",
            test_type="rule",
            status=ABTestStatus.RUNNING,
            traffic_split_percentage=50,
            group_a_config={"rule_id": str(uuid.uuid4())},
            group_b_config={"rule_id": str(uuid.uuid4())},
            start_time=datetime.utcnow(),
        )

        # ABTestService 초기화
        ab_test_service = ABTestService(mock_db)

        # 1000개 거래 ID 생성 및 그룹 할당
        num_transactions = 1000
        group_counts = {"A": 0, "B": 0}

        for _ in range(num_transactions):
            transaction_id = uuid.uuid4()
            group = ab_test_service.assign_group(test, transaction_id)
            group_counts[group] += 1

        # 비율 계산
        ratio_a = group_counts["A"] / num_transactions * 100
        ratio_b = group_counts["B"] / num_transactions * 100

        print(f"Step 1 (T109): 트래픽 분할 비율 - A: {ratio_a:.1f}%, B: {ratio_b:.1f}%")

        # 비율이 대략 50:50인지 확인 (±5% 허용)
        assert 45 <= ratio_a <= 55, f"A 그룹 비율 벗어남: {ratio_a}%"
        assert 45 <= ratio_b <= 55, f"B 그룹 비율 벗어남: {ratio_b}%"

        print("Step 2 (T109): 트래픽 분할 비율 검증 완료 (±5% 이내)")

    async def test_ab_test_result_aggregation(self):
        """
        Step 3: A/B 테스트 결과 집계 검증

        시나리오:
        1. A/B 테스트 생성
        2. 그룹별 평가 결과 기록 (TP, FP, FN)
        3. 집계 값이 정확히 업데이트되는지 확인
        """
        # Mock DB
        mock_db = AsyncMock()

        # A/B 테스트 생성 (명시적으로 기본값 설정)
        test = ABTest(
            id=uuid.uuid4(),
            name="결과 집계 테스트",
            test_type="rule",
            status=ABTestStatus.RUNNING,
            traffic_split_percentage=50,
            group_a_config={"rule_id": str(uuid.uuid4())},
            group_b_config={"rule_id": str(uuid.uuid4())},
            start_time=datetime.utcnow(),
            # 명시적 기본값 설정
            group_a_total_transactions=0,
            group_a_true_positives=0,
            group_a_false_positives=0,
            group_a_false_negatives=0,
            group_a_avg_evaluation_time_ms=0.0,
            group_b_total_transactions=0,
            group_b_true_positives=0,
            group_b_false_positives=0,
            group_b_false_negatives=0,
            group_b_avg_evaluation_time_ms=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # ABTestService 초기화
        ab_test_service = ABTestService(mock_db)

        # 초기 상태 확인
        assert test.group_a_total_transactions == 0
        assert test.group_b_total_transactions == 0
        print("Step 1 (T109): 초기 상태 - A/B 그룹 거래 수 0")

        # 그룹 A에 결과 기록
        await ab_test_service.record_test_result(
            test=test,
            group="A",
            is_true_positive=True,
            is_false_positive=False,
            is_false_negative=False,
            evaluation_time_ms=85.5,
        )

        assert test.group_a_total_transactions == 1
        assert test.group_a_true_positives == 1
        assert test.group_a_false_positives == 0
        assert test.group_a_avg_evaluation_time_ms == 85.5
        print("Step 2 (T109): 그룹 A 결과 기록 완료 - TP=1")

        # 그룹 B에 결과 기록
        await ab_test_service.record_test_result(
            test=test,
            group="B",
            is_true_positive=False,
            is_false_positive=True,
            is_false_negative=False,
            evaluation_time_ms=120.0,
        )

        assert test.group_b_total_transactions == 1
        assert test.group_b_true_positives == 0
        assert test.group_b_false_positives == 1
        assert test.group_b_avg_evaluation_time_ms == 120.0
        print("Step 3 (T109): 그룹 B 결과 기록 완료 - FP=1")

        # 그룹 A에 추가 결과 기록 (평균 시간 업데이트 확인)
        await ab_test_service.record_test_result(
            test=test,
            group="A",
            is_true_positive=True,
            is_false_positive=False,
            is_false_negative=False,
            evaluation_time_ms=94.5,
        )

        assert test.group_a_total_transactions == 2
        assert test.group_a_true_positives == 2
        expected_avg_time = (85.5 + 94.5) / 2
        assert abs(test.group_a_avg_evaluation_time_ms - expected_avg_time) < 0.01
        print(
            f"Step 4 (T109): 그룹 A 평균 시간 업데이트 - {test.group_a_avg_evaluation_time_ms}ms"
        )

    async def test_ab_test_get_active_test(self):
        """
        Step 4: 진행 중인 A/B 테스트 조회 검증

        시나리오:
        1. 여러 상태의 A/B 테스트 생성
        2. get_active_test()가 RUNNING 상태만 반환하는지 확인
        """
        # Mock DB
        mock_db = AsyncMock()

        # 진행 중인 테스트
        running_test = ABTest(
            id=uuid.uuid4(),
            name="진행 중인 테스트",
            test_type="rule",
            status=ABTestStatus.RUNNING,
            traffic_split_percentage=50,
            group_a_config={},
            group_b_config={},
            start_time=datetime.utcnow(),
        )

        # 완료된 테스트 (반환되지 않아야 함)
        completed_test = ABTest(
            id=uuid.uuid4(),
            name="완료된 테스트",
            test_type="rule",
            status=ABTestStatus.COMPLETED,
            traffic_split_percentage=50,
            group_a_config={},
            group_b_config={},
            start_time=datetime.utcnow(),
        )

        # Mock DB execute 결과 (RUNNING 테스트만 반환)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = running_test
        mock_db.execute.return_value = mock_result

        # ABTestService 초기화
        ab_test_service = ABTestService(mock_db)

        # 진행 중인 테스트 조회
        active_test = await ab_test_service.get_active_test(test_type="rule")

        assert active_test is not None
        assert active_test.id == running_test.id
        assert active_test.status == ABTestStatus.RUNNING
        print(f"Step 1 (T109): 진행 중인 테스트 조회 완료 - {active_test.name}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
