"""
Prometheus 메트릭 미들웨어

FastAPI 애플리케이션에 Prometheus 메트릭 수집을 자동으로 적용합니다.

기능:
- HTTP 요청/응답 자동 추적
- /metrics 엔드포인트 자동 등록
- 요청 처리 시간, 상태 코드, 엔드포인트별 메트릭
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
from typing import Callable

from src.utils.prometheus_metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_progress,
    errors_total,
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Prometheus 메트릭을 수집하는 FastAPI 미들웨어

    모든 HTTP 요청에 대해:
    - 요청 수 카운트 (메서드, 엔드포인트, 상태 코드별)
    - 요청 처리 시간 측정
    - 동시 처리 중인 요청 수 추적
    - 에러 발생 추적
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # /metrics 엔드포인트는 메트릭 수집에서 제외
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = request.url.path

        # 경로 템플릿 추출 (동적 경로 파라미터 처리)
        endpoint = self._get_endpoint_template(request)

        # 진행 중인 요청 증가
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        start_time = time.time()
        status_code = 500  # 기본값 (에러 발생 시)

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response

        except Exception as e:
            # 예외 발생 시 에러 메트릭 기록
            errors_total.labels(
                error_type=type(e).__name__, severity="critical"
            ).inc()
            raise

        finally:
            # 요청 처리 완료 후 메트릭 기록
            duration = time.time() - start_time

            # 요청 수 카운트
            http_requests_total.labels(
                method=method, endpoint=endpoint, status_code=status_code
            ).inc()

            # 요청 처리 시간 기록
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
                duration
            )

            # 진행 중인 요청 감소
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()

            # 에러 상태 코드 추적
            if status_code >= 400:
                severity = "warning" if status_code < 500 else "error"
                error_type = f"http_{status_code}"
                errors_total.labels(error_type=error_type, severity=severity).inc()

    def _get_endpoint_template(self, request: Request) -> str:
        """
        FastAPI 라우트 템플릿 추출

        예: /v1/products/123 -> /v1/products/{id}
        예: /v1/orders -> /v1/orders
        """
        # FastAPI의 route 정보에서 경로 템플릿 추출
        if hasattr(request, "scope") and "route" in request.scope:
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path

        # 템플릿 정보를 찾을 수 없는 경우 실제 경로 반환
        return request.url.path

    @staticmethod
    def _normalize_path(path: str) -> str:
        """
        경로 정규화 (선택적 사용)

        UUID, 숫자 등을 일반화하여 카디널리티 감소
        예: /v1/products/123 -> /v1/products/{id}
        예: /v1/orders/550e8400-e29b-41d4-a716-446655440000 -> /v1/orders/{id}
        """
        import re

        # UUID 패턴 치환
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/{id}",
            path,
            flags=re.IGNORECASE,
        )

        # 숫자 ID 패턴 치환
        path = re.sub(r"/\d+", "/{id}", path)

        return path
