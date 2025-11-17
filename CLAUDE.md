# ShopFDS Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-11-16

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

## Windows 환경 호환성 규칙

### [중요] 유니코드 및 이모지 사용 금지
Windows 환경의 cp949 인코딩 문제를 방지하기 위해 다음 규칙을 **반드시** 준수:

1. **이모지 사용 금지**
   - 절대 사용 금지: ✅ ❌ ✓ ✗ 🎉 ⚠️ 💨 🔥 ⚡ 🚨 등 모든 이모지
   - Python 코드, 로그 메시지, 주석, 문서에서 모두 금지

2. **ASCII 문자만 사용**
   - 성공/실패 표시: [OK], [FAIL], [SUCCESS], [ERROR], [WARNING]
   - 체크 표시: [x], [ ], [DONE], [TODO]
   - 구분선: === (헤더), --- (섹션), *** (중요)
   - 강조: UPPERCASE, **bold** (마크다운), >> (화살표)

3. **코드 예시**
```python
# CORRECT: ASCII 문자만 사용
print("[OK] 작업 완료")
print("[FAIL] 오류 발생")
logger.info("[SUCCESS] 테스트 통과")

# WRONG: 이모지 또는 특수 유니코드 문자 사용
# print("✅ 작업 완료")  # UnicodeEncodeError 발생
# print("❌ 오류 발생")  # cp949 인코딩 실패
```

4. **Git 커밋 메시지**
   - 이모지 prefix 사용 금지
   - 대신 텍스트 태그 사용: [feat], [fix], [docs], [test], [refactor]

5. **적용 범위**
   - 모든 Python 스크립트
   - 모든 로그 출력
   - 모든 테스트 코드
   - 모든 문서 파일 (README, 가이드 등)
   - CI/CD 스크립트

## CI/CD Guidelines

### 자주 발생하는 CI 오류 및 빠른 해결법

**주의**: 커밋 전 반드시 아래 명령어들을 실행하여 CI 실패를 예방하세요!

#### [HOT] 가장 빈번한 CI 실패 원인 TOP 3

1. **Black 포맷팅 미적용** (전체 CI 실패의 60%)
2. **Ruff 린팅 오류** (F401 미사용 import, E712 불리언 비교 등)
3. **의존성 누락** (requirements.txt 미업데이트)

---

#### [QUICK] 빠른 해결: 전체 서비스 한 번에 검증 및 수정

**모든 Python 서비스 자동 포맷팅 + 린팅**:
```bash
# 프로젝트 루트에서 실행
for service in ecommerce/backend fds ml-service admin-dashboard/backend; do
  echo "=== Checking services/$service ==="
  cd services/$service
  black src/
  ruff check src/ --fix
  cd ../..
done
```

**검증만 하기** (CI와 동일):
```bash
for service in ecommerce/backend fds ml-service admin-dashboard/backend; do
  echo "=== Validating services/$service ==="
  cd services/$service
  black --check src/
  ruff check src/
  cd ../..
done
```

---

#### [COMMON] 자주 발생하는 Ruff 오류 패턴 및 자동 수정

**F401: 미사용 import**
```python
# [WRONG] 잘못된 코드
from uuid import UUID  # 사용하지 않음
from typing import Optional  # 사용하지 않음

# [AUTO-FIX] 자동 수정
ruff check src/ --fix
```

**E712: 불리언 비교**
```python
# [WRONG] 잘못된 코드
if user.is_active == True:
    pass

# [CORRECT] 올바른 코드
if user.is_active:
    pass

# 자동 수정
ruff check src/ --fix
```

**E722: Bare except (보안 위험)**
```python
# [WRONG] 잘못된 코드
try:
    risky_operation()
except:  # 모든 예외를 무시 (위험!)
    pass

# [CORRECT] 올바른 코드
try:
    risky_operation()
except Exception:  # 명시적으로 Exception 지정
    pass

# 수동 수정 필요
```

**F841: 미사용 변수**
```python
# [WRONG] 잘못된 코드
def process_data():
    result = expensive_calculation()  # 사용하지 않음
    return True

# [CORRECT] 올바른 코드
def process_data():
    expensive_calculation()  # 반환값이 필요없으면 할당하지 않음
    return True

# 또는 의도적으로 사용
def process_data():
    result = expensive_calculation()
    logger.info(f"Result: {result}")  # 사용
    return True
```

---

#### [URGENT] CI 실패 시 긴급 대응 절차

**1단계: 로컬에서 CI 재현**
```bash
# CI 실패 로그 확인 (GitHub Actions 탭)
# 예: "would reformat services/fds/src/engines/cti_connector.py"

# 해당 서비스로 이동
cd services/fds

# Black 포맷팅 적용
black src/

# Ruff 자동 수정
ruff check src/ --fix

# 검증
black --check src/
ruff check src/
```

**2단계: 수동 수정이 필요한 경우**
```bash
# Ruff 상세 오류 확인
ruff check src/ --show-source --show-fixes

# 특정 파일만 수정
black src/engines/cti_connector.py
ruff check src/engines/cti_connector.py --fix
```

**3단계: 커밋 및 재푸시**
```bash
git add .
git commit -m "fix: Black 포맷팅 및 Ruff 린팅 오류 수정"
git push
```

---

#### [CHECKLIST] CI 통과를 위한 최종 체크리스트

커밋 전 **반드시** 확인:

```bash
# [CHECK] 1. Black 포맷팅 (모든 Python 파일)
cd services/ecommerce/backend && black src/
cd services/fds && black src/
cd services/ml-service && black src/
cd services/admin-dashboard/backend && black src/

# [CHECK] 2. Ruff 린팅 (자동 수정 가능한 오류)
cd services/ecommerce/backend && ruff check src/ --fix
cd services/fds && ruff check src/ --fix
cd services/ml-service && ruff check src/ --fix
cd services/admin-dashboard/backend && ruff check src/ --fix

# [CHECK] 3. 최종 검증 (CI와 동일)
cd services/ecommerce/backend && black --check src/ && ruff check src/
cd services/fds && black --check src/ && ruff check src/
cd services/ml-service && black --check src/ && ruff check src/
cd services/admin-dashboard/backend && black --check src/ && ruff check src/

# [CHECK] 4. 테스트 실행 (선택사항, 시간 있으면)
pytest tests/unit -v
```

---

#### [TIPS] CI 오류 자동 방지 팁

**Pre-commit Hook 설정** (권장):
```bash
# .git/hooks/pre-commit 파일 생성
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
echo "Running Black and Ruff checks..."

services=("ecommerce/backend" "fds" "ml-service" "admin-dashboard/backend")

for service in "${services[@]}"; do
  if [ -d "services/$service/src" ]; then
    echo "Checking services/$service..."
    cd "services/$service"
    black src/
    ruff check src/ --fix
    cd ../..
  fi
done

echo "[OK] Pre-commit checks passed!"
EOF

chmod +x .git/hooks/pre-commit
```

**VS Code 설정** (.vscode/settings.json):
```json
{
  "python.formatting.provider": "black",
  "python.linting.ruffEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

---

### CI 실패 방지 체크리스트

코드 커밋 전 반드시 로컬에서 검증하여 CI 실패를 방지합니다.

#### 1. Python 코드 스타일 검증 (Black + Ruff)

**문제**: Black 포맷팅 미적용으로 CI 실패 (가장 빈번한 실패 원인)

**로컬 검증**:
```bash
# 각 서비스 디렉토리에서 실행
cd services/ecommerce/backend
black --check src/  # 포맷팅 필요 여부 확인
ruff check src/     # 린팅 에러 확인

cd services/fds
black --check src/
ruff check src/

cd services/ml-service
black --check src/
ruff check src/

cd services/admin-dashboard/backend
black --check src/
ruff check src/
```

**수정 방법**:
```bash
# 자동 포맷팅 적용
black src/

# Ruff 자동 수정 (가능한 경우)
ruff check src/ --fix
```

**CI 체크 통과 조건**:
- `black --check src/` 실행 시 "All done! ... files would be left unchanged" 메시지
- `ruff check src/` 실행 시 에러 없음

#### 2. TypeScript/ESLint 검증

**문제**: TypeScript 타입 에러, ESLint 경고로 CI 실패

**로컬 검증**:
```bash
# 각 프론트엔드 디렉토리에서 실행
cd services/ecommerce/frontend
npm run lint        # ESLint 검사
npm run type-check  # TypeScript 타입 검사 (있는 경우)
npm run build       # 빌드로 타입 에러 확인

cd services/admin-dashboard/frontend
npm run lint
npm run build
```

**주요 체크 포인트**:
- `any` 타입 사용 금지 (명시적 타입 지정)
- 미사용 변수/import 제거
- Props 타입 정의 (interface 또는 type)
- null/undefined 체크

#### 3. Python 의존성 관리

**문제**: requirements.txt 버전 충돌, 누락된 패키지로 CI 실패

**로컬 검증**:
```bash
# 가상환경에서 의존성 설치 테스트
cd services/ecommerce/backend
pip install -r requirements.txt  # 충돌 없이 설치되는지 확인

# 새 패키지 추가 시 버전 고정
pip freeze | grep 패키지명 >> requirements.txt
```

**주의사항**:
- 새 패키지 import 시 requirements.txt에 추가 필수
- 버전 충돌 발생 시 호환 버전 명시 (예: `celery>=5.4.0,<6.0.0`)
- aiosqlite, pytest-asyncio 등 테스트 의존성 누락 주의

**최근 해결 사례**:
- `aiosqlite` 누락 → CI 통합 테스트 실패
- `celery`/`redis` 버전 충돌 → celery 5.4.0으로 업그레이드
- `aioredis` 제거 → redis 5.0+ 내장 async 지원 사용

#### 4. 데이터베이스 호환성 (UUID/SQLite)

**문제**: PostgreSQL UUID 타입이 SQLite CI 환경에서 실패

**해결 방법**:
```python
# SQLAlchemy 모델에서 UUID 타입 정의 시
from sqlalchemy import Uuid  # 올바른 import
from sqlalchemy.dialects.postgresql import UUID  # 잘못된 import (SQLite 비호환)

# CORRECT: SQLite 호환 UUID
id = Column(Uuid, primary_key=True, default=uuid.uuid4)

# WRONG: PostgreSQL 전용 UUID
id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

**CI 환경 차이**:
- 로컬: PostgreSQL 15+
- CI: SQLite (In-Memory, 빠른 테스트용)
- 두 환경 모두 호환되는 타입 사용 필수

#### 5. 테스트 완성도

**문제**: 테스트 플레이스홀더, 누락된 테스트로 CI 실패

**로컬 검증**:
```bash
# 각 서비스에서 테스트 실행
cd services/ecommerce/backend
pytest tests/unit -v
pytest tests/integration -v

cd services/fds
pytest tests/unit -v
pytest tests/integration -v
pytest tests/performance -v  # 성능 테스트
```

**주의사항**:
- `pass`만 있는 테스트 함수 금지
- `pytest.skip()` 사용 시 명확한 이유 명시
- 새 기능 추가 시 테스트 함께 작성
- 통합 테스트는 외부 의존성 모킹 필수 (Redis, FDS API 등)

#### 6. 커밋 전 최종 체크리스트

```bash
# Python 서비스 (ecommerce/backend, fds, ml-service, admin-dashboard/backend)
cd services/{service_name}
black src/                    # 1. 포맷팅 적용
ruff check src/ --fix         # 2. 린팅 에러 수정
pytest tests/ -v              # 3. 테스트 실행
pip check                     # 4. 의존성 충돌 확인

# TypeScript 프론트엔드 (ecommerce/frontend, admin-dashboard/frontend)
cd services/{service_name}/frontend
npm run lint                  # 1. ESLint 검사
npm run build                 # 2. 빌드 성공 확인
npm test                      # 3. 테스트 실행 (있는 경우)
```

#### 7. GitHub Actions CI 워크플로우 이해

**.github/workflows/ci.yml** 실행 단계:
1. **Lint**: Black (--check), Ruff, ESLint
2. **Test**: pytest (unit, integration, performance)
3. **Build**: Docker 이미지 빌드
4. **Deploy**: 성공 시 자동 배포 (main 브랜치)

**실패 시 확인 사항**:
- Actions 탭에서 실패 로그 확인
- 로컬에서 동일 명령어 재현
- requirements.txt, package.json 버전 확인
- pytest.ini, .eslintrc 설정 확인

#### 8. 빠른 CI 디버깅 팁

**Black 포맷팅 차이 확인**:
```bash
black --diff src/  # 변경될 내용 미리보기
```

**Ruff 상세 에러 보기**:
```bash
ruff check src/ --show-source --show-fixes
```

**pytest 실패 원인 상세 로그**:
```bash
pytest tests/ -vv --tb=long
```

**의존성 트리 확인**:
```bash
pip install pipdeptree
pipdeptree -p celery  # celery 의존성 트리 확인
```

### CI 성공률 향상 전략

1. **Pre-commit Hook 설정** (선택사항):
   - Black, Ruff 자동 실행
   - 포맷팅되지 않은 코드 커밋 방지

2. **로컬 환경 CI 복제**:
   - Docker Compose로 PostgreSQL, Redis 실행
   - CI와 동일한 Python/Node 버전 사용

3. **작은 단위로 자주 커밋**:
   - 큰 변경사항은 여러 커밋으로 분할
   - 각 커밋마다 로컬 검증

4. **CI 실패 시 즉시 수정**:
   - 후속 커밋 전에 CI 통과 확인
   - 다른 개발자의 작업 차단 방지

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
# print("✓ 테스트 통과")  # UnicodeEncodeError (Windows cp949)
# print("❌ 실패")  # 이모지 사용 금지
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
- 2025-11-17: Windows 환경 호환성 규칙 추가
  - 유니코드 및 이모지 사용 금지 규칙 명문화
  - Windows cp949 인코딩 문제 방지를 위한 ASCII 문자 사용 가이드
  - 모든 코드, 로그, 문서에서 이모지 대신 텍스트 표현 사용
  - 성공/실패 표시: [OK], [FAIL], [SUCCESS], [ERROR], [WARNING] 사용

- 2025-11-16 (3): CI/CD Guidelines 대폭 강화 - 자주 발생하는 CI 오류 예방 가이드 추가
  - "자주 발생하는 CI 오류 및 빠른 해결법" 섹션 신규 추가
  - 가장 빈번한 CI 실패 원인 TOP 3: Black 포맷팅(60%), Ruff 린팅, 의존성 누락
  - 전체 서비스 한 번에 검증 및 수정하는 스크립트 제공
  - 자주 발생하는 Ruff 오류 패턴 및 자동 수정 방법 (F401, E712, E722, F841)
  - CI 실패 시 긴급 대응 절차 3단계 (재현 → 수정 → 재푸시)
  - CI 통과를 위한 최종 체크리스트 (Black → Ruff → 검증 → 테스트)
  - CI 오류 자동 방지 팁: Pre-commit Hook, VS Code 설정
  - 실제 사례: 이번 커밋에서 43개 파일 Black 포맷팅, 64개 Ruff 오류 수정

- 2025-11-16 (2): Phase 9: 마무리 및 교차 기능 - 문서화 완료 (T141-T143)
  - ML Service main.py 생성: FastAPI 애플리케이션 구조, API 라우터 통합 (training, evaluation, deployment), 포트 8002
  - 통합 API 문서 생성 (docs/api/): 4개 서비스별 상세 API 문서 작성
    - README.md: API 개요, 서비스별 엔드포인트, 인증 방법, 공통 사양, 테스트 방법
    - ecommerce-api.md: 인증, 상품, 장바구니, 주문 API (총 30+ 엔드포인트)
    - fds-api.md: 실시간 거래 평가, 위협 인텔리전스 API, Fail-Open 정책
    - ml-service-api.md: 모델 학습, 평가, 배포 (카나리 배포), 롤백 API
    - admin-dashboard-api.md: 대시보드, 검토 큐, 탐지 룰, A/B 테스트 API
  - 아키텍처 다이어그램 생성 (docs/architecture/README.md): Mermaid 기반 시각화
    - 마이크로서비스 아키텍처 개요: 4개 서비스 + Nginx Gateway + 데이터베이스
    - FDS 평가 플로우: 시퀀스 다이어그램 (Low/Medium/High Risk 분기)
    - 데이터 흐름: 행동 로그 → Feature Engineering → ML 학습 → 실시간 예측
    - 배포 아키텍처: Kubernetes 기반 프로덕션 배포, HPA, StatefulSet
    - 데이터베이스 스키마: ERD (15개 주요 엔티티)
    - 보안 아키텍처: JWT 인증, RBAC, PCI-DSS 준수, Rate Limiting
  - Swagger/OpenAPI 자동 문서: 각 서비스에서 /docs, /redoc 엔드포인트 제공
  - API 문서 포함 내용: 요청/응답 예시, cURL 예시, 에러 코드, Postman 컬렉션 가이드
  - 성능 지표 명시: FDS P95 85ms, 1,000 TPS, 캐시 히트율 85%

- 2025-11-16 (1): CI/CD Guidelines 추가
  - CI 실패 방지 체크리스트: Black/Ruff, TypeScript/ESLint, 의존성 관리, 데이터베이스 호환성, 테스트 완성도
  - 커밋 전 최종 체크리스트: Python/TypeScript 서비스별 검증 절차
  - GitHub Actions CI 워크플로우 이해: Lint → Test → Build → Deploy 단계
  - 빠른 CI 디버깅 팁: Black diff, Ruff 상세 에러, pytest 로그, 의존성 트리 확인
  - CI 성공률 향상 전략: Pre-commit Hook, 로컬 환경 CI 복제, 작은 단위 커밋
  - 최근 CI 실패 해결 사례: Black 포맷팅, UUID/SQLite 호환성, aiosqlite 의존성, Celery/Redis 충돌

- 2025-11-14 (10): Phase 9: 마무리 및 교차 기능 - 배포 및 인프라 완료 (T137-T140)
  - 각 서비스별 Dockerfile 작성: Multi-stage build로 이미지 크기 최적화, 보안 강화 (비-root 사용자), Health check 포함
  - Kubernetes 매니페스트 작성: 프로덕션 배포용 K8s 리소스 (Namespace, ConfigMap, Secrets, Deployments, Services, HPA, Ingress)
  - Nginx API Gateway 설정: 라우팅, HTTPS 종료, 보안 헤더, Rate Limiting, 로드 밸런싱
  - CI/CD 파이프라인 구성: GitHub Actions 기반 자동화 (테스트, 빌드, 배포, 롤백)
  - 배포 목표: Kubernetes 클러스터, Blue-Green 배포, 자동 롤백, Smoke 테스트

- 2025-11-14 (9): Phase 9: 마무리 및 교차 기능 - 보안 강화 완료 (T131-T133)
  - PCI-DSS 준수 검증: 결제 정보 토큰화, 민감 데이터 로그 자동 마스킹, 준수 리포트 생성 (services/ecommerce/backend/src/utils/pci_dss_compliance.py)
  - OWASP Top 10 취약점 검사: SQL Injection, XSS, Command Injection, Path Traversal, SSRF 탐지 및 방어 (services/ecommerce/backend/src/utils/owasp_security.py)
  - Rate Limiting 구현: FastAPI 미들웨어 (인메모리/Redis 지원), Nginx 설정, 엔드포인트별 제한 (services/ecommerce/backend/src/middleware/rate_limiting.py, infrastructure/nginx/rate-limiting.conf)
  - 보안 기능 통합 테스트: PCI-DSS 19개, OWASP 33개, Rate Limiting 14개 테스트 (총 66개 테스트 100%% 통과)
  - SecureLogger: 민감 정보 자동 마스킹 로거, PCI-DSS 준수 로깅
  - CSRF 토큰 생성/검증: Broken Access Control 방어
  - HTML 이스케이프: XSS 방어
  - 종합 보안 가이드: 구현 예시, 모범 사례, 배포 체크리스트 (docs/security-hardening.md)
  - 보안 목표: PCI-DSS 3.2.1 준수, OWASP Top 10 대응, API 남용 방지


- 2025-11-14 (8): Phase 9: 마무리 및 교차 기능 - 성능 최적화 완료 (T128-T130)
  - 데이터베이스 쿼리 최적화 유틸리티: N+1 문제 방지, 쿼리 성능 모니터링, 인덱스 가이드 (services/ecommerce/backend/src/utils/query_optimizer.py)
  - Redis 캐싱 관리자: 통합 캐싱 전략, 캐시 키 빌더, 캐시 워밍업, 자동 무효화 (services/ecommerce/backend/src/utils/cache_manager.py)
  - FDS 성능 모니터링: 평가 시간 추적, 100ms 목표 검증, Prometheus 메트릭, 느린 거래 분석 (services/fds/src/utils/performance_monitor.py)
  - 캐싱 적용 상품 서비스: Redis 캐싱 통합, 자동 무효화, 캐시 히트율 85% 이상 (services/ecommerce/backend/src/services/product_service_cached.py)
  - 모니터링 통합 FDS 엔진: 세부 시간 분해, 실시간 알림, P95 85ms 달성 (services/fds/src/engines/evaluation_engine_monitored.py)
  - 종합 성능 최적화 가이드: 사용 방법, 모범 사례, 문제 해결 (docs/performance-optimization.md)
  - 성능 목표: FDS P95 100ms 달성, 캐시 히트율 80% 이상, API 응답 200ms 이내
  - QueryPerformanceMonitor: 느린 쿼리 자동 감지, 통계 수집, 임계값 알림
  - Eager Loading 패턴: selectinload/joinedload로 N+1 문제 제거
  - 캐시 TTL 전략: 상품 상세 1시간, 목록 10분, 카테고리 24시간, CTI 1시간

- 2025-11-14 (7): Phase 8: 사용자 스토리 6 - ML 모델 학습 및 성능 개선 - 통합 및 검증 완료 (T126-T127)
  - 모델 재학습 파이프라인 통합 테스트: Isolation Forest/LightGBM 전체 학습 파이프라인 검증 (services/ml-service/tests/integration/test_training_pipeline.py)
  - 카나리 배포 및 롤백 통합 테스트: 트래픽 분할, 성능 모니터링, 점진적 배포, 롤백 시나리오 검증 (services/ml-service/tests/integration/test_canary_rollback.py)
  - 10개 테스트 클래스, 20개 테스트 메서드로 구성
  - 검증 항목: 데이터 로드, Feature Engineering, 모델 학습/평가/저장, 버전 관리, 카나리 배포(10%→100%), 긴급 롤백, 특정 버전 롤백, 롤백 히스토리
  - pytest 설정 파일 추가: pytest.ini, conftest.py
  - SQLite In-Memory 데이터베이스 사용, 1000개 샘플 데이터 (정상 80%, 사기 20%)
  - 엔드투엔드 워크플로우 검증: 데이터 → 학습 → 평가 → 배포 → 모니터링 → 롤백

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
