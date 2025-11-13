# 구현 계획: AI/ML 기반 이커머스 FDS 플랫폼

**Branch**: `001-ecommerce-fds-platform` | **Date**: 2025-11-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-ecommerce-fds-platform/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## 요약

본 프로젝트는 실제 운영 가능한 이커머스 플랫폼을 구축하고, 이를 기반으로 AI/ML 기반 FDS(Fraud Detection System)를 통합하여 사기 거래를 실시간으로 탐지하고 대응하는 종합 보안 솔루션을 개발합니다.

**Phase 1**에서는 회원가입/로그인, 상품 카탈로그, 장바구니, 주문/결제 프로세스, 주문 추적 등 핵심 이커머스 기능과 관리자 기능을 구현하며, 모든 사용자 행동 로그와 거래 데이터를 체계적으로 수집합니다.

**Phase 2**에서는 실시간 위험 평가 엔진(100ms 이내), 다층 탐지 시스템(룰 기반 + ML 기반 + CTI 연동), 위험도에 따른 자동 대응 메커니즘(추가 인증/거래 보류/자동 차단), 보안팀 운영 대시보드를 구현합니다.

## Technical Context

**Language/Version**: NEEDS CLARIFICATION (Python 3.11+ 또는 Node.js 18+ 권장)
**Primary Dependencies**: NEEDS CLARIFICATION
- Backend Framework: FastAPI/Django (Python) 또는 Express/NestJS (Node.js)
- ML Framework: scikit-learn, TensorFlow/PyTorch (이상 탐지 모델)
- Frontend Framework: React/Vue/Next.js
**Storage**: NEEDS CLARIFICATION
- 관계형 DB: PostgreSQL (거래, 사용자, 상품 데이터)
- NoSQL/캐시: Redis (세션, 실시간 위험 점수 캐싱)
- 시계열 DB: InfluxDB 또는 TimescaleDB (행동 로그, 시계열 분석)
**Testing**: NEEDS CLARIFICATION
- Python: pytest, pytest-asyncio
- Node.js: Jest, Supertest
- Integration: Postman/Newman, Playwright
**Target Platform**: 클라우드 환경 (AWS/GCP/Azure), Linux 서버, 웹 브라우저 (반응형)
**Project Type**: Web (Frontend + Backend + ML Service)
**Performance Goals**:
- 위험 평가: 100ms 이내 (P95)
- 거래 처리: 1,000 TPS (초당 거래)
- API 응답: <200ms (일반 조회), <500ms (복잡한 분석)
**Constraints**:
- FDS 평가 지연이 사용자 경험에 영향을 주지 않아야 함 (비동기 처리)
- PCI-DSS 준수 (결제 정보 토큰화)
- 개인정보보호법 준수 (데이터 암호화, 접근 로그)
**Scale/Scope**:
- 초기: 일일 거래 1만 건 이하
- 확장 목표: 초당 1,000건 처리
- 사용자: 수만~수십만 명 규모

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**참고**: Constitution 파일이 아직 템플릿 상태입니다. 이 프로젝트의 특성에 맞는 원칙을 정의해야 합니다.

### 권장 원칙 (프로젝트 진행 전 확정 필요)

1. **마이크로서비스 아키텍처**:
   - 이커머스 플랫폼, FDS 엔진, ML 서비스를 독립적으로 배포 가능하도록 분리
   - 각 서비스는 독립적인 데이터베이스 보유
   - API Gateway를 통한 통합

2. **테스트 우선 개발 (TDD)**:
   - 모든 핵심 비즈니스 로직은 테스트 작성 후 구현
   - 유닛 테스트 커버리지 80% 이상
   - 통합 테스트 필수: 결제 플로우, FDS 평가 플로우

3. **보안 우선**:
   - 모든 결제 정보는 토큰화하여 저장
   - 비밀번호는 bcrypt 해싱
   - API 엔드포인트는 인증/인가 필수
   - 민감 데이터 로그 금지

4. **성능 모니터링**:
   - 모든 FDS 평가는 처리 시간 로깅
   - APM(Application Performance Monitoring) 도구 사용
   - 실시간 알림 시스템 구축

5. **데이터 품질**:
   - 모든 거래 데이터는 ML 학습에 활용 가능한 형태로 저장
   - 데이터 스키마 버전 관리
   - 데이터 마이그레이션 전략 수립

**GATE 상태**: ⚠️ PENDING - Constitution 확정 후 재평가 필요

---

### Phase 1 완료 후 재검토 (2025-11-13)

**Phase 1 산출물**:
- ✅ research.md: 기술 스택 결정 완료 (Python/FastAPI, React, PostgreSQL, Redis, scikit-learn)
- ✅ data-model.md: 15개 엔티티 정의 완료
- ✅ contracts/openapi.yaml: REST API 계약 완료
- ✅ contracts/fds-contract.md: FDS 내부 통신 계약 완료
- ✅ quickstart.md: 개발 환경 구축 가이드 완료
- ✅ CLAUDE.md: 에이전트 컨텍스트 업데이트 완료

**재검토 결과**:

1. **마이크로서비스 아키텍처**: ✅ PASS
   - 4개 독립 서비스 (이커머스, FDS, ML, 관리자 대시보드) 설계 완료
   - 각 서비스별 독립 데이터베이스 전략 수립
   - API Gateway 통합 계획 수립

2. **테스트 우선 개발**: ✅ PASS
   - pytest, Playwright 기반 테스트 전략 수립
   - 유닛/통합/E2E 테스트 디렉토리 구조 정의
   - FDS 성능 테스트 (100ms 목표) 명시

3. **보안 우선**: ✅ PASS
   - PCI-DSS 준수: 결제 정보 토큰화 전략 수립
   - 비밀번호 bcrypt 해싱, JWT 인증 설계
   - 민감 데이터 로그 금지 정책 명시

4. **성능 모니터링**: ✅ PASS
   - Prometheus + Grafana 모니터링 스택 선정
   - FDS 평가 시간 메트릭 수집 계획
   - 알림 조건 및 심각도 정의 (fds-contract.md)

5. **데이터 품질**: ✅ PASS
   - UserBehaviorLog를 TimescaleDB로 시계열 저장
   - FraudCase 테이블로 ML 학습 데이터 관리
   - 데이터 보존 정책 3년 수립

**다음 단계**: Constitution 파일 정식 작성 권장

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# 마이크로서비스 아키텍처 기반 구조

services/
├── ecommerce/                # 이커머스 플랫폼 서비스
│   ├── backend/
│   │   ├── src/
│   │   │   ├── models/      # User, Product, Cart, Order, Payment
│   │   │   ├── services/    # 비즈니스 로직 (주문 처리, 재고 관리)
│   │   │   ├── api/         # REST API 엔드포인트
│   │   │   ├── middleware/  # 인증, 로깅
│   │   │   └── utils/
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   ├── integration/
│   │   │   └── e2e/
│   │   └── requirements.txt (Python) 또는 package.json (Node.js)
│   └── frontend/
│       ├── src/
│       │   ├── components/  # 상품 카드, 장바구니, 주문 폼
│       │   ├── pages/       # 홈, 상품 목록, 주문, 마이페이지
│       │   ├── services/    # API 호출 레이어
│       │   ├── store/       # 상태 관리 (Redux/Zustand)
│       │   └── utils/
│       └── tests/
│
├── fds/                      # FDS 위험 평가 서비스
│   ├── src/
│   │   ├── models/          # Transaction, RiskFactor, DetectionRule
│   │   ├── engines/
│   │   │   ├── rule_engine.py    # 룰 기반 탐지
│   │   │   ├── ml_engine.py      # ML 기반 이상 탐지
│   │   │   └── cti_connector.py  # CTI 연동
│   │   ├── api/             # FDS API 엔드포인트
│   │   ├── services/        # 위험 평가, 대응 로직
│   │   └── utils/
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── performance/     # 100ms 목표 성능 테스트
│   └── requirements.txt
│
├── ml-service/               # ML 모델 학습/배포 서비스
│   ├── src/
│   │   ├── models/          # MLModel 메타데이터
│   │   ├── training/        # 모델 학습 파이프라인
│   │   ├── evaluation/      # 모델 성능 평가
│   │   ├── deployment/      # 모델 배포 (카나리, 롤백)
│   │   └── data/
│   │       ├── preprocessing.py
│   │       └── feature_engineering.py
│   ├── notebooks/           # 탐색적 분석
│   ├── tests/
│   └── requirements.txt
│
├── admin-dashboard/          # 보안팀/관리자 대시보드
│   ├── backend/
│   │   ├── src/
│   │   │   ├── api/         # 대시보드 API
│   │   │   ├── services/    # 통계, 검토 큐 관리
│   │   │   └── auth/        # 관리자 권한 관리
│   │   └── tests/
│   └── frontend/
│       ├── src/
│       │   ├── components/  # 실시간 차트, 알림, 검토 인터페이스
│       │   ├── pages/       # 대시보드, 룰 관리, 검토 큐
│       │   └── services/
│       └── tests/
│
└── shared/                   # 공통 라이브러리
    ├── schemas/             # 공통 데이터 스키마
    ├── utils/               # 공통 유틸리티
    └── constants/           # 공통 상수 (위험 점수 임계값 등)

infrastructure/
├── docker/                  # 각 서비스별 Dockerfile
├── k8s/                     # Kubernetes 배포 매니페스트
├── nginx/                   # API Gateway 설정
└── scripts/                 # 배포, 마이그레이션 스크립트

docs/
├── api/                     # API 문서 (OpenAPI/Swagger)
├── architecture/            # 아키텍처 다이어그램
└── deployment/              # 배포 가이드
```

**Structure Decision**:
- **마이크로서비스 아키텍처** 선택: 이커머스 플랫폼, FDS, ML 서비스를 독립적으로 개발/배포 가능
- 각 서비스는 자체 API와 데이터베이스를 보유하여 느슨한 결합 유지
- 프론트엔드는 이커머스 고객용과 관리자/보안팀용으로 분리
- 공통 라이브러리는 `shared/` 디렉토리에서 관리하여 중복 제거

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
