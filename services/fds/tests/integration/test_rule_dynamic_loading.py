"""
T108: 새 룰 추가 및 즉시 적용 검증

보안팀이 관리자 대시보드에서 새로운 탐지 룰을 추가하고,
코드 배포 없이 즉시 FDS 평가에 적용되는지 검증합니다.

테스트 시나리오:
1. 초기 상태: 기본 룰만 존재
2. 보안팀이 새로운 고액 거래 탐지 룰 추가 (금액 임계값 200만원)
3. 룰 캐시 무효화 (force_reload 또는 캐시 TTL 대기)
4. 250만원 거래 평가 → 새 룰이 즉시 트리거되는지 확인
5. 룰 비활성화 후 다시 평가 → 룰이 트리거되지 않는지 확인
"""

import pytest
import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.detection_rule import DetectionRule, RuleType
from src.models.risk_factor import FactorSeverity
from src.engines.rule_engine import RuleEngine, TransactionContext


@pytest.mark.asyncio
class TestRuleDynamicLoading:
    """룰 동적 로딩 및 즉시 적용 테스트"""

    async def test_add_new_rule_and_immediately_apply(
        self, db_session: AsyncSession, mock_redis
    ):
        """
        Step 1: 새 룰 추가 및 즉시 적용 검증

        시나리오:
        - 보안팀이 새로운 고액 거래 탐지 룰 추가 (200만원 이상)
        - 250만원 거래 평가
        - 새 룰이 즉시 트리거되는지 확인
        """
        # 1. RuleEngine 초기화
        rule_engine = RuleEngine(db_session, mock_redis)

        # 2. 초기 상태: 활성화된 룰 로드 (빈 상태)
        initial_rules = await rule_engine.load_active_rules()
        print(f"Step 1: 초기 활성 룰 개수: {len(initial_rules)}")

        # 3. 거래 컨텍스트 생성 (250만원 거래)
        transaction_id = uuid.uuid4()
        user_id = uuid.uuid4()
        order_id = uuid.uuid4()

        context = TransactionContext(
            transaction_id=transaction_id,
            user_id=user_id,
            order_id=order_id,
            amount=Decimal("2500000"),  # 250만원
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0)",
            device_type="desktop",
            geolocation={"latitude": 37.5665, "longitude": 126.9780},  # 서울
            payment_info={"card_bin": "123456"},
            session_context={},
            user_profile={},
        )

        # 4. 초기 평가 (새 룰 없음)
        initial_results = await rule_engine.evaluate_transaction(context)
        print(f"Step 2: 초기 평가 결과 - 트리거된 룰: {len(initial_results)}개")

        # 5. 보안팀이 새로운 룰 추가
        new_rule = DetectionRule(
            id=uuid.uuid4(),
            name="고액 거래 탐지 (200만원 이상)",
            description="200만원 이상의 고액 거래를 탐지합니다",
            rule_type=RuleType.THRESHOLD,
            condition={
                "field": "amount",
                "operator": "gte",
                "value": 2000000,  # 200만원 임계값
            },
            risk_score_weight=50,
            is_active=True,
            priority=100,
            created_by="admin",
        )

        db_session.add(new_rule)
        await db_session.commit()
        await db_session.refresh(new_rule)

        print(f"Step 3: 새 룰 추가 완료 - ID: {new_rule.id}, 이름: {new_rule.name}")

        # 6. 룰 캐시 강제 재로드
        rule_engine.invalidate_cache()
        updated_rules = await rule_engine.load_active_rules(force_reload=True)
        print(f"Step 4: 재로드 후 활성 룰 개수: {len(updated_rules)}개")

        assert len(updated_rules) == len(initial_rules) + 1, "새 룰이 로드되지 않음"

        # 7. 동일한 거래를 다시 평가 (새 룰이 트리거되어야 함)
        updated_results = await rule_engine.evaluate_transaction(context)
        print(f"Step 5: 재평가 결과 - 트리거된 룰: {len(updated_results)}개")

        # 8. 새 룰이 트리거되었는지 확인
        triggered_rule_names = [result.rule_name for result in updated_results]
        print(f"Step 6: 트리거된 룰 목록: {triggered_rule_names}")

        assert any(
            result.rule_id == new_rule.id for result in updated_results
        ), "새 룰이 트리거되지 않음"

        # 9. 트리거된 룰의 세부 정보 확인
        triggered_rule_result = next(
            result for result in updated_results if result.rule_id == new_rule.id
        )

        assert triggered_rule_result.triggered is True
        assert triggered_rule_result.risk_score == 50
        assert "200만원" in triggered_rule_result.description or "2000000" in triggered_rule_result.description
        assert triggered_rule_result.metadata["actual_value"] == 2500000.0
        assert triggered_rule_result.metadata["threshold_value"] == 2000000

        print("Step 7: 새 룰이 성공적으로 트리거되었습니다!")

        # 10. 룰 트리거 횟수 확인
        await db_session.refresh(new_rule)
        assert new_rule.trigger_count == 1, f"룰 트리거 횟수가 예상과 다름: {new_rule.trigger_count}"
        print(f"Step 8: 룰 트리거 횟수 업데이트 확인: {new_rule.trigger_count}회")

    async def test_disable_rule_and_verify_not_triggered(
        self, db_session: AsyncSession, mock_redis
    ):
        """
        Step 2: 룰 비활성화 후 트리거되지 않는지 검증

        시나리오:
        - 기존 활성 룰을 비활성화
        - 조건을 만족하는 거래 평가
        - 비활성화된 룰이 트리거되지 않는지 확인
        """
        # 1. 활성 룰 생성
        active_rule = DetectionRule(
            id=uuid.uuid4(),
            name="고액 거래 탐지 (300만원 이상)",
            description="300만원 이상의 고액 거래를 탐지합니다",
            rule_type=RuleType.THRESHOLD,
            condition={
                "field": "amount",
                "operator": "gte",
                "value": 3000000,  # 300만원
            },
            risk_score_weight=60,
            is_active=True,  # 초기에는 활성화
            priority=100,
            created_by="admin",
        )

        db_session.add(active_rule)
        await db_session.commit()
        await db_session.refresh(active_rule)

        print(f"Step 1: 활성 룰 생성 - ID: {active_rule.id}")

        # 2. RuleEngine 초기화 및 룰 로드
        rule_engine = RuleEngine(db_session, mock_redis)
        rules = await rule_engine.load_active_rules(force_reload=True)

        assert any(r.id == active_rule.id for r in rules), "활성 룰이 로드되지 않음"
        print(f"Step 2: 활성 룰 로드 확인 - 총 {len(rules)}개")

        # 3. 거래 컨텍스트 생성 (350만원 거래 - 조건 만족)
        transaction_id = uuid.uuid4()
        context = TransactionContext(
            transaction_id=transaction_id,
            user_id=uuid.uuid4(),
            order_id=uuid.uuid4(),
            amount=Decimal("3500000"),  # 350만원
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            device_type="desktop",
        )

        # 4. 평가 수행 (룰이 트리거되어야 함)
        results_before = await rule_engine.evaluate_transaction(context)
        print(f"Step 3: 룰 활성화 상태 평가 - 트리거된 룰: {len(results_before)}개")

        assert any(
            result.rule_id == active_rule.id for result in results_before
        ), "활성 룰이 트리거되지 않음"

        # 5. 보안팀이 룰을 비활성화
        active_rule.is_active = False
        db_session.add(active_rule)
        await db_session.commit()
        await db_session.refresh(active_rule)

        print(f"Step 4: 룰 비활성화 완료 - is_active: {active_rule.is_active}")

        # 6. 룰 캐시 무효화 및 재로드
        rule_engine.invalidate_cache()
        updated_rules = await rule_engine.load_active_rules(force_reload=True)

        assert not any(
            r.id == active_rule.id for r in updated_rules
        ), "비활성화된 룰이 여전히 로드됨"

        print(f"Step 5: 재로드 후 활성 룰 개수: {len(updated_rules)}개 (비활성화된 룰 제외)")

        # 7. 동일한 거래를 다시 평가 (룰이 트리거되지 않아야 함)
        results_after = await rule_engine.evaluate_transaction(context)
        print(f"Step 6: 룰 비활성화 상태 평가 - 트리거된 룰: {len(results_after)}개")

        assert not any(
            result.rule_id == active_rule.id for result in results_after
        ), "비활성화된 룰이 트리거됨"

        print("Step 7: 비활성화된 룰이 트리거되지 않음 (검증 성공)")

        # 8. 룰 트리거 횟수가 증가하지 않았는지 확인
        await db_session.refresh(active_rule)
        assert active_rule.trigger_count == 1, "비활성화 후 트리거 횟수가 증가함"
        print(f"Step 8: 트리거 횟수 확인 - 비활성화 후에도 1회 유지")

    async def test_rule_priority_ordering(
        self, db_session: AsyncSession, mock_redis
    ):
        """
        Step 3: 룰 우선순위 정렬 검증

        시나리오:
        - 여러 우선순위의 룰 생성
        - 룰 엔진이 우선순위 순으로 로드하는지 확인
        """
        # 1. 여러 우선순위의 룰 생성
        rules_data = [
            {"name": "낮은 우선순위 룰", "priority": 10},
            {"name": "높은 우선순위 룰", "priority": 100},
            {"name": "중간 우선순위 룰", "priority": 50},
        ]

        created_rules = []
        for rule_data in rules_data:
            rule = DetectionRule(
                id=uuid.uuid4(),
                name=rule_data["name"],
                description=f"{rule_data['name']} - 우선순위 {rule_data['priority']}",
                rule_type=RuleType.THRESHOLD,
                condition={"field": "amount", "operator": "gte", "value": 1000000},
                risk_score_weight=30,
                is_active=True,
                priority=rule_data["priority"],
                created_by="admin",
            )
            created_rules.append(rule)
            db_session.add(rule)

        await db_session.commit()
        print(f"Step 1: {len(created_rules)}개의 룰 생성 완료")

        # 2. RuleEngine에서 룰 로드
        rule_engine = RuleEngine(db_session, mock_redis)
        loaded_rules = await rule_engine.load_active_rules(force_reload=True)

        print(f"Step 2: 룰 로드 완료 - 총 {len(loaded_rules)}개")

        # 3. 우선순위 순으로 정렬되었는지 확인 (높은 우선순위 먼저)
        created_rule_ids = {r.id for r in created_rules}
        loaded_test_rules = [r for r in loaded_rules if r.id in created_rule_ids]

        assert len(loaded_test_rules) >= 3, "생성한 룰이 모두 로드되지 않음"

        # 4. 우선순위 순서 검증
        priorities = [r.priority for r in loaded_test_rules]
        expected_order = [100, 50, 10]  # 높은 우선순위 먼저

        # 실제 순서 확인
        actual_order = priorities[:3]
        print(f"Step 3: 룰 우선순위 순서 - 실제: {actual_order}, 예상: {expected_order}")

        assert actual_order == expected_order, f"우선순위 정렬 오류: {actual_order}"

        print("Step 4: 룰 우선순위 정렬 검증 완료")

    async def test_rule_cache_ttl(
        self, db_session: AsyncSession, mock_redis
    ):
        """
        Step 4: 룰 캐시 TTL (5분) 검증

        시나리오:
        - 룰 로드 후 캐시 사용
        - 캐시 TTL 내에서는 데이터베이스 재조회하지 않음
        - force_reload=True로 강제 재로드 가능
        """
        # 1. RuleEngine 초기화
        rule_engine = RuleEngine(db_session, mock_redis)

        # 2. 첫 번째 룰 로드 (데이터베이스 조회)
        first_load = await rule_engine.load_active_rules()
        first_cache_timestamp = rule_engine._cache_timestamp

        print(f"Step 1: 첫 번째 룰 로드 - {len(first_load)}개, 타임스탬프: {first_cache_timestamp}")

        # 3. 새로운 룰 추가
        new_rule = DetectionRule(
            id=uuid.uuid4(),
            name="캐시 테스트 룰",
            description="캐시 TTL 검증용 룰",
            rule_type=RuleType.THRESHOLD,
            condition={"field": "amount", "operator": "gte", "value": 500000},
            risk_score_weight=40,
            is_active=True,
            priority=90,
            created_by="admin",
        )

        db_session.add(new_rule)
        await db_session.commit()

        print(f"Step 2: 새 룰 추가 완료 - ID: {new_rule.id}")

        # 4. 캐시 TTL 내에서 재로드 (캐시 사용 - 새 룰이 없어야 함)
        second_load = await rule_engine.load_active_rules()
        second_cache_timestamp = rule_engine._cache_timestamp

        assert first_cache_timestamp == second_cache_timestamp, "캐시가 갱신됨 (예상: 캐시 사용)"
        assert len(second_load) == len(first_load), "캐시 사용 중 룰 개수가 변경됨"

        print(f"Step 3: 캐시 사용 확인 - 타임스탬프 동일, 룰 개수: {len(second_load)}")

        # 5. force_reload=True로 강제 재로드 (새 룰이 로드되어야 함)
        third_load = await rule_engine.load_active_rules(force_reload=True)
        third_cache_timestamp = rule_engine._cache_timestamp

        assert third_cache_timestamp != first_cache_timestamp, "캐시가 갱신되지 않음"
        assert len(third_load) == len(first_load) + 1, "force_reload 후 새 룰이 로드되지 않음"

        print(f"Step 4: force_reload 후 - 타임스탬프 갱신, 룰 개수: {len(third_load)}")

        # 6. 캐시 무효화 후 재로드
        rule_engine.invalidate_cache()
        fourth_load = await rule_engine.load_active_rules()

        assert len(fourth_load) == len(third_load), "캐시 무효화 후 룰 개수 불일치"
        print(f"Step 5: 캐시 무효화 후 재로드 - 룰 개수: {len(fourth_load)}")

        print("Step 6: 룰 캐시 TTL 검증 완료")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
