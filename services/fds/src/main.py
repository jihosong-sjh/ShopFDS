"""
FDS 서비스 메인 애플리케이션

실시간 사기 거래 탐지 시스템 (Fraud Detection System)
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# .env 파일 로드
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

from .models import init_db, close_db
from .api.evaluation import router as evaluation_router
from .api.threat import router as threat_router
from .api.device_fingerprint import router as device_fingerprint_router
from .api.behavior_pattern import router as behavior_pattern_router
from .api.blacklist import router as blacklist_router
from .api.network_analysis import router as network_analysis_router
from .api.rules import router as rules_router
from .api.health import router as health_router
from .api.metrics import router as metrics_router

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 생명주기 관리

    시작 시 데이터베이스 초기화, 종료 시 연결 정리
    """
    # 시작 시
    logger.info("FDS 서비스 시작 중...")
    await init_db()
    logger.info("데이터베이스 초기화 완료")

    yield

    # 종료 시
    logger.info("FDS 서비스 종료 중...")
    await close_db()
    logger.info("데이터베이스 연결 종료 완료")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="ShopFDS - Fraud Detection System",
    description="""
    ## AI/ML 기반 이커머스 FDS 플랫폼

    실시간 사기 거래 탐지 시스템

    ### 주요 기능
    - 실시간 거래 위험도 평가 (목표: 100ms 이내)
    - 룰 기반 + ML 기반 하이브리드 탐지
    - CTI(Cyber Threat Intelligence) 연동
    - 자동 차단 및 추가 인증 요구

    ### 위험 수준 분류
    - **Low (0-30점)**: 자동 승인
    - **Medium (40-70점)**: 추가 인증 요구 (OTP, 생체인증)
    - **High (80-100점)**: 자동 차단 + 수동 검토 큐 추가
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 미들웨어 설정 (내부 서비스 간 통신용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],  # 이커머스 서비스
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(evaluation_router)
app.include_router(threat_router)
app.include_router(device_fingerprint_router)
app.include_router(behavior_pattern_router)
app.include_router(blacklist_router)
app.include_router(network_analysis_router)
app.include_router(rules_router)
app.include_router(health_router)
app.include_router(metrics_router)


@app.get("/", tags=["Root"])
async def root():
    """루트 엔드포인트"""
    return {
        "service": "ShopFDS - Fraud Detection System",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8001,  # FDS 서비스는 8001 포트 사용
        reload=True,
        log_level="info",
    )
