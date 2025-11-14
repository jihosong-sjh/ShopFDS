"""
관리자 대시보드 FastAPI 메인 애플리케이션

보안팀을 위한 FDS 모니터링 및 검토 대시보드 API 서버입니다.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os

from src.database import close_db
from src.config import settings

# 로깅 설정 (이커머스 백엔드와 동일한 구조)
import logging

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 라이프사이클 관리

    시작 시: 데이터베이스 연결, 캐시 초기화 등
    종료 시: 리소스 정리
    """
    logger.info("관리자 대시보드 서버 시작 중...")

    logger.info("서버 시작 완료")
    yield

    logger.info("관리자 대시보드 서버 종료 중...")
    await close_db()
    logger.info("서버 종료 완료")


# FastAPI 애플리케이션 인스턴스
app = FastAPI(
    title="관리자 대시보드 API",
    description="보안팀을 위한 FDS 모니터링 및 검토 대시보드",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# CORS 미들웨어 설정 (관리자 대시보드 프론트엔드 연동)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 전역 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """모든 예외를 캐치하는 최종 핸들러"""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
        },
    )


# 헬스 체크 엔드포인트
@app.get("/", tags=["Health"])
async def root():
    """루트 엔드포인트"""
    return {
        "service": "관리자 대시보드 API",
        "status": "running",
        "version": "1.0.0",
        "description": "보안팀을 위한 FDS 모니터링 및 검토 대시보드",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """헬스 체크 엔드포인트 (로드 밸런서용)"""
    # TODO: 데이터베이스 연결, Redis 연결 등 상태 체크
    return {
        "status": "healthy",
        "database": "connected",  # TODO: 실제 DB 상태 체크
        "redis": "connected",  # TODO: 실제 Redis 상태 체크
    }


# API 라우터 등록
from src.api.dashboard import router as dashboard_router
from src.api.review import router as review_router
from src.api.transactions import router as transactions_router
from src.api.rules import router as rules_router
from src.api.ab_tests import router as ab_tests_router

app.include_router(dashboard_router)
app.include_router(review_router)
app.include_router(transactions_router)
app.include_router(rules_router)
app.include_router(ab_tests_router)


if __name__ == "__main__":
    # 개발 서버 실행
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )
