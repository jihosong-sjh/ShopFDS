# Feature Specification: 프로덕션 인프라 구축

**Feature Branch**: `002-production-infra`
**Created**: 2025-11-17
**Status**: Draft
**Input**: User description: "ShopFDS 플랫폼 실전 배포를 위한 핵심 인프라 구축 - 기존 구현을 활용하면서 부족한 부분만 추가 구현"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 고가용성 데이터베이스 운영 (Priority: P1)

개발팀이 프로덕션 환경에서 읽기 부하를 분산하고 데이터베이스 장애에 대비하여 Read Replica를 구성합니다. 이를 통해 조회 성능을 개선하고 메인 데이터베이스 부하를 줄입니다.

**Why this priority**: 데이터베이스는 모든 서비스의 핵심 인프라이며, 단일 장애점 제거가 가장 중요합니다. 읽기 부하 분산은 성능 개선의 기초입니다.

**Independent Test**: PostgreSQL 마스터-슬레이브 복제가 구성된 상태에서 읽기 전용 쿼리가 Replica로 라우팅되고, 쓰기 쿼리는 Master로 라우팅되는지 확인합니다. Master 중단 시 Replica가 읽기 요청을 계속 처리하는지 검증합니다.

**Acceptance Scenarios**:

1. **Given** 데이터베이스 Read Replica가 구성되어 있고, **When** 개발자가 조회 API를 호출하면, **Then** 읽기 전용 연결 풀을 통해 Replica에서 데이터를 조회합니다
2. **Given** Master 데이터베이스에 새 주문이 생성되고, **When** 10초 후 Replica를 조회하면, **Then** 복제된 주문 데이터가 존재합니다
3. **Given** 애플리케이션이 실행 중이고, **When** 주문 생성 API를 호출하면, **Then** Master 데이터베이스에 쓰기 작업이 수행됩니다
4. **Given** Read Replica가 다운되고, **When** 조회 API를 호출하면, **Then** 자동으로 Master로 폴백하여 데이터를 조회합니다

---

### User Story 2 - Redis 클러스터 기반 캐싱 및 블랙리스트 관리 (Priority: P1)

운영팀이 Redis Cluster를 구성하여 캐시 데이터를 자동 샤딩하고, FDS 블랙리스트(IP/이메일/카드)를 실시간으로 관리합니다. 이를 통해 사기 거래 차단 성능을 향상시킵니다.

**Why this priority**: FDS의 핵심 기능인 블랙리스트 관리와 캐싱은 실시간 사기 탐지 성능에 직접적인 영향을 미칩니다. 단일 Redis 노드의 메모리 한계를 극복해야 합니다.

**Independent Test**: 6노드 Redis Cluster가 구성된 상태에서 블랙리스트 IP를 추가하고, 해당 IP로 주문 요청 시 FDS가 자동으로 거부하는지 확인합니다. 클러스터 노드 하나가 다운되어도 서비스가 계속 작동하는지 검증합니다.

**Acceptance Scenarios**:

1. **Given** Redis Cluster가 6노드로 구성되어 있고, **When** 블랙리스트 IP 주소를 추가하면, **Then** 클러스터 전체에 자동 샤딩되어 저장됩니다
2. **Given** 블랙리스트에 등록된 IP에서, **When** 주문 요청이 들어오면, **Then** FDS가 즉시 "high" 위험도로 평가하고 거래를 차단합니다
3. **Given** 블랙리스트 이메일에 TTL 7일이 설정되고, **When** 7일이 경과하면, **Then** 자동으로 블랙리스트에서 제거됩니다
4. **Given** Redis Cluster 노드 1개가 다운되고, **When** 캐시 조회 요청이 발생하면, **Then** 다른 노드로 자동 페일오버되어 데이터를 조회합니다
5. **Given** 세션 스토어가 Redis에 저장되고, **When** 사용자가 로그인 후 30분이 경과하면, **Then** 세션이 자동으로 만료됩니다

---

### User Story 3 - 비동기 작업 처리 시스템 (Priority: P2)

개발팀이 Celery + RabbitMQ를 사용하여 주문 확인 이메일 발송, FDS 배치 평가, 리포트 생성 등 시간이 걸리는 작업을 비동기로 처리합니다. 이를 통해 API 응답 시간을 단축합니다.

**Why this priority**: 이메일 발송, 배치 작업 등은 사용자 경험에 즉시 영향을 주지 않으며, 비동기 처리로 API 성능을 크게 개선할 수 있습니다.

**Independent Test**: 주문 생성 API 호출 후 즉시 응답을 받고, 백그라운드에서 Celery 워커가 이메일 발송 작업을 처리하는지 확인합니다. Flower 대시보드에서 작업 상태를 모니터링할 수 있는지 검증합니다.

**Acceptance Scenarios**:

1. **Given** Celery 워커가 실행 중이고, **When** 주문이 생성되면, **Then** 주문 확인 이메일 발송 작업이 RabbitMQ 큐에 추가됩니다
2. **Given** 이메일 발송 작업이 큐에 있고, **When** Celery 워커가 작업을 가져오면, **Then** 5초 이내에 이메일이 발송됩니다
3. **Given** FDS 배치 평가 작업이 스케줄되고, **When** 매일 자정이 되면, **Then** 지난 24시간의 거래를 재평가합니다
4. **Given** Flower 모니터링이 활성화되고, **When** 관리자가 Flower 대시보드에 접속하면, **Then** 실시간 작업 상태, 성공/실패 건수, 워커 상태를 확인할 수 있습니다
5. **Given** 데이터 정리 작업이 주간 스케줄로 설정되고, **When** 매주 일요일 새벽 2시가 되면, **Then** 90일 이상 지난 로그 데이터를 자동으로 아카이빙합니다

---

### User Story 4 - 통합 로그 모니터링 및 알림 (Priority: P2)

운영팀이 ELK Stack(Elasticsearch, Logstash, Kibana)으로 모든 서비스의 로그를 중앙 집중화하고, Prometheus + Alertmanager로 시스템 메트릭을 모니터링하며, 이상 발생 시 Slack/Email로 즉시 알림을 받습니다.

**Why this priority**: 프로덕션 환경에서 장애 조기 발견과 신속한 대응은 서비스 안정성의 핵심입니다. 하지만 기본 인프라(DB, Redis, MQ)보다는 우선순위가 낮습니다.

**Independent Test**: 애플리케이션 에러 로그가 Elasticsearch에 수집되고, Kibana 대시보드에서 실시간으로 조회되는지 확인합니다. CPU 사용률이 80%를 초과하면 Slack으로 알림이 발송되는지 검증합니다.

**Acceptance Scenarios**:

1. **Given** Logstash 파이프라인이 구성되어 있고, **When** FastAPI 애플리케이션에서 에러가 발생하면, **Then** 5초 이내에 Elasticsearch에 로그가 인덱싱됩니다
2. **Given** Kibana 대시보드가 설정되고, **When** 운영자가 접속하면, **Then** 최근 1시간 에러율, 응답 시간, 트래픽 패턴을 시각화하여 확인할 수 있습니다
3. **Given** Prometheus가 메트릭을 수집 중이고, **When** CPU 사용률이 80%를 초과하면, **Then** Alertmanager가 Slack 채널에 경고 메시지를 발송합니다
4. **Given** Sentry가 각 환경별로 구성되고, **When** Python 예외가 발생하면, **Then** Sentry 대시보드에 스택 트레이스와 사용자 컨텍스트가 기록됩니다
5. **Given** Health Check 엔드포인트가 구현되고, **When** Prometheus가 `/health` 엔드포인트를 호출하면, **Then** DB 연결, Redis PING, 디스크 공간(90% 미만)을 실시간 체크하여 상태를 반환합니다

---

### User Story 5 - 개발 환경 자동화 및 시드 데이터 (Priority: P3)

개발자가 Makefile과 스크립트를 사용하여 로컬 개발 환경을 빠르게 설정하고, 테스트용 시드 데이터(사용자 1000명, 주문 10000건)를 자동으로 생성합니다. 이를 통해 신규 개발자 온보딩 시간을 단축합니다.

**Why this priority**: 개발 편의성은 중요하지만, 프로덕션 인프라 안정성보다는 우선순위가 낮습니다. MVP 단계에서는 수동 설정도 가능합니다.

**Independent Test**: 신규 개발자가 `make setup`을 실행하고, 5분 이내에 모든 서비스가 실행되며 시드 데이터가 로드되는지 확인합니다.

**Acceptance Scenarios**:

1. **Given** 신규 개발자가 프로젝트를 클론하고, **When** `make setup`을 실행하면, **Then** Docker Compose, 의존성 설치, DB 마이그레이션이 자동으로 완료됩니다
2. **Given** 개발 환경이 설정되고, **When** `make seed`를 실행하면, **Then** 사용자 1000명, 상품 500개, 주문 10000건, 리뷰 5000개가 생성됩니다
3. **Given** 데이터베이스에 기존 데이터가 있고, **When** `make reset-db`를 실행하면, **Then** 모든 테이블이 삭제되고 최신 스키마로 재생성됩니다
4. **Given** 개발 서버가 실행 중이고, **When** `make test`를 실행하면, **Then** 전체 서비스의 유닛 테스트와 통합 테스트가 순차적으로 실행됩니다
5. **Given** CI/CD 파이프라인에서, **When** 새 커밋이 푸시되면, **Then** Alembic 마이그레이션이 자동으로 실행되고, 롤백 스크립트가 문서에 기록됩니다

---

### Edge Cases

- **데이터베이스 복제 지연**: Master와 Replica 간 복제 지연이 30초를 초과하면 어떻게 처리하나요?
  - 헬스 체크에서 복제 지연을 모니터링하고, 임계값 초과 시 알림을 발송합니다
  - 읽기 쿼리가 최신 데이터를 요구하는 경우(예: 결제 후 주문 확인) Master에서 직접 조회합니다

- **Redis Cluster 노드 절반 이상 다운**: 3개 이상의 노드가 동시에 다운되면 어떻게 하나요?
  - Redis Cluster는 과반수 노드가 살아있어야 작동하므로, 4개 이상 다운 시 읽기 전용 모드로 전환합니다
  - 애플리케이션은 Redis 연결 실패 시 DB 직접 조회로 폴백하여 서비스를 유지합니다

- **Celery 워커 모두 다운**: 모든 워커가 중단되면 비동기 작업이 처리되지 않는데 어떻게 하나요?
  - RabbitMQ 큐에 작업이 누적되며, 워커 재시작 시 순차적으로 처리됩니다
  - 중요한 작업(예: 결제 완료 이메일)은 24시간 이상 미처리 시 관리자에게 알림을 발송합니다

- **Elasticsearch 디스크 공간 부족**: 로그 인덱싱이 중단되면 어떻게 하나요?
  - Curator를 사용하여 30일 이상 지난 로그를 자동 삭제합니다
  - 디스크 사용률 85% 도달 시 경고 알림, 95% 도달 시 긴급 알림을 발송합니다

- **시드 데이터 생성 중 중복 발생**: 시드 스크립트를 여러 번 실행하면 중복 데이터가 생성되나요?
  - 멱등성을 보장하기 위해 시드 스크립트는 실행 전 기존 시드 데이터를 모두 삭제합니다
  - 또는 `--append` 플래그를 제공하여 추가 모드를 지원합니다

## Requirements *(mandatory)*

### Functional Requirements

#### 데이터베이스 고도화

- **FR-001**: 시스템은 PostgreSQL 스트리밍 복제를 사용하여 최소 1개 이상의 Read Replica를 구성해야 합니다
- **FR-002**: 애플리케이션은 읽기 전용 쿼리(SELECT)를 Read Replica로, 쓰기 쿼리(INSERT/UPDATE/DELETE)를 Master로 자동 라우팅해야 합니다
- **FR-003**: Read Replica가 사용 불가능할 경우, 시스템은 자동으로 Master로 폴백하여 읽기 쿼리를 처리해야 합니다
- **FR-004**: 시드 데이터 생성 스크립트는 사용자 1000명, 주문 10000건, 상품 500개, 리뷰 5000개, 장바구니 데이터를 생성해야 합니다
- **FR-005**: 시드 데이터는 실제 운영 데이터와 유사한 분포(정상 거래 85%, 의심 거래 10%, 사기 거래 5%)를 가져야 합니다
- **FR-006**: Alembic 마이그레이션은 CI/CD 파이프라인에서 자동으로 실행되어야 하며, 실패 시 배포를 중단해야 합니다
- **FR-007**: 각 마이그레이션 파일은 롤백 스크립트(downgrade)를 반드시 포함해야 합니다

#### Redis Cluster 구축

- **FR-008**: Redis Cluster는 최소 6개 노드(마스터 3개, 슬레이브 3개)로 구성되어야 합니다
- **FR-009**: Redis Cluster는 자동 샤딩을 통해 16384개 해시 슬롯을 마스터 노드에 균등 분배해야 합니다
- **FR-010**: FDS 블랙리스트는 IP 주소, 이메일, 카드 번호(해시) 세 가지 유형을 지원해야 합니다
- **FR-011**: 블랙리스트 항목은 TTL(Time To Live)을 설정하여 지정된 기간 후 자동 제거되어야 합니다(기본값: 7일)
- **FR-012**: 블랙리스트 업데이트는 실시간으로 모든 FDS 인스턴스에 반영되어야 합니다
- **FR-013**: 세션 스토어는 Redis에 저장되며, 기본 만료 시간은 30분으로 설정되어야 합니다
- **FR-014**: Redis Cluster 노드 장애 시 10초 이내에 자동 페일오버가 완료되어야 합니다

#### 메시지 큐 시스템

- **FR-015**: Celery 워커는 최소 4개의 동시 작업을 처리할 수 있어야 합니다
- **FR-016**: 주문 생성 시 주문 확인 이메일 발송 작업이 자동으로 큐에 추가되어야 합니다
- **FR-017**: FDS 배치 평가는 매일 자정에 스케줄되어 지난 24시간 거래를 재평가해야 합니다
- **FR-018**: 리포트 생성 작업은 요청 시 백그라운드에서 처리되며, 완료 시 다운로드 링크를 제공해야 합니다
- **FR-019**: 데이터 정리 작업은 주간 스케줄(매주 일요일 새벽 2시)로 90일 이상 지난 로그를 아카이빙해야 합니다
- **FR-020**: Flower 모니터링 대시보드는 실시간 작업 상태, 성공/실패 통계, 워커 상태를 제공해야 합니다
- **FR-021**: 작업 실패 시 최대 3회까지 자동 재시도하며, 최종 실패 시 Dead Letter Queue로 이동해야 합니다

#### 모니터링 및 알림

- **FR-022**: Logstash는 모든 서비스(Ecommerce, FDS, ML Service, Admin Dashboard)의 로그를 수집하여 Elasticsearch에 인덱싱해야 합니다
- **FR-023**: Kibana 대시보드는 에러율, API 응답 시간, 트래픽 패턴, FDS 차단율을 실시간으로 시각화해야 합니다
- **FR-024**: Sentry는 개발(dev), 스테이징(staging), 프로덕션(production) 환경별로 별도 프로젝트를 생성해야 합니다
- **FR-025**: Health Check 엔드포인트(`/health`)는 데이터베이스 연결, Redis PING, 디스크 공간(90% 미만)을 확인해야 합니다
- **FR-026**: Prometheus Alertmanager는 다음 조건에서 알림을 발송해야 합니다:
  - CPU 사용률 80% 초과 (경고), 90% 초과 (긴급)
  - 메모리 사용률 85% 초과 (경고), 95% 초과 (긴급)
  - 디스크 공간 85% 초과 (경고), 95% 초과 (긴급)
  - API 에러율 5% 초과 (경고), 10% 초과 (긴급)
  - Health Check 실패 (긴급)
- **FR-027**: 알림은 Slack과 Email 두 가지 채널로 발송되어야 하며, 긴급 알림은 둘 다 사용해야 합니다
- **FR-028**: Elasticsearch 인덱스는 30일 이상 지난 로그를 자동으로 삭제해야 합니다(Curator 사용)

#### 개발 편의성

- **FR-029**: Makefile은 다음 명령어를 제공해야 합니다:
  - `make dev`: 전체 개발 환경 실행 (Docker Compose up)
  - `make test`: 전체 서비스 테스트 실행
  - `make migrate`: 모든 서비스의 DB 마이그레이션 실행
  - `make seed`: 시드 데이터 로드
  - `make clean`: 컨테이너 및 볼륨 정리
- **FR-030**: `setup.sh` 스크립트는 의존성 설치, Docker 이미지 빌드, 초기 마이그레이션을 순차적으로 실행해야 합니다
- **FR-031**: `reset-db.sh` 스크립트는 모든 데이터베이스 테이블을 삭제하고 최신 스키마로 재생성해야 합니다
- **FR-032**: `load-fixtures.sh` 스크립트는 멱등성을 보장하며, 중복 실행 시 기존 시드 데이터를 삭제 후 재생성해야 합니다

### Key Entities

- **Read Replica**: PostgreSQL 읽기 전용 복제본, 마스터 데이터베이스의 실시간 복사본
- **Redis Cluster Node**: Redis 클러스터의 개별 노드(마스터 또는 슬레이브), 특정 해시 슬롯 범위를 담당
- **Blacklist Entry**: FDS 블랙리스트 항목, 유형(IP/이메일/카드), 값(해시), TTL, 등록 사유, 생성 일시
- **Celery Task**: 비동기 작업 단위, 작업 유형(이메일/배치/리포트/정리), 상태(대기/진행중/완료/실패), 재시도 횟수
- **Log Index**: Elasticsearch 로그 인덱스, 서비스명, 로그 레벨, 타임스탬프, 메시지, 메타데이터
- **Alert Rule**: Prometheus 알림 규칙, 메트릭 이름, 조건, 임계값, 알림 레벨(경고/긴급), 채널(Slack/Email)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 데이터베이스 읽기 쿼리의 80% 이상이 Read Replica에서 처리되어 Master 부하가 50% 이상 감소합니다
- **SC-002**: 블랙리스트에 등록된 IP/이메일/카드로부터의 거래 요청이 100ms 이내에 차단됩니다
- **SC-003**: Redis Cluster 노드 1개 장애 시에도 서비스 중단 없이 자동 페일오버가 완료됩니다
- **SC-004**: 주문 생성 API 응답 시간이 이메일 발송 비동기 처리로 인해 평균 500ms 단축됩니다
- **SC-005**: Celery 워커가 시간당 1000개 이상의 비동기 작업을 처리할 수 있습니다
- **SC-006**: 애플리케이션 에러 발생 시 10초 이내에 Elasticsearch에 인덱싱되고 Kibana에서 조회 가능합니다
- **SC-007**: CPU 사용률 80% 초과 시 30초 이내에 Slack 알림이 발송됩니다
- **SC-008**: 신규 개발자가 `make setup` 명령어로 5분 이내에 전체 개발 환경을 구축할 수 있습니다
- **SC-009**: 시드 데이터 생성 스크립트가 10분 이내에 사용자 1000명, 주문 10000건을 생성합니다
- **SC-010**: Health Check 엔드포인트가 100ms 이내에 시스템 상태(DB/Redis/디스크)를 반환합니다
- **SC-011**: Alembic 마이그레이션이 CI/CD 파이프라인에서 자동 실행되며, 실패 시 배포가 즉시 중단됩니다
- **SC-012**: 전체 인프라(DB, Redis, RabbitMQ, ELK)가 `docker-compose up -d` 명령어로 2분 이내에 시작됩니다

## Assumptions

- PostgreSQL 15 이상, Redis 7 이상, Elasticsearch 7.17, RabbitMQ 3.12 이상을 사용합니다
- Docker Compose는 로컬 개발 환경용이며, 프로덕션은 Kubernetes 또는 별도 관리형 서비스를 사용할 수 있습니다
- 시드 데이터는 개발/테스트 환경에서만 사용되며, 프로덕션에는 로드하지 않습니다
- 블랙리스트 카드 번호는 SHA-256 해시로 저장하여 원본 정보를 보호합니다
- Celery 워커는 최소 2개 인스턴스를 실행하여 가용성을 보장합니다
- Slack Webhook URL과 Email SMTP 설정은 환경 변수로 제공됩니다
- Elasticsearch 디스크 공간은 최소 100GB 이상 확보되어 있습니다
- 복제 지연 임계값은 10초로 설정하며, 초과 시 경고를 발송합니다
- Health Check는 Kubernetes liveness/readiness probe에서 사용됩니다
- 시드 데이터의 사용자 이메일은 `user{N}@test.com` 형식을 사용합니다

## Out of Scope

- Kubernetes 프로덕션 배포 설정 (기존 infrastructure/k8s/에 이미 구현됨)
- CI/CD GitHub Actions 워크플로우 수정 (기존 .github/workflows/ci.yml 활용)
- ML 모델 학습 파이프라인 (별도 기능으로 이미 구현됨)
- 프론트엔드 빌드 및 배포 자동화
- 데이터베이스 백업 및 복원 자동화 (추후 구현 예정)
- Redis Cluster 동적 리샤딩 (초기 구성만 포함)
- 멀티 리전 배포 및 글로벌 로드 밸런싱
- 로그 장기 보관용 S3/클라우드 스토리지 연동

## Dependencies

- 기존 Docker Compose 설정 (`infrastructure/docker/docker-compose.yml`)
- 기존 PostgreSQL 데이터베이스 스키마 (Alembic 마이그레이션)
- 기존 Redis 캐싱 인프라 (단일 노드 → 클러스터로 확장)
- 기존 FastAPI Health Check 엔드포인트 (개선 필요)
- 기존 Prometheus 설정 (`infrastructure/monitoring/prometheus/`)
- 기존 Nginx 설정 (`infrastructure/nginx/`)

## Risks

- **복제 지연**: 네트워크 문제로 Master-Replica 간 복제 지연이 발생하면 데이터 일관성 문제가 생길 수 있습니다
  - 완화: 복제 지연 모니터링 및 임계값 초과 시 Master 직접 조회로 폴백
- **Redis Cluster 복잡성**: 6노드 클러스터 관리가 단일 노드보다 복잡하며, 네트워크 파티션 시 스플릿 브레인이 발생할 수 있습니다
  - 완화: 최소 3개 마스터 노드 유지, 자동 페일오버 테스트, Redis 연결 실패 시 DB 폴백
- **ELK 리소스 소비**: Elasticsearch는 메모리와 디스크를 많이 사용하여 로컬 개발 환경에서 성능 저하가 발생할 수 있습니다
  - 완화: 로컬 환경에서는 ELK를 선택적으로 실행(docker-compose 프로파일 사용), 인덱스 자동 삭제
- **Celery 워커 장애**: 모든 워커가 중단되면 비동기 작업이 처리되지 않아 이메일 미발송 등의 문제가 발생합니다
  - 완화: 최소 2개 워커 인스턴스 실행, RabbitMQ에 작업 지속성 보장, 24시간 미처리 작업 알림
- **시드 데이터 생성 시간**: 10000건 주문 생성 시 외래 키 제약 조건으로 인해 시간이 오래 걸릴 수 있습니다
  - 완화: 배치 삽입 사용, 인덱스 임시 비활성화 옵션 제공, 진행 상황 표시
