"""
Prometheus 메트릭 엔드포인트

/metrics 엔드포인트를 통해 Prometheus가 메트릭을 수집할 수 있도록 합니다.
"""

from fastapi import APIRouter, Response
from src.utils.prometheus_metrics import get_metrics, get_content_type

router = APIRouter(tags=["Monitoring"])


@router.get("/metrics")
async def metrics():
    """
    Prometheus 메트릭 노출 엔드포인트

    이 엔드포인트는 Prometheus 서버가 주기적으로 스크래핑합니다.

    **사용법:**
    ```yaml
    # prometheus.yml
    scrape_configs:
      - job_name: 'ecommerce-backend'
        scrape_interval: 15s
        static_configs:
          - targets: ['ecommerce-backend:8000']
    ```

    **응답 형식:**
    ```
    # HELP ecommerce_http_requests_total 전체 HTTP 요청 수
    # TYPE ecommerce_http_requests_total counter
    ecommerce_http_requests_total{method="GET",endpoint="/v1/products",status_code="200"} 1234.0

    # HELP ecommerce_http_request_duration_seconds HTTP 요청 처리 시간 (초)
    # TYPE ecommerce_http_request_duration_seconds histogram
    ecommerce_http_request_duration_seconds_bucket{method="GET",endpoint="/v1/products",le="0.1"} 1200.0
    ecommerce_http_request_duration_seconds_sum{method="GET",endpoint="/v1/products"} 85.5
    ecommerce_http_request_duration_seconds_count{method="GET",endpoint="/v1/products"} 1234.0
    ```
    """
    return Response(content=get_metrics(), media_type=get_content_type())
