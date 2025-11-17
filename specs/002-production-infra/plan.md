# Implementation Plan: 프로덕션 인프라 구축

**Branch**: `002-production-infra` | **Date**: 2025-11-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-production-infra/spec.md`

## Summary

ShopFDS 플랫폼의 실전 배포를 위한 핵심 인프라를 구축합니다. PostgreSQL Read Replica를 통한 읽기 부하 분산, Redis Cluster 기반 블랙리스트 관리, Celery+RabbitMQ 비동기 작업 처리, ELK Stack 통합 로그 모니터링, Prometheus 알림 시스템, 그리고 개발 환경 자동화를 포함합니다.

## Technical Context

**Language/Version**: Python 3.11+, Shell Script (Bash)

**Primary Dependencies**:
- Database: PostgreSQL 15+ (스트리밍 복제), SQLAlchemy 2.0+
- Cache: Redis 7+ (Cluster mode), redis-py-cluster 2.1+
- Message Queue: RabbitMQ 3.12+, Celery 5.4+, Flower
- Logging: Elasticsearch 7.17, Logstash 7.17, Kibana 7.17
- Monitoring: Prometheus 2.40+, Alertmanager 0.25+, Grafana 9.3+
- Container: Docker 24+, Docker Compose 2.20+

**Storage**:
- PostgreSQL 15+ (Master + Read Replica)
- Redis Cluster (6 nodes: 3 masters + 3 replicas)
- Elasticsearch (로그 인덱싱, 30일 자동 삭제)

**Testing**: pytest, pytest-asyncio

**Target Platform**: Linux server (Docker Compose 로컬, Kubernetes 프로덕션)

**Project Type**: Infrastructure (멀티 서비스 지원)

**Performance Goals**:
- DB Read Replica: 읽기 쿼리 80% 이상 Replica 처리
- Redis 블랙리스트: 차단 결정 100ms 이내
- Celery: 시간당 1000+ 작업 처리
- 로그 인덱싱: 10초 이내 Elasticsearch 인덱싱
- Health Check: 100ms 이내 응답

**Constraints**:
- 복제 지연: 10초 이내
- Redis 페일오버: 10초 이내
- Elasticsearch 디스크: 최소 100GB
- 개발 환경 설정: 5분 이내

## Constitution Check

*GATE: Must pass before Phase 0 research.*

**Status**: N/A (프로젝트 Constitution이 템플릿 상태)

**Notes**: 인프라 레이어 구축으로 새 서비스 추가 없음

## Project Structure

### Documentation (this feature)

```text
specs/002-production-infra/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/           # Phase 1 output
    ├── health-check.md
    └── admin-blacklist-api.yaml
```

### Source Code

```text
infrastructure/
├── docker/
│   ├── docker-compose.yml           # [수정] Redis Cluster, RabbitMQ, ELK 추가
│   ├── docker-compose.monitoring.yml # [신규] Prometheus, Grafana
│   ├── postgres/
│   │   ├── master.conf              # [신규] Master 설정
│   │   └── replica.conf             # [신규] Replica 설정
│   ├── redis/
│   │   └── redis-cluster.conf       # [신규] Cluster 설정
│   └── elasticsearch/
│       └── elasticsearch.yml        # [신규]
├── monitoring/
│   ├── prometheus/
│   │   └── alerts/
│   │       ├── infrastructure.yml   # [신규] CPU/메모리/디스크 알림
│   │       └── application.yml      # [신규] API 에러율, Health Check
│   ├── alertmanager/
│   │   └── alertmanager.yml         # [신규] Slack/Email 라우팅
│   ├── logstash/
│   │   └── pipeline/
│   │       └── app-logs.conf        # [신규] FastAPI 로그 파싱
│   └── kibana/
│       └── dashboards/
│           └── fds-monitoring.json  # [신규] 대시보드
├── scripts/
│   ├── setup.sh                     # [신규] 전체 환경 설정
│   ├── reset-db.sh                  # [신규] DB 리셋
│   ├── seed-data.py                 # [신규] 시드 데이터
│   └── init-redis-cluster.sh        # [신규] Redis Cluster 초기화
└── Makefile                         # [신규] 개발 명령어

services/
├── ecommerce/backend/
│   ├── src/
│   │   ├── db/connection.py         # [수정] Read Replica 연결 풀
│   │   ├── api/health.py            # [수정] Health Check 강화
│   │   ├── tasks/                   # [신규] Celery 작업
│   │   │   ├── email.py
│   │   │   ├── reports.py
│   │   │   └── cleanup.py
│   │   └── middleware/logging.py    # [수정] 구조화 로깅
│   └── celeryconfig.py              # [신규]
├── fds/
│   ├── src/
│   │   ├── cache/blacklist.py       # [신규] 블랙리스트 관리
│   │   ├── tasks/batch_evaluation.py # [신규] 배치 평가
│   │   └── api/health.py            # [수정]
│   └── celeryconfig.py              # [신규]
├── ml-service/
│   └── src/api/health.py            # [수정]
└── admin-dashboard/backend/
    ├── src/api/blacklist.py         # [신규] 블랙리스트 API
    └── tests/integration/
        └── test_blacklist_api.py    # [신규]

tests/infrastructure/                # [신규] 인프라 통합 테스트
├── test_postgres_replication.py
├── test_redis_cluster.py
├── test_celery_tasks.py
└── test_elk_logging.py
```

**Structure Decision**: Infrastructure 중심 구조, 기존 서비스 지원
