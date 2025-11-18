"""
Celery Task Logger

Celery 작업의 시작, 완료, 실패를 CeleryTaskLog 모델에 기록하는 유틸리티
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os

from src.models.celery_task_log import CeleryTaskLog, TaskStatus

logger = logging.getLogger(__name__)


class CeleryTaskLogger:
    """Celery 작업 로깅 유틸리티"""

    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://shopfds:shopfds@localhost:5432/shopfds",
        )
        self.engine = create_async_engine(self.database_url, echo=False)
        self.async_session_factory = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def log_task_start(
        self,
        task_id: str,
        task_name: str,
        args: Optional[tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        queue_name: Optional[str] = None,
        worker_name: Optional[str] = None,
    ):
        """
        Celery 작업 시작 시 로그 기록

        Args:
            task_id: Celery 작업 ID
            task_name: 작업 이름 (예: src.tasks.email.send_order_confirmation_email)
            args: 위치 인자
            kwargs: 키워드 인자
            queue_name: 큐 이름
            worker_name: 워커 이름
        """
        try:
            async with self.async_session_factory() as session:
                task_log = CeleryTaskLog(
                    task_id=task_id,
                    task_name=task_name,
                    status=TaskStatus.STARTED,
                    queued_at=datetime.utcnow(),
                    started_at=datetime.utcnow(),
                    args=list(args) if args else None,
                    kwargs=kwargs,
                    queue_name=queue_name,
                    worker_name=worker_name,
                )
                session.add(task_log)
                await session.commit()

                logger.info(
                    f"[CeleryTaskLogger] Task started: {task_name} (task_id={task_id})"
                )
        except Exception as exc:
            logger.error(
                f"[FAIL] Failed to log task start: {task_name} (task_id={task_id}), error={exc}"
            )

    async def log_task_success(
        self, task_id: str, result: Optional[Dict[str, Any]] = None
    ):
        """
        Celery 작업 성공 시 로그 업데이트

        Args:
            task_id: Celery 작업 ID
            result: 작업 결과 (JSON 직렬화 가능)
        """
        try:
            async with self.async_session_factory() as session:
                from sqlalchemy import select

                stmt = select(CeleryTaskLog).where(CeleryTaskLog.task_id == task_id)
                result_obj = await session.execute(stmt)
                task_log = result_obj.scalars().first()

                if task_log:
                    task_log.mark_as_success(result=result)
                    await session.commit()

                    logger.info(
                        f"[CeleryTaskLogger] Task succeeded: {task_log.task_name} "
                        f"(task_id={task_id}, duration={task_log.execution_time_seconds:.2f}s)"
                    )
                else:
                    logger.warning(
                        f"[WARNING] Task log not found for task_id={task_id}"
                    )
        except Exception as exc:
            logger.error(
                f"[FAIL] Failed to log task success: task_id={task_id}, error={exc}"
            )

    async def log_task_failure(
        self,
        task_id: str,
        error: str,
        traceback: Optional[str] = None,
    ):
        """
        Celery 작업 실패 시 로그 업데이트

        Args:
            task_id: Celery 작업 ID
            error: 에러 메시지
            traceback: 스택 트레이스
        """
        try:
            async with self.async_session_factory() as session:
                from sqlalchemy import select

                stmt = select(CeleryTaskLog).where(CeleryTaskLog.task_id == task_id)
                result_obj = await session.execute(stmt)
                task_log = result_obj.scalars().first()

                if task_log:
                    task_log.mark_as_failure(error=error, traceback=traceback)
                    await session.commit()

                    logger.error(
                        f"[CeleryTaskLogger] Task failed: {task_log.task_name} "
                        f"(task_id={task_id}, error={error})"
                    )
                else:
                    logger.warning(
                        f"[WARNING] Task log not found for task_id={task_id}"
                    )
        except Exception as exc:
            logger.error(
                f"[FAIL] Failed to log task failure: task_id={task_id}, error={exc}"
            )

    async def log_task_retry(self, task_id: str):
        """
        Celery 작업 재시도 시 로그 업데이트

        Args:
            task_id: Celery 작업 ID
        """
        try:
            async with self.async_session_factory() as session:
                from sqlalchemy import select

                stmt = select(CeleryTaskLog).where(CeleryTaskLog.task_id == task_id)
                result_obj = await session.execute(stmt)
                task_log = result_obj.scalars().first()

                if task_log:
                    task_log.mark_as_retry()
                    await session.commit()

                    logger.warning(
                        f"[CeleryTaskLogger] Task retrying: {task_log.task_name} "
                        f"(task_id={task_id}, retry_count={task_log.retries})"
                    )
                else:
                    logger.warning(
                        f"[WARNING] Task log not found for task_id={task_id}"
                    )
        except Exception as exc:
            logger.error(
                f"[FAIL] Failed to log task retry: task_id={task_id}, error={exc}"
            )


# 전역 인스턴스 (싱글톤)
_celery_task_logger = None


def get_celery_task_logger() -> CeleryTaskLogger:
    """CeleryTaskLogger 싱글톤 인스턴스 반환"""
    global _celery_task_logger
    if _celery_task_logger is None:
        _celery_task_logger = CeleryTaskLogger()
    return _celery_task_logger
