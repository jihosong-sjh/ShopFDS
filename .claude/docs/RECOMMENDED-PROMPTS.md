# Recommended Prompts for ShopFDS Development

## Overview

이 문서는 ShopFDS 프로젝트에서 `/speckit.implement`와 자동 CI 검증을 효과적으로 사용하는 권장 프롬프트를 제공합니다.

---

## 기본 워크플로우 이해

### 현재 시스템 동작

```
User: /speckit.implement [spec] [tasks]
   ↓
Claude: Execute tasks (코드 생성/수정)
   ↓
Claude: 완료 보고
   ↓
[MANUAL] User or Claude: /test-ci 실행 필요
   ↓
System: CI 검증 수행
   ↓
System: 리포트 생성
```

### 자동화 목표 (향후)

```
User: /speckit.implement [spec] [tasks]
   ↓
Claude: Execute tasks
   ↓
[AUTO] System: /test-ci 자동 실행
   ↓
System: CI 검증 수행
   ↓
Claude: 검증 결과 포함 완료 보고
```

---

## 권장 프롬프트 패턴

### Pattern A: 명시적 테스트 요청 (가장 안전)

**사용 시기**: 중요한 기능 구현, 복잡한 변경사항

**프롬프트**:
```
/speckit.implement 004-frontend-ux-enhancement T001-T010 한국어로 구현해줘.

구현 완료 후 반드시 다음 작업을 수행해줘:

1. 자동 CI 검증 실행
   - 명령어: python .claude/scripts/auto_validate_ci.py --fix-auto
   - 변경된 서비스 자동 감지
   - Black, Ruff 자동 수정 활성화
   - 모든 테스트 실행

2. 검증 결과 리포트
   - 통과한 체크 목록
   - 실패한 체크 상세 내용
   - 수정 제안

3. 실패 시 자동 수정
   - Black 포맷팅 적용
   - Ruff 린팅 자동 수정
   - 재검증

4. 최종 상태 보고
   - 모든 체크 통과 확인
   - 커밋 준비 완료 여부
```

**장점**:
- 모든 단계가 명시적으로 지정됨
- Claude가 각 단계를 순서대로 수행
- 실패 시 자동 복구 포함

**단점**:
- 프롬프트가 길어짐
- 매번 작성해야 함

---

### Pattern B: 두 단계 프롬프트 (권장)

**사용 시기**: 일반적인 구현 작업

**프롬프트 1: 구현**:
```
/speckit.implement 004-frontend-ux-enhancement T001-T010 한국어로 구현해줘
```

**프롬프트 2: 검증** (구현 완료 후):
```
/test-ci
```

또는 한 번에:
```
1. /speckit.implement 004-frontend-ux-enhancement T001-T010 한국어로 구현해줘
2. 구현 완료 후 /test-ci 실행해서 CI 검증해줘
```

**장점**:
- 간결하고 명확
- 각 단계가 명확히 구분됨
- 실패 시 중간에 개입 가능

**단점**:
- 두 번의 프롬프트 필요 (또는 명시적 단계 지정)

---

### Pattern C: Task Agent 자동화 (가장 강력)

**사용 시기**: 복잡한 멀티 서비스 구현, 완전 자동화 원할 때

**프롬프트**:
```
다음 작업을 Task Agent로 수행해줘:

[구현 단계]
1. /speckit.implement 004-frontend-ux-enhancement T001-T010 실행
2. 모든 태스크 완료까지 자율 진행

[검증 단계]
3. 구현 완료 즉시 python .claude/scripts/auto_validate_ci.py --fix-auto 실행
4. 변경된 서비스 자동 감지 및 검증
5. 실패한 체크 자동 수정 시도 (Black, Ruff)
6. 재검증

[리포트 단계]
7. 최종 검증 결과 요약
8. 실패한 체크 및 수동 수정 필요 사항 리스트
9. 커밋 준비 상태 확인

모든 단계를 자동으로 수행하고 최종 결과만 보고해줘.
```

**장점**:
- 완전 자동화
- 한 번의 프롬프트로 모든 작업 완료
- 중간 개입 불필요

**단점**:
- Task Agent 실행 시간이 길어질 수 있음
- 실패 시 디버깅 어려움

---

### Pattern D: 간단한 변경 (빠른 개발)

**사용 시기**: 작은 버그 수정, 단순 변경사항

**프롬프트**:
```
services/ecommerce/frontend/src/components/Navbar.tsx의
로고 크기를 40px로 변경하고, CI 검증까지 해줘.
```

**확장 프롬프트**:
```
services/fds/src/engines/rule_engine.py의
evaluate_rule 함수에 로깅 추가하고,
Black/Ruff 검증 + 유닛 테스트 실행해줘.
```

**장점**:
- 매우 간결
- 빠른 개발 사이클

**단점**:
- 복잡한 작업에는 부적합

---

## 서비스별 권장 프롬프트

### Python 서비스 (Backend, FDS, ML Service)

```
/speckit.implement 004-frontend-ux-enhancement T001-T010 한국어로 구현해줘.

구현 완료 후:
1. Black 포맷팅 적용: black src/
2. Ruff 린팅 수정: ruff check src/ --fix
3. 유닛 테스트: pytest tests/unit -v --cov=src
4. 통합 테스트: pytest tests/integration -v
5. [FDS만] 성능 테스트: pytest tests/performance -v --benchmark-only

자동화 명령어:
python .claude/scripts/validate_python_service.py services/[service_name] -v
```

### TypeScript 서비스 (Frontend)

```
/speckit.implement 004-frontend-ux-enhancement T001-T010 한국어로 구현해줘.

구현 완료 후:
1. 의존성 설치: npm ci
2. ESLint 검사: npm run lint
3. TypeScript 타입 체크: npx tsc --noEmit
4. 유닛 테스트: npm test -- --run --coverage
5. 프로덕션 빌드: npm run build

자동화 명령어:
python .claude/scripts/validate_typescript_service.py services/[service_name]/frontend -v
```

### 멀티 서비스 변경

```
/speckit.implement 004-frontend-ux-enhancement T001-T010 한국어로 구현해줘.

이 작업은 다음 서비스를 변경합니다:
- services/ecommerce/backend (Python)
- services/ecommerce/frontend (TypeScript)
- services/fds (Python)

구현 완료 후 자동으로 모든 서비스 검증:
python .claude/scripts/auto_validate_ci.py --fix-auto -v

각 서비스별 상세 검증 결과를 보고해줘.
```

---

## 실패 처리 프롬프트

### 검증 실패 시

```
CI 검증에서 다음 실패가 발생했어:

[FAIL] services/ecommerce/backend
  - Black formatting: 3 files need formatting
  - Ruff linting: F401 (2 unused imports)
  - Unit tests: 2 tests failed

자동으로 수정 가능한 것들은 수정하고,
수동 수정이 필요한 것들은 상세히 설명해줘.

수정 후 재검증도 자동으로 해줘.
```

### 테스트 실패 시

```
pytest 테스트가 실패했어:

FAILED tests/unit/test_order_service.py::test_create_order_high_risk

실패 원인을 분석하고, 코드를 수정한 다음,
해당 테스트만 재실행해서 통과 확인해줘.

명령어: pytest tests/unit/test_order_service.py::test_create_order_high_risk -v
```

---

## 고급 패턴

### Pattern E: 단계별 검증 (Incremental)

**사용 시기**: 대규모 변경, 리팩토링

**프롬프트**:
```
/speckit.implement 004-frontend-ux-enhancement T001-T010 한국어로 구현해줘.

단, 다음과 같이 단계별로 검증하면서 진행해줘:

Step 1: T001-T003 구현
  -> CI 검증 실행
  -> 통과 확인 후 다음 단계

Step 2: T004-T007 구현
  -> CI 검증 실행
  -> 통과 확인 후 다음 단계

Step 3: T008-T010 구현
  -> 최종 CI 검증 실행
  -> 전체 통과 확인

각 단계마다 검증 결과를 보고해줘.
실패 시 해당 단계에서 멈추고 수정 후 진행해줘.
```

**장점**:
- 문제 조기 발견
- 디버깅 용이
- 안전한 진행

**단점**:
- 시간이 오래 걸림

---

### Pattern F: 특정 서비스만 검증

**프롬프트**:
```
/speckit.implement 004-frontend-ux-enhancement T001-T005 한국어로 구현해줘.

이 작업은 services/ecommerce/frontend만 변경해.

구현 완료 후 해당 서비스만 검증:
python .claude/scripts/validate_typescript_service.py services/ecommerce/frontend

전체 CI 검증은 건너뛰고, 프론트엔드 검증만 수행해줘.
```

---

### Pattern G: 성능 테스트 포함 (FDS)

**프롬프트**:
```
/speckit.implement 005-fds-performance-optimization T001-T010 한국어로 구현해줘.

이 작업은 FDS 성능 최적화야. 구현 완료 후:

1. 일반 검증:
   python .claude/scripts/validate_python_service.py services/fds

2. 성능 벤치마크 (중요):
   cd services/fds
   pytest tests/performance -v --benchmark-only

   목표: P95 < 100ms

3. 성능 개선 확인:
   - Before/After 비교
   - P50, P95, P99 지표 리포트

성능 목표 미달 시 추가 최적화 제안해줘.
```

---

## 프롬프트 템플릿 요약

### 템플릿 1: 기본 (단순 구현)

```
/speckit.implement [SPEC] [TASKS] 한국어로 구현해줘.
구현 완료 후 /test-ci 실행해줘.
```

### 템플릿 2: 자동화 (권장)

```
/speckit.implement [SPEC] [TASKS] 한국어로 구현해줘.

구현 완료 후 자동으로:
python .claude/scripts/auto_validate_ci.py --fix-auto

검증 결과 리포트해줘.
```

### 템플릿 3: 완전 자동화 (Task Agent)

```
Task Agent로 다음 작업 수행:
1. /speckit.implement [SPEC] [TASKS]
2. 자동 CI 검증 (auto_validate_ci.py --fix-auto)
3. 실패 시 자동 수정 재시도
4. 최종 결과 리포트

모든 단계를 자율적으로 수행하고 최종 결과만 보고해줘.
```

### 템플릿 4: 특정 서비스 (빠른 개발)

```
[변경 내용 설명]

영향받는 서비스: services/[SERVICE_NAME]

구현 후 해당 서비스만 검증:
python .claude/scripts/validate_[python|typescript]_service.py services/[SERVICE_NAME]
```

---

## 실전 예시

### 예시 1: 프론트엔드 UX 개선

```
/speckit.implement 004-frontend-ux-enhancement T001-T010 한국어로 구현해줘.

이 작업은 다음을 포함해:
- T001-T003: Navbar 반응형 개선
- T004-T007: 상품 카드 레이아웃 개선
- T008-T010: 로딩 상태 UX 개선

구현 완료 후:
1. ESLint, TypeScript 타입 체크
2. 프로덕션 빌드 검증
3. 빌드 크기 확인 (목표: < 500KB gzipped)

자동화:
python .claude/scripts/validate_typescript_service.py services/ecommerce/frontend -v

모든 체크 통과 확인 후 커밋 준비 완료 보고해줘.
```

### 예시 2: FDS 룰 엔진 개선

```
/speckit.implement 006-fds-rule-enhancement T001-T015 한국어로 구현해줘.

이 작업은 FDS 룰 엔진 성능 개선이야:
- T001-T005: 룰 평가 로직 최적화
- T006-T010: 캐싱 전략 개선
- T011-T015: 병렬 처리 추가

구현 완료 후:
1. Black, Ruff 검증 및 자동 수정
2. 유닛 테스트 실행 (커버리지 > 80%)
3. 성능 테스트 (목표: P95 < 100ms)

명령어:
python .claude/scripts/validate_python_service.py services/fds -v

성능 벤치마크 결과 상세히 보고해줘:
- Before/After 비교
- P50, P95, P99 지표
- 목표 달성 여부
```

### 예시 3: 멀티 서비스 통합

```
/speckit.implement 007-payment-integration T001-T020 한국어로 구현해줘.

이 작업은 결제 통합으로 여러 서비스를 변경해:
- services/ecommerce/backend: 결제 API 추가
- services/ecommerce/frontend: 결제 UI 추가
- services/fds: 결제 사기 탐지 룰 추가

구현 완료 후 전체 서비스 자동 검증:
python .claude/scripts/auto_validate_ci.py --fix-auto -v

각 서비스별 검증 결과를 다음 형식으로 리포트:
- [PASS/FAIL] services/ecommerce/backend
  - Black: [OK/FAIL]
  - Ruff: [OK/FAIL] (X auto-fixed)
  - Tests: [OK/FAIL] (X/Y passed)
- [PASS/FAIL] services/ecommerce/frontend
  - ESLint: [OK/FAIL]
  - TypeScript: [OK/FAIL]
  - Build: [OK/FAIL]
- [PASS/FAIL] services/fds
  - Black: [OK/FAIL]
  - Ruff: [OK/FAIL]
  - Tests: [OK/FAIL]
  - Performance: [OK/FAIL] (P95: Xms)

전체 통과 확인 후 커밋 가이드 제공해줘.
```

---

## 최종 권장사항

### 일반적인 구현 작업

**간단한 프롬프트 (권장)**:
```
/speckit.implement [SPEC] [TASKS] 한국어로 구현해줘.
구현 완료 후 python .claude/scripts/auto_validate_ci.py --fix-auto 실행해서 CI 검증해줘.
```

### 복잡한 멀티 서비스 작업

**Task Agent 사용 (권장)**:
```
Task Agent로 다음 작업 자동 수행:
1. /speckit.implement [SPEC] [TASKS]
2. 자동 CI 검증 (auto_validate_ci.py --fix-auto)
3. 실패 시 재시도
4. 최종 리포트

병렬로 실행하고 결과만 보고해줘.
```

### 프로덕션 배포 전 작업

**단계별 검증 (권장)**:
```
/speckit.implement [SPEC] [TASKS] 한국어로 구현해줘.

단계별 검증:
1. 각 태스크 그룹(3-5개)마다 CI 검증
2. 실패 시 즉시 중단 및 수정
3. 모든 단계 통과 후 최종 검증
4. 프로덕션 배포 체크리스트 제공

안전하게 진행해줘.
```

---

## FAQ

### Q1: 매번 긴 프롬프트를 작성해야 하나요?

**A**: 아니요. 간단한 작업은 다음으로 충분합니다:
```
/speckit.implement [SPEC] [TASKS] 한국어로 구현해줘. 구현 후 /test-ci 실행해줘.
```

### Q2: Task Agent는 언제 사용하나요?

**A**: 다음 경우에 사용:
- 멀티 서비스 변경
- 복잡한 구현 + 검증 자동화
- 중간 개입 없이 완전 자동화 원할 때

### Q3: 검증이 실패하면 어떻게 하나요?

**A**: Claude가 자동으로:
1. Black, Ruff 자동 수정 시도
2. 재검증
3. 여전히 실패 시 상세 수정 가이드 제공

### Q4: 특정 서비스만 검증하려면?

**A**:
```python
# Python 서비스
python .claude/scripts/validate_python_service.py services/[SERVICE]

# TypeScript 서비스
python .claude/scripts/validate_typescript_service.py services/[SERVICE]/frontend
```

### Q5: CI 검증을 건너뛰려면?

**A**: 프롬프트에서 검증 요청을 제외하면 됩니다:
```
/speckit.implement [SPEC] [TASKS] 한국어로 구현해줘.
```

단, 커밋 전에 수동으로 검증 권장:
```bash
python .claude/scripts/auto_validate_ci.py
```

---

## 체크리스트

구현 전:
- [ ] 어떤 서비스를 변경하는지 파악
- [ ] 필요한 검증 수준 결정 (간단/표준/철저)
- [ ] 프롬프트 템플릿 선택

구현 중:
- [ ] 진행 상황 모니터링
- [ ] 중간 검증 필요 시 개입

구현 후:
- [ ] CI 검증 결과 확인
- [ ] 실패 시 수정 가이드 따름
- [ ] 모든 체크 통과 확인
- [ ] 커밋 및 푸시

---

## 참고 문서

- **자동 CI 검증 시스템**: `.claude/docs/automatic-ci-validation.md`
- **빠른 시작 가이드**: `.claude/docs/QUICKSTART-CI-VALIDATION.md`
- **프로젝트 가이드라인**: `CLAUDE.md`
- **Speckit 문서**: `.claude/commands/speckit.*.md`
