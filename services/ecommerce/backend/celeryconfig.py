"""
Celery Configuration for Ecommerce Service

이 파일은 Celery 작업 큐, 브로커, 결과 백엔드, 작업 라우팅을 설정합니다.
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
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
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
    # 이메일 발송 작업 (높은 우선순위)
    "src.tasks.email.send_order_confirmation_email": {
        "queue": "email",
        "priority": 9,
    },
    "src.tasks.email.send_password_reset_email": {
        "queue": "email",
        "priority": 9,
    },
    # 리포트 생성 작업 (낮은 우선순위)
    "src.tasks.reports.generate_sales_report": {
        "queue": "reports",
        "priority": 3,
    },
    # 정리 작업 (매우 낮은 우선순위)
    "src.tasks.cleanup.cleanup_old_sessions": {
        "queue": "cleanup",
        "priority": 1,
    },
    "src.tasks.cleanup.archive_old_logs": {
        "queue": "cleanup",
        "priority": 1,
    },
}

# =======================
# Beat Schedule (주기적 작업)
# =======================

beat_schedule = {
    # 매일 자정 3시에 오래된 세션 정리
    "cleanup-old-sessions": {
        "task": "src.tasks.cleanup.cleanup_old_sessions",
        "schedule": crontab(hour=3, minute=0),
    },
    # 매주 일요일 자정 2시에 오래된 로그 아카이빙
    "archive-old-logs": {
        "task": "src.tasks.cleanup.archive_old_logs",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),
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

# 워커 동시 실행 수
worker_concurrency = int(os.getenv("CELERY_WORKER_CONCURRENCY", "4"))

# =======================
# Monitoring
# =======================

# 작업 이벤트 활성화 (Flower 모니터링용)
worker_send_task_events = True
task_send_sent_event = True

# =======================
# Signal Handlers (작업 로깅)
# =======================


def setup_task_signal_handlers(celery_app):
    """
    Celery 작업 시그널 핸들러 설정

    작업 시작, 완료, 실패, 재시도 시 CeleryTaskLog에 기록
    """
    import asyncio
    from celery.signals import task_prerun, task_postrun, task_failure, task_retry
    from src.utils.celery_logger import get_celery_task_logger

    celery_logger = get_celery_task_logger()

    @task_prerun.connect
    def log_task_start(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
        """작업 시작 시 로깅"""
        try:
            # 비동기 함수를 동기적으로 실행
            asyncio.run(
                celery_logger.log_task_start(
                    task_id=task_id,
                    task_name=sender.name if sender else task.name,
                    args=args,
                    kwargs=kwargs,
                    queue_name=extra.get("queue"),
                )
            )
        except Exception as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[FAIL] Failed to log task start: {exc}")

    @task_postrun.connect
    def log_task_success(sender=None, task_id=None, task=None, retval=None, **extra):
        """작업 완료 시 로깅"""
        try:
            result = {"return_value": str(retval)} if retval else None
            asyncio.run(
                celery_logger.log_task_success(
                    task_id=task_id,
                    result=result,
                )
            )
        except Exception as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[FAIL] Failed to log task success: {exc}")

    @task_failure.connect
    def log_task_error(sender=None, task_id=None, exception=None, traceback=None, **extra):
        """작업 실패 시 로깅"""
        try:
            import traceback as tb_module
            asyncio.run(
                celery_logger.log_task_failure(
                    task_id=task_id,
                    error=str(exception),
                    traceback=tb_module.format_exc() if traceback else None,
                )
            )
        except Exception as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[FAIL] Failed to log task failure: {exc}")

    @task_retry.connect
    def log_task_retry_handler(sender=None, task_id=None, **extra):
        """작업 재시도 시 로깅"""
        try:
            asyncio.run(
                celery_logger.log_task_retry(task_id=task_id)
            )
        except Exception as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[FAIL] Failed to log task retry: {exc}")
