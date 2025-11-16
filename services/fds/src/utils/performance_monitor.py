"""
FDS 성능 모니터링 유틸리티

FDS 평가 시간을 추적하고 100ms 목표 달성 여부를 검증
"""

import time
import logging
import statistics
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class PerformanceMetric(str, Enum):
    """성능 지표 타입"""

    EVALUATION_TIME = "evaluation_time"  # FDS 전체 평가 시간
    RULE_ENGINE_TIME = "rule_engine_time"  # 룰 엔진 실행 시간
    ML_ENGINE_TIME = "ml_engine_time"  # ML 엔진 실행 시간
    CTI_CHECK_TIME = "cti_check_time"  # CTI 조회 시간
    DB_QUERY_TIME = "db_query_time"  # 데이터베이스 쿼리 시간
    REDIS_OP_TIME = "redis_op_time"  # Redis 작업 시간


@dataclass
class PerformanceSnapshot:
    """성능 측정 스냅샷"""

    metric_type: PerformanceMetric
    value_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    transaction_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceTracker:
    """
    성능 추적기

    실시간으로 성능 지표를 수집하고 통계를 계산합니다.
    """

    def __init__(self, window_size: int = 1000):
        """
        Args:
            window_size: 최근 N개의 측정값을 유지 (슬라이딩 윈도우)
        """
        self.window_size = window_size
        self.snapshots: Dict[PerformanceMetric, deque] = {
            metric: deque(maxlen=window_size) for metric in PerformanceMetric
        }
        self.total_measurements: Dict[PerformanceMetric, int] = {
            metric: 0 for metric in PerformanceMetric
        }

    def track(
        self,
        metric_type: PerformanceMetric,
        value_ms: float,
        transaction_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        성능 지표 기록

        Args:
            metric_type: 지표 타입
            value_ms: 측정값 (밀리초)
            transaction_id: 거래 ID (선택)
            metadata: 추가 메타데이터 (선택)
        """
        snapshot = PerformanceSnapshot(
            metric_type=metric_type,
            value_ms=value_ms,
            transaction_id=transaction_id,
            metadata=metadata or {},
        )

        self.snapshots[metric_type].append(snapshot)
        self.total_measurements[metric_type] += 1

        # 100ms 목표 초과 시 경고
        if metric_type == PerformanceMetric.EVALUATION_TIME and value_ms > 100:
            logger.warning(
                f"FDS 평가 시간 목표 초과: {value_ms:.2f}ms (목표: 100ms) "
                f"[transaction_id={transaction_id}]"
            )

    def get_stats(self, metric_type: PerformanceMetric) -> Dict[str, float]:
        """
        특정 지표의 통계 조회

        Args:
            metric_type: 지표 타입

        Returns:
            통계 정보 (평균, 중앙값, P95, P99, 최소, 최대)
        """
        values = [s.value_ms for s in self.snapshots[metric_type]]

        if not values:
            return {
                "count": 0,
                "mean": 0.0,
                "median": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "min": 0.0,
                "max": 0.0,
                "total_measurements": self.total_measurements[metric_type],
            }

        sorted_values = sorted(values)
        count = len(sorted_values)

        return {
            "count": count,
            "mean": statistics.mean(sorted_values),
            "median": statistics.median(sorted_values),
            "p50": self._percentile(sorted_values, 50),
            "p95": self._percentile(sorted_values, 95),
            "p99": self._percentile(sorted_values, 99),
            "min": min(sorted_values),
            "max": max(sorted_values),
            "total_measurements": self.total_measurements[metric_type],
        }

    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """모든 지표의 통계 조회"""
        return {metric.value: self.get_stats(metric) for metric in PerformanceMetric}

    def check_target_compliance(
        self, metric_type: PerformanceMetric, target_ms: float, percentile: int = 95
    ) -> Dict[str, Any]:
        """
        목표 성능 준수 여부 확인

        Args:
            metric_type: 지표 타입
            target_ms: 목표 시간 (밀리초)
            percentile: 확인할 백분위수 (기본: P95)

        Returns:
            준수 여부 및 상세 정보
        """
        stats = self.get_stats(metric_type)

        if stats["count"] == 0:
            return {"compliant": None, "message": "측정 데이터 없음", "stats": stats}

        percentile_key = f"p{percentile}"
        actual_value = stats[percentile_key]
        compliant = actual_value <= target_ms

        return {
            "compliant": compliant,
            "target_ms": target_ms,
            "actual_ms": actual_value,
            "percentile": percentile,
            "margin_ms": target_ms - actual_value,
            "margin_percent": ((target_ms - actual_value) / target_ms * 100),
            "message": (
                f"목표 달성: P{percentile}={actual_value:.2f}ms <= {target_ms}ms"
                if compliant
                else f"목표 미달: P{percentile}={actual_value:.2f}ms > {target_ms}ms"
            ),
            "stats": stats,
        }

    def get_slow_transactions(
        self, metric_type: PerformanceMetric, threshold_ms: float = 100, limit: int = 10
    ) -> List[PerformanceSnapshot]:
        """
        느린 거래 조회

        Args:
            metric_type: 지표 타입
            threshold_ms: 임계값 (밀리초)
            limit: 최대 조회 개수

        Returns:
            느린 거래 스냅샷 리스트
        """
        slow_snapshots = [
            s for s in self.snapshots[metric_type] if s.value_ms > threshold_ms
        ]

        # 시간 내림차순 정렬
        slow_snapshots.sort(key=lambda s: s.value_ms, reverse=True)

        return slow_snapshots[:limit]

    def reset(self):
        """모든 측정 데이터 초기화"""
        for metric in PerformanceMetric:
            self.snapshots[metric].clear()
            self.total_measurements[metric] = 0
        logger.info("성능 추적 데이터 초기화 완료")

    @staticmethod
    def _percentile(sorted_values: List[float], percentile: int) -> float:
        """백분위수 계산"""
        if not sorted_values:
            return 0.0

        index = (len(sorted_values) - 1) * percentile / 100
        lower = int(index)
        upper = lower + 1

        if upper >= len(sorted_values):
            return sorted_values[-1]

        weight = index - lower
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


class PerformanceMonitor:
    """
    FDS 성능 모니터링 관리자

    성능 추적, 목표 검증, 알림 등을 통합 관리
    """

    # FDS 성능 목표
    FDS_TARGET_MS = 100  # P95 기준 100ms 이내
    FDS_WARNING_MS = 80  # 80ms 초과 시 경고
    FDS_CRITICAL_MS = 150  # 150ms 초과 시 크리티컬

    def __init__(self, window_size: int = 1000):
        self.tracker = PerformanceTracker(window_size)
        self.alert_callbacks: List[callable] = []

    def track_evaluation(
        self,
        evaluation_time_ms: float,
        transaction_id: Optional[str] = None,
        breakdown: Optional[Dict[str, float]] = None,
    ):
        """
        FDS 평가 성능 추적

        Args:
            evaluation_time_ms: 전체 평가 시간 (밀리초)
            transaction_id: 거래 ID
            breakdown: 세부 시간 분해 (rule_engine, ml_engine, cti_check 등)
        """
        # 전체 평가 시간 기록
        self.tracker.track(
            PerformanceMetric.EVALUATION_TIME,
            evaluation_time_ms,
            transaction_id,
            metadata=breakdown or {},
        )

        # 세부 시간 기록
        if breakdown:
            for key, value_ms in breakdown.items():
                if key == "rule_engine_time":
                    self.tracker.track(
                        PerformanceMetric.RULE_ENGINE_TIME, value_ms, transaction_id
                    )
                elif key == "ml_engine_time":
                    self.tracker.track(
                        PerformanceMetric.ML_ENGINE_TIME, value_ms, transaction_id
                    )
                elif key == "cti_check_time":
                    self.tracker.track(
                        PerformanceMetric.CTI_CHECK_TIME, value_ms, transaction_id
                    )

        # 성능 임계값 확인 및 알림
        if evaluation_time_ms > self.FDS_CRITICAL_MS:
            self._trigger_alert("CRITICAL", evaluation_time_ms, transaction_id)
        elif evaluation_time_ms > self.FDS_WARNING_MS:
            self._trigger_alert("WARNING", evaluation_time_ms, transaction_id)

    def check_fds_target(self) -> Dict[str, Any]:
        """
        FDS 100ms 목표 달성 여부 확인

        Returns:
            목표 준수 여부 및 상세 정보
        """
        return self.tracker.check_target_compliance(
            PerformanceMetric.EVALUATION_TIME,
            target_ms=self.FDS_TARGET_MS,
            percentile=95,
        )

    def get_performance_report(self) -> str:
        """
        성능 리포트 생성

        Returns:
            포맷된 성능 리포트 문자열
        """
        all_stats = self.tracker.get_all_stats()
        fds_compliance = self.check_fds_target()

        lines = [
            "=" * 70,
            "FDS 성능 모니터링 리포트",
            "=" * 70,
            "",
            "[ FDS 평가 시간 ]",
            f"  목표: P95 <= {self.FDS_TARGET_MS}ms",
            f"  상태: {fds_compliance['message']}",
        ]

        eval_stats = all_stats[PerformanceMetric.EVALUATION_TIME.value]
        if eval_stats["count"] > 0:
            lines.extend(
                [
                    f"  평균: {eval_stats['mean']:.2f}ms",
                    f"  중앙값: {eval_stats['median']:.2f}ms",
                    f"  P95: {eval_stats['p95']:.2f}ms",
                    f"  P99: {eval_stats['p99']:.2f}ms",
                    f"  최소: {eval_stats['min']:.2f}ms",
                    f"  최대: {eval_stats['max']:.2f}ms",
                    f"  측정 횟수: {eval_stats['count']}회 (전체: {eval_stats['total_measurements']}회)",
                    "",
                ]
            )

        # 세부 시간 분해
        lines.append("[ 세부 시간 분해 ]")
        for metric in [
            PerformanceMetric.RULE_ENGINE_TIME,
            PerformanceMetric.ML_ENGINE_TIME,
            PerformanceMetric.CTI_CHECK_TIME,
        ]:
            stats = all_stats[metric.value]
            if stats["count"] > 0:
                lines.append(
                    f"  {metric.value}: "
                    f"평균 {stats['mean']:.2f}ms, "
                    f"P95 {stats['p95']:.2f}ms"
                )

        lines.extend(["", "=" * 70])

        return "\n".join(lines)

    def get_slow_evaluations(self, limit: int = 10) -> List[PerformanceSnapshot]:
        """
        느린 FDS 평가 조회

        Args:
            limit: 최대 조회 개수

        Returns:
            느린 평가 스냅샷 리스트
        """
        return self.tracker.get_slow_transactions(
            PerformanceMetric.EVALUATION_TIME,
            threshold_ms=self.FDS_TARGET_MS,
            limit=limit,
        )

    def register_alert_callback(self, callback: callable):
        """
        알림 콜백 등록

        Args:
            callback: 알림 함수 (level, time_ms, transaction_id를 인자로 받음)
        """
        self.alert_callbacks.append(callback)

    def _trigger_alert(self, level: str, time_ms: float, transaction_id: Optional[str]):
        """알림 트리거"""
        for callback in self.alert_callbacks:
            try:
                callback(level, time_ms, transaction_id)
            except Exception as e:
                logger.error(f"알림 콜백 실행 실패: {e}")

    def export_metrics_prometheus(self) -> str:
        """
        Prometheus 형식으로 메트릭 내보내기

        Returns:
            Prometheus 메트릭 문자열
        """
        lines = [
            "# HELP fds_evaluation_time_seconds FDS evaluation time in seconds",
            "# TYPE fds_evaluation_time_seconds summary",
        ]

        eval_stats = self.tracker.get_stats(PerformanceMetric.EVALUATION_TIME)
        if eval_stats["count"] > 0:
            lines.extend(
                [
                    f"fds_evaluation_time_seconds{{quantile=\"0.5\"}} {eval_stats['p50'] / 1000}",
                    f"fds_evaluation_time_seconds{{quantile=\"0.95\"}} {eval_stats['p95'] / 1000}",
                    f"fds_evaluation_time_seconds{{quantile=\"0.99\"}} {eval_stats['p99'] / 1000}",
                    f"fds_evaluation_time_seconds_sum {eval_stats['mean'] * eval_stats['count'] / 1000}",
                    f"fds_evaluation_time_seconds_count {eval_stats['total_measurements']}",
                ]
            )

        return "\n".join(lines)


# 전역 모니터 인스턴스
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """전역 성능 모니터 인스턴스 조회"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def track_performance(metric_type: PerformanceMetric):
    """
    성능 측정 데코레이터

    Usage:
        @track_performance(PerformanceMetric.EVALUATION_TIME)
        async def evaluate_transaction(request):
            ...
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.time() - start_time) * 1000
                monitor = get_performance_monitor()
                monitor.tracker.track(metric_type, elapsed_ms)

        return wrapper

    return decorator


class PerformanceContext:
    """
    성능 측정 컨텍스트 매니저

    Usage:
        async with PerformanceContext("evaluation") as ctx:
            # FDS 평가 수행
            ...
        print(f"평가 시간: {ctx.elapsed_ms}ms")
    """

    def __init__(self, name: str, track_to_monitor: bool = True):
        self.name = name
        self.track_to_monitor = track_to_monitor
        self.start_time = None
        self.elapsed_ms = None
        self.breakdown: Dict[str, float] = {}

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.elapsed_ms = (time.time() - self.start_time) * 1000

        if self.track_to_monitor:
            monitor = get_performance_monitor()
            monitor.track_evaluation(
                self.elapsed_ms, transaction_id=None, breakdown=self.breakdown
            )

        logger.debug(f"{self.name} 완료: {self.elapsed_ms:.2f}ms")

    def add_breakdown(self, component: str, time_ms: float):
        """세부 시간 추가"""
        self.breakdown[component] = time_ms
