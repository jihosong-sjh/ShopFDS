"""
Celery Configuration for FDS Service

이 파일은 FDS 배치 평가 및 비동기 작업을 위한 Celery 설정을 제공합니다.
"""

import os
from celery.schedules import crontab

# =======================
# Broker and Backend
# =======================

# RabbitMQ broker URL
broker_url = os.getenv(
    "CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//"
)

# Redis result backend (클러스터 모드)
result_backend = os.getenv(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/1"
)

# =======================
# Task Configuration
# =======================

# 작업 직렬화 포맷
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"

# 타임존 설정
timezone = "Asia/Seoul"
enable_utc = True

# 작업 결과 만료 시간 (7일)
result_expires = 60 * 60 * 24 * 7

# 작업 재시도 설정
task_acks_late = True  # 작업 완료 후 ACK
task_reject_on_worker_lost = True  # 워커 중단 시 작업 재큐잉
worker_prefetch_multiplier = 4  # 동시 작업 수

# =======================
# Task Routing
# =======================

task_routes = {
    # FDS 배치 평가 작업 (중간 우선순위)
    "src.tasks.batch_evaluation.batch_evaluate_transactions": {
        "queue": "fds_batch",
        "priority": 5,
    },
    # FDS 실시간 평가 작업 (높은 우선순위)
    "src.tasks.evaluation.evaluate_transaction_async": {
        "queue": "fds_realtime",
        "priority": 9,
    },
}

# =======================
# Beat Schedule (주기적 작업)
# =======================

beat_schedule = {
    # 매일 자정에 지난 24시간 거래 재평가
    "batch-evaluate-transactions": {
        "task": "src.tasks.batch_evaluation.batch_evaluate_transactions",
        "schedule": crontab(hour=0, minute=0),
    },
}

# =======================
# Worker Configuration
# =======================

# 워커 로그 레벨
worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
worker_task_log_format = (
    "[%(asctime)s: %(levelname)s/%(processName)s] "
    "[%(task_name)s(%(task_id)s)] %(message)s"
)

# 워커 동시 실행 수 (FDS는 CPU 집약적이므로 낮게 설정)
worker_concurrency = int(os.getenv("CELERY_WORKER_CONCURRENCY", "2"))

# =======================
# Monitoring
# =======================

# 작업 이벤트 활성화 (Flower 모니터링용)
worker_send_task_events = True
task_send_sent_event = True
