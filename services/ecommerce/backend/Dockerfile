# ========================================
# Multi-stage Dockerfile for Ecommerce Backend
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

# Python 패키지 설치 (시스템 전역)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# 메타데이터
LABEL maintainer="ShopFDS Team"
LABEL description="Ecommerce Backend Service - FastAPI"
LABEL version="1.0.0"

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (런타임용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# builder stage에서 설치된 패키지 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 애플리케이션 코드 복사
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY celeryconfig.py .

# 비-root 사용자 생성 (보안)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# 사용자 전환
USER appuser

# 포트 노출
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 애플리케이션 실행 (Uvicorn)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
