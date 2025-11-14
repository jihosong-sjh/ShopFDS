# 보안 강화 가이드: ShopFDS

**작성일**: 2025-11-14
**Phase**: 9 - 마무리 및 교차 기능
**태스크**: T131-T133 (보안 강화)

## 개요

ShopFDS 플랫폼의 보안을 강화하기 위해 다음 세 가지 주요 보안 기능을 구현했습니다:

1. **PCI-DSS 준수 검증** (T131): 결제 정보 보호 및 민감 데이터 로그 금지
2. **OWASP Top 10 취약점 점검** (T132): SQL Injection, XSS 등 주요 웹 취약점 방어
3. **Rate Limiting** (T133): API 남용 방지 및 DDoS 공격 완화

---

## 1. PCI-DSS 준수 검증 (T131)

### 개요

PCI-DSS (Payment Card Industry Data Security Standard)는 카드 정보를 처리하는 모든 시스템이 준수해야 하는 보안 표준입니다.

### 구현 위치

- `services/ecommerce/backend/src/utils/pci_dss_compliance.py`
- `services/ecommerce/backend/tests/unit/test_pci_dss_compliance.py`

### 주요 기능

#### 1.1 결제 데이터 검증

```python
from src.utils.pci_dss_compliance import PCIDSSCompliance

# 결제 데이터 검증
payment_data = {
    "card_token": "tok_1A2B3C4D5E6F7G8H9I0J",  # 토큰화된 데이터 (안전)
    "card_last_four": "1111",
    "card_brand": "VISA",
}

result = PCIDSSCompliance.validate_payment_data(payment_data)
# {
#   "compliant": true,
#   "violations": [],
#   "warnings": [],
#   "timestamp": "2025-11-14T10:00:00"
# }
```

#### 1.2 민감 정보 로그 마스킹

```python
from src.utils.pci_dss_compliance import SecureLogger
import logging

# 안전한 로거 사용
logger = logging.getLogger(__name__)
secure_logger = SecureLogger(logger)

# 민감 정보 자동 마스킹
secure_logger.info(
    "Payment processed",
    extra={
        "card_token": "tok_secret",  # ******** 로 마스킹
        "password": "user_password",  # ******** 로 마스킹
        "amount": 50000  # 안전한 필드는 그대로
    }
)
```

#### 1.3 PCI-DSS 준수 리포트 생성

```python
report = PCIDSSCompliance.generate_compliance_report()
print(f"PCI-DSS 버전: {report['pci_dss_version']}")  # 3.2.1
print(f"검사 항목: {len(report['compliance_checks'])}")  # 6개

for check in report['compliance_checks']:
    print(f"- {check['requirement']}: {check['status']}")
```

### 테스트 결과

✅ **19개 테스트 통과 (100%)**

- 금지된 카드 데이터 필드 검증
- 토큰화된 데이터 검증
- 민감 정보 패턴 탐지
- 로그 데이터 마스킹
- 준수 리포트 생성

---

## 2. OWASP Top 10 취약점 점검 (T132)

### 개요

OWASP (Open Web Application Security Project) Top 10은 웹 애플리케이션에서 가장 critical한 보안 위험 10가지를 정의합니다.

### 구현 위치

- `services/ecommerce/backend/src/utils/owasp_security.py`
- `services/ecommerce/backend/tests/unit/test_owasp_security.py`

### 주요 기능

#### 2.1 SQL Injection 검사

```python
from src.utils.owasp_security import OWASPSecurityChecker

malicious_input = "admin' OR '1'='1"
result = OWASPSecurityChecker.check_sql_injection(malicious_input)
# {
#   "safe": false,
#   "vulnerability": "SQL Injection",
#   "detected_patterns": ["(\bor\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+)"],
#   "recommendation": "SQLAlchemy ORM 파라미터 바인딩 사용"
# }
```

#### 2.2 XSS (Cross-Site Scripting) 방어

```python
# XSS 검사
xss_input = "<script>alert('XSS')</script>"
result = OWASPSecurityChecker.check_xss(xss_input)
# {
#   "safe": false,
#   "vulnerability": "Cross-Site Scripting (XSS)"
# }

# HTML 이스케이프 처리
safe_html = OWASPSecurityChecker.sanitize_html(xss_input)
# "&lt;script&gt;alert('XSS')&lt;/script&gt;"
```

#### 2.3 CSRF 토큰 생성/검증

```python
# CSRF 토큰 생성
csrf_token = OWASPSecurityChecker.generate_csrf_token()
# "8N4jK2pL9mQ5rT1wX7yA3bC6dE0fH4gI9jK2lM5nO8pQ1rS4tU7vW0x"

# CSRF 토큰 검증
is_valid = OWASPSecurityChecker.validate_csrf_token(user_token, session_token)
```

#### 2.4 SSRF (Server-Side Request Forgery) 방어

```python
# 내부 IP 접근 시도 탐지
malicious_url = "http://localhost:8000/admin"
result = OWASPSecurityChecker.check_ssrf(malicious_url)
# {
#   "safe": false,
#   "vulnerability": "Server-Side Request Forgery (SSRF)",
#   "detected_issue": "내부 호스트 접근 시도: localhost"
# }
```

#### 2.5 종합 보안 검사

```python
# 모든 취약점 자동 검사
test_data = {
    "username": "admin",
    "comment": "<script>alert('xss')</script>",
    "query": "SELECT * FROM users WHERE id=1 OR 1=1",
    "file_path": "../../../etc/passwd",
    "callback_url": "http://localhost:8000/admin",
}

comprehensive_result = OWASPSecurityChecker.comprehensive_security_check(test_data)
# {
#   "overall_safe": false,
#   "checks": [
#     {"field": "comment", "vulnerability": "XSS", ...},
#     {"field": "query", "vulnerability": "SQL Injection", ...},
#     {"field": "file_path", "vulnerability": "Path Traversal", ...},
#     {"field": "callback_url", "vulnerability": "SSRF", ...}
#   ]
# }
```

### 보호하는 OWASP Top 10 항목

| ID | 카테고리 | 상태 | 구현 |
|----|---------|------|------|
| A01:2021 | Broken Access Control | ✅ 구현됨 | RBAC + CSRF 토큰 |
| A02:2021 | Cryptographic Failures | ✅ 구현됨 | bcrypt + 토큰화 + HTTPS |
| A03:2021 | Injection | ✅ 구현됨 | SQLAlchemy ORM + HTML 이스케이프 |
| A04:2021 | Insecure Design | ✅ 구현됨 | FDS 위험 평가 |
| A05:2021 | Security Misconfiguration | ⚠️ 부분 구현 | 환경 변수 관리 |
| A06:2021 | Vulnerable Components | 📋 권장 사항 | 정기 의존성 업데이트 |
| A07:2021 | Auth Failures | ✅ 구현됨 | JWT + OTP + 로그인 제한 |
| A08:2021 | Data Integrity Failures | ⚠️ 부분 구현 | 데이터 검증 + 감사 로그 |
| A09:2021 | Logging Failures | ✅ 구현됨 | 민감 정보 마스킹 + 메트릭 |
| A10:2021 | SSRF | ✅ 구현됨 | 내부 IP 차단 |

### 테스트 결과

✅ **33개 테스트 통과 (100%)**

- SQL Injection 검사 (4개 테스트)
- XSS 검사 (5개 테스트)
- Command Injection 검사 (4개 테스트)
- Path Traversal 검사 (3개 테스트)
- SSRF 검사 (4개 테스트)
- 입력 정제 (2개 테스트)
- CSRF 토큰 (3개 테스트)
- 종합 검사 (5개 테스트)
- 보안 리포트 (3개 테스트)

---

## 3. Rate Limiting (T133)

### 개요

Rate Limiting은 API 남용 방지, DDoS 공격 완화, 서버 자원 보호를 위한 필수 보안 기능입니다.

### 구현 위치

- **FastAPI 레벨**: `services/ecommerce/backend/src/middleware/rate_limiting.py`
- **Nginx 레벨**: `infrastructure/nginx/rate-limiting.conf`
- **테스트**: `services/ecommerce/backend/tests/unit/test_rate_limiting.py`

### 주요 기능

#### 3.1 FastAPI 미들웨어 Rate Limiting

```python
from src.middleware.rate_limiting import RateLimitMiddleware
from fastapi import FastAPI

app = FastAPI()

# Rate Limiting 미들웨어 추가
app.add_middleware(
    RateLimitMiddleware,
    redis_client=redis_client  # Redis 사용 (권장) 또는 None (인메모리)
)
```

**기본 Rate Limit 설정**:

- **일반 API**: 100 요청/분
- **회원가입**: 5 요청/시간
- **로그인**: 10 요청/15분
- **OTP 요청**: 3 요청/5분
- **주문**: 30 요청/분

#### 3.2 응답 헤더

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 2025-11-14T10:01:00Z
```

#### 3.3 Rate Limit 초과 시

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 2025-11-14T10:01:00Z

{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded. Max 100 requests per 60 seconds.",
  "retry_after": 60
}
```

#### 3.4 Nginx Rate Limiting

**설정 파일**: `infrastructure/nginx/rate-limiting.conf`

```nginx
# IP 기반 일반 Rate Limiting
limit_req_zone $binary_remote_addr zone=general:10m rate=100r/m;

# 인증 엔드포인트 Rate Limiting
limit_req_zone $binary_remote_addr zone=auth:10m rate=10r/15m;

# 주문 API Rate Limiting
limit_req_zone $binary_remote_addr zone=orders:10m rate=30r/m;
```

**적용**:

```nginx
location /v1/auth/login {
    limit_req zone=auth burst=5 nodelay;
    limit_conn conn_limit 5;
    limit_req_status 429;

    proxy_pass http://backend:8000;
    # ...
}
```

**Nginx Rate Limit 테스트**:

```bash
# Apache Bench로 테스트
ab -n 100 -c 10 http://api.shopfds.local/v1/products

# wrk로 테스트
wrk -t4 -c100 -d30s http://api.shopfds.local/
```

### 테스트 결과

✅ **14개 테스트 통과 (100%)**

- 제한 내 요청 허용
- Rate Limit 초과 차단
- 시간 창 만료 후 리셋
- 서로 다른 키 독립 처리
- 남은 요청 수 확인
- 메타데이터 검증
- 제외 경로 처리
- X-Forwarded-For 헤더 처리

---

## 통합 사용 예시

### 1. 안전한 결제 처리

```python
from src.utils.pci_dss_compliance import PCIDSSCompliance, SecureLogger
from src.utils.owasp_security import OWASPSecurityChecker
import logging

# 1. PCI-DSS 검증
payment_data = {
    "card_token": "tok_1A2B3C4D5E6F7G8H9I0J",
    "card_last_four": "1111",
}

pci_result = PCIDSSCompliance.validate_payment_data(payment_data)
if not pci_result["compliant"]:
    raise ValueError(f"PCI-DSS 위반: {pci_result['violations']}")

# 2. OWASP 보안 검사 (사용자 입력)
user_input = {
    "shipping_name": request.form["name"],
    "shipping_address": request.form["address"],
}

owasp_result = OWASPSecurityChecker.comprehensive_security_check(user_input)
if not owasp_result["overall_safe"]:
    raise ValueError(f"보안 위협 탐지: {owasp_result['checks']}")

# 3. Rate Limiting은 미들웨어에서 자동 처리

# 4. 안전한 로깅
logger = logging.getLogger(__name__)
secure_logger = SecureLogger(logger)
secure_logger.info(
    "Payment processed successfully",
    extra={"user_id": user.id, "amount": amount}
)
```

### 2. API 엔드포인트 보안

```python
from fastapi import FastAPI, Request, HTTPException
from src.middleware.rate_limiting import RateLimitMiddleware
from src.utils.owasp_security import OWASPSecurityChecker

app = FastAPI()
app.add_middleware(RateLimitMiddleware)

@app.post("/v1/orders")
async def create_order(request: Request, order_data: dict):
    # 1. Rate Limiting (미들웨어에서 자동 처리)

    # 2. CSRF 토큰 검증
    csrf_token = request.headers.get("X-CSRF-Token")
    session_token = request.session.get("csrf_token")

    if not OWASPSecurityChecker.validate_csrf_token(csrf_token, session_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    # 3. 입력 검증
    security_result = OWASPSecurityChecker.comprehensive_security_check(order_data)
    if not security_result["overall_safe"]:
        raise HTTPException(
            status_code=400,
            detail=f"Security check failed: {security_result['checks']}"
        )

    # 4. 안전하게 주문 처리
    order = await create_order_service(order_data)
    return {"order_id": order.id}
```

---

## 모범 사례

### PCI-DSS 준수

1. ✅ **절대 저장하지 말 것**: 카드 번호, CVV, 만료일 원본
2. ✅ **토큰화 필수**: 모든 카드 정보는 결제 게이트웨이에서 토큰 발급
3. ✅ **로그 마스킹**: SecureLogger 사용으로 민감 정보 자동 마스킹
4. ✅ **정기 감사**: PCI-DSS 준수 리포트 분기별 검토

### OWASP Top 10 방어

1. ✅ **입력 검증**: 모든 사용자 입력에 대해 comprehensive_security_check 실행
2. ✅ **출력 인코딩**: sanitize_html로 XSS 방어
3. ✅ **ORM 사용**: SQLAlchemy 파라미터 바인딩으로 SQL Injection 방지
4. ✅ **CSRF 토큰**: 모든 상태 변경 요청에 CSRF 토큰 필수
5. ✅ **HTTPS**: 프로덕션 환경에서 TLS 1.2+ 사용

### Rate Limiting

1. ✅ **계층적 방어**: Nginx (네트워크 레벨) + FastAPI (애플리케이션 레벨)
2. ✅ **엔드포인트별 제한**: 민감한 API는 더 엄격한 제한 적용
3. ✅ **Redis 사용**: 분산 환경에서는 Redis 기반 Rate Limiting 필수
4. ✅ **모니터링**: Rate Limit 초과 로그 수집 및 분석

---

## 프로덕션 배포 체크리스트

### 보안 설정

- [ ] HTTPS 인증서 설치 (Let's Encrypt)
- [ ] 환경 변수 암호화 (Vault, AWS Secrets Manager)
- [ ] PostgreSQL pgcrypto 확장 설치
- [ ] Redis 비밀번호 설정
- [ ] Nginx Rate Limiting 활성화
- [ ] CORS 허용 도메인 설정
- [ ] 보안 헤더 추가 (X-Frame-Options, CSP 등)

### 모니터링

- [ ] Sentry 에러 트래킹 설정
- [ ] Prometheus Rate Limit 메트릭 수집
- [ ] Grafana 대시보드 구성
- [ ] 보안 로그 중앙 집중화 (ELK Stack)

### 정기 검토

- [ ] 분기별: PCI-DSS 준수 리포트 검토
- [ ] 분기별: OWASP 보안 감사
- [ ] 월별: Rate Limit 임계값 조정
- [ ] 주별: 의존성 취약점 스캔 (pip-audit, safety)

---

## 참고 자료

### 공식 문서

- [PCI-DSS v3.2.1](https://www.pcisecuritystandards.org/)
- [OWASP Top 10 2021](https://owasp.org/www-project-top-ten/)
- [Nginx Rate Limiting](https://www.nginx.com/blog/rate-limiting-nginx/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

### 내부 문서

- `services/ecommerce/backend/src/utils/pci_dss_compliance.py`
- `services/ecommerce/backend/src/utils/owasp_security.py`
- `services/ecommerce/backend/src/middleware/rate_limiting.py`
- `infrastructure/nginx/rate-limiting.conf`

### 테스트

```bash
# PCI-DSS 테스트
pytest tests/unit/test_pci_dss_compliance.py -v

# OWASP 테스트
pytest tests/unit/test_owasp_security.py -v

# Rate Limiting 테스트
pytest tests/unit/test_rate_limiting.py -v

# 전체 보안 테스트
pytest tests/unit/test_*security*.py tests/unit/test_*limiting*.py -v
```

---

**작성자**: Claude Code
**버전**: 1.0
**최종 수정**: 2025-11-14
