# 기술 리서치: AI/ML 기반 이커머스 FDS 플랫폼

**Date**: 2025-11-13
**Purpose**: Technical Context의 NEEDS CLARIFICATION 항목 해결 및 기술 스택 결정

## 1. 백엔드 프레임워크 선택

### 결정: Python + FastAPI

**선택 이유**:
1. **ML 통합 용이성**: Python은 scikit-learn, TensorFlow, PyTorch 등 ML 라이브러리와의 통합이 자연스러움
2. **비동기 처리**: FastAPI는 async/await를 기본 지원하여 FDS 평가를 비동기로 처리 가능 (100ms 목표 달성에 유리)
3. **빠른 개발 속도**: 타입 힌팅 + Pydantic을 통한 자동 검증 및 문서화
4. **성능**: Starlette 기반으로 Node.js와 유사한 성능 제공
5. **생태계**: PostgreSQL(SQLAlchemy), Redis(aioredis), Celery(비동기 작업) 등 풍부한 라이브러리

**대안 고려**:
- **Django**: 관리자 패널이 강력하지만, 비동기 지원이 FastAPI보다 약함. FDS 성능 요구사항에 부적합
- **Node.js + Express/NestJS**: 비동기 처리는 강력하지만, ML 라이브러리 통합이 Python보다 복잡함

**Dependencies**:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1          # DB 마이그레이션
pydantic==2.5.0
python-jose[cryptography]==3.3.0  # JWT 인증
passlib[bcrypt]==1.7.4   # 비밀번호 해싱
aioredis==2.0.1          # Redis 비동기 클라이언트
httpx==0.25.2            # 비동기 HTTP 클라이언트 (결제 게이트웨이, CTI 연동)
celery[redis]==5.3.4     # 백그라운드 작업 (ML 재학습, 이메일 발송)
```

---

## 2. ML 프레임워크 선택

### 결정: scikit-learn (주요) + LightGBM (고급 모델)

**선택 이유**:
1. **scikit-learn**:
   - 전통적인 ML 알고리즘 (Isolation Forest, Random Forest, Logistic Regression) 제공
   - 빠른 프로토타이핑과 학습 가능
   - 추론 속도가 빠름 (100ms 목표 충족 가능)
   - 사기 탐지에서 검증된 알고리즘 보유

2. **LightGBM**:
   - Gradient Boosting 기반으로 정확도가 높음
   - 대규모 데이터셋 학습에 효율적
   - Feature Importance 제공으로 설명 가능한 AI 구현 가능

**대안 고려**:
- **TensorFlow/PyTorch**: 딥러닝 모델은 초기 데이터가 부족할 때 오버피팅 위험. 데이터 축적 후 Phase 3에서 고려
- **XGBoost**: LightGBM과 유사하지만, LightGBM이 학습 속도와 메모리 효율성에서 우수

**ML Pipeline**:
```python
# Phase 1: 룰 기반 + 기본 ML 모델
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

# Phase 2: 고급 모델 (데이터 축적 후)
import lightgbm as lgb
```

**Dependencies**:
```
scikit-learn==1.3.2
lightgbm==4.1.0
pandas==2.1.4
numpy==1.26.2
joblib==1.3.2            # 모델 직렬화
mlflow==2.9.2            # 모델 버전 관리 및 실험 추적
```

---

## 3. 데이터베이스 아키텍처

### 결정: PostgreSQL (주요) + Redis (캐시) + TimescaleDB (시계열)

**PostgreSQL**:
- 용도: 사용자, 상품, 주문, 거래, FDS 룰, 사기 케이스 등 구조화된 데이터
- 선택 이유:
  - ACID 트랜잭션 보장 (결제 데이터 무결성 중요)
  - JSONB 컬럼으로 유연한 스키마 지원 (위험 요인, 행동 로그)
  - 강력한 인덱싱 (B-tree, GIN, GiST) → 빠른 조회 성능
  - 풍부한 확장 기능 (PostGIS for IP geolocation)

**Redis**:
- 용도: 세션 관리, FDS 위험 점수 캐싱, Velocity Check (단시간 내 반복 거래 탐지)
- 선택 이유:
  - 인메모리 DB로 초고속 읽기/쓰기 (< 1ms)
  - Sorted Sets로 시간 기반 데이터 관리 용이
  - TTL 자동 만료로 세션 관리 간편

**TimescaleDB** (PostgreSQL 확장):
- 용도: 사용자 행동 로그, 시계열 위험 점수 추이
- 선택 이유:
  - PostgreSQL 호환으로 별도 학습 불필요
  - 시계열 데이터 압축 및 효율적인 쿼리
  - Continuous Aggregates로 실시간 통계 산출

**대안 고려**:
- **MongoDB**: 스키마리스 장점이 있지만, 트랜잭션 보장이 PostgreSQL보다 약함. 결제 시스템에 부적합
- **InfluxDB**: 순수 시계열 DB지만, TimescaleDB로 통합 가능하여 관리 복잡도 감소

**Dependencies**:
```
psycopg2-binary==2.9.9   # PostgreSQL 드라이버
redis==5.0.1
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0          # 비동기 PostgreSQL 클라이언트
```

---

## 4. 프론트엔드 프레임워크

### 결정: React + TypeScript + Vite

**선택 이유**:
1. **React**: 컴포넌트 재사용성 높음 (상품 카드, 장바구니, 주문 폼 등)
2. **TypeScript**: 타입 안정성으로 API 계약 명확화, 런타임 오류 감소
3. **Vite**: 빠른 개발 서버 시작 및 HMR (Hot Module Replacement)
4. **생태계**: React Query (API 상태 관리), Zustand (전역 상태), Tailwind CSS (빠른 스타일링)

**대안 고려**:
- **Vue.js**: 학습 곡선이 낮지만, 생태계와 채용 시장에서 React가 더 유리
- **Next.js**: SSR이 필요한 경우 유리하지만, 이 프로젝트는 SPA로 충분. 향후 SEO 필요 시 전환 가능

**Dependencies**:
```json
{
  "react": "^18.2.0",
  "typescript": "^5.3.3",
  "vite": "^5.0.8",
  "@tanstack/react-query": "^5.17.0",  // API 상태 관리
  "zustand": "^4.4.7",                  // 전역 상태 (장바구니)
  "react-router-dom": "^6.21.1",        // 라우팅
  "axios": "^1.6.5",                    // HTTP 클라이언트
  "zod": "^3.22.4",                     // 런타임 타입 검증
  "tailwindcss": "^3.4.0"               // 스타일링
}
```

---

## 5. 테스트 프레임워크

### 결정: pytest (Backend) + Playwright (E2E) + Jest (Frontend)

**pytest**:
- 용도: 백엔드 유닛 테스트, 통합 테스트
- 플러그인:
  - `pytest-asyncio`: 비동기 테스트
  - `pytest-cov`: 커버리지 측정
  - `pytest-mock`: 외부 의존성 모킹 (결제 게이트웨이, CTI)

**Playwright**:
- 용도: E2E 테스트 (전체 주문 플로우, FDS 대응 시나리오)
- 선택 이유:
  - Selenium보다 빠르고 안정적
  - 자동 대기, 재시도 메커니즘
  - 브라우저 자동화 (Chromium, Firefox, WebKit)

**Jest**:
- 용도: 프론트엔드 유닛 테스트 (컴포넌트, 유틸 함수)
- React Testing Library와 함께 사용

**Dependencies**:
```
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
httpx==0.25.2            # 테스트용 HTTP 클라이언트
faker==22.0.0            # 테스트 데이터 생성
```

---

## 6. CTI(Cyber Threat Intelligence) 연동

### 결정: AbuseIPDB + 자체 블랙리스트 DB

**AbuseIPDB**:
- 용도: 악성 IP 검증
- API: `https://api.abuseipdb.com/api/v2/check`
- 응답 시간: 평균 30-50ms (타임아웃 50ms 설정)
- 무료 플랜: 일 1,000건 (유료 시 확장 가능)

**자체 블랙리스트**:
- 용도: 과거 사기 IP, 이메일 도메인, 카드 BIN 저장
- PostgreSQL ThreatIntelligence 테이블에 저장
- Redis에 캐싱하여 조회 속도 <1ms 보장

**도난 카드 정보 DB**:
- Ethoca/Verifi 같은 외부 서비스 연동 (Phase 3)
- 초기에는 자체 사기 케이스 DB 활용

**대안 고려**:
- **VirusTotal**: IP 검증 가능하지만, API 비용이 높음
- **IPQualityScore**: 포괄적이지만, 무료 플랜 제한적

---

## 7. 성능 최적화 전략

### FDS 100ms 목표 달성 방안

1. **비동기 처리**:
   ```python
   async def evaluate_risk(transaction):
       # 병렬로 실행
       rule_score, ml_score, cti_check = await asyncio.gather(
           rule_engine.evaluate(transaction),
           ml_engine.predict(transaction),
           cti_connector.check_ip(transaction.ip)
       )
       return combine_scores(rule_score, ml_score, cti_check)
   ```

2. **Redis 캐싱**:
   - ML 모델 예측 결과 캐싱 (동일 패턴 거래 시 재사용)
   - CTI 결과 캐싱 (동일 IP 재조회 방지)

3. **Connection Pooling**:
   - PostgreSQL: `max_connections=50, pool_size=20`
   - Redis: `ConnectionPool` 사용

4. **모델 최적화**:
   - ML 모델 양자화 (ONNX Runtime 사용 시 2-3배 추론 속도 향상)
   - Feature 수 최소화 (30개 이하로 유지)

5. **인덱싱**:
   ```sql
   CREATE INDEX idx_transaction_user_id ON transactions(user_id);
   CREATE INDEX idx_transaction_created_at ON transactions(created_at);
   CREATE INDEX idx_threat_intel_value ON threat_intelligence(value) USING HASH;
   ```

---

## 8. 보안 구현 방안

### PCI-DSS 준수

1. **결제 정보 토큰화**:
   ```python
   # 실제 카드 번호는 결제 게이트웨이에 저장
   payment.card_token = stripe.create_token(card_number)
   payment.last_four = card_number[-4:]  # 마지막 4자리만 저장
   ```

2. **비밀번호 해싱**:
   ```python
   from passlib.context import CryptContext
   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
   user.password_hash = pwd_context.hash(password)
   ```

3. **JWT 인증**:
   ```python
   # Access Token: 15분 만료
   # Refresh Token: 7일 만료, HTTPOnly 쿠키로 전송
   access_token = create_access_token(data={"sub": user.id}, expires_delta=timedelta(minutes=15))
   ```

4. **민감 데이터 로그 금지**:
   ```python
   # 로그에서 자동 마스킹
   logger.info(f"Payment processed: user={user.id}, amount={amount}, card=****{card_last_four}")
   ```

---

## 9. 배포 및 인프라

### 결정: Docker + Kubernetes (GKE/EKS) + Nginx

**Docker**:
- 각 서비스별 Dockerfile 작성
- Multi-stage build로 이미지 크기 최소화

**Kubernetes**:
- 마이크로서비스 오케스트레이션
- HPA (Horizontal Pod Autoscaler)로 자동 스케일링
- Secrets로 환경 변수 관리

**Nginx**:
- API Gateway 역할
- Rate Limiting (DDoS 방지)
- HTTPS 종료

**CI/CD**:
- GitHub Actions: 테스트 자동화, Docker 이미지 빌드
- ArgoCD: GitOps 기반 배포

**Monitoring**:
- Prometheus + Grafana: 메트릭 수집 및 시각화
- ELK Stack: 로그 집계
- Sentry: 에러 트래킹

---

## 10. 최종 기술 스택 요약

| 영역 | 기술 | 버전 |
|------|------|------|
| **Backend** | Python + FastAPI | 3.11+ / 0.104+ |
| **Frontend** | React + TypeScript + Vite | 18.2+ / 5.3+ / 5.0+ |
| **Database** | PostgreSQL + TimescaleDB | 15+ |
| **Cache** | Redis | 7+ |
| **ML** | scikit-learn + LightGBM | 1.3+ / 4.1+ |
| **Testing** | pytest + Playwright + Jest | - |
| **Deployment** | Docker + Kubernetes + Nginx | - |
| **Monitoring** | Prometheus + Grafana + Sentry | - |
| **CTI** | AbuseIPDB + 자체 DB | - |

---

## 11. Phase 1 구현 우선순위

### Week 1-2: 이커머스 플랫폼 기반
1. User 모델 + 인증 API (JWT)
2. Product, Cart 모델 + CRUD API
3. Order, Payment 모델 + 주문 플로우

### Week 3-4: 프론트엔드 기본
1. 회원가입/로그인 페이지
2. 상품 목록/상세 페이지
3. 장바구니, 주문 페이지

### Week 5-6: FDS 기반 (Phase 2 준비)
1. Transaction 모델 + 행동 로그 수집
2. 룰 엔진 기본 구현 (Velocity Check, Amount Threshold)
3. Redis 기반 실시간 카운팅

### Week 7-8: FDS 고도화
1. ML 모델 학습 파이프라인 (Isolation Forest)
2. CTI 연동 (AbuseIPDB)
3. 자동 대응 로직 (위험도별 분기)

### Week 9-10: 관리자 대시보드
1. 보안팀 대시보드 기본 UI
2. 실시간 알림 시스템 (WebSocket)
3. 수동 검토 큐 인터페이스

---

## 다음 단계

✅ Technical Context NEEDS CLARIFICATION 모두 해결 완료
→ 다음: Phase 1 - data-model.md 및 contracts/ 생성
