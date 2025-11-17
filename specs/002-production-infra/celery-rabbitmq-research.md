# Celery + RabbitMQ 비동기 작업 아키텍처 리서치

**작성일**: 2025-11-17
**카테고리**: 비동기 작업 처리, 메시지 큐
**버전**: 1.0

---

## 목차

1. [개요](#개요)
2. [핵심 결정사항](#핵심-결정사항)
3. [Celery 워커 설정](#celery-워커-설정)
4. [작업 재시도 전략](#작업-재시도-전략)
5. [Dead Letter Queue 설정](#dead-letter-queue-설정)
6. [Flower 모니터링](#flower-모니터링)
7. [비동기 작업 패턴](#비동기-작업-패턴)
8. [Celery Beat 스케줄링](#celery-beat-스케줄링)
9. [대안 기술 비교](#대안-기술-비교)
10. [프로덕션 배포 가이드](#프로덕션-배포-가이드)
11. [구현 시 주의사항](#구현-시-주의사항)

---

## 개요

ShopFDS 플랫폼에서 비동기 작업 처리를 위한 Celery + RabbitMQ 아키텍처 리서치 문서입니다. 이메일 발송, 배치 FDS 평가, 리포트 생성, 데이터 정리 등의 비동기 작업을 처리하기 위한 설계 및 구현 가이드를 제공합니다.

### 주요 요구사항

- **비동기 작업 처리**: 이메일 발송, 리포트 생성 등 무거운 작업을 백그라운드에서 처리
- **스케줄링**: 매일 자정 배치 FDS 평가, 주간 데이터 정리 등 주기적 작업
- **안정성**: 작업 실패 시 자동 재시도, Dead Letter Queue로 실패한 작업 관리
- **모니터링**: 실시간 작업 상태 확인, 워커 성능 모니터링
- **확장성**: Kubernetes 환경에서 워커 자동 스케일링

---

## 핵심 결정사항

### Decision

**Celery 5.4+ + RabbitMQ 3.12+**를 메시지 큐 시스템으로 선택

### Rationale

1. **안정성 및 신뢰성**
   - RabbitMQ는 메시지 브로커 전용으로 설계되어 메시지 손실 방지에 최적화
   - 메시지 확인(ACK) 및 영구 저장(Persistence) 기능으로 높은 신뢰성 보장
   - Redis의 가시성 타임아웃 문제 없음 (장기 실행 작업에서 작업 중복 실행 방지)

2. **고급 기능 지원**
   - Dead Letter Exchange (DLX): 실패한 작업을 별도 큐로 자동 이동
   - 클러스터링 및 고가용성(HA): 프로덕션 환경에서 안정적인 운영
   - Routing 및 Exchange 패턴: 작업 유형별 큐 분리 가능

3. **성능 특성**
   - 고처리량(High Throughput)에 최적화: 대량의 메시지 처리에 유리
   - Redis는 저지연(Low Latency)에 강점이지만, 본 프로젝트는 안정성과 처리량이 더 중요

4. **프로덕션 검증**
   - 대규모 프로덕션 환경에서 검증된 안정성
   - Celery 공식 문서에서 RabbitMQ를 기본 브로커로 권장

### Alternatives Considered

#### 1. Redis (as Message Broker)

**장점**:
- 매우 빠른 속도 (In-Memory)
- Pub/Sub 메시징 지원
- Redis를 캐시로도 사용 중이므로 인프라 단순화

**단점**:
- **가시성 타임아웃 문제**: 장기 실행 작업이 타임아웃 후 다른 워커에 재할당되어 중복 실행 발생
- **메시지 영구성 제한**: RabbitMQ와 달리 메시지를 장기간 보관하기 어려움
- **고가용성 제한**: 클러스터링이 RabbitMQ보다 복잡

**결론**: 실시간 성능보다 안정성이 중요한 본 프로젝트에는 부적합

#### 2. AWS SQS

**장점**:
- 완전 관리형 서비스 (인프라 관리 불필요)
- 자동 스케일링 및 고가용성
- AWS 생태계와의 원활한 통합

**단점**:
- **모니터링 제한**: 5분 간격 메트릭만 제공 (상세 모니터링 불가)
- **Celery 기능 제한**: celery-events, remote commands 사용 불가
- **비용**: 대량 메시지 처리 시 비용 증가
- **락인 위험**: AWS 종속성 증가

**결론**: 클라우드 중립적 설계를 위해 부적합

#### 3. Apache Kafka

**장점**:
- 초고속 처리량 (실시간 스트리밍)
- 이벤트 소싱 및 로그 집계에 최적화

**단점**:
- **오버엔지니어링**: 본 프로젝트 규모에 비해 과도하게 복잡
- **운영 부담**: Kafka 클러스터 관리가 RabbitMQ보다 복잡
- **학습 곡선**: Celery + Kafka 통합이 RabbitMQ보다 어려움

**결론**: 현재 요구사항에 비해 과도한 기술 스택

---

## Celery 워커 설정

### 1. Concurrency (동시성)

워커가 동시에 처리할 수 있는 작업 수를 결정합니다.

#### CPU-bound 작업

```python
# CPU 집약적 작업 (예: 데이터 처리, ML 추론)
CELERYD_CONCURRENCY = 2 * NUM_CPUS  # 예: 4 코어 = 8 워커
```

#### IO-bound 작업

```python
# I/O 집약적 작업 (예: 이메일 발송, API 호출)
CELERYD_CONCURRENCY = 100 * NUM_CPUS  # 예: 4 코어 = 400 워커
```

#### ShopFDS 권장 설정

```python
# services/ecommerce/backend/src/celery_app.py

# 기본 워커 (이메일 발송, API 호출 등)
CELERYD_CONCURRENCY = 50  # I/O 작업 중심

# FDS 평가 워커 (ML 추론)
FDS_WORKER_CONCURRENCY = 4  # CPU 작업 중심
```

**명령줄 실행**:
```bash
# 기본 워커
celery -A celery_app worker --concurrency=50 --queue=default

# FDS 워커
celery -A celery_app worker --concurrency=4 --queue=fds
```

### 2. Prefetch Multiplier (프리페치 배수)

워커가 미리 가져올 작업 수를 결정합니다.

#### 설정 전략

```python
# services/ecommerce/backend/src/celery_app.py

from celery import Celery

app = Celery('shopfds')

# 기본 설정
app.conf.update(
    # 장기 실행 작업: 1개씩만 가져오기
    worker_prefetch_multiplier=1,

    # 짧은 작업 + 높은 처리량: 2-4
    # worker_prefetch_multiplier=4,
)
```

#### 권장 설정

| 작업 유형 | Prefetch Multiplier | 이유 |
|---------|---------------------|------|
| 이메일 발송 | 1 | 실패 시 다른 워커가 즉시 처리 가능 |
| FDS 평가 (실시간) | 1 | 낮은 지연시간 유지 |
| FDS 배치 평가 | 2-4 | 처리량 최적화 |
| 리포트 생성 | 1 | 장기 실행 작업 |

**이유**:
- `prefetch_multiplier=1`: 작업이 실패하거나 워커가 종료되어도 다른 워커가 즉시 작업을 가져갈 수 있음
- 높은 값: 네트워크 왕복 시간(RTT)이 중요한 짧은 작업에서 처리량 향상

### 3. Task Acknowledgement (작업 확인)

작업 확인 시점을 제어합니다.

```python
# services/ecommerce/backend/src/celery_app.py

app.conf.update(
    # 작업 완료 후 ACK 전송 (권장)
    task_acks_late=True,

    # 워커 종료 시 작업 거부 (재시도 방지)
    task_reject_on_worker_lost=True,
)
```

#### task_acks_late=True 장점

- **워커 종료 시 작업 보존**: 워커가 갑자기 종료되어도 작업이 큐에 남아 다른 워커가 처리
- **멱등성(Idempotency) 필수**: 작업이 여러 번 실행되어도 안전해야 함

#### 주의사항

```python
# [WRONG] 비멱등 작업 예시
@app.task(acks_late=True)
def charge_payment(order_id, amount):
    # 위험: 워커 종료 후 재실행 시 중복 결제 발생
    payment_gateway.charge(order_id, amount)

# [CORRECT] 멱등성 보장
@app.task(acks_late=True)
def charge_payment(order_id, amount):
    # 이미 결제된 경우 스킵
    if Payment.objects.filter(order_id=order_id).exists():
        return {"status": "already_charged"}

    payment_gateway.charge(order_id, amount)
```

### 4. Max Tasks Per Child (워커 재시작)

메모리 누수 방지를 위해 일정 작업 후 워커 프로세스를 재시작합니다.

```python
# services/ecommerce/backend/src/celery_app.py

app.conf.update(
    # 100-500개 작업 후 워커 재시작 (메모리 누수 방지)
    worker_max_tasks_per_child=200,
)
```

**명령줄 실행**:
```bash
celery -A celery_app worker --max-tasks-per-child=200
```

**권장값**: 100-500 (프로덕션 환경에서 메모리 누수 최소화 검증됨)

---

## 작업 재시도 전략

### 1. autoretry_for (자동 재시도 예외)

특정 예외 발생 시 자동으로 재시도합니다.

```python
# services/ecommerce/backend/src/tasks/email_tasks.py

from celery import Task
from celery.exceptions import Reject
import smtplib
from requests.exceptions import RequestException, Timeout

@app.task(
    autoretry_for=(
        smtplib.SMTPException,      # SMTP 서버 오류
        RequestException,            # API 호출 실패
        Timeout,                     # 타임아웃
    ),
    retry_kwargs={
        'max_retries': 3,
        'countdown': 60,             # 60초 후 재시도
    },
)
def send_order_confirmation_email(order_id: str):
    """주문 확인 이메일 발송"""
    order = Order.objects.get(id=order_id)
    send_email(
        to=order.user.email,
        subject=f"[OK] 주문 확인 (Order {order.id})",
        template="order_confirmation.html",
        context={"order": order},
    )
```

### 2. Exponential Backoff (지수 백오프)

재시도 간격을 점진적으로 늘립니다.

```python
# services/ecommerce/backend/src/tasks/fds_tasks.py

@app.task(
    autoretry_for=(Exception,),
    retry_kwargs={
        'max_retries': 5,
    },
    retry_backoff=True,             # 지수 백오프 활성화
    retry_backoff_max=600,          # 최대 10분 대기
    retry_jitter=True,              # 무작위 지연 추가 (동시 재시도 방지)
)
def batch_fds_evaluation(transaction_ids: list[str]):
    """배치 FDS 평가"""
    # 재시도 간격: 1초, 2초, 4초, 8초, 16초 (최대 10분)
    results = []
    for txn_id in transaction_ids:
        result = evaluate_transaction(txn_id)
        results.append(result)
    return results
```

**지수 백오프 동작**:
- 1차 재시도: 1초 후
- 2차 재시도: 2초 후
- 3차 재시도: 4초 후
- 4차 재시도: 8초 후
- 5차 재시도: 16초 후

### 3. 선택적 예외 처리

모든 예외를 재시도하면 안 됩니다.

```python
# services/ecommerce/backend/src/tasks/report_tasks.py

from celery.exceptions import Reject

class InvalidReportParameterError(Exception):
    """리포트 파라미터 오류 (재시도 불필요)"""
    pass

@app.task(
    autoretry_for=(ConnectionError, Timeout),  # 네트워크 오류만 재시도
    max_retries=3,
)
def generate_sales_report(start_date: str, end_date: str):
    """매출 리포트 생성"""
    try:
        # 파라미터 검증
        if start_date > end_date:
            # 로직 오류는 재시도해도 실패하므로 즉시 거부
            raise Reject("Invalid date range", requeue=False)

        # 리포트 생성
        report = create_report(start_date, end_date)
        return report

    except InvalidReportParameterError as e:
        # 비즈니스 로직 오류는 재시도하지 않음
        raise Reject(str(e), requeue=False)
```

### 4. 커스텀 재시도 로직

```python
# services/fds/src/tasks/cti_tasks.py

from celery import Task

class CTITask(Task):
    """CTI API 호출 작업 기본 클래스"""

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """재시도 시 로깅"""
        print(f"[WARNING] Retrying CTI task {task_id}: {exc}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """최종 실패 시 알림"""
        print(f"[FAIL] CTI task {task_id} failed after retries: {exc}")
        # Sentry에 에러 리포트
        sentry_sdk.capture_exception(exc)

@app.task(
    base=CTITask,
    autoretry_for=(RequestException,),
    max_retries=3,
    retry_backoff=True,
)
def fetch_threat_intelligence(ip_address: str):
    """위협 인텔리전스 조회"""
    response = cti_api.get_threat_score(ip_address)
    return response
```

---

## Dead Letter Queue 설정

실패한 작업을 별도 큐로 이동하여 분석 및 수동 처리합니다.

### 1. RabbitMQ DLX 설정

```python
# services/ecommerce/backend/src/celery_app.py

from kombu import Exchange, Queue

app = Celery('shopfds')

# Dead Letter Exchange 정의
dead_letter_exchange = Exchange('dlx', type='topic', durable=True)

app.conf.task_queues = (
    # 기본 큐
    Queue(
        'default',
        Exchange('default', type='direct'),
        routing_key='default',
        queue_arguments={
            'x-dead-letter-exchange': 'dlx',              # DLX 지정
            'x-dead-letter-routing-key': 'failed.default', # DLQ 라우팅 키
        },
    ),

    # FDS 큐
    Queue(
        'fds',
        Exchange('fds', type='direct'),
        routing_key='fds',
        queue_arguments={
            'x-dead-letter-exchange': 'dlx',
            'x-dead-letter-routing-key': 'failed.fds',
        },
    ),

    # Email 큐
    Queue(
        'email',
        Exchange('email', type='direct'),
        routing_key='email',
        queue_arguments={
            'x-dead-letter-exchange': 'dlx',
            'x-dead-letter-routing-key': 'failed.email',
        },
    ),

    # Dead Letter Queues
    Queue(
        'failed.default',
        exchange=dead_letter_exchange,
        routing_key='failed.default',
    ),
    Queue(
        'failed.fds',
        exchange=dead_letter_exchange,
        routing_key='failed.fds',
    ),
    Queue(
        'failed.email',
        exchange=dead_letter_exchange,
        routing_key='failed.email',
    ),
)

# ACK late 설정 (필수)
app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
```

### 2. 작업 거부 (Reject) 로직

```python
# services/ecommerce/backend/src/tasks/order_tasks.py

from celery.exceptions import Reject

@app.task(max_retries=3)
def process_order(order_id: str):
    """주문 처리"""
    try:
        order = Order.objects.get(id=order_id)

        # 이미 처리된 주문은 스킵
        if order.status == OrderStatus.COMPLETED:
            return {"status": "already_processed"}

        # 주문 처리
        process_payment(order)
        ship_order(order)

    except Order.DoesNotExist:
        # 주문이 없으면 재시도 불필요 -> DLQ로 이동
        raise Reject(f"Order {order_id} not found", requeue=False)

    except Exception as e:
        # 기타 예외는 재시도 후 DLQ로 이동
        raise self.retry(exc=e, countdown=60)
```

### 3. DLQ 모니터링 및 재처리

```python
# services/ecommerce/backend/src/tasks/dlq_tasks.py

@app.task
def reprocess_failed_tasks():
    """DLQ의 실패한 작업 재처리"""
    from kombu import Connection

    with Connection(app.conf.broker_url) as conn:
        with conn.channel() as channel:
            # failed.email 큐에서 메시지 가져오기
            message = channel.basic_get(queue='failed.email')

            if message:
                # 메시지 재처리
                task_name = message.headers.get('task')
                task_args = message.body.get('args', [])

                # 원본 작업 재실행
                app.send_task(task_name, args=task_args, queue='email')

                # DLQ에서 메시지 제거
                message.ack()
                print(f"[OK] Reprocessed task: {task_name}")
```

---

## Flower 모니터링

Celery 워커 및 작업 상태를 실시간으로 모니터링합니다.

### 1. 설치 및 실행

```bash
# requirements.txt
flower==2.0.0
```

```bash
# 로컬 실행
flower --broker=amqp://guest:guest@localhost:5672// --port=5555

# 인증 추가
flower \
  --broker=amqp://guest:guest@localhost:5672// \
  --port=5555 \
  --basic_auth=admin:secret123
```

### 2. Docker Compose 설정

```yaml
# infrastructure/docker/docker-compose.yml

version: '3.8'

services:
  # RabbitMQ
  rabbitmq:
    image: rabbitmq:3.12-management
    ports:
      - "5672:5672"      # AMQP
      - "15672:15672"    # Management UI
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  # Celery Worker
  celery-worker:
    build:
      context: ../../services/ecommerce/backend
      dockerfile: Dockerfile
    command: celery -A celery_app worker --loglevel=info --concurrency=4
    environment:
      CELERY_BROKER_URL: amqp://guest:guest@rabbitmq:5672//
      CELERY_RESULT_BACKEND: redis://redis:6379/1
    depends_on:
      - rabbitmq
      - redis

  # Celery Beat (스케줄러)
  celery-beat:
    build:
      context: ../../services/ecommerce/backend
      dockerfile: Dockerfile
    command: celery -A celery_app beat --loglevel=info
    environment:
      CELERY_BROKER_URL: amqp://guest:guest@rabbitmq:5672//
    depends_on:
      - rabbitmq

  # Flower 모니터링
  flower:
    image: mher/flower:2.0.0
    command: celery --broker=amqp://guest:guest@rabbitmq:5672// flower --port=5555
    ports:
      - "5555:5555"
    environment:
      CELERY_BROKER_URL: amqp://guest:guest@rabbitmq:5672//
      CELERY_RESULT_BACKEND: redis://redis:6379/1
      FLOWER_BASIC_AUTH: admin:secret123
    depends_on:
      - rabbitmq
      - redis

volumes:
  rabbitmq_data:
```

### 3. Flower UI 주요 기능

- **대시보드**: 워커 상태, 작업 처리량, 실패율
- **작업 목록**: 실행 중, 완료, 실패한 작업 조회
- **워커 관리**: 워커 시작/중지, 로그 확인
- **통계**: 작업 실행 시간, 큐 길이, 처리율

**접속**: http://localhost:5555 (ID: admin, PW: secret123)

---

## 비동기 작업 패턴

### 1. 이메일 발송

```python
# services/ecommerce/backend/src/tasks/email_tasks.py

from celery import shared_task
from django.core.mail import send_mail

@shared_task(
    name='send_order_confirmation_email',
    autoretry_for=(smtplib.SMTPException,),
    max_retries=3,
    retry_backoff=True,
    queue='email',
)
def send_order_confirmation_email(order_id: str):
    """주문 확인 이메일 발송"""
    from src.models import Order

    order = Order.objects.get(id=order_id)

    send_mail(
        subject=f"[ShopFDS] 주문 확인 (Order {order.id})",
        message=f"주문이 완료되었습니다. 주문번호: {order.id}",
        from_email="noreply@shopfds.com",
        recipient_list=[order.user.email],
        html_message=render_template("order_confirmation.html", order=order),
    )

    print(f"[OK] Email sent to {order.user.email}")
```

**호출**:
```python
# services/ecommerce/backend/src/services/order_service.py

def create_order(user_id: str, ...):
    order = Order.objects.create(...)

    # 비동기 이메일 발송
    send_order_confirmation_email.delay(order_id=str(order.id))

    return order
```

### 2. 배치 FDS 평가 (스케줄링)

```python
# services/fds/src/tasks/batch_tasks.py

@shared_task(
    name='batch_fds_evaluation',
    autoretry_for=(Exception,),
    max_retries=3,
    queue='fds',
)
def batch_fds_evaluation():
    """매일 자정 배치 FDS 평가"""
    from src.models import Transaction
    from datetime import datetime, timedelta

    # 어제 생성된 미평가 거래 조회
    yesterday = datetime.now() - timedelta(days=1)
    transactions = Transaction.objects.filter(
        created_at__date=yesterday.date(),
        fds_result__isnull=True,
    )

    results = []
    for txn in transactions:
        # FDS 평가
        result = evaluate_transaction(txn.id)
        results.append(result)

    print(f"[OK] Batch FDS evaluation completed: {len(results)} transactions")
    return results
```

### 3. 리포트 생성 (AsyncResult 추적)

```python
# services/ecommerce/backend/src/tasks/report_tasks.py

from celery import shared_task
from celery.result import AsyncResult

@shared_task(
    name='generate_sales_report',
    bind=True,  # self 파라미터 추가
    queue='reports',
)
def generate_sales_report(self, start_date: str, end_date: str, user_id: str):
    """매출 리포트 생성"""
    total_steps = 5

    # Step 1: 데이터 조회
    self.update_state(state='PROGRESS', meta={'current': 1, 'total': total_steps, 'status': 'Fetching data...'})
    orders = Order.objects.filter(created_at__range=[start_date, end_date])

    # Step 2: 데이터 집계
    self.update_state(state='PROGRESS', meta={'current': 2, 'total': total_steps, 'status': 'Aggregating...'})
    aggregated = aggregate_sales_data(orders)

    # Step 3: 차트 생성
    self.update_state(state='PROGRESS', meta={'current': 3, 'total': total_steps, 'status': 'Creating charts...'})
    charts = create_charts(aggregated)

    # Step 4: PDF 생성
    self.update_state(state='PROGRESS', meta={'current': 4, 'total': total_steps, 'status': 'Generating PDF...'})
    pdf_path = generate_pdf(aggregated, charts)

    # Step 5: 이메일 발송
    self.update_state(state='PROGRESS', meta={'current': 5, 'total': total_steps, 'status': 'Sending email...'})
    send_report_email(user_id, pdf_path)

    return {'status': 'completed', 'pdf_path': pdf_path}
```

**진행 상황 추적 API**:
```python
# services/ecommerce/backend/src/api/reports.py

from fastapi import APIRouter
from celery.result import AsyncResult

router = APIRouter(prefix="/v1/reports", tags=["reports"])

@router.post("/sales")
async def create_sales_report(start_date: str, end_date: str, user_id: str):
    """매출 리포트 생성 요청"""
    task = generate_sales_report.delay(start_date, end_date, user_id)
    return {"task_id": task.id, "status": "pending"}

@router.get("/sales/{task_id}")
async def get_report_status(task_id: str):
    """리포트 생성 진행 상황 조회"""
    result = AsyncResult(task_id)

    if result.state == 'PENDING':
        return {"status": "pending", "progress": 0}
    elif result.state == 'PROGRESS':
        return {
            "status": "in_progress",
            "current": result.info.get('current', 0),
            "total": result.info.get('total', 1),
            "progress": int((result.info.get('current', 0) / result.info.get('total', 1)) * 100),
            "message": result.info.get('status', ''),
        }
    elif result.state == 'SUCCESS':
        return {"status": "completed", "result": result.result}
    else:
        return {"status": "failed", "error": str(result.info)}
```

### 4. 데이터 정리 (주간 스케줄)

```python
# services/ecommerce/backend/src/tasks/maintenance_tasks.py

@shared_task(
    name='archive_old_logs',
    queue='maintenance',
)
def archive_old_logs():
    """90일 이상 로그 아카이빙"""
    from datetime import datetime, timedelta
    from src.models import ActivityLog

    cutoff_date = datetime.now() - timedelta(days=90)

    # 오래된 로그 조회
    old_logs = ActivityLog.objects.filter(created_at__lt=cutoff_date)
    count = old_logs.count()

    # S3에 아카이빙
    archive_to_s3(old_logs)

    # DB에서 삭제
    old_logs.delete()

    print(f"[OK] Archived and deleted {count} logs older than 90 days")
    return {"archived_count": count}
```

---

## Celery Beat 스케줄링

### 1. 기본 설정

```python
# services/ecommerce/backend/src/celery_app.py

from celery import Celery
from celery.schedules import crontab

app = Celery('shopfds')

app.conf.beat_schedule = {
    # 매일 자정 배치 FDS 평가
    'batch-fds-evaluation': {
        'task': 'batch_fds_evaluation',
        'schedule': crontab(hour=0, minute=0),  # 00:00
    },

    # 매주 일요일 자정 데이터 아카이빙
    'archive-old-logs': {
        'task': 'archive_old_logs',
        'schedule': crontab(hour=0, minute=0, day_of_week=0),  # 일요일 00:00
    },

    # 매시간 30분마다 CTI 업데이트
    'update-threat-intelligence': {
        'task': 'update_threat_intelligence',
        'schedule': crontab(minute=30),  # 매시간 30분
    },

    # 매일 오전 9시 매출 리포트 생성
    'daily-sales-report': {
        'task': 'generate_daily_sales_report',
        'schedule': crontab(hour=9, minute=0),  # 09:00
    },

    # 10초마다 헬스체크 (개발 환경)
    'health-check': {
        'task': 'health_check',
        'schedule': 10.0,  # 10초 간격
    },
}

# 시간대 설정
app.conf.timezone = 'Asia/Seoul'
```

### 2. Crontab 패턴 예시

```python
# 매일 오전 7:30
crontab(hour=7, minute=30)

# 매주 월요일 오전 9:00
crontab(hour=9, minute=0, day_of_week=1)

# 매월 1일 자정
crontab(hour=0, minute=0, day_of_month=1)

# 30분마다 (00:30, 01:30, 02:30, ...)
crontab(minute=30)

# 매 5분마다 (00:00, 00:05, 00:10, ...)
crontab(minute='*/5')

# 평일 오후 6시 (월-금)
crontab(hour=18, minute=0, day_of_week='1-5')
```

### 3. Beat 실행

```bash
# 로컬 실행
celery -A celery_app beat --loglevel=info

# Docker Compose (위 섹션 참조)
docker-compose up -d celery-beat
```

---

## 대안 기술 비교

### 요약 테이블

| 항목 | RabbitMQ | Redis | AWS SQS | Kafka |
|-----|----------|-------|---------|-------|
| **안정성** | [OK] 매우 높음 | [WARNING] 보통 | [OK] 높음 | [OK] 매우 높음 |
| **처리량** | [OK] 높음 | [OK] 매우 높음 | [WARNING] 보통 | [OK] 초고속 |
| **지연시간** | [WARNING] 보통 | [OK] 매우 낮음 | [WARNING] 높음 | [WARNING] 보통 |
| **운영 복잡도** | [WARNING] 보통 | [OK] 낮음 | [OK] 매우 낮음 | [FAIL] 높음 |
| **비용** | [OK] 낮음 (자체 호스팅) | [OK] 낮음 | [WARNING] 변동 | [WARNING] 높음 |
| **Celery 통합** | [OK] 완벽 | [OK] 완벽 | [WARNING] 제한적 | [WARNING] 어려움 |
| **모니터링** | [OK] 우수 | [WARNING] 기본적 | [FAIL] 제한적 | [OK] 우수 |
| **고가용성** | [OK] 클러스터링 | [WARNING] 복잡 | [OK] 자동 | [OK] 복제 |

### 선택 가이드

- **ShopFDS (본 프로젝트)**: RabbitMQ (안정성 + 고급 기능)
- **초저지연 요구사항**: Redis
- **완전 관리형 선호**: AWS SQS
- **대규모 이벤트 스트리밍**: Kafka

---

## 프로덕션 배포 가이드

### 1. Kubernetes 배포

#### Deployment 매니페스트

```yaml
# infrastructure/k8s/celery-worker-deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
  namespace: shopfds
spec:
  replicas: 3
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
      - name: celery-worker
        image: shopfds/ecommerce-backend:latest
        command:
          - celery
          - -A
          - celery_app
          - worker
          - --loglevel=info
          - --concurrency=1        # 1 core per container
          - --max-tasks-per-child=100
        env:
        - name: CELERY_BROKER_URL
          valueFrom:
            secretKeyRef:
              name: celery-secrets
              key: broker-url
        - name: CELERY_RESULT_BACKEND
          valueFrom:
            secretKeyRef:
              name: celery-secrets
              key: result-backend
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          exec:
            command:
            - celery
            - -A
            - celery_app
            - inspect
            - ping
          initialDelaySeconds: 30
          periodSeconds: 60
        readinessProbe:
          exec:
            command:
            - celery
            - -A
            - celery_app
            - inspect
            - active
          initialDelaySeconds: 10
          periodSeconds: 30
      terminationGracePeriodSeconds: 120  # 120초 그레이스풀 셧다운
```

#### HPA (Horizontal Pod Autoscaler)

```yaml
# infrastructure/k8s/celery-worker-hpa.yaml

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: celery-worker-hpa
  namespace: shopfds
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: celery-worker
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 2. RabbitMQ 클러스터 배포

```yaml
# infrastructure/k8s/rabbitmq-statefulset.yaml

apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: rabbitmq
  namespace: shopfds
spec:
  serviceName: rabbitmq
  replicas: 3
  selector:
    matchLabels:
      app: rabbitmq
  template:
    metadata:
      labels:
        app: rabbitmq
    spec:
      containers:
      - name: rabbitmq
        image: rabbitmq:3.12-management
        ports:
        - containerPort: 5672
          name: amqp
        - containerPort: 15672
          name: management
        env:
        - name: RABBITMQ_ERLANG_COOKIE
          valueFrom:
            secretKeyRef:
              name: rabbitmq-secrets
              key: erlang-cookie
        - name: RABBITMQ_DEFAULT_USER
          value: admin
        - name: RABBITMQ_DEFAULT_PASS
          valueFrom:
            secretKeyRef:
              name: rabbitmq-secrets
              key: password
        volumeMounts:
        - name: rabbitmq-data
          mountPath: /var/lib/rabbitmq
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
  volumeClaimTemplates:
  - metadata:
      name: rabbitmq-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

### 3. Flower 모니터링 배포

```yaml
# infrastructure/k8s/flower-deployment.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: flower
  namespace: shopfds
spec:
  replicas: 1
  selector:
    matchLabels:
      app: flower
  template:
    metadata:
      labels:
        app: flower
    spec:
      containers:
      - name: flower
        image: mher/flower:2.0.0
        command:
          - celery
          - --broker=$(CELERY_BROKER_URL)
          - flower
          - --port=5555
        env:
        - name: CELERY_BROKER_URL
          valueFrom:
            secretKeyRef:
              name: celery-secrets
              key: broker-url
        - name: FLOWER_BASIC_AUTH
          valueFrom:
            secretKeyRef:
              name: celery-secrets
              key: flower-auth
        ports:
        - containerPort: 5555
          name: http
---
apiVersion: v1
kind: Service
metadata:
  name: flower
  namespace: shopfds
spec:
  selector:
    app: flower
  ports:
  - port: 5555
    targetPort: 5555
  type: ClusterIP
```

---

## 구현 시 주의사항

### 1. 멱등성 보장

모든 작업은 여러 번 실행되어도 안전해야 합니다 (acks_late=True 사용 시 필수).

```python
# [WRONG] 비멱등 작업
@app.task
def increment_view_count(product_id: str):
    product = Product.objects.get(id=product_id)
    product.view_count += 1  # 재실행 시 중복 증가
    product.save()

# [CORRECT] 멱등 작업
@app.task
def increment_view_count(product_id: str, request_id: str):
    # request_id로 중복 실행 방지
    if ViewLog.objects.filter(request_id=request_id).exists():
        return {"status": "already_processed"}

    product = Product.objects.get(id=product_id)
    product.view_count += 1
    product.save()

    ViewLog.objects.create(request_id=request_id, product_id=product_id)
```

### 2. 작업 타임아웃 설정

장기 실행 작업은 타임아웃을 설정하여 무한 대기를 방지합니다.

```python
@app.task(
    time_limit=300,        # Hard timeout: 5분
    soft_time_limit=240,   # Soft timeout: 4분 (SoftTimeLimitExceeded 예외 발생)
)
def long_running_task():
    try:
        # 무거운 작업
        process_large_dataset()
    except SoftTimeLimitExceeded:
        # 정리 작업 후 종료
        cleanup()
        raise
```

### 3. 데이터베이스 연결 관리

Celery 워커는 Django ORM의 자동 연결 관리를 사용하지 못하므로 명시적으로 연결을 닫아야 합니다.

```python
from django.db import connection

@app.task
def database_task():
    try:
        # 데이터베이스 작업
        User.objects.filter(is_active=True).count()
    finally:
        # 연결 닫기 (필수)
        connection.close()
```

또는 Celery 시그널 사용:

```python
# services/ecommerce/backend/src/celery_app.py

from celery.signals import task_postrun
from django.db import connection

@task_postrun.connect
def close_db_connection(**kwargs):
    """작업 완료 후 자동으로 DB 연결 닫기"""
    connection.close()
```

### 4. 메모리 누수 방지

```python
# services/ecommerce/backend/src/celery_app.py

app.conf.update(
    # 100-500개 작업 후 워커 재시작
    worker_max_tasks_per_child=200,

    # 메모리 제한 초과 시 워커 재시작
    worker_max_memory_per_child=300000,  # 300MB
)
```

### 5. 보안 고려사항

```python
# services/ecommerce/backend/src/celery_app.py

app.conf.update(
    # 작업 직렬화 (보안)
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # 결과 만료 (메모리 절약)
    result_expires=3600,  # 1시간 후 결과 삭제

    # 브로커 연결 보안
    broker_use_ssl={
        'ssl_cert_reqs': ssl.CERT_REQUIRED,
        'ssl_ca_certs': '/etc/ssl/certs/ca-certificates.crt',
    },
)
```

### 6. 로깅 및 모니터링

```python
import logging

logger = logging.getLogger(__name__)

@app.task
def monitored_task(data: dict):
    logger.info(f"[START] Processing task with data: {data}")

    try:
        result = process_data(data)
        logger.info(f"[OK] Task completed: {result}")
        return result

    except Exception as e:
        logger.error(f"[FAIL] Task failed: {e}", exc_info=True)
        raise
```

### 7. Graceful Shutdown (우아한 종료)

Kubernetes 환경에서 워커를 안전하게 종료합니다.

```bash
# 워커에 SIGTERM 전송 시 동작
# 1. 새 작업 수신 중지
# 2. 진행 중인 작업 완료 대기 (최대 120초)
# 3. 타임아웃 시 SIGKILL로 강제 종료
```

```yaml
# infrastructure/k8s/celery-worker-deployment.yaml

spec:
  terminationGracePeriodSeconds: 120  # 120초 그레이스 기간
```

---

## 요약

### 핵심 설정

```python
# services/ecommerce/backend/src/celery_app.py

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

app = Celery('shopfds')

# 브로커 및 백엔드
app.conf.broker_url = 'amqp://guest:guest@rabbitmq:5672//'
app.conf.result_backend = 'redis://redis:6379/1'

# 워커 설정
app.conf.update(
    worker_prefetch_multiplier=1,           # 장기 작업
    task_acks_late=True,                    # 작업 완료 후 ACK
    task_reject_on_worker_lost=True,        # 워커 종료 시 작업 거부
    worker_max_tasks_per_child=200,         # 메모리 누수 방지
    task_time_limit=300,                    # Hard timeout: 5분
    task_soft_time_limit=240,               # Soft timeout: 4분
)

# 큐 설정 (DLX 포함)
dead_letter_exchange = Exchange('dlx', type='topic', durable=True)

app.conf.task_queues = (
    Queue(
        'default',
        Exchange('default', type='direct'),
        routing_key='default',
        queue_arguments={
            'x-dead-letter-exchange': 'dlx',
            'x-dead-letter-routing-key': 'failed.default',
        },
    ),
    Queue('failed.default', exchange=dead_letter_exchange, routing_key='failed.default'),
)

# 스케줄 설정
app.conf.beat_schedule = {
    'batch-fds-evaluation': {
        'task': 'batch_fds_evaluation',
        'schedule': crontab(hour=0, minute=0),
    },
}

app.conf.timezone = 'Asia/Seoul'
```

### 배포 체크리스트

- [x] RabbitMQ 클러스터 배포 (3 replicas)
- [x] Celery 워커 배포 (HPA: 3-20 replicas)
- [x] Celery Beat 배포 (1 replica)
- [x] Flower 모니터링 배포
- [x] Dead Letter Queue 설정
- [x] Prometheus + Grafana 메트릭 수집
- [x] Secrets 관리 (broker URL, 인증 정보)
- [x] 로깅 설정 (Fluentd/ELK)
- [x] Health check 및 Liveness probe
- [x] Graceful shutdown (terminationGracePeriodSeconds=120)

---

**문서 버전**: 1.0
**최종 수정일**: 2025-11-17
**작성자**: Claude Code
**리뷰 필요 사항**: RabbitMQ 클러스터링 설정, Prometheus 메트릭 통합
