"""
Celery Tasks for ML Service

Asynchronous background tasks for model training, evaluation, and deployment.

Tasks:
- train_model_task: Train new model version
- evaluate_model_task: Evaluate model performance
- deploy_model_task: Deploy model to production
- auto_retrain_check_task: Periodic retraining check
"""

import logging
from datetime import datetime
from typing import Dict
from uuid import UUID

from celery import Celery, Task
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.config import get_settings
from src.training.auto_retrainer import AutoRetrainer
from src.models.retraining_job import RetrainStatus

logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Initialize Celery app
celery_app = Celery(
    "ml_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 minutes soft limit
    worker_prefetch_multiplier=1,  # One task at a time
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks
)

# Database setup for async tasks
async_engine = create_async_engine(
    settings.DATABASE_URL_ASYNC,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class AsyncTask(Task):
    """Base task for async database operations"""

    async def get_db_session(self):
        """Get database session"""
        async with AsyncSessionLocal() as session:
            yield session


@celery_app.task(bind=True, base=AsyncTask, name="ml_service.train_model")
def train_model_task(self, job_id: str) -> Dict:
    """
    Train new model version

    Args:
        job_id: Retraining job ID

    Returns:
        dict: Training result
    """
    logger.info(f"[CELERY] Starting model training: job_id={job_id}")

    # Run async training
    import asyncio

    result = asyncio.run(_train_model_async(UUID(job_id)))

    logger.info(f"[CELERY] Model training complete: job_id={job_id}")

    return result


async def _train_model_async(job_id: UUID) -> Dict:
    """Async model training logic"""
    async with AsyncSessionLocal() as session:
        auto_retrainer = AutoRetrainer(session)

        # Update job status to RUNNING
        await auto_retrainer.update_job_status(
            job_id=job_id,
            status=RetrainStatus.RUNNING.value,
            started_at=datetime.utcnow(),
        )

        try:
            # TODO: Implement actual model training logic
            # This is a placeholder for the training pipeline
            logger.info(f"[TRAINING] Training model for job {job_id}")

            # Simulate training
            import time

            time.sleep(5)

            # Mock metrics
            metrics = {
                "accuracy": 0.95,
                "precision": 0.93,
                "recall": 0.90,
                "f1_score": 0.915,
            }

            # Update job status to COMPLETED
            await auto_retrainer.update_job_status(
                job_id=job_id,
                status=RetrainStatus.COMPLETED.value,
                completed_at=datetime.utcnow(),
                metrics=metrics,
            )

            return {
                "success": True,
                "job_id": str(job_id),
                "metrics": metrics,
            }

        except Exception as e:
            logger.error(f"[TRAINING] Error training model: {str(e)}")

            # Update job status to FAILED
            await auto_retrainer.update_job_status(
                job_id=job_id,
                status=RetrainStatus.FAILED.value,
                completed_at=datetime.utcnow(),
                error_message=str(e),
            )

            return {
                "success": False,
                "job_id": str(job_id),
                "error": str(e),
            }


@celery_app.task(bind=True, name="ml_service.auto_retrain_check")
def auto_retrain_check_task(self) -> Dict:
    """
    Periodic auto-retraining check

    This task runs periodically (e.g., daily) to check if retraining is needed.

    Returns:
        dict: Check result
    """
    logger.info("[CELERY] Running auto-retrain check")

    import asyncio

    result = asyncio.run(_auto_retrain_check_async())

    logger.info(
        f"[CELERY] Auto-retrain check complete: triggered={result.get('retraining_triggered')}"
    )

    return result


async def _auto_retrain_check_async() -> Dict:
    """Async auto-retrain check logic"""
    async with AsyncSessionLocal() as session:
        auto_retrainer = AutoRetrainer(session)

        result = await auto_retrainer.run_auto_retraining_check()

        # If retraining was triggered, start training task
        if result.get("retraining_triggered"):
            job_id = result.get("job_id")
            logger.info(f"[CELERY] Triggering training task for job {job_id}")

            # Start training task asynchronously
            train_model_task.apply_async(args=[str(job_id)])

        return result


@celery_app.task(bind=True, name="ml_service.evaluate_drift")
def evaluate_drift_task(self) -> Dict:
    """
    Evaluate data drift

    Returns:
        dict: Drift evaluation result
    """
    logger.info("[CELERY] Evaluating data drift")

    import asyncio

    result = asyncio.run(_evaluate_drift_async())

    logger.info(
        f"[CELERY] Drift evaluation complete: drift_detected={result.get('drift_detected')}"
    )

    return result


async def _evaluate_drift_async() -> Dict:
    """Async drift evaluation logic"""
    from src.monitoring.drift_detector import DriftDetector

    async with AsyncSessionLocal() as session:
        drift_detector = DriftDetector(session)
        result = await drift_detector.detect_all_features_drift()
        return result


@celery_app.task(bind=True, name="ml_service.evaluate_performance")
def evaluate_performance_task(self) -> Dict:
    """
    Evaluate model performance

    Returns:
        dict: Performance evaluation result
    """
    logger.info("[CELERY] Evaluating model performance")

    import asyncio

    result = asyncio.run(_evaluate_performance_async())

    logger.info(
        f"[CELERY] Performance evaluation complete: degraded={result.get('performance_degraded')}"
    )

    return result


async def _evaluate_performance_async() -> Dict:
    """Async performance evaluation logic"""
    from src.monitoring.performance_monitor import PerformanceMonitor

    async with AsyncSessionLocal() as session:
        performance_monitor = PerformanceMonitor(session)
        result = await performance_monitor.evaluate_current_performance()
        return result


# Periodic task schedule
celery_app.conf.beat_schedule = {
    "auto-retrain-check-daily": {
        "task": "ml_service.auto_retrain_check",
        "schedule": 86400.0,  # Every 24 hours
    },
    "evaluate-drift-daily": {
        "task": "ml_service.evaluate_drift",
        "schedule": 86400.0,  # Every 24 hours
    },
    "evaluate-performance-daily": {
        "task": "ml_service.evaluate_performance",
        "schedule": 86400.0,  # Every 24 hours
    },
}
