"""
Prometheus 메트릭 API 엔드포인트

Prometheus가 스크래핑할 수 있는 메트릭 엔드포인트를 제공합니다.

**엔드포인트**:
- GET /metrics - Prometheus 메트릭 (텍스트 형식)
- GET /v1/fds/metrics/summary - 메트릭 요약 (JSON 형식)
"""

import logging
from fastapi import APIRouter, Response
from ..monitoring.prometheus_metrics import get_metrics_response, registry
from prometheus_client import CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(tags=["Prometheus Metrics"])


@router.get(
    "/metrics",
    summary="Prometheus 메트릭",
    description="""
    Prometheus가 스크래핑할 수 있는 메트릭을 제공합니다.

    **메트릭 카테고리**:
    - FDS 평가 시간 (히스토그램)
    - ML 모델 추론 시간 (히스토그램)
    - 위험 수준별 거래 분포 (카운터)
    - 캐시 히트율 (게이지)
    - API 요청 수 (카운터)
    - 에러 발생 수 (카운터)

    **Prometheus 설정 예시**:
    ```yaml
    scrape_configs:
      - job_name: 'shopfds-fds'
        static_configs:
          - targets: ['localhost:8001']
        metrics_path: '/metrics'
        scrape_interval: 15s
    ```
    """,
)
async def prometheus_metrics() -> Response:
    """
    Prometheus 메트릭 반환

    Returns:
        Response: Prometheus 텍스트 형식 메트릭
    """
    return get_metrics_response()


@router.get(
    "/v1/fds/metrics/summary",
    summary="메트릭 요약 (JSON)",
    description="현재 메트릭 상태를 JSON 형식으로 요약하여 제공합니다.",
)
async def metrics_summary() -> dict:
    """
    메트릭 요약 (JSON 형식)

    Returns:
        dict: 메트릭 요약 정보
    """
    # Prometheus 레지스트리에서 메트릭 수집
    metrics_data = {}

    try:
        # 수집된 메트릭을 순회하며 요약 데이터 생성
        for collector in registry.collect():
            for metric in collector.samples:
                metric_name = metric.name
                labels = metric.labels
                value = metric.value

                if metric_name not in metrics_data:
                    metrics_data[metric_name] = []

                metrics_data[metric_name].append(
                    {
                        "labels": labels,
                        "value": value,
                    }
                )

        return {
            "status": "success",
            "metrics_count": len(metrics_data),
            "metrics": metrics_data,
        }

    except Exception as e:
        logger.error(f"메트릭 요약 실패: {e}")
        return {
            "status": "error",
            "error": str(e),
        }
