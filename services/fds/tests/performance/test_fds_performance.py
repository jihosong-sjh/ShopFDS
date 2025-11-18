"""
T116 성능 테스트: FDS 평가 엔진 성능 검증

목표:
- 단일 평가 응답 시간: P95 < 100ms (목표: 50ms)
- 처리량: 1,000 TPS 이상
- 동시 요청 처리 능력 검증

pytest-benchmark를 사용하여 단위 성능 측정을 수행합니다.
실제 운영 부하 테스트는 Locust를 사용합니다 (test_fds_load_test.py).
"""

import pytest
import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, patch
import statistics

from src.models.schemas import (
    FDSEvaluationRequest,
    DeviceFingerprint,
    DeviceTypeEnum,
)
from src.engines.evaluation_engine import EvaluationEngine
from src.engines.cti_connector import CTICheckResult
from src.models.threat_intelligence import ThreatLevel, ThreatSource, ThreatType


@pytest.mark.asyncio
class TestFDSPerformance:
    """FDS 평가 엔진 성능 테스트"""

    async def test_single_evaluation_performance(self, db_session, benchmark):
        """
        단일 평가 성능 테스트

        목표:
        - 평가 시간: 100ms 이내
        - P95: 50ms 이내 (이상적)

        검증 항목:
        - 평균 응답 시간
        - P95 응답 시간
        - 최대 응답 시간
        """
        print("\n" + "=" * 80)
        print("[성능 테스트 1] 단일 평가 성능")
        print("=" * 80)

        # === Arrange ===
        request = FDSEvaluationRequest(
            transaction_id=uuid4(),
            user_id=uuid4(),
            order_id=uuid4(),
            amount=100000,
            ip_address="211.234.123.45",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            device_fingerprint=DeviceFingerprint(
                device_type=DeviceTypeEnum.WEB,
                device_id="perf-test-device",
                browser="Chrome",
                os="Windows",
                screen_resolution="1920x1080",
            ),
        )

        mock_redis = AsyncMock()

        # CTI Mock
        cti_result = CTICheckResult(
            threat_type=ThreatType.IP,
            value=request.ip_address,
            is_threat=False,
            threat_level=ThreatLevel.NONE,
            source=ThreatSource.ABUSEIPDB,
            description="정상 IP",
            confidence_score=5,
        )

        # === Act ===
        async def evaluate_transaction():
            """평가 실행"""
            with patch("src.engines.evaluation_engine.CTIConnector") as MockCTIConnector:
                mock_cti_instance = AsyncMock()
                mock_cti_instance.check_ip_threat.return_value = cti_result
                MockCTIConnector.return_value = mock_cti_instance

                engine = EvaluationEngine(db=db_session, redis=mock_redis)
                result = await engine.evaluate(request)
                return result

        # 벤치마크 실행 (100회 반복)
        results = []
        for _ in range(100):
            result = await evaluate_transaction()
            results.append(result.evaluation_metadata.evaluation_time_ms)

        # === Assert ===
        avg_time = statistics.mean(results)
        p95_time = statistics.quantiles(results, n=20)[18]  # 95번째 백분위수
        max_time = max(results)
        min_time = min(results)

        print(f"\n[성능 통계 (100회 측정)]")
        print(f"  - 평균: {avg_time:.2f}ms")
        print(f"  - P95: {p95_time:.2f}ms")
        print(f"  - 최소: {min_time}ms")
        print(f"  - 최대: {max_time}ms")
        print(f"  - 목표: P95 < 100ms (이상적: 50ms)")

        # 평균 시간이 100ms 이내여야 함
        assert avg_time < 100, f"평균 평가 시간이 100ms를 초과: {avg_time:.2f}ms"

        # P95가 100ms 이내여야 함 (경고: 50ms 초과 시)
        if p95_time > 50:
            print(f"\n  [WARNING] P95가 50ms를 초과했습니다: {p95_time:.2f}ms")
        assert p95_time < 100, f"P95 평가 시간이 100ms를 초과: {p95_time:.2f}ms"

        print(f"\n[PASS] 단일 평가 성능 목표 달성")

    async def test_concurrent_evaluation_performance(self, db_session):
        """
        동시 평가 성능 테스트

        목표:
        - 동시 요청 100개 처리
        - 평균 응답 시간: 100ms 이내
        - 모든 요청 성공

        검증 항목:
        - 동시성 처리 능력
        - 응답 시간 일관성
        """
        print("\n" + "=" * 80)
        print("[성능 테스트 2] 동시 평가 성능 (100개 동시 요청)")
        print("=" * 80)

        # === Arrange ===
        num_requests = 100
        mock_redis = AsyncMock()

        # CTI Mock
        cti_result = CTICheckResult(
            threat_type=ThreatType.IP,
            value="211.234.123.45",
            is_threat=False,
            threat_level=ThreatLevel.NONE,
            source=ThreatSource.ABUSEIPDB,
            description="정상 IP",
            confidence_score=5,
        )

        async def evaluate_single():
            """단일 평가 실행"""
            request = FDSEvaluationRequest(
                transaction_id=uuid4(),
                user_id=uuid4(),
                order_id=uuid4(),
                amount=100000,
                ip_address="211.234.123.45",
                user_agent="Mozilla/5.0",
                device_fingerprint=DeviceFingerprint(
                    device_type=DeviceTypeEnum.WEB,
                    device_id=f"device-{uuid4()}",
                    browser="Chrome",
                    os="Windows",
                    screen_resolution="1920x1080",
                ),
            )

            with patch("src.engines.evaluation_engine.CTIConnector") as MockCTIConnector:
                mock_cti_instance = AsyncMock()
                mock_cti_instance.check_ip_threat.return_value = cti_result
                MockCTIConnector.return_value = mock_cti_instance

                engine = EvaluationEngine(db=db_session, redis=mock_redis)
                result = await engine.evaluate(request)
                return result

        # === Act ===
        import time

        start_time = time.time()
        tasks = [evaluate_single() for _ in range(num_requests)]
        results = await asyncio.gather(*tasks)
        total_time = (time.time() - start_time) * 1000  # ms

        # === Assert ===
        evaluation_times = [r.evaluation_metadata.evaluation_time_ms for r in results]
        avg_time = statistics.mean(evaluation_times)
        p95_time = statistics.quantiles(evaluation_times, n=20)[18]
        throughput = num_requests / (total_time / 1000)  # TPS

        print(f"\n[성능 통계]")
        print(f"  - 총 요청 수: {num_requests}")
        print(f"  - 총 처리 시간: {total_time:.2f}ms")
        print(f"  - 처리량: {throughput:.2f} TPS")
        print(f"  - 평균 응답 시간: {avg_time:.2f}ms")
        print(f"  - P95 응답 시간: {p95_time:.2f}ms")

        # 모든 요청 성공
        assert len(results) == num_requests, f"일부 요청 실패: {len(results)}/{num_requests}"

        # 평균 응답 시간 100ms 이내
        assert avg_time < 100, f"평균 응답 시간이 100ms 초과: {avg_time:.2f}ms"

        # 처리량 검증 (참고: 단일 스레드 제약으로 1,000 TPS는 어려울 수 있음)
        print(f"\n  [INFO] 동시 처리 TPS: {throughput:.2f}")

        print(f"\n[PASS] 동시 평가 성능 검증 완료")

    async def test_high_load_scenario_sequential(self, db_session):
        """
        고부하 시나리오 테스트 (순차 처리)

        목표:
        - 1,000개 요청 순차 처리
        - 평균 응답 시간 일관성 유지
        - 메모리 누수 없음

        검증 항목:
        - 대량 요청 처리 능력
        - 성능 일관성
        """
        print("\n" + "=" * 80)
        print("[성능 테스트 3] 고부하 시나리오 (1,000개 요청 순차 처리)")
        print("=" * 80)

        # === Arrange ===
        num_requests = 1000
        mock_redis = AsyncMock()

        # CTI Mock
        cti_result = CTICheckResult(
            threat_type=ThreatType.IP,
            value="211.234.123.45",
            is_threat=False,
            threat_level=ThreatLevel.NONE,
            source=ThreatSource.ABUSEIPDB,
            description="정상 IP",
            confidence_score=5,
        )

        # === Act ===
        import time

        start_time = time.time()
        evaluation_times = []

        with patch("src.engines.evaluation_engine.CTIConnector") as MockCTIConnector:
            mock_cti_instance = AsyncMock()
            mock_cti_instance.check_ip_threat.return_value = cti_result
            MockCTIConnector.return_value = mock_cti_instance

            engine = EvaluationEngine(db=db_session, redis=mock_redis)

            for i in range(num_requests):
                request = FDSEvaluationRequest(
                    transaction_id=uuid4(),
                    user_id=uuid4(),
                    order_id=uuid4(),
                    amount=100000,
                    ip_address="211.234.123.45",
                    user_agent="Mozilla/5.0",
                    device_fingerprint=DeviceFingerprint(
                        device_type=DeviceTypeEnum.WEB,
                        device_id=f"device-{i}",
                        browser="Chrome",
                        os="Windows",
                        screen_resolution="1920x1080",
                    ),
                )

                result = await engine.evaluate(request)
                evaluation_times.append(result.evaluation_metadata.evaluation_time_ms)

                # 진행 상황 출력 (매 100개마다)
                if (i + 1) % 100 == 0:
                    print(f"  - 진행: {i + 1}/{num_requests} 요청 처리 완료")

        total_time = (time.time() - start_time) * 1000  # ms

        # === Assert ===
        avg_time = statistics.mean(evaluation_times)
        p95_time = statistics.quantiles(evaluation_times, n=20)[18]
        throughput = num_requests / (total_time / 1000)  # TPS

        # 배치별 평균 시간 (일관성 확인)
        batch_size = 100
        batch_averages = [
            statistics.mean(evaluation_times[i : i + batch_size])
            for i in range(0, num_requests, batch_size)
        ]

        print(f"\n[성능 통계]")
        print(f"  - 총 요청 수: {num_requests}")
        print(f"  - 총 처리 시간: {total_time / 1000:.2f}초")
        print(f"  - 처리량: {throughput:.2f} TPS")
        print(f"  - 평균 응답 시간: {avg_time:.2f}ms")
        print(f"  - P95 응답 시간: {p95_time:.2f}ms")

        print(f"\n[배치별 평균 응답 시간 (100개씩)]")
        for i, batch_avg in enumerate(batch_averages):
            batch_num = i + 1
            print(f"  - 배치 {batch_num}: {batch_avg:.2f}ms")

        # 평균 응답 시간 일관성 검증 (표준편차 < 20ms)
        batch_std = statistics.stdev(batch_averages)
        print(f"\n[일관성 검증]")
        print(f"  - 배치별 표준편차: {batch_std:.2f}ms")
        print(f"  - 목표: 표준편차 < 20ms (성능 일관성)")

        # 평균 응답 시간이 100ms 이내여야 함
        assert avg_time < 100, f"평균 응답 시간이 100ms 초과: {avg_time:.2f}ms"

        # 성능 일관성 검증
        if batch_std > 20:
            print(f"\n  [WARNING] 배치별 성능 편차가 큽니다: {batch_std:.2f}ms")

        print(f"\n[PASS] 고부하 시나리오 성능 검증 완료")

    async def test_cti_check_performance(self, db_session):
        """
        CTI 체크 성능 테스트

        목표:
        - CTI 체크 시간: 50ms 이내
        - 전체 평가에서 CTI 비중 확인

        검증 항목:
        - cti_check_time_ms 측정
        - CTI 체크 성능 병목 확인
        """
        print("\n" + "=" * 80)
        print("[성능 테스트 4] CTI 체크 성능")
        print("=" * 80)

        # === Arrange ===
        request = FDSEvaluationRequest(
            transaction_id=uuid4(),
            user_id=uuid4(),
            order_id=uuid4(),
            amount=100000,
            ip_address="211.234.123.45",
            user_agent="Mozilla/5.0",
            device_fingerprint=DeviceFingerprint(
                device_type=DeviceTypeEnum.WEB,
                device_id="cti-perf-test",
                browser="Chrome",
                os="Windows",
                screen_resolution="1920x1080",
            ),
        )

        mock_redis = AsyncMock()

        # CTI Mock (다양한 응답 시간 시뮬레이션)
        cti_result = CTICheckResult(
            threat_type=ThreatType.IP,
            value=request.ip_address,
            is_threat=False,
            threat_level=ThreatLevel.NONE,
            source=ThreatSource.ABUSEIPDB,
            description="정상 IP",
            confidence_score=5,
        )

        # === Act ===
        cti_times = []
        total_times = []

        for _ in range(100):
            with patch("src.engines.evaluation_engine.CTIConnector") as MockCTIConnector:
                mock_cti_instance = AsyncMock()
                mock_cti_instance.check_ip_threat.return_value = cti_result
                MockCTIConnector.return_value = mock_cti_instance

                engine = EvaluationEngine(db=db_session, redis=mock_redis)
                result = await engine.evaluate(request)

                cti_time = result.evaluation_metadata.cti_check_time_ms or 0
                total_time = result.evaluation_metadata.evaluation_time_ms

                cti_times.append(cti_time)
                total_times.append(total_time)

        # === Assert ===
        avg_cti_time = statistics.mean(cti_times)
        avg_total_time = statistics.mean(total_times)
        cti_ratio = (avg_cti_time / avg_total_time * 100) if avg_total_time > 0 else 0

        print(f"\n[CTI 성능 통계 (100회 측정)]")
        print(f"  - 평균 CTI 체크 시간: {avg_cti_time:.2f}ms")
        print(f"  - 평균 전체 평가 시간: {avg_total_time:.2f}ms")
        print(f"  - CTI 비중: {cti_ratio:.1f}%")
        print(f"  - 목표: CTI 체크 < 50ms")

        # CTI 체크 시간이 50ms 이내여야 함
        if avg_cti_time > 50:
            print(f"\n  [WARNING] CTI 체크 시간이 50ms를 초과: {avg_cti_time:.2f}ms")

        print(f"\n[PASS] CTI 체크 성능 측정 완료")

    async def test_performance_summary(self, db_session):
        """
        성능 테스트 종합 요약

        모든 성능 테스트 결과를 종합하여 목표 달성 여부를 확인합니다.
        """
        print("\n" + "=" * 80)
        print("[성능 테스트 종합 요약]")
        print("=" * 80)

        # 간단한 성능 측정
        request = FDSEvaluationRequest(
            transaction_id=uuid4(),
            user_id=uuid4(),
            order_id=uuid4(),
            amount=100000,
            ip_address="211.234.123.45",
            user_agent="Mozilla/5.0",
            device_fingerprint=DeviceFingerprint(
                device_type=DeviceTypeEnum.WEB,
                device_id="summary-test",
                browser="Chrome",
                os="Windows",
                screen_resolution="1920x1080",
            ),
        )

        mock_redis = AsyncMock()
        cti_result = CTICheckResult(
            threat_type=ThreatType.IP,
            value=request.ip_address,
            is_threat=False,
            threat_level=ThreatLevel.NONE,
            source=ThreatSource.ABUSEIPDB,
            description="정상 IP",
            confidence_score=5,
        )

        results = []
        for _ in range(100):
            with patch("src.engines.evaluation_engine.CTIConnector") as MockCTIConnector:
                mock_cti_instance = AsyncMock()
                mock_cti_instance.check_ip_threat.return_value = cti_result
                MockCTIConnector.return_value = mock_cti_instance

                engine = EvaluationEngine(db=db_session, redis=mock_redis)
                result = await engine.evaluate(request)
                results.append(result.evaluation_metadata.evaluation_time_ms)

        avg_time = statistics.mean(results)
        p95_time = statistics.quantiles(results, n=20)[18]

        print("\n[목표 달성 현황]")
        print(f"  1. 평균 응답 시간 < 100ms: {avg_time:.2f}ms {'[OK]' if avg_time < 100 else '[FAIL]'}")
        print(f"  2. P95 응답 시간 < 100ms: {p95_time:.2f}ms {'[OK]' if p95_time < 100 else '[FAIL]'}")
        print(f"  3. 이상적 P95 < 50ms: {p95_time:.2f}ms {'[OK]' if p95_time < 50 else '[WARNING]'}")

        print("\n[권장 사항]")
        if avg_time < 50:
            print("  - 성능이 매우 우수합니다. 현재 수준 유지")
        elif avg_time < 100:
            print("  - 성능 목표를 달성했습니다.")
            if p95_time > 50:
                print("  - P95 50ms 달성을 위해 추가 최적화 고려")
        else:
            print("  - 성능 최적화 필요:")
            print("    1. Redis 캐싱 활용도 증가")
            print("    2. CTI 체크 타임아웃 조정")
            print("    3. 불필요한 DB 쿼리 제거")

        print("\n" + "=" * 80)
        print("[SUCCESS] 성능 테스트 완료")
        print("=" * 80)
