"""
Prometheus 메트릭 미들웨어 - FDS 서비스

FastAPI 애플리케이션에 Prometheus 메트릭 수집을 자동으로 적용합니다.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable

from src.utils.prometheus_metrics import fds_errors_total


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Prometheus 메트릭을 수집하는 FastAPI 미들웨어 (FDS 전용)

    FDS 특화 메트릭은 evaluation_engine에서 직접 기록하므로,
    이 미들웨어는 HTTP 수준의 에러만 추적합니다.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # /metrics 엔드포인트는 메트릭 수집에서 제외
        if request.url.path == "/metrics":
            return await call_next(request)

        try:
            response = await call_next(request)
            return response

        except Exception as e:
            # 예외 발생 시 에러 메트릭 기록
            fds_errors_total.labels(
                error_type=type(e).__name__, severity="critical"
            ).inc()
            raise
