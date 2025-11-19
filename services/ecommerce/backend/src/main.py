"""
이커머스 플랫폼 FastAPI 메인 애플리케이션

FDS 통합 이커머스 플랫폼의 백엔드 API 서버입니다.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os

from src.models.base import close_db
from src.utils.logging import setup_logging, get_logger
from src.utils.exceptions import (
    AppException,
    ValidationException,
)

# API 라우터
from src.api.auth import router as auth_router
from src.api.products import router as products_router
from src.api.cart import router as cart_router
from src.api.orders import router as orders_router
from src.api.search import router as search_router
from src.api.reviews import router as reviews_router
from src.api.coupons import router as coupons_router
from src.api.oauth import router as oauth_router
from src.api.wishlist import router as wishlist_router
from src.api.recommendations import router as recommendations_router
from src.api.addresses import router as addresses_router
from src.api.push import router as push_router

# Admin API 라우터
from src.api.admin.products import router as admin_products_router
from src.api.admin.orders import router as admin_orders_router
from src.api.admin.users import router as admin_users_router
from src.api.admin.dashboard import router as admin_dashboard_router

# 로깅 설정
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 라이프사이클 관리

    시작 시: 데이터베이스 연결, 캐시 초기화 등
    종료 시: 리소스 정리
    """
    logger.info("🚀 이커머스 플랫폼 서버 시작 중...")

    # TODO: 개발 환경에서만 자동 테이블 생성 (프로덕션에서는 Alembic 사용)
    if os.getenv("ENV") == "development":
        logger.info("데이터베이스 테이블 초기화...")
        # await init_db()  # 주석 처리: Alembic 사용 권장

    logger.info("✅ 서버 시작 완료")
    yield

    logger.info("🛑 이커머스 플랫폼 서버 종료 중...")
    await close_db()
    logger.info("✅ 서버 종료 완료")


# FastAPI 애플리케이션 인스턴스
app = FastAPI(
    title="ShopFDS - 이커머스 플랫폼 API",
    description="""
## FDS 통합 이커머스 플랫폼

AI/ML 기반 실시간 사기 거래 탐지 시스템이 통합된 전자상거래 플랫폼입니다.

### 주요 기능

- [OK] **인증 및 권한 관리**: JWT 기반 인증, OAuth 2.0 소셜 로그인 (Google, Kakao, Naver)
- [OK] **상품 관리**: 상품 조회, 검색, 자동완성, 추천 시스템
- [OK] **리뷰 시스템**: 별점, 사진 리뷰, 도움돼요 투표
- [OK] **장바구니 & 주문**: 실시간 FDS 평가, OTP 추가 인증
- [OK] **쿠폰 시스템**: 할인 쿠폰 발급 및 적용
- [OK] **위시리스트**: 관심 상품 저장 및 관리
- [OK] **배송지 관리**: 다중 배송지, 기본 배송지 설정
- [OK] **푸시 알림**: 주문 상태 변경 알림 (FCM)
- [OK] **관리자 대시보드**: 상품, 주문, 회원, 매출 통계

### 성능 지표

- FDS 평가: P95 100ms 이하
- API 응답: P95 200ms 이하
- 동시 사용자: 10,000 DAU 지원

### 보안

- PCI-DSS 준수 (결제 정보 토큰화)
- OWASP Top 10 대응
- Rate Limiting 적용
- 민감 정보 자동 마스킹

### 기술 스택

- **Backend**: Python 3.11+, FastAPI 0.104+
- **Database**: PostgreSQL 15+, Redis 7+
- **ML**: scikit-learn, LightGBM
- **Monitoring**: Prometheus, Grafana, Sentry
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "ShopFDS Team",
        "email": "support@shopfds.com",
    },
    license_info={
        "name": "MIT License",
    },
    servers=[
        {"url": "http://localhost:8000", "description": "Development server"},
        {"url": "https://api.shopfds.com", "description": "Production server"},
    ],
)


# CORS 미들웨어 설정 (프론트엔드 연동)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 전역 예외 핸들러
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """애플리케이션 정의 예외 처리"""
    logger.warning(
        f"AppException: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "path": request.url.path,
            "method": request.method,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(ValidationException)
async def validation_exception_handler(request: Request, exc: ValidationException):
    """입력 검증 실패 예외 처리"""
    logger.warning(f"ValidationException: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


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
        "service": "이커머스 플랫폼 API",
        "status": "running",
        "version": "1.0.0",
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
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(search_router)
app.include_router(reviews_router)
app.include_router(coupons_router)
app.include_router(oauth_router)
app.include_router(wishlist_router)
app.include_router(recommendations_router)
app.include_router(addresses_router)
app.include_router(push_router)

# Admin 라우터 등록
app.include_router(admin_products_router)
app.include_router(admin_orders_router)
app.include_router(admin_users_router)
app.include_router(admin_dashboard_router)


if __name__ == "__main__":
    # 개발 서버 실행
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENV") == "development",
        log_level="info",
    )
