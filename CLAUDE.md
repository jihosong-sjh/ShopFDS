# ShopFDS Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-13

## 프로젝트 개요

AI/ML 기반 이커머스 FDS 플랫폼 - 실시간 사기 거래 탐지 시스템을 통합한 전자상거래 플랫폼

## Active Technologies

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 15+ (SQLAlchemy, Alembic)
- **Cache**: Redis 7+ (aioredis)
- **ML**: scikit-learn, LightGBM
- **Testing**: pytest, pytest-asyncio

### Frontend
- **Framework**: React 18+ with TypeScript 5.3+
- **Build Tool**: Vite 5.0+
- **State Management**: Zustand (global), React Query (API)
- **HTTP Client**: Axios
- **Styling**: Tailwind CSS

### Infrastructure
- **Container**: Docker, Docker Compose
- **Orchestration**: Kubernetes (planned)
- **Gateway**: Nginx
- **Monitoring**: Prometheus, Grafana, Sentry

## Project Structure

```text
services/
├── ecommerce/                # 이커머스 플랫폼 서비스
│   ├── backend/             # FastAPI 백엔드
│   │   ├── src/
│   │   │   ├── models/      # SQLAlchemy 모델
│   │   │   ├── services/    # 비즈니스 로직
│   │   │   ├── api/         # REST API 엔드포인트
│   │   │   └── middleware/  # 인증, 로깅
│   │   └── tests/           # pytest 테스트
│   └── frontend/            # React + TypeScript
│       ├── src/
│       │   ├── components/
│       │   ├── pages/
│       │   └── services/
│       └── tests/
├── fds/                      # FDS 위험 평가 서비스
│   ├── src/
│   │   ├── engines/         # 룰/ML/CTI 엔진
│   │   ├── models/
│   │   └── api/
│   └── tests/
├── ml-service/               # ML 모델 학습/배포
│   ├── src/
│   │   ├── training/
│   │   ├── evaluation/
│   │   └── deployment/
│   └── notebooks/
├── admin-dashboard/          # 보안팀 대시보드
└── shared/                   # 공통 라이브러리

infrastructure/
├── docker/                   # Dockerfile, compose
├── k8s/                      # Kubernetes manifests
└── nginx/                    # API Gateway 설정

specs/001-ecommerce-fds-platform/
├── spec.md                   # 기능 명세서
├── plan.md                   # 구현 계획
├── research.md               # 기술 리서치
├── data-model.md             # 데이터베이스 스키마
├── quickstart.md             # 빠른 시작 가이드
└── contracts/                # API 계약
    ├── openapi.yaml
    └── fds-contract.md
```

## Commands

### 데이터베이스 마이그레이션
```bash
cd services/ecommerce/backend
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

### 개발 서버 실행
```bash
# 백엔드 (이커머스)
cd services/ecommerce/backend
python src/main.py  # http://localhost:8000

# 백엔드 (FDS)
cd services/fds
python src/main.py  # http://localhost:8001

# 프론트엔드
cd services/ecommerce/frontend
npm run dev  # http://localhost:3000
```

### 테스트
```bash
# Python 유닛 테스트
pytest tests/unit -v --cov=src

# Python 통합 테스트
pytest tests/integration -v

# FDS 성능 테스트 (목표: 100ms)
pytest tests/performance -v --benchmark

# TypeScript 테스트
npm test
```

### Docker Compose
```bash
# 전체 서비스 실행
docker-compose up -d

# 특정 서비스만 실행
docker-compose up -d postgres redis

# 로그 확인
docker-compose logs -f ecommerce-backend
```

## Code Style

### Python (Black + Ruff)
```bash
black src/
ruff check src/
```

### TypeScript (Prettier + ESLint)
```bash
npm run lint
npm run format
```

### 네이밍 컨벤션
- **Python**: `snake_case` (함수, 변수), `PascalCase` (클래스)
- **TypeScript**: `camelCase` (함수, 변수), `PascalCase` (컴포넌트, 인터페이스)
- **API 엔드포인트**: `/kebab-case`
- **데이터베이스**: `snake_case`

## 핵심 원칙

1. **보안 우선**: 결제 정보 토큰화, 비밀번호 bcrypt 해싱, 민감 데이터 로그 금지
2. **성능 목표**: FDS 평가 100ms 이내, API 응답 200ms 이내
3. **테스트 우선**: 유닛 테스트 커버리지 80% 이상, 통합 테스트 필수
4. **비동기 처리**: FastAPI async/await 활용, Redis 캐싱
5. **마이크로서비스**: 서비스별 독립 배포, API Gateway 통합

## Testing Guidelines

### Python 통합 테스트 작성 필수 가이드

#### 1. Import 패턴
```python
# CORRECT: src. prefix 사용
from src.models import User, Product, Order
from src.services.order_service import OrderService

# WRONG: src. prefix 없이 사용
from models import User  # ModuleNotFoundError 발생
```

#### 2. Service 메서드 호출
```python
# CORRECT: create_order_from_cart() 사용
order, fds_result = await order_service.create_order_from_cart(
    user_id=test_user.id,  # UUID 객체 직접 사용
    shipping_name="홍길동",
    shipping_address="서울특별시 강남구",
    shipping_phone="010-1234-5678",
    payment_info={  # dict 형식
        "card_number": "1234567890125678",
        "card_expiry": "12/25",
        "card_cvv": "123",
    },
)

# WRONG: 존재하지 않는 메서드 사용
order = await order_service.create_order(...)  # AttributeError
card_token="tok_test",  # 잘못된 파라미터
```

#### 3. UUID 처리
```python
# CORRECT: UUID 객체 직접 사용
user_id=test_user.id,
order_id=order.id

# WRONG: str() 변환 사용
user_id=str(test_user.id),  # AttributeError: 'str' object has no attribute 'hex'
```

#### 4. 외부 서비스 모킹 (필수)
```python
# Redis 모킹 (필수)
mock_redis = AsyncMock()

# FDS, Redis, OTP 모킹 패턴
with patch("src.services.order_service.get_redis", return_value=mock_redis), \
     patch.object(OrderService, "_evaluate_transaction") as mock_fds, \
     patch("src.services.order_service.get_otp_service") as mock_get_otp:

    # FDS 응답 설정
    mock_fds.return_value = {
        "risk_score": 55,
        "risk_level": "medium",
        "decision": "additional_auth_required",
        "requires_verification": True,
        "risk_factors": [],
    }

    # OTP 서비스 설정
    mock_otp_service = AsyncMock()
    mock_otp_service.verify_otp.return_value = {
        "valid": True,
        "message": "OTP 검증 성공",
        "attempts_remaining": 2,
        "metadata": {
            "order_id": str(order.id),  # metadata는 JSON이므로 str 변환
            "user_id": str(test_user.id),
        },
    }
    mock_get_otp.return_value = mock_otp_service
```

#### 5. SQLAlchemy Relationship 로딩
```python
# CORRECT: 명시적 relationship 로딩
await db_session.refresh(order, ["payment"])  # payment relationship 로드
assert order.payment.status == PaymentStatus.COMPLETED

# WRONG: 명시적 로딩 없이 접근
assert order.payment.status  # MissingGreenlet error (async context 문제)
```

#### 6. Windows 콘솔 호환성
```python
# CORRECT: ASCII 문자만 사용
print("테스트 통과 (남은 시도: 2회)")
print("Step 1: 주문 생성 완료")

# WRONG: 특수 Unicode 문자 사용
print("✓ 테스트 통과")  # UnicodeEncodeError (Windows cp949)
print("❌ 실패")
```

#### 7. pytest.ini 설정 확인
```ini
[pytest]
pythonpath = .  # 중요: 프로젝트 루트를 Python path에 추가
testpaths = tests
asyncio_mode = auto
addopts = -v --tb=short --strict-markers --disable-warnings
```

#### 8. Fixture 패턴
```python
# conftest.py의 db_session fixture 활용
@pytest.fixture
async def test_user(self, db_session: AsyncSession):
    user = User(id=uuid.uuid4(), email="test@example.com", ...)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)  # 중요: DB에서 다시 로드
    return user
```

#### 9. 주의사항
- **lazy="dynamic"** 관계는 eager loading 불가 → 제거 필요
- **metadata에 UUID 저장 시**: 반드시 `str(uuid)` 변환 (JSON serialization)
- **메서드 호출 전**: 항상 실제 메서드 시그니처 확인
- **모든 외부 의존성**: Redis, FDS API, OTP 서비스는 반드시 mock 처리

#### 10. 통합 테스트 체크리스트
- [ ] Import 경로에 `src.` prefix 사용
- [ ] UUID를 str() 변환 없이 직접 전달
- [ ] Redis 모킹 추가
- [ ] FDS API `_evaluate_transaction` 모킹
- [ ] OTP 서비스 모킹 (필요시)
- [ ] SQLAlchemy relationship 명시적 로딩
- [ ] Windows 호환 문자만 사용
- [ ] pytest.ini 설정 확인

## Recent Changes

- 2025-11-14 (6): Phase 8: ML 서비스 API 구현 완료 (T121-T123)
  - 모델 학습 트리거 API: 비동기 학습 시작, 상태 추적, 학습 히스토리 조회 (services/ml-service/src/api/training.py)
  - 모델 배포 API: 스테이징/프로덕션 배포, 카나리 배포 관리 (시작/상태/트래픽조정/완료/중단), 롤백 (긴급/특정버전) (services/ml-service/src/api/deployment.py)
  - 모델 평가 API: 모델 비교, 목록 조회, 상세 조회, 성능 지표, 현재 프로덕션 모델 (services/ml-service/src/api/evaluation.py)
  - FastAPI 라우터, Pydantic 모델, 백그라운드 작업 지원
  - 총 17개 REST API 엔드포인트 구현 (POST /v1/ml/train, GET /v1/ml/train/status, GET /v1/ml/models/compare 등)

- 2025-11-14 (5): Phase 8: ML 모델 배포 구현 완료 (T117-T120)
  - 모델 버전 관리 시스템: MLflow 기반 모델 등록, 로드, 승격, 비교 기능 (services/ml-service/src/deployment/version_manager.py)
  - 카나리 배포 로직: 트래픽 분할 (10% → 25% → 50% → 100%), 실시간 성능 모니터링, 자동 권장사항 (services/ml-service/src/deployment/canary_deploy.py)
  - 모델 롤백 시스템: 긴급 롤백, 특정 버전 롤백, 롤백 히스토리 관리 (services/ml-service/src/deployment/rollback.py)
  - FDS ML 엔진 통합: Isolation Forest/LightGBM 지원, 특징 추출, 카나리 라우팅 (services/fds/src/engines/ml_engine.py)
  - MLflow 트래킹 서버 연동, Semantic Versioning, 성능 지표 추적 (Accuracy, Precision, Recall, F1 Score)

- 2025-11-14 (4): Phase 7: 보안팀 프론트엔드 구현 완료 (T105-T107)
  - 룰 관리 페이지: 룰 목록 조회, 필터링, 활성화/비활성화, 생성/수정/삭제 (services/admin-dashboard/frontend/src/pages/RuleManagement.tsx)
  - A/B 테스트 설정 페이지: 테스트 목록, 필터링, 상태 관리 (시작/일시중지/재개/완료), 생성/삭제 (services/admin-dashboard/frontend/src/pages/ABTestSetup.tsx)
  - A/B 테스트 결과 대시보드: 그룹 A/B 성과 지표 비교, 정밀도/재현율/F1 스코어 차트, 평가 시간 비교, 권장 사항 표시 (services/admin-dashboard/frontend/src/pages/ABTestResults.tsx)
  - API 서비스 확장: rulesApi, abTestsApi 추가 (services/admin-dashboard/frontend/src/services/api.ts)
  - React Query + Zustand 기반 상태 관리, Recharts 차트 라이브러리 활용
  - Tailwind CSS 기반 반응형 UI 디자인

- 2025-11-14 (3): Phase 7: A/B 테스트 기능 구현 완료 (T101-T104)
  - ABTest 모델 생성: 그룹 A/B 설정, 트래픽 분할, 성과 지표 집계 (services/fds/src/models/ab_test.py)
  - A/B 테스트 관리 API: POST /v1/ab-tests, GET /v1/ab-tests, PUT /v1/ab-tests/{id}, PATCH /v1/ab-tests/{id}/status (services/admin-dashboard/backend/src/api/ab_tests.py)
  - A/B 테스트 결과 집계 API: GET /v1/ab-tests/{id}/results (정탐률, 오탐률, F1 스코어, 평가 시간 비교)
  - FDS 평가 시 A/B 테스트 그룹 분할 로직: transaction_id 해시 기반 일관된 그룹 할당 (services/fds/src/services/ab_test_service.py)
  - FDS EvaluationEngine에 A/B 테스트 통합: 진행 중인 테스트 자동 탐지 및 결과 기록
  - Admin Dashboard main.py에 A/B 테스트 라우터 등록 완료

- 2025-11-14 (2): Phase 6: 관리자 백엔드 API 구현 완료 (T086-T090)
  - 상품 관리 API: POST, PUT, DELETE /v1/admin/products
  - 재고 관리 API: PATCH /v1/admin/products/{id}/stock
  - 주문 관리 API: GET /v1/admin/orders, GET /v1/admin/orders/{id}, PATCH /v1/admin/orders/{id}/status
  - 회원 관리 API: GET /v1/admin/users, GET /v1/admin/users/{id}, PATCH /v1/admin/users/{id}/status
  - 매출 대시보드 API: GET /v1/admin/dashboard/sales (일별 집계 지원)
  - 모든 Admin API에 RBAC 권한 체크 적용 (Permission.PRODUCT_CREATE, ORDER_READ_ALL 등)
  - FastAPI main.py에 Admin 라우터 등록 완료

- 2025-11-14 (1): Testing Guidelines 추가
  - Python 통합 테스트 작성 필수 가이드 추가
  - Import 패턴, UUID 처리, 모킹 패턴 등 10가지 가이드라인
  - OTP 성공/실패 시나리오 통합 테스트 완료 (10개 테스트 통과)

- 2025-11-13: 프로젝트 초기 설정 완료
  - Phase 0: 기술 스택 리서치 (research.md)
  - Phase 1: 데이터 모델 정의 (data-model.md)
  - Phase 1: API 계약 작성 (contracts/)
  - Phase 1: 빠른 시작 가이드 (quickstart.md)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
