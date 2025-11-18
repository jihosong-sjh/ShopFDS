"""
추론 성능 모니터링 모듈

실시간 추론 시간 추적 및 P95 50ms 목표 검증
- 추론 시간 메트릭 수집
- P50, P95, P99 지연 시간 계산
- Prometheus 메트릭 노출
- 느린 추론 알림
- 성능 리포트 생성
"""

import time
import asyncio
from collections import deque
from typing import List, Dict, Any, Optional, Deque
from dataclasses import dataclass, field
from datetime import datetime
import statistics
import logging

logger = logging.getLogger(__name__)


@dataclass
class InferenceMetric:
    """
    단일 추론 메트릭

    Attributes:
        request_id: 요청 ID
        model_name: 모델 이름
        inference_time_ms: 추론 시간 (ms)
        batch_size: 배치 크기
        timestamp: 측정 시각
        metadata: 추가 메타데이터
    """

    request_id: str
    model_name: str
    inference_time_ms: float
    batch_size: int = 1
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceReport:
    """
    성능 리포트

    Attributes:
        model_name: 모델 이름
        total_requests: 총 요청 수
        time_window_seconds: 집계 시간 (초)
        mean_latency_ms: 평균 지연 시간
        p50_latency_ms: P50 지연 시간
        p95_latency_ms: P95 지연 시간
        p99_latency_ms: P99 지연 시간
        throughput_qps: 처리량 (QPS)
        slow_requests_count: 느린 요청 수 (P95 초과)
        meets_sla: SLA 달성 여부
    """

    model_name: str
    total_requests: int
    time_window_seconds: float
    mean_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_qps: float
    slow_requests_count: int
    meets_sla: bool
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class InferencePerformanceMonitor:
    """
    추론 성능 모니터링 클래스

    Features:
    - 추론 시간 실시간 수집
    - P95 50ms 목표 검증
    - 롤링 윈도우 통계 (최근 1000개 요청)
    - Prometheus 메트릭 노출
    - 느린 추론 자동 알림
    - 성능 리포트 생성

    Performance Goals:
    - P95 latency < 50ms
    - P99 latency < 100ms
    - Throughput > 1,000 QPS
    """

    def __init__(
        self,
        model_name: str,
        window_size: int = 1000,
        sla_p95_ms: float = 50.0,
        sla_p99_ms: float = 100.0,
        alert_threshold_ms: float = 150.0,
    ):
        """
        Args:
            model_name: 모니터링할 모델 이름
            window_size: 롤링 윈도우 크기 (최근 N개 요청)
            sla_p95_ms: P95 SLA 목표 (ms)
            sla_p99_ms: P99 SLA 목표 (ms)
            alert_threshold_ms: 알림 임계값 (ms)
        """
        self.model_name = model_name
        self.window_size = window_size
        self.sla_p95_ms = sla_p95_ms
        self.sla_p99_ms = sla_p99_ms
        self.alert_threshold_ms = alert_threshold_ms

        # 롤링 윈도우 (최근 요청들)
        self.metrics: Deque[InferenceMetric] = deque(maxlen=window_size)

        # 통계
        self.total_requests = 0
        self.slow_requests = 0
        self.start_time = time.time()

        logger.info(f"[MONITOR] Initialized for {model_name}")
        logger.info(f"  SLA: P95 < {sla_p95_ms}ms, P99 < {sla_p99_ms}ms")

    def record_inference(
        self,
        request_id: str,
        inference_time_ms: float,
        batch_size: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        추론 메트릭 기록

        Args:
            request_id: 요청 ID
            inference_time_ms: 추론 시간 (ms)
            batch_size: 배치 크기
            metadata: 추가 메타데이터
        """
        metric = InferenceMetric(
            request_id=request_id,
            model_name=self.model_name,
            inference_time_ms=inference_time_ms,
            batch_size=batch_size,
            metadata=metadata or {},
        )

        self.metrics.append(metric)
        self.total_requests += 1

        # 느린 요청 카운트
        if inference_time_ms > self.alert_threshold_ms:
            self.slow_requests += 1
            logger.warning(
                f"[SLOW REQUEST] {request_id}: {inference_time_ms:.2f}ms "
                f"(threshold: {self.alert_threshold_ms}ms)"
            )

        # 주기적 SLA 체크 (100 요청마다)
        if self.total_requests % 100 == 0:
            self._check_sla()

    def get_latency_percentiles(
        self, percentiles: List[float] = [50, 95, 99]
    ) -> Dict[str, float]:
        """
        지연 시간 백분위수 계산

        Args:
            percentiles: 계산할 백분위수 리스트 (0-100)

        Returns:
            백분위수 딕셔너리 {"p50": 25.5, "p95": 48.2, "p99": 87.3}
        """
        if not self.metrics:
            return {f"p{int(p)}": 0.0 for p in percentiles}

        latencies = [m.inference_time_ms for m in self.metrics]
        sorted_latencies = sorted(latencies)

        result = {}
        for p in percentiles:
            index = int(len(sorted_latencies) * (p / 100.0))
            index = min(index, len(sorted_latencies) - 1)
            result[f"p{int(p)}"] = sorted_latencies[index]

        return result

    def get_mean_latency(self) -> float:
        """
        평균 지연 시간 계산

        Returns:
            평균 지연 시간 (ms)
        """
        if not self.metrics:
            return 0.0

        latencies = [m.inference_time_ms for m in self.metrics]
        return statistics.mean(latencies)

    def get_throughput_qps(self) -> float:
        """
        처리량 계산 (QPS)

        Returns:
            초당 처리 요청 수
        """
        elapsed_seconds = time.time() - self.start_time

        if elapsed_seconds == 0:
            return 0.0

        return self.total_requests / elapsed_seconds

    def generate_report(self) -> PerformanceReport:
        """
        성능 리포트 생성

        Returns:
            PerformanceReport 객체
        """
        percentiles = self.get_latency_percentiles([50, 95, 99])
        mean_latency = self.get_mean_latency()
        throughput = self.get_throughput_qps()

        p95_latency = percentiles["p95"]
        p99_latency = percentiles["p99"]

        # SLA 달성 여부
        meets_sla = p95_latency <= self.sla_p95_ms and p99_latency <= self.sla_p99_ms

        elapsed_seconds = time.time() - self.start_time

        report = PerformanceReport(
            model_name=self.model_name,
            total_requests=self.total_requests,
            time_window_seconds=elapsed_seconds,
            mean_latency_ms=mean_latency,
            p50_latency_ms=percentiles["p50"],
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            throughput_qps=throughput,
            slow_requests_count=self.slow_requests,
            meets_sla=meets_sla,
        )

        return report

    def _check_sla(self) -> None:
        """
        SLA 달성 여부 체크 및 로깅
        """
        report = self.generate_report()

        if report.meets_sla:
            logger.info(
                f"[SLA CHECK] {self.model_name} - [PASS] "
                f"P95: {report.p95_latency_ms:.2f}ms, "
                f"P99: {report.p99_latency_ms:.2f}ms, "
                f"QPS: {report.throughput_qps:.2f}"
            )
        else:
            logger.warning(
                f"[SLA CHECK] {self.model_name} - [FAIL] "
                f"P95: {report.p95_latency_ms:.2f}ms (target: {self.sla_p95_ms}ms), "
                f"P99: {report.p99_latency_ms:.2f}ms (target: {self.sla_p99_ms}ms)"
            )

    def print_summary(self) -> None:
        """
        성능 요약 출력
        """
        report = self.generate_report()

        print("\n" + "=" * 60)
        print(f"PERFORMANCE REPORT: {report.model_name}")
        print("=" * 60)
        print(f"Total Requests: {report.total_requests}")
        print(f"Time Window: {report.time_window_seconds:.2f}s")
        print(f"Throughput: {report.throughput_qps:.2f} QPS")
        print("-" * 60)
        print(f"Mean Latency: {report.mean_latency_ms:.2f}ms")
        print(f"P50 Latency: {report.p50_latency_ms:.2f}ms")
        print(
            f"P95 Latency: {report.p95_latency_ms:.2f}ms (target: {self.sla_p95_ms}ms)"
        )
        print(
            f"P99 Latency: {report.p99_latency_ms:.2f}ms (target: {self.sla_p99_ms}ms)"
        )
        print("-" * 60)
        print(
            f"Slow Requests: {report.slow_requests_count} (>{self.alert_threshold_ms}ms)"
        )
        print(f"SLA Status: {'[PASS]' if report.meets_sla else '[FAIL]'}")
        print("=" * 60 + "\n")

    def get_prometheus_metrics(self) -> str:
        """
        Prometheus 메트릭 형식으로 출력

        Returns:
            Prometheus 메트릭 문자열
        """
        report = self.generate_report()

        metrics = f"""
# HELP inference_latency_mean_ms Mean inference latency in milliseconds
# TYPE inference_latency_mean_ms gauge
inference_latency_mean_ms{{model="{self.model_name}"}} {report.mean_latency_ms:.2f}

# HELP inference_latency_p50_ms P50 inference latency in milliseconds
# TYPE inference_latency_p50_ms gauge
inference_latency_p50_ms{{model="{self.model_name}"}} {report.p50_latency_ms:.2f}

# HELP inference_latency_p95_ms P95 inference latency in milliseconds
# TYPE inference_latency_p95_ms gauge
inference_latency_p95_ms{{model="{self.model_name}"}} {report.p95_latency_ms:.2f}

# HELP inference_latency_p99_ms P99 inference latency in milliseconds
# TYPE inference_latency_p99_ms gauge
inference_latency_p99_ms{{model="{self.model_name}"}} {report.p99_latency_ms:.2f}

# HELP inference_throughput_qps Inference throughput in queries per second
# TYPE inference_throughput_qps gauge
inference_throughput_qps{{model="{self.model_name}"}} {report.throughput_qps:.2f}

# HELP inference_total_requests Total number of inference requests
# TYPE inference_total_requests counter
inference_total_requests{{model="{self.model_name}"}} {report.total_requests}

# HELP inference_slow_requests_total Total number of slow requests
# TYPE inference_slow_requests_total counter
inference_slow_requests_total{{model="{self.model_name}"}} {report.slow_requests_count}

# HELP inference_sla_status SLA status (1=pass, 0=fail)
# TYPE inference_sla_status gauge
inference_sla_status{{model="{self.model_name}"}} {1 if report.meets_sla else 0}
"""
        return metrics.strip()

    def reset(self) -> None:
        """
        통계 리셋
        """
        self.metrics.clear()
        self.total_requests = 0
        self.slow_requests = 0
        self.start_time = time.time()
        logger.info(f"[RESET] Statistics reset for {self.model_name}")


class PerformanceMonitorManager:
    """
    여러 모델의 성능 모니터 관리
    """

    def __init__(self):
        self.monitors: Dict[str, InferencePerformanceMonitor] = {}

    def get_or_create_monitor(
        self, model_name: str, **kwargs
    ) -> InferencePerformanceMonitor:
        """
        모델별 모니터 가져오기 (없으면 생성)

        Args:
            model_name: 모델 이름
            **kwargs: InferencePerformanceMonitor 생성자 인자

        Returns:
            InferencePerformanceMonitor 인스턴스
        """
        if model_name not in self.monitors:
            self.monitors[model_name] = InferencePerformanceMonitor(
                model_name=model_name, **kwargs
            )

        return self.monitors[model_name]

    def record_inference(
        self,
        model_name: str,
        request_id: str,
        inference_time_ms: float,
        **kwargs,
    ) -> None:
        """
        추론 메트릭 기록 (모델별)

        Args:
            model_name: 모델 이름
            request_id: 요청 ID
            inference_time_ms: 추론 시간 (ms)
            **kwargs: 추가 인자
        """
        monitor = self.get_or_create_monitor(model_name)
        monitor.record_inference(request_id, inference_time_ms, **kwargs)

    def get_all_reports(self) -> List[PerformanceReport]:
        """
        모든 모델의 성능 리포트 가져오기

        Returns:
            PerformanceReport 리스트
        """
        return [monitor.generate_report() for monitor in self.monitors.values()]

    def get_prometheus_metrics(self) -> str:
        """
        모든 모델의 Prometheus 메트릭

        Returns:
            Prometheus 메트릭 문자열
        """
        all_metrics = []
        for monitor in self.monitors.values():
            all_metrics.append(monitor.get_prometheus_metrics())

        return "\n\n".join(all_metrics)

    def print_all_summaries(self) -> None:
        """
        모든 모델의 성능 요약 출력
        """
        for monitor in self.monitors.values():
            monitor.print_summary()


# 전역 싱글톤 모니터 매니저
_global_monitor_manager: Optional[PerformanceMonitorManager] = None


def get_monitor_manager() -> PerformanceMonitorManager:
    """
    전역 모니터 매니저 가져오기

    Returns:
        PerformanceMonitorManager 인스턴스
    """
    global _global_monitor_manager

    if _global_monitor_manager is None:
        _global_monitor_manager = PerformanceMonitorManager()

    return _global_monitor_manager


# 사용 예시
if __name__ == "__main__":
    import random

    # 모니터 생성
    monitor = InferencePerformanceMonitor(
        model_name="fraud_detector",
        window_size=1000,
        sla_p95_ms=50.0,
        sla_p99_ms=100.0,
    )

    # 시뮬레이션: 1,000개 추론 요청
    print("[SIMULATION] Simulating 1,000 inference requests...")

    for i in range(1000):
        # 추론 시간 시뮬레이션 (대부분 20-60ms, 가끔 느린 요청)
        if random.random() < 0.05:  # 5% 느린 요청
            inference_time = random.uniform(100, 200)
        else:
            inference_time = random.uniform(20, 60)

        monitor.record_inference(
            request_id=f"req-{i}",
            inference_time_ms=inference_time,
            batch_size=random.randint(1, 50),
        )

        time.sleep(0.001)  # 1ms 대기

    # 성능 요약 출력
    monitor.print_summary()

    # Prometheus 메트릭 출력
    print("\nPROMETHEUS METRICS:")
    print(monitor.get_prometheus_metrics())
