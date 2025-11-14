"""
Prometheus 메트릭 엔드포인트 - FDS 서비스

/metrics 엔드포인트를 통해 Prometheus가 FDS 메트릭을 수집할 수 있도록 합니다.
"""

from fastapi import APIRouter, Response
from src.utils.prometheus_metrics import get_metrics, get_content_type

router = APIRouter(tags=["Monitoring"])


@router.get("/metrics")
async def metrics():
    """
    Prometheus 메트릭 노출 엔드포인트 (FDS)

    FDS 서비스의 핵심 메트릭:
    - fds_evaluation_duration_seconds: FDS 평가 처리 시간 (목표: P95 < 100ms)
    - fds_evaluations_total: 위험도별 평가 횟수
    - fds_rule_engine_duration_seconds: 룰 엔진 실행 시간
    - fds_ml_engine_duration_seconds: ML 엔진 실행 시간
    - fds_cti_engine_duration_seconds: CTI 엔진 실행 시간
    - fds_sla_violations_total: SLA 위반 횟수 (100ms 초과)
    - fds_precision, fds_recall, fds_f1_score: 탐지 정확도

    **사용법:**
    ```yaml
    # prometheus.yml
    scrape_configs:
      - job_name: 'fds'
        scrape_interval: 15s
        static_configs:
          - targets: ['fds:8001']
    ```
    """
    return Response(content=get_metrics(), media_type=get_content_type())
