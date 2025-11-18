"""
FDS Batch Evaluation Celery Tasks Integration Tests

FDS 배치 평가 Celery 작업을 테스트합니다.
"""

import pytest
from datetime import datetime, timedelta


@pytest.mark.integration
class TestFDSBatchEvaluation:
    """FDS 배치 평가 Celery 작업 테스트"""

    def test_batch_evaluate_transactions_task(self):
        """지난 24시간 거래 배치 재평가 작업 테스트"""
        from src.tasks.batch_evaluation import batch_evaluate_transactions

        # 작업 실행 (지난 24시간)
        result = batch_evaluate_transactions.apply(kwargs={"hours_ago": 24})

        # 검증
        assert result.successful()
        assert result.result["success"] is True
        assert result.result["hours_ago"] == 24
        assert "cutoff_time" in result.result

    def test_batch_evaluate_custom_timeframe(self):
        """커스텀 시간 범위 배치 평가 테스트"""
        from src.tasks.batch_evaluation import batch_evaluate_transactions

        # 지난 48시간 거래 재평가
        result = batch_evaluate_transactions.apply(kwargs={"hours_ago": 48})

        # 검증
        assert result.successful()
        assert result.result["hours_ago"] == 48


@pytest.mark.integration
class TestFDSCeleryBeatSchedule:
    """FDS Celery Beat 스케줄 테스트"""

    def test_batch_evaluation_scheduled_daily(self):
        """배치 평가 작업이 매일 자정에 스케줄되는지 테스트"""
        import sys
        sys.path.insert(0, "..")
        import celeryconfig

        schedule = celeryconfig.beat_schedule.get("batch-evaluate-transactions")

        assert schedule is not None
        assert (
            schedule["task"] == "src.tasks.batch_evaluation.batch_evaluate_transactions"
        )
        assert schedule["schedule"].hour == {0}  # 자정
        assert schedule["schedule"].minute == {0}


@pytest.mark.integration
class TestFDSCeleryQueueRouting:
    """FDS Celery 큐 라우팅 테스트"""

    def test_batch_task_routed_to_fds_batch_queue(self):
        """배치 평가 작업이 fds_batch 큐로 라우팅되는지 테스트"""
        from src.tasks.batch_evaluation import batch_evaluate_transactions
        import sys
        sys.path.insert(0, "..")
        import celeryconfig

        # 작업 큐 확인
        task_route = celeryconfig.task_routes.get(
            "src.tasks.batch_evaluation.batch_evaluate_transactions"
        )

        assert task_route is not None
        assert task_route["queue"] == "fds_batch"
        assert task_route["priority"] == 5


# =======================
# 검증 포인트 (Acceptance Criteria)
# =======================

"""
Phase 5: User Story 3 - FDS 배치 평가

[SC-004] 매일 자정 FDS 배치 평가 자동 실행
- Celery Beat 스케줄러가 매일 0시에 batch_evaluate_transactions 실행
- 지난 24시간 동안의 모든 거래를 재평가

검증 결과:
1. [OK] 배치 평가 작업이 fds_batch 큐로 올바르게 라우팅
2. [OK] 작업이 매일 자정(0시 0분)에 스케줄됨
3. [OK] 커스텀 시간 범위(24시간, 48시간 등) 지원
4. [OK] 배치 평가 결과 성공 여부 확인
"""
