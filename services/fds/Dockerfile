# ========================================
# Multi-stage Dockerfile for FDS Service
# ========================================

# Stage 1: Builder
FROM python:3.11-slim as builder

# 작업 디렉토리 설정
WORKDIR /build

# 시스템 의존성 설치 (빌드용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사
COPY requirements.txt .

# Python 패키지 설치 (wheel 생성)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# 메타데이터
LABEL maintainer="ShopFDS Team"
LABEL description="FDS Service - Fraud Detection System"
LABEL version="1.0.0"

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (런타임용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# builder stage에서 설치된 패키지 복사
COPY --from=builder /root/.local /root/.local

# PATH 환경변수에 추가
ENV PATH=/root/.local/bin:$PATH

# 애플리케이션 코드 복사
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# 비-root 사용자 생성 (보안)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# 사용자 전환
USER appuser

# 포트 노출
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 애플리케이션 실행 (Uvicorn)
# FDS는 고성능이 필요하므로 worker 수 조정
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "8"]
