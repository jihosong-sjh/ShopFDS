# Implementation Plan: E2E 테스트 자동화 및 시스템 복원력 검증

**Branch**: \ | **Date**: 2025-11-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from 
**Note**: This template is filled in by the \ command. See \ for the execution workflow.

## Summary

E2E 테스트 자동화 및 시스템 복원력 검증 기능을 구현하여 배포 안정성을 극대화한다. Playwright를 활용한 20개 핵심 사용자 플로우 자동 검증, Istio 기반 카나리 배포(10% → 50% → 100% 점진적 전환), Litmus Chaos를 통한 5가지 장애 시나리오 복원력 테스트, Newman API 통합 테스트, k6 성능 테스트를 통합하여 CI/CD 파이프라인에서 자동 실행한다. 목표: E2E 테스트 100% 통과율, 카나리 배포 자동 롤백 30초 이내, 시스템 장애 복구 30초 이내.

**기술적 접근**:
- **E2E Testing**: Playwright (브라우저 자동화), Docker 격리 환경
- **Canary Deployment**: Istio Service Mesh (트래픽 분할), Flagger (자동 카나리 컨트롤러)
- **Chaos Engineering**: Litmus Chaos (Kubernetes 네이티브 장애 주입)
- **API Testing**: Newman (Postman CLI), Supertest (통합 테스트)
- **Performance Testing**: k6 (부하 테스트), Prometheus/Grafana (모니터링)
- **CI/CD Integration**: GitHub Actions (자동화 파이프라인), ArgoCD (GitOps 배포)

## Technical Context

**Language/Version**: Python 3.11+ (백엔드), TypeScript 5.3+ (E2E 테스트), JavaScript (k6 스크립트)

**Primary Dependencies**:
- E2E: Playwright 1.40+, @playwright/test
- Service Mesh: Istio 1.20+, Flagger 1.35+
- Chaos: Litmus Chaos 3.8+, chaos-mesh (옵션)
- API: Newman 6.0+, Postman Collections, Supertest 6.3+
- Performance: k6 0.48+, Grafana k6 Dashboard
- Monitoring: Prometheus 2.45+, Grafana 10.0+

**Storage**:
- PostgreSQL 15+ (테스트 데이터베이스 - 독립 환경)
- Redis 7+ (캐시 - 테스트 격리)
- Prometheus TSDB (메트릭 저장)
- Elasticsearch (로그 수집 - 옵션)

**Testing**:
- E2E: Playwright Test Runner, Jest (유닛 테스트)
- API: Newman CLI, Supertest
- Performance: k6 run, k6 cloud (옵션)
- Chaos: Litmus Experiment CRDs
- CI: GitHub Actions, Docker Compose (로컬)

**Target Platform**:
- Kubernetes 1.28+ (프로덕션/스테이징)
- Linux x86_64 (CI 러너)
- Docker 24.0+ (로컬 개발)
- 브라우저: Chromium 119+, Firefox 120+, WebKit (Safari 17+)

**Project Type**: 마이크로서비스 웹 애플리케이션 (백엔드 4개 서비스 + 프론트엔드 2개)

**Performance Goals**:
- E2E 테스트: 전체 슈트 실행 시간 10분 이내
- 카나리 배포: 10% → 100% 점진적 전환 시간 30분 이내
- 장애 복구: Pod 종료/네트워크 지연 등 30초 이내 자동 복구
- API 테스트: 전체 컬렉션 실행 5분 이내
- 부하 테스트: Spike Test 1,000 TPS, Soak Test 24시간

**Constraints**:
- E2E 테스트는 Staging 환경에서만 실행 (프로덕션 영향 없음)
- Chaos 실험은 프로덕션에서 수동 승인 후 실행
- 카나리 배포 에러율 임계값: 5% (초과 시 자동 롤백)
- CI 파이프라인 전체 실행 시간: 30분 이내
- 브라우저 호환성: 최신 3개 메이저 버전만 지원 (IE 제외)

**Scale/Scope**:
- E2E 시나리오: 20개 핵심 사용자 플로우
- 크로스 브라우저: 3개 브라우저 x 2개 화면 크기 (데스크톱/모바일)
- API 테스트: 50개 엔드포인트 커버리지
- Chaos 실험: 5가지 장애 유형 (Pod 종료, 네트워크 지연, DB 연결 실패, Redis 다운, 리소스 제한)
- 카나리 배포: 4개 마이크로서비스 (Ecommerce, FDS, ML-Service, Admin-Dashboard)
- 성능 테스트: Spike Test (10배 트래픽), Soak Test (24시간), Stress Test (한계 탐색)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 프로젝트 구성 원칙 준수 검증

**1. 기존 기술 스택 활용** [PASS]
- Python 3.11+ (백엔드): 기존 FastAPI 서비스와 동일
- TypeScript 5.3+: 기존 프론트엔드 테스트 프레임워크 확장
- PostgreSQL 15+, Redis 7+: 기존 데이터베이스/캐시 활용
- Kubernetes: 이미 계획된 오케스트레이션 플랫폼
- Prometheus, Grafana: 기존 모니터링 스택

**2. 마이크로서비스 아키텍처 유지** [PASS]
- 각 서비스의 독립적인 배포 지원 (카나리 배포)
- 서비스 메시(Istio)를 통한 트래픽 관리
- API Gateway(Nginx) 통합 유지
- 서비스 간 계약 테스트 강화 (Newman API 테스트)

**3. 보안 우선 원칙** [PASS]
- E2E 테스트는 격리된 Staging 환경에서 실행
- 테스트 데이터는 실제 사용자 데이터와 완전히 분리
- Chaos 실험은 프로덕션에서 수동 승인 필요
- 민감 정보(결제 정보, 비밀번호)는 테스트 환경에서 마스킹

**4. 성능 목표 준수** [PASS]
- FDS 평가 100ms 이내 목표 유지 (성능 테스트로 검증)
- API 응답 200ms 이내 목표 검증
- 카나리 배포 시 성능 저하 모니터링 (자동 롤백)

**5. 테스트 우선 원칙** [PASS]
- E2E 테스트 자동화로 커버리지 확대
- API 통합 테스트 강화
- 성능 테스트 확장 (Spike, Soak, Stress)
- Chaos Engineering으로 복원력 검증

**6. CI/CD 통합** [PASS]
- GitHub Actions 기존 워크플로우 확장
- 배포 전 자동 E2E 테스트 실행
- 카나리 배포 자동화
- 테스트 실패 시 배포 차단

**새로운 의존성 추가 정당성**:
- **Playwright**: Jest 단위 테스트만으로는 실제 사용자 플로우 검증 불가
- **Istio/Flagger**: Kubernetes 기본 기능만으로는 세밀한 트래픽 분할 불가
- **Litmus Chaos**: 수동 장애 시뮬레이션은 재현성과 자동화 불가
- **Newman/k6**: curl 스크립트만으로는 복잡한 API 시나리오 및 부하 테스트 불가

**잠재적 복잡도 증가**:
- 서비스 메시 도입으로 네트워크 레이어 복잡도 증가 → Istio 표준 패턴으로 완화
- E2E 테스트 유지보수 부담 → Page Object Model로 재사용성 향상
- Chaos 실험 안전성 → Staging 환경 우선, 프로덕션은 수동 승인

## Project Structure

### Documentation (this feature)

```text
specs/005-e2e-testing/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification (completed)
├── research.md          # Phase 0: Technology research
│                        # - Playwright vs Cypress vs Selenium
│                        # - Istio vs Linkerd vs Consul Connect
│                        # - Litmus Chaos vs Chaos Mesh vs Gremlin
│                        # - Newman vs Supertest vs Postman CLI
│                        # - k6 vs JMeter vs Locust
├── data-model.md        # Phase 1: E2E test scenarios, canary config, chaos experiments
│                        # - E2E Test Scenario (시나리오 이름, 단계, 예상 결과, 환경)
│                        # - Canary Deployment Config (서비스, 트래픽 비율, 에러율 임계값)
│                        # - Chaos Experiment (실험 이름, 장애 유형, 대상, 복구 시간)
│                        # - API Test Suite (컬렉션, 테스트 케이스, 검증 조건)
│                        # - Performance Test (테스트 유형, 부하 수준, 목표 지표)
├── quickstart.md        # Phase 1: E2E 테스트 로컬 실행, 카나리 배포 가이드
├── contracts/           # Phase 1: API test contracts
│   ├── postman_collection.json      # Newman API 테스트 컬렉션
│   ├── e2e-test-spec.md             # E2E 테스트 시나리오 명세
│   ├── canary-deployment.yaml       # Flagger Canary CRD 예시
│   └── chaos-experiments.yaml       # Litmus Chaos Experiment CRDs
└── tasks.md             # Phase 2: 구현 작업 목록 (/speckit.tasks)
```

### Source Code (repository root)

```text
# E2E Testing Framework
tests/e2e/                              # Playwright E2E 테스트
├── fixtures/                           # 테스트 데이터 생성
├── pages/                              # Page Object Model
├── scenarios/                          # E2E 테스트 시나리오
├── utils/                              # 테스트 유틸리티
├── playwright.config.ts                # Playwright 설정
└── package.json                        # 의존성 관리

# API Testing
tests/api/                              # Newman/Supertest API 테스트
├── collections/                        # Postman 컬렉션
├── environments/                       # 환경 변수
├── integration/                        # Supertest 통합 테스트
└── run-newman.sh                       # Newman 실행 스크립트

# Performance Testing
tests/performance/                      # k6 부하 테스트
├── scenarios/
├── utils/
├── config/
└── README.md

# Canary Deployment
infrastructure/k8s/canary/              # Istio + Flagger 카나리 배포
├── istio/
├── flagger/
├── monitoring/
└── README.md

# Chaos Engineering
infrastructure/chaos/                   # Litmus Chaos 장애 주입
├── experiments/
├── rbac/
├── workflows/
└── README.md

# CI/CD Integration
.github/workflows/
├── e2e-tests.yml
├── api-tests.yml
├── performance-tests.yml
├── canary-deployment.yml
└── chaos-experiments.yml

# Documentation
docs/
├── e2e-testing/
├── canary-deployment/
├── chaos-engineering/
└── performance-testing/

# Scripts
scripts/
├── setup-istio.sh
├── setup-flagger.sh
├── setup-litmus.sh
├── run-e2e-local.sh
├── run-canary-deployment.sh
└── run-chaos-experiment.sh
```

**Structure Decision**:

기존 마이크로서비스 구조를 유지하면서 독립적인 테스트 계층을 추가:

1. **E2E Testing Layer** (`tests/e2e/`): Playwright 기반 브라우저 자동화 테스트로 실제 사용자 플로우 검증. Page Object Model 패턴으로 유지보수성 향상.

2. **API Testing Layer** (`tests/api/`): Newman(Postman CLI)과 Supertest로 서비스 간 통합 검증. Postman 컬렉션으로 API 계약 문서화.

3. **Performance Testing Layer** (`tests/performance/`): k6 기반 부하 테스트로 Spike/Soak/Stress 시나리오 검증. Prometheus/Grafana 메트릭 연동.

4. **Infrastructure Layer** (`infrastructure/`): 기존 k8s/, docker/ 디렉토리에 `canary/`, `chaos/` 추가. Istio + Flagger로 카나리 배포 자동화, Litmus Chaos로 장애 복원력 검증.

5. **CI/CD Integration**: GitHub Actions 워크플로우 5개 추가 (E2E, API, Performance, Canary, Chaos). 각 테스트는 독립적으로 실행 가능하며, 배포 파이프라인에 통합.

6. **Documentation**: 각 기능별 독립적인 문서화로 개발자/QA/SRE 팀 별 접근성 향상.

이 구조는 기존 프로젝트의 마이크로서비스 아키텍처를 유지하면서, 테스트 자동화와 배포 안정성을 크게 향상시킨다.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

해당 사항 없음. 모든 헌법 검사 항목 통과.

새로운 도구(Playwright, Istio, Litmus Chaos, Newman, k6)는 기존 기술로는 달성할 수 없는 명확한 요구사항을 충족하기 위해 추가되며, 각각의 도입 정당성은 Constitution Check 섹션에서 설명됨.

---

## Phase 1 설계 완료 후 Constitution Check 재평가

*Gate: Phase 1 설계(data-model.md, contracts/, quickstart.md) 완료 후 재검증*

### 설계 아티팩트 검증

**1. 데이터 모델 설계 (data-model.md)** [PASS]
- 6개 핵심 엔티티 정의: E2E Test Scenario, E2E Test Run, Canary Deployment, Chaos Experiment, Performance Test, API Test Suite
- PostgreSQL 기반 스토리지 전략 (기존 스택 활용)
- 명확한 상태 전이 (draft -> active -> archived 등)
- 적절한 데이터 보존 정책 (90-365일)
- 보안: RBAC 권한, Audit Log, 승인 워크플로우

**2. API 계약 (contracts/)** [PASS]
- OpenAPI 3.0 기반 명세서 5개 생성
- RESTful API 설계 원칙 준수
- JWT Bearer 인증 (기존 인증 시스템 활용)
- 에러 처리 표준화 (400, 401, 403, 404, 500)
- Rate Limiting 적용 (100 req/min)
- 총 32개 API 엔드포인트 (E2E 10개, Canary 6개, Chaos 6개, Performance 4개, API 6개)

**3. Quick Start 가이드 (quickstart.md)** [PASS]
- Windows 환경 호환성 확보 (PowerShell 명령어)
- 5분 빠른 시작 가이드 제공
- 단계별 상세 설명 (Playwright, Istio, Litmus Chaos, k6, Newman)
- 트러블슈팅 섹션 포함
- ASCII 문자만 사용 (이모지 없음)

**4. 기술 리서치 (research.md)** [PASS]
- 6개 기술 결정 사항 문서화
- 대안 비교 매트릭스 제공
- 통합 패턴 설명
- 모범 사례 포함
- 예상 성과 지표 (배포 신뢰도 60% -> 95%, 장애 복구 5분 -> 30초)

### 최종 검증 결과

**모든 Constitution Check 항목 통과** [PASS]

1. **기존 기술 스택 활용**: Python, TypeScript, PostgreSQL, Redis, Kubernetes, Prometheus 모두 기존 스택
2. **마이크로서비스 아키텍처**: 서비스 독립성 유지, Istio로 트래픽 관리 강화
3. **보안 우선**: Staging 환경 격리, 프로덕션 Chaos 실험 수동 승인, RBAC 적용
4. **성능 목표**: FDS 100ms, API 200ms 목표 검증 가능
5. **테스트 우선**: E2E/API/성능 테스트 자동화로 커버리지 확대
6. **CI/CD 통합**: GitHub Actions 기존 워크플로우 확장

### 추가 확인 사항

**Windows 환경 호환성** [PASS]
- quickstart.md의 모든 명령어가 PowerShell 호환
- ASCII 문자만 사용 (이모지/특수 유니코드 없음)
- cp949 인코딩 문제 없음

**CI/CD 파이프라인 영향** [PASS]
- 기존 ci.yml 워크플로우 확장
- 새로운 워크플로우 5개 추가 (독립 실행 가능)
- 전체 파이프라인 실행 시간 30분 이내 유지

**복잡도 증가 완화** [PASS]
- Istio: CNCF 졸업 프로젝트, 커뮤니티 지원 강력
- Playwright: Page Object Model로 유지보수성 확보
- Litmus Chaos: Kubernetes 네이티브, CRD 기반 선언적 관리
- Newman/k6: 기존 Postman/Grafana와 통합

**결론**: Phase 1 설계가 모든 프로젝트 원칙을 준수하며, Phase 2 구현 단계로 진행 가능합니다.
