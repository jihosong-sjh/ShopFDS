# ========================================
# Nginx API Gateway Dockerfile
# ========================================

FROM nginx:1.25-alpine

# 메타데이터
LABEL maintainer="ShopFDS Team"
LABEL description="Nginx API Gateway for ShopFDS Platform"
LABEL version="1.0.0"

# Nginx 설정 파일 복사
COPY nginx.conf /etc/nginx/nginx.conf
COPY api-gateway.conf /etc/nginx/conf.d/api-gateway.conf
COPY frontend.conf /etc/nginx/conf.d/frontend.conf
COPY rate-limiting.conf /etc/nginx/conf.d/rate-limiting.conf

# SSL 디렉토리 생성
RUN mkdir -p /etc/nginx/ssl && \
    mkdir -p /var/www/certbot

# certbot을 위한 디렉토리 권한 설정
RUN chown -R nginx:nginx /var/www/certbot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/nginx-health || exit 1

# 포트 노출
EXPOSE 80 443

# Nginx 실행
CMD ["nginx", "-g", "daemon off;"]
