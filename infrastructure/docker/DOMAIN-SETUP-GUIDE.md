# ShopFDS 도메인 설정 가이드

프로덕션 배포를 위한 도메인 구매 및 설정 완벽 가이드

---

## 목차

1. [도메인 구매 전략](#1-도메인-구매-전략)
2. [도메인 일괄 변경 방법](#2-도메인-일괄-변경-방법)
3. [DNS 설정 가이드](#3-dns-설정-가이드)
4. [수동 변경 방법](#4-수동-변경-방법)
5. [SSL/TLS 인증서 설정](#5-ssltls-인증서-설정)
6. [검증 및 테스트](#6-검증-및-테스트)

---

## 1. 도메인 구매 전략

### 필요한 도메인 개수: **1개만**

예: `myshop.com` 하나만 구매하면 됩니다!

### 서브도메인 구조

하나의 도메인으로 모든 서비스를 분리합니다:

```
myshop.com               ← 메인 쇼핑몰 (고객용 프론트엔드)
api.myshop.com          ← 쇼핑몰 백엔드 API
fds.myshop.com          ← 사기 탐지 시스템 API
ml.myshop.com           ← ML 모델 서비스 API
admin.myshop.com        ← 관리자 대시보드 (직원용 프론트엔드)
admin-api.myshop.com    ← 관리자 대시보드 백엔드 API
```

### 왜 서브도메인을 사용하나요?

- **비용 절감**: 도메인 1개만 구매
- **관리 편의성**: 하나의 도메인으로 통합 관리
- **보안**: 서비스별 독립적인 도메인으로 CORS 제어
- **확장성**: 새 서비스 추가 시 서브도메인만 추가

### 추천 도메인 등록업체

- **국내**: Gabia, Cafe24, Hosting.kr
- **해외**: Namecheap, GoDaddy, Google Domains
- **DNS 관리 추천**: Cloudflare (무료 CDN + DDoS 보호)

---

## 2. 도메인 일괄 변경 방법

### 자동 스크립트 사용 (권장)

도메인 하나만 구매했다면, 스크립트로 한 번에 변경할 수 있습니다!

#### Linux/Mac:

```bash
cd infrastructure/docker

# 도메인 일괄 변경 (예: myshop.com으로)
./update-domain.sh myshop.com

# 확인 메시지가 나오면 'y' 입력
```

#### Windows:

```cmd
cd infrastructure\docker

REM 도메인 일괄 변경 (예: myshop.com으로)
update-domain.bat myshop.com

REM 확인 메시지가 나오면 'y' 입력
```

### 스크립트가 하는 일

1. `.env.production` 파일 백업 생성
2. `shopfds.example.com` → `myshop.com`으로 **8곳** 자동 변경:
   - Line 197: `VITE_API_BASE_URL`
   - Line 198: `VITE_FDS_API_URL`
   - Line 199: `ECOMMERCE_FRONTEND_URL`
   - Line 202: `VITE_ADMIN_API_BASE_URL`
   - Line 203: `VITE_ML_API_URL`
   - Line 204: `ADMIN_FRONTEND_URL`
   - Line 215: `SMTP_FROM`
   - Line 259: `CORS_ORIGINS`
3. 변경 내용 확인 및 백업 파일 생성

---

## 3. DNS 설정 가이드

도메인 구매 후, DNS 레코드를 설정해야 합니다.

### 준비 사항

- **서버 공인 IP 주소** (예: `123.456.789.012`)
- 도메인 등록업체의 DNS 관리 페이지 접속

### DNS A 레코드 추가

도메인 등록업체(GoDaddy, Namecheap, Cloudflare 등)에서 다음과 같이 설정:

| 타입 | 호스트(Host) | 값(Value) | TTL |
|------|-------------|----------|-----|
| A | `@` | `123.456.789.012` | 3600 |
| A | `api` | `123.456.789.012` | 3600 |
| A | `fds` | `123.456.789.012` | 3600 |
| A | `ml` | `123.456.789.012` | 3600 |
| A | `admin` | `123.456.789.012` | 3600 |
| A | `admin-api` | `123.456.789.012` | 3600 |

**참고**: 모두 **동일한 서버 IP**를 가리킵니다. Nginx/Ingress가 도메인별로 라우팅을 처리합니다.

### Cloudflare 사용 시 (권장)

Cloudflare를 사용하면 다음 추가 기능을 무료로 사용할 수 있습니다:

1. **무료 SSL/TLS 인증서** (Let's Encrypt 대신)
2. **CDN** (전 세계 캐싱)
3. **DDoS 보호**
4. **DNS 관리 UI**

#### Cloudflare 설정 절차:

1. Cloudflare 계정 생성 (https://cloudflare.com)
2. 도메인 추가
3. Nameserver를 Cloudflare로 변경 (도메인 등록업체에서)
4. DNS 레코드 추가 (위 표와 동일)
5. SSL/TLS 설정: **Full (Strict)** 모드 선택

---

## 4. 수동 변경 방법

스크립트를 사용하지 않고 직접 수정하고 싶다면:

### 텍스트 에디터로 수정

```bash
# .env.production 파일 열기
cd infrastructure/docker
vi .env.production  # 또는 code .env.production, notepad .env.production
```

### 변경할 8곳 (찾기 & 바꾸기 사용 권장)

**찾기**: `shopfds.example.com`
**바꾸기**: `myshop.com` (실제 구매한 도메인)

#### 수정할 정확한 위치:

```ini
# Line 197
VITE_API_BASE_URL=https://api.myshop.com

# Line 198
VITE_FDS_API_URL=https://fds.myshop.com

# Line 199
ECOMMERCE_FRONTEND_URL=https://myshop.com

# Line 202
VITE_ADMIN_API_BASE_URL=https://admin-api.myshop.com

# Line 203
VITE_ML_API_URL=https://ml.myshop.com

# Line 204
ADMIN_FRONTEND_URL=https://admin.myshop.com

# Line 215
SMTP_FROM=noreply@myshop.com

# Line 259
CORS_ORIGINS=https://myshop.com,https://admin.myshop.com
```

### VS Code에서 일괄 변경

1. `Ctrl+H` (찾기 및 바꾸기)
2. 찾기: `shopfds.example.com`
3. 바꾸기: `myshop.com`
4. `Replace All` 클릭

---

## 5. SSL/TLS 인증서 설정

HTTPS를 위해서는 SSL/TLS 인증서가 필요합니다.

### 옵션 1: Cloudflare (가장 쉬움, 권장)

Cloudflare를 사용하면 **자동으로 무료 SSL 인증서**가 제공됩니다!

1. Cloudflare에 도메인 추가
2. SSL/TLS → **Full (Strict)** 모드 선택
3. 끝! (자동으로 HTTPS 활성화)

### 옵션 2: Let's Encrypt + Certbot

서버에서 직접 인증서 발급:

```bash
# Certbot 설치 (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# 인증서 발급 (도메인별로 실행)
sudo certbot --nginx -d myshop.com
sudo certbot --nginx -d api.myshop.com
sudo certbot --nginx -d fds.myshop.com
sudo certbot --nginx -d ml.myshop.com
sudo certbot --nginx -d admin.myshop.com
sudo certbot --nginx -d admin-api.myshop.com

# 자동 갱신 테스트
sudo certbot renew --dry-run
```

### 옵션 3: Kubernetes + cert-manager

Kubernetes 환경에서는 cert-manager 사용:

```bash
# cert-manager 설치
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# ClusterIssuer 생성 (Let's Encrypt)
kubectl apply -f infrastructure/k8s/cert-issuer.yaml

# Ingress에 자동으로 인증서 발급됨
```

---

## 6. 검증 및 테스트

### DNS 전파 확인

DNS 변경 후 전파까지 최대 24-48시간 소요될 수 있습니다.

```bash
# DNS 전파 확인
nslookup myshop.com
nslookup api.myshop.com

# 또는 온라인 도구 사용
# https://dnschecker.org/
```

### 도메인 접속 테스트

```bash
# HTTP 테스트
curl http://myshop.com
curl http://api.myshop.com/health

# HTTPS 테스트 (SSL 설정 후)
curl https://myshop.com
curl https://api.myshop.com/health
```

### 브라우저에서 확인

1. **메인 쇼핑몰**: https://myshop.com
2. **관리자 대시보드**: https://admin.myshop.com
3. **API Health Check**: https://api.myshop.com/health

### CORS 테스트

브라우저 개발자 도구 (F12) → Console에서 확인:

- CORS 에러가 없어야 정상
- `Access-Control-Allow-Origin` 헤더 확인

---

## 요약: 단계별 체크리스트

### 사전 준비

- [ ] 도메인 1개 구매 (예: myshop.com)
- [ ] 서버 공인 IP 주소 확인

### 도메인 설정

- [ ] `.env.production`에서 도메인 일괄 변경
  - **자동**: `./update-domain.sh myshop.com`
  - **수동**: 8곳 직접 수정
- [ ] DNS A 레코드 6개 추가 (myshop.com, api, fds, ml, admin, admin-api)
- [ ] DNS 전파 확인 (nslookup)

### SSL/TLS 인증서

- [ ] Cloudflare 사용 (자동 SSL) 또는
- [ ] Let's Encrypt + Certbot 또는
- [ ] Kubernetes cert-manager

### 배포 및 테스트

- [ ] Docker 이미지 빌드: `./build-images.sh v1.0.0`
- [ ] 프로덕션 배포: `docker-compose -f docker-compose.prod.yml up -d`
- [ ] Health Check: `curl https://api.myshop.com/health`
- [ ] 브라우저 접속 테스트
- [ ] CORS 에러 없는지 확인

---

## 자주 묻는 질문 (FAQ)

### Q1: 도메인을 여러 개 구매해야 하나요?

**A**: 아니요! 도메인 **1개만** 구매하면 됩니다. 서브도메인은 무료로 무제한 생성 가능합니다.

### Q2: 서브도메인도 따로 돈을 내나요?

**A**: 아니요! 서브도메인은 무료입니다. DNS 설정만 추가하면 됩니다.

### Q3: 로컬 개발 시에는 어떻게 하나요?

**A**: 로컬 개발은 `.env` 파일을 사용하며, `localhost:포트` 형식으로 접속합니다. `.env.production`은 프로덕션 배포 시에만 사용됩니다.

### Q4: Cloudflare를 꼭 사용해야 하나요?

**A**: 선택사항이지만 **강력 권장**합니다. 무료로 SSL, CDN, DDoS 보호를 받을 수 있습니다.

### Q5: 도메인 변경 후 어떻게 되돌리나요?

**A**: 스크립트가 자동으로 백업 파일을 생성합니다 (`.env.production.backup.날짜`). 이 파일을 복원하면 됩니다.

```bash
cp .env.production.backup.20251119_143000 .env.production
```

### Q6: SSL 인증서 비용은 얼마인가요?

**A**: Cloudflare나 Let's Encrypt를 사용하면 **완전 무료**입니다!

---

## 추가 리소스

- [Cloudflare DNS 설정 가이드](https://developers.cloudflare.com/dns/)
- [Let's Encrypt 공식 문서](https://letsencrypt.org/docs/)
- [Nginx 리버스 프록시 설정](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [Kubernetes Ingress 가이드](https://kubernetes.io/docs/concepts/services-networking/ingress/)

---

**마지막 업데이트**: 2025-11-19
**버전**: 1.0.0
