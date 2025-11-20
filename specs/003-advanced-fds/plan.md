# Implementation Plan: 실시간 사기 탐지 시스템 실전 고도화

**Branch**: `003-advanced-fds` | **Date**: 2025-11-18 | **Spec**: [spec.md](./spec.md)

## Summary

현재 구축된 FDS 프레임워크를 실전 시스템으로 고도화한다. 디바이스 핑거프린팅, 행동 패턴 분석, 네트워크 분석, 실전 룰 30개, 앙상블 ML 모델, 실시간 추론 최적화, XAI, 자동화된 학습 파이프라인, 외부 서비스 통합을 구현하여 사기 탐지율 95% 이상, 오탐률 6% 이하를 달성한다.

## Technical Context

**Language/Version**: Python 3.11+, TypeScript 5.3+, JavaScript

**Primary Dependencies**:
- Backend: FastAPI, SQLAlchemy, scikit-learn, XGBoost, PyTorch, TensorFlow, SHAP, LIME
- ML: MLflow, TorchServe, ONNX Runtime, WASM
- External: EmailRep, Numverify, BinList, HaveIBeenPwned
- Frontend: React 18+, Recharts, Zustand

**Storage**: PostgreSQL 15+, Redis 7+, MLflow Store, S3/MinIO

**Testing**: pytest, pytest-asyncio, pytest-benchmark, Locust, Jest

**Target Platform**: Linux server, 모던 브라우저, WebAssembly, GPU (NVIDIA T4+)

**Project Type**: Web (백엔드 + 프론트엔드 + ML 서비스)

**Performance Goals**:
- FDS P95: 50ms 이내
- 디바이스 핑거프린팅: 100ms 이내
- SHAP 분석: 95%가 5초 이내
- 처리량: 1,000 TPS

**Constraints**:
- 거래 처리 시간 증가: 50ms 이내
- 모델 양자화 정확도 손실: 1% 이내
- Redis 캐시 히트율: 85% 이상
- GDPR/CCPA/PCI-DSS 준수

**Scale/Scope**:
- 일일 거래: 50,000건
- 학습 데이터: 100,000건+
- 룰: 30개
- ML 모델: 4개
- 외부 API: 월 100,000건

## Constitution Check

**Status**: [PASS] 모든 검증 항목 통과

1. Test-First: 각 User Story에 Acceptance Scenarios 명시
2. 모듈화: 독립적인 엔진 분리
3. Observability: Prometheus/Grafana, 구조화된 로깅
4. 통합 테스트: 외부 API 모킹
5. 버전 관리: MLflow, API 버저닝
6. 보안: GDPR/PCI-DSS 준수

## Project Structure

### Documentation

```text
specs/003-advanced-fds/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
```

### Source Code

```text
services/
├── fds/src/
│   ├── engines/          [NEW] 5개 엔진
│   ├── models/           [NEW] 9개 모델
│   ├── services/         [NEW] 외부 API, XAI
│   └── api/              [NEW] 고도화 API
├── ml-service/src/
│   ├── models/           [NEW] 앙상블 4개
│   ├── training/         [NEW] 학습 파이프라인
│   ├── deployment/       [NEW] 양자화, WASM
│   ├── monitoring/       [NEW] 드리프트 감지
│   └── api/              [NEW] 학습/배포 API
├── ecommerce/frontend/
│   └── utils/            [NEW] 핑거프린팅, 행동 추적
└── admin-dashboard/frontend/
    └── pages/            [NEW] XAI, 모니터링
```

## Complexity Tracking

해당 없음 - Constitution Check 통과
