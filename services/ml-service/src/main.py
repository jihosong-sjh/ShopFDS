"""
ML 서비스 메인 애플리케이션

ML 모델 학습, 평가, 배포를 담당하는 API 서버입니다.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import logging

# API 라우터
from src.api.training import router as training_router
from src.api.evaluation import router as evaluation_router
from src.api.deployment import router as deployment_router

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 라이프사이클 관리

    시작 시: MLflow 연결, 모델 레지스트리 초기화
    종료 시: 리소스 정리
    """
    logger.info("ML 서비스 시작 중...")
    logger.info("서버 시작 완료")
    yield
    logger.info("ML 서비스 종료 중...")
    logger.info("서버 종료 완료")


# FastAPI 애플리케이션 인스턴스
app = FastAPI(
    title="ML 서비스 API",
    description="""
    ## ML 모델 학습 및 배포 서비스

    FDS ML 모델의 전체 생명주기를 관리합니다.

    ### 주요 기능
    - **모델 학습**: Isolation Forest, LightGBM 모델 학습
    - **모델 평가**: 성능 지표 측정 및 비교
    - **모델 배포**: 카나리 배포, 버전 관리, 롤백

    ### 워크플로우
    1. 데이터 전처리 및 특징 추출
    2. 모델 학습 (비동기 백그라운드 작업)
    3. 모델 평가 및 성능 비교
    4. 스테이징 환경 배포
    5. 카나리 배포 (10% → 25% → 50% → 100%)
    6. 프로덕션 배포 또는 롤백
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# CORS 미들웨어 설정
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:8000,http://localhost:8001,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
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
        "service": "ML 서비스 API",
        "status": "running",
        "version": "1.0.0",
        "description": "ML 모델 학습, 평가, 배포 서비스",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """헬스 체크 엔드포인트 (로드 밸런서용)"""
    return {
        "status": "healthy",
        "mlflow": "connected",  # TODO: 실제 MLflow 연결 상태 체크
        "database": "connected",  # TODO: 실제 DB 상태 체크
    }


# API 라우터 등록
app.include_router(training_router)
app.include_router(evaluation_router)
app.include_router(deployment_router)


if __name__ == "__main__":
    # 개발 서버 실행
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8002")),
        reload=os.getenv("ENV") == "development",
        log_level="info",
    )
