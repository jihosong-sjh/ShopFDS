# ========================================
# Multi-stage Dockerfile for Ecommerce Frontend
# ========================================

# Stage 1: Builder
FROM node:18-alpine as builder

# 작업 디렉토리 설정
WORKDIR /build

# 패키지 파일 복사
COPY package*.json ./

# 의존성 설치 (빌드에 devDependencies 필요)
RUN npm ci && \
    npm cache clean --force

# 소스 코드 복사
COPY . .

# 환경변수 설정 (빌드 시)
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_FDS_API_URL=http://localhost:8001
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_FDS_API_URL=$VITE_FDS_API_URL

# 프로덕션 빌드
RUN npm run build

# Stage 2: Runtime (Nginx)
FROM nginx:1.25-alpine

# 메타데이터
LABEL maintainer="ShopFDS Team"
LABEL description="Ecommerce Frontend - React + Vite"
LABEL version="1.0.0"

# Nginx 설정 복사
COPY nginx.conf /etc/nginx/nginx.conf
COPY default.conf /etc/nginx/conf.d/default.conf

# 빌드된 정적 파일 복사
COPY --from=builder /build/dist /usr/share/nginx/html

# 비-root 사용자로 실행 (보안)
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

USER nginx

# 포트 노출
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Nginx 실행
CMD ["nginx", "-g", "daemon off;"]
