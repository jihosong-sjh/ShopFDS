# Nginx API Gateway 설정

ShopFDS 플랫폼의 Nginx API Gateway 설정입니다.

## 구조

```
nginx/
├── Dockerfile              # Nginx Gateway 이미지 빌드
├── nginx.conf              # 메인 Nginx 설정
├── api-gateway.conf        # API 라우팅 설정
├── frontend.conf           # 프론트엔드 서버 설정
├── rate-limiting.conf      # Rate Limiting 설정
└── README.md               # 이 파일
```

## 기능

### 1. API 라우팅

- **이커머스 백엔드** (`/v1/auth`, `/v1/products`, `/v1/cart`, `/v1/orders`)
- **FDS 서비스** (`/v1/fds`, `/internal/fds`)
- **ML 서비스** (`/v1/ml`)
- **관리자 대시보드** (`/v1/dashboard`, `/v1/review-queue`, `/v1/rules`)

### 2. HTTPS 종료 (TLS Termination)

- TLS 1.2, 1.3 지원
- HTTP -> HTTPS 자동 리디렉션
- HSTS 헤더 추가

### 3. 로드 밸런싱

- Least Connection 알고리즘
- Health Check (자동 failover)
- Keepalive 연결 관리

### 4. 보안

- Rate Limiting (DDoS 방어)
- IP 화이트리스트 (관리자 API)
- 보안 헤더 자동 추가
- 내부 API 접근 제어

### 5. 성능 최적화

- Gzip 압축
- 정적 파일 캐싱
- 커넥션 풀링
- 버퍼 최적화

## 배포

### Docker로 실행

```bash
# Nginx Gateway 이미지 빌드
cd infrastructure/nginx
docker build -t shopfds/nginx-gateway:latest .

# 실행
docker run -d \
  --name nginx-gateway \
  -p 80:80 \
  -p 443:443 \
  -v $(pwd)/ssl:/etc/nginx/ssl:ro \
  shopfds/nginx-gateway:latest
```

### Docker Compose로 실행

```bash
# docker-compose.yml에 포함되어 있음
docker-compose up -d nginx-gateway
```

### Kubernetes로 배포

```bash
# ConfigMap으로 설정 파일 등록
kubectl create configmap nginx-config \
  --from-file=nginx.conf \
  --from-file=api-gateway.conf \
  --from-file=frontend.conf \
  -n shopfds

# Deployment 적용
kubectl apply -f infrastructure/k8s/nginx-gateway.yaml
```

## SSL/TLS 인증서 설정

### Let's Encrypt (권장)

```bash
# Certbot 사용
certbot certonly --webroot \
  -w /var/www/certbot \
  -d shopfds.example.com \
  -d admin.shopfds.example.com \
  -d api.shopfds.example.com

# 인증서 위치
# /etc/letsencrypt/live/shopfds.example.com/fullchain.pem
# /etc/letsencrypt/live/shopfds.example.com/privkey.pem
```

### 자체 서명 인증서 (개발용)

```bash
# SSL 디렉토리 생성
mkdir -p ssl

# 자체 서명 인증서 생성
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/shopfds.example.com.key \
  -out ssl/shopfds.example.com.crt \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=ShopFDS/CN=shopfds.example.com"

# API Gateway용
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/api.shopfds.example.com.key \
  -out ssl/api.shopfds.example.com.crt \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=ShopFDS/CN=api.shopfds.example.com"

# Admin Dashboard용
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/admin.shopfds.example.com.key \
  -out ssl/admin.shopfds.example.com.crt \
  -subj "/C=KR/ST=Seoul/L=Seoul/O=ShopFDS/CN=admin.shopfds.example.com"
```

## 설정 확인

### Nginx 설정 테스트

```bash
# 설정 파일 문법 검사
docker exec nginx-gateway nginx -t

# 또는 로컬에서
nginx -t -c nginx.conf
```

### 설정 리로드

```bash
# Nginx 재시작 없이 설정 리로드
docker exec nginx-gateway nginx -s reload

# 또는
kubectl exec -n shopfds <nginx-pod> -- nginx -s reload
```

## 모니터링

### 로그 확인

```bash
# 액세스 로그
docker logs nginx-gateway -f

# 에러 로그
docker exec nginx-gateway tail -f /var/log/nginx/error.log

# JSON 포맷 로그
docker exec nginx-gateway tail -f /var/log/nginx/access.log | jq .
```

### 메트릭 확인

```bash
# Nginx 상태 확인
curl http://localhost/nginx-health

# Upstream 서버 상태 (nginx-plus 필요)
curl http://localhost/api/upstream
```

## Rate Limiting 설정

현재 설정된 Rate Limit:

- **일반 요청**: 100 req/s
- **인증 요청**: 5 req/s
- **API 요청**: 50 req/s
- **동시 연결**: 50개

수정 방법:

```nginx
# nginx.conf에서
limit_req_zone $binary_remote_addr zone=auth:10m rate=5r/s;  # 5 req/s로 제한

# api-gateway.conf에서
location /v1/auth {
    limit_req zone=auth burst=5 nodelay;  # burst 5개 허용
    proxy_pass http://ecommerce_backend;
}
```

## 로드 밸런싱 알고리즘 변경

```nginx
# Least Connection (기본)
upstream ecommerce_backend {
    least_conn;
    server ecommerce-backend-1:8000;
    server ecommerce-backend-2:8000;
}

# Round Robin
upstream ecommerce_backend {
    server ecommerce-backend-1:8000;
    server ecommerce-backend-2:8000;
}

# IP Hash (세션 유지)
upstream ecommerce_backend {
    ip_hash;
    server ecommerce-backend-1:8000;
    server ecommerce-backend-2:8000;
}

# Weighted Round Robin
upstream ecommerce_backend {
    server ecommerce-backend-1:8000 weight=3;
    server ecommerce-backend-2:8000 weight=1;
}
```

## 캐싱 설정

```nginx
# api-gateway.conf에서
location /v1/products {
    proxy_pass http://ecommerce_backend;

    # 캐시 설정
    proxy_cache_valid 200 10m;
    proxy_cache_key "$scheme$request_method$host$request_uri";
    add_header X-Cache-Status $upstream_cache_status;
}
```

## 트러블슈팅

### 502 Bad Gateway

```bash
# Upstream 서버 연결 확인
docker exec nginx-gateway nc -zv ecommerce-backend-1 8000

# 방화벽 확인
iptables -L -n

# 로그 확인
docker exec nginx-gateway tail -f /var/log/nginx/error.log
```

### 인증서 오류

```bash
# 인증서 유효기간 확인
openssl x509 -in ssl/shopfds.example.com.crt -noout -dates

# 인증서 내용 확인
openssl x509 -in ssl/shopfds.example.com.crt -noout -text
```

### Rate Limiting 조정

```bash
# 현재 Rate Limit 상태 확인 (로그에서)
grep "limiting requests" /var/log/nginx/error.log

# 특정 IP 화이트리스트 추가
# api-gateway.conf에서
geo $limit {
    default 1;
    10.0.0.0/8 0;  # 내부 네트워크는 제한 없음
}

map $limit $limit_key {
    0 "";
    1 $binary_remote_addr;
}

limit_req_zone $limit_key zone=api:10m rate=50r/s;
```

## 보안 권장사항

1. **SSL/TLS 인증서**: Let's Encrypt 사용, 자동 갱신 설정
2. **보안 헤더**: HSTS, CSP 추가
3. **IP 화이트리스트**: 관리자 API는 특정 IP만 허용
4. **Rate Limiting**: DDoS 공격 방어
5. **로그 모니터링**: 실시간 로그 분석 (ELK Stack)

## 참고 자료

- [Nginx 공식 문서](https://nginx.org/en/docs/)
- [Nginx Rate Limiting](https://www.nginx.com/blog/rate-limiting-nginx/)
- [SSL/TLS Best Practices](https://wiki.mozilla.org/Security/Server_Side_TLS)
