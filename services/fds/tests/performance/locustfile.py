"""
T116 부하 테스트: Locust를 사용한 실전 성능 검증

목표:
- 처리량: 1,000 TPS 이상
- P95 응답 시간: 100ms 이내 (이상적: 50ms)
- 동시 사용자: 100명
- 테스트 기간: 5분

실행 방법:
1. FDS 서비스 실행: cd services/fds && python src/main.py
2. Locust 실행: locust -f tests/performance/locustfile.py --host=http://localhost:8001
3. 브라우저에서 http://localhost:8089 접속
4. 사용자 수: 100, Spawn rate: 10 입력 후 Start swarming

커맨드라인 실행 (헤드리스):
locust -f tests/performance/locustfile.py --host=http://localhost:8001 \
    --users 100 --spawn-rate 10 --run-time 5m --headless \
    --html locust_report.html

성능 목표:
- 평균 응답 시간: 50ms 이내
- P95 응답 시간: 100ms 이내
- 실패율: 0%
- 처리량: 1,000 TPS 이상
"""

from locust import HttpUser, task, between, events
from uuid import uuid4
import json
import time
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 성능 메트릭 수집
performance_metrics = {
    "total_requests": 0,
    "success_requests": 0,
    "failed_requests": 0,
    "response_times": [],
}


class FDSUser(HttpUser):
    """FDS 평가 API 부하 테스트 사용자"""

    # 사용자당 요청 간격 (초): 0.5~2초 (평균 1초 = 1 RPS per user)
    # 100명 사용자 = 약 100 RPS
    # 1,000 TPS 달성을 위해서는 wait_time을 짧게 설정하거나 사용자 수를 늘려야 함
    wait_time = between(0.01, 0.05)  # 10~50ms 대기 (높은 TPS 목표)

    def on_start(self):
        """테스트 시작 시 실행 (각 사용자마다)"""
        self.user_id = uuid4()
        logger.info(f"사용자 시작: {self.user_id}")

    @task(10)  # 가중치 10: 정상 거래가 가장 빈번
    def evaluate_normal_transaction(self):
        """정상 거래 평가 (저위험)"""
        request_data = {
            "transaction_id": str(uuid4()),
            "user_id": str(self.user_id),
            "order_id": str(uuid4()),
            "amount": 50000,  # 50,000원 (정상)
            "ip_address": "211.234.123.45",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "device_fingerprint": {
                "device_type": "web",
                "device_id": f"device-{self.user_id}",
                "browser": "Chrome",
                "os": "Windows",
                "screen_resolution": "1920x1080",
            },
        }

        headers = {
            "Content-Type": "application/json",
            "X-Service-Token": "dev-service-token-12345",  # 개발용 토큰
        }

        start_time = time.time()

        with self.client.post(
            "/v1/internal/fds/evaluate",
            json=request_data,
            headers=headers,
            catch_response=True,
        ) as response:
            response_time_ms = (time.time() - start_time) * 1000

            # 성공 여부 확인
            if response.status_code == 200:
                try:
                    result = response.json()

                    # 평가 결과 검증
                    if "risk_score" in result and "decision" in result:
                        # 정상 거래는 낮은 위험 점수 예상
                        if result["risk_score"] <= 30:
                            response.success()
                            performance_metrics["success_requests"] += 1
                        else:
                            response.failure(f"예상치 못한 위험 점수: {result['risk_score']}")
                            performance_metrics["failed_requests"] += 1
                    else:
                        response.failure("응답에 필수 필드 누락")
                        performance_metrics["failed_requests"] += 1

                    performance_metrics["response_times"].append(response_time_ms)
                except json.JSONDecodeError:
                    response.failure("JSON 파싱 실패")
                    performance_metrics["failed_requests"] += 1
            else:
                response.failure(f"HTTP {response.status_code}")
                performance_metrics["failed_requests"] += 1

            performance_metrics["total_requests"] += 1

    @task(5)  # 가중치 5: 고액 거래 (중간 위험)
    def evaluate_high_amount_transaction(self):
        """고액 거래 평가 (중간 위험)"""
        request_data = {
            "transaction_id": str(uuid4()),
            "user_id": str(self.user_id),
            "order_id": str(uuid4()),
            "amount": 1000000,  # 1,000,000원 (고액)
            "ip_address": "211.234.123.45",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "device_fingerprint": {
                "device_type": "web",
                "device_id": f"device-{self.user_id}",
                "browser": "Chrome",
                "os": "Windows",
                "screen_resolution": "1920x1080",
            },
        }

        headers = {
            "Content-Type": "application/json",
            "X-Service-Token": "dev-service-token-12345",
        }

        with self.client.post(
            "/v1/internal/fds/evaluate",
            json=request_data,
            headers=headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    # 고액 거래는 중간 위험 점수 예상
                    if "risk_score" in result and 40 <= result["risk_score"] <= 70:
                        response.success()
                    else:
                        response.failure(f"예상 범위 밖의 위험 점수: {result.get('risk_score')}")
                except json.JSONDecodeError:
                    response.failure("JSON 파싱 실패")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)  # 가중치 2: 의심스러운 거래 (고위험)
    def evaluate_suspicious_transaction(self):
        """의심스러운 거래 평가 (고위험)"""
        request_data = {
            "transaction_id": str(uuid4()),
            "user_id": str(self.user_id),
            "order_id": str(uuid4()),
            "amount": 5000000,  # 5,000,000원 (매우 고액)
            "ip_address": "185.220.100.45",  # 의심스러운 IP (TOR)
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "device_fingerprint": {
                "device_type": "web",
                "device_id": f"suspicious-device-{uuid4()}",  # 매번 다른 디바이스
                "browser": "Chrome",
                "os": "Windows",
                "screen_resolution": "1920x1080",
            },
        }

        headers = {
            "Content-Type": "application/json",
            "X-Service-Token": "dev-service-token-12345",
        }

        with self.client.post(
            "/v1/internal/fds/evaluate",
            json=request_data,
            headers=headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    # 의심스러운 거래는 고위험 또는 차단 예상
                    if "risk_score" in result:
                        response.success()
                    else:
                        response.failure("응답에 필수 필드 누락")
                except json.JSONDecodeError:
                    response.failure("JSON 파싱 실패")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)  # 가중치 1: 연속 거래 (velocity check)
    def evaluate_velocity_transaction(self):
        """연속 거래 평가 (velocity check 테스트)"""
        # 같은 사용자로 짧은 시간 내 여러 거래
        for i in range(3):
            request_data = {
                "transaction_id": str(uuid4()),
                "user_id": str(self.user_id),  # 같은 사용자
                "order_id": str(uuid4()),
                "amount": 200000,  # 200,000원
                "ip_address": "211.234.123.45",
                "user_agent": "Mozilla/5.0",
                "device_fingerprint": {
                    "device_type": "web",
                    "device_id": f"device-{self.user_id}",
                    "browser": "Chrome",
                    "os": "Windows",
                    "screen_resolution": "1920x1080",
                },
            }

            headers = {
                "Content-Type": "application/json",
                "X-Service-Token": "dev-service-token-12345",
            }

            with self.client.post(
                "/v1/internal/fds/evaluate",
                json=request_data,
                headers=headers,
                catch_response=True,
                name="/v1/internal/fds/evaluate (velocity)",
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"HTTP {response.status_code}")

            # 짧은 대기 (velocity check 발동을 위해)
            time.sleep(0.1)


# 이벤트 핸들러: 테스트 완료 시 성능 요약 출력
@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """테스트 종료 시 성능 요약"""
    logger.info("\n" + "=" * 80)
    logger.info("[부하 테스트 성능 요약]")
    logger.info("=" * 80)

    total = performance_metrics["total_requests"]
    success = performance_metrics["success_requests"]
    failed = performance_metrics["failed_requests"]
    response_times = performance_metrics["response_times"]

    logger.info(f"총 요청 수: {total}")
    logger.info(f"성공: {success} ({success / total * 100:.1f}%)")
    logger.info(f"실패: {failed} ({failed / total * 100:.1f}%)")

    if response_times:
        avg_time = sum(response_times) / len(response_times)
        sorted_times = sorted(response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p95_time = sorted_times[p95_index]

        logger.info(f"\n[응답 시간]")
        logger.info(f"평균: {avg_time:.2f}ms")
        logger.info(f"P95: {p95_time:.2f}ms")
        logger.info(f"최소: {min(response_times):.2f}ms")
        logger.info(f"최대: {max(response_times):.2f}ms")

        logger.info(f"\n[목표 달성 여부]")
        logger.info(
            f"1. 평균 응답 시간 < 50ms: {'[OK]' if avg_time < 50 else '[FAIL]'} ({avg_time:.2f}ms)"
        )
        logger.info(
            f"2. P95 응답 시간 < 100ms: {'[OK]' if p95_time < 100 else '[FAIL]'} ({p95_time:.2f}ms)"
        )
        logger.info(
            f"3. 실패율 < 1%: {'[OK]' if failed / total < 0.01 else '[FAIL]'} ({failed / total * 100:.2f}%)"
        )

    logger.info("=" * 80)


# 이벤트 핸들러: 주기적 성능 보고 (매 10초)
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """테스트 시작 시 성능 메트릭 초기화"""
    performance_metrics["total_requests"] = 0
    performance_metrics["success_requests"] = 0
    performance_metrics["failed_requests"] = 0
    performance_metrics["response_times"] = []

    logger.info("\n" + "=" * 80)
    logger.info("[FDS 평가 API 부하 테스트 시작]")
    logger.info("=" * 80)
    logger.info("목표:")
    logger.info("  - 처리량: 1,000 TPS 이상")
    logger.info("  - P95 응답 시간: 100ms 이내")
    logger.info("  - 실패율: 0%")
    logger.info("=" * 80 + "\n")
