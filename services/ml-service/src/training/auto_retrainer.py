"""
Auto Retraining System

This module automatically triggers model retraining when:
1. Performance degrades below threshold
2. Data drift is detected
3. Sufficient new labeled data is available

Business Logic:
- Monitors performance and drift continuously
- Triggers retraining when conditions are met
- Manages retraining job lifecycle
- Implements safety checks before deployment
"""

import logging
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.training.auto_labeler import AutoLabeler
from src.training.feedback_collector import FeedbackCollector
from src.monitoring.drift_detector import DriftDetector
from src.monitoring.performance_monitor import PerformanceMonitor
from src.models.retraining_job import RetrainingJob, RetrainStatus, RetrainTriggerType

logger = logging.getLogger(__name__)


class AutoRetrainer:
    """Automatically triggers and manages model retraining"""

    def __init__(
        self,
        db_session: AsyncSession,
        auto_labeler: Optional[AutoLabeler] = None,
        feedback_collector: Optional[FeedbackCollector] = None,
        drift_detector: Optional[DriftDetector] = None,
        performance_monitor: Optional[PerformanceMonitor] = None,
    ):
        """
        Initialize AutoRetrainer

        Args:
            db_session: Database session
            auto_labeler: AutoLabeler instance
            feedback_collector: FeedbackCollector instance
            drift_detector: DriftDetector instance
            performance_monitor: PerformanceMonitor instance
        """
        self.db_session = db_session
        self.auto_labeler = auto_labeler or AutoLabeler(db_session)
        self.feedback_collector = feedback_collector or FeedbackCollector(db_session)
        self.drift_detector = drift_detector or DriftDetector(db_session)
        self.performance_monitor = performance_monitor or PerformanceMonitor(db_session)

    async def check_retraining_conditions(self) -> Dict[str, any]:
        """
        Check all conditions that trigger retraining

        Returns:
            dict: Retraining condition status
        """
        logger.info("[RETRAINER] Checking retraining conditions")

        # 1. Check performance degradation
        performance_summary = await self.performance_monitor.get_performance_summary()
        performance_degraded = performance_summary.get("status") == "degraded"

        # 2. Check data drift
        drift_summary = await self.drift_detector.get_drift_summary()
        drift_detected = drift_summary.get("retraining_recommended", False)

        # 3. Check data availability
        labeling_stats = await self.auto_labeler.get_labeling_statistics()
        labeled_count = labeling_stats.get("labeled_transactions", 0)
        sufficient_data = labeled_count >= 1000  # Minimum 1000 labeled transactions

        # 4. Check new feedback
        feedback_threshold = await self.feedback_collector.check_retraining_threshold()
        new_feedback_available = feedback_threshold.get("threshold_met", False)

        # Determine if retraining should be triggered
        should_retrain = any(
            [
                performance_degraded,
                drift_detected,
                new_feedback_available,
            ]
        )

        # Determine trigger reason
        trigger_reasons = []
        if performance_degraded:
            trigger_reasons.append("performance_degradation")
        if drift_detected:
            trigger_reasons.append("data_drift")
        if new_feedback_available:
            trigger_reasons.append("new_data")

        logger.info(
            f"[RETRAINER] Retraining conditions: "
            f"performance_degraded={performance_degraded}, "
            f"drift_detected={drift_detected}, "
            f"sufficient_data={sufficient_data}, "
            f"new_feedback={new_feedback_available}, "
            f"should_retrain={should_retrain}"
        )

        return {
            "should_retrain": should_retrain and sufficient_data,
            "trigger_reasons": trigger_reasons,
            "conditions": {
                "performance_degraded": performance_degraded,
                "drift_detected": drift_detected,
                "sufficient_data": sufficient_data,
                "new_feedback_available": new_feedback_available,
            },
            "details": {
                "current_f1_score": performance_summary.get("current_metrics", {}).get(
                    "f1_score"
                ),
                "drift_count_30d": drift_summary.get("recent_drift_count_30d"),
                "labeled_transactions": labeled_count,
                "unprocessed_feedback": feedback_threshold.get("unprocessed_count"),
            },
        }

    async def trigger_retraining(
        self,
        trigger_reason: str,
        triggered_by: str = "system",
        notes: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        Trigger a new retraining job

        Args:
            trigger_reason: Reason for retraining (TriggerReason enum)
            triggered_by: Who triggered the retraining
            notes: Additional notes

        Returns:
            dict: Retraining job details
        """
        logger.info(f"[RETRAINER] Triggering retraining: reason={trigger_reason}")

        # Create retraining job
        retraining_job = RetrainingJob(
            trigger_reason=trigger_reason,
            triggered_by=RetrainTriggerType.AUTO
            if triggered_by == "auto_retrainer"
            else RetrainTriggerType.MANUAL,
            status=RetrainStatus.PENDING,
            logs=notes,
        )
        self.db_session.add(retraining_job)
        await self.db_session.commit()
        await self.db_session.refresh(retraining_job)

        logger.info(
            f"[RETRAINER] Retraining job created: {retraining_job.job_id} "
            f"(reason: {trigger_reason})"
        )

        return {
            "success": True,
            "job_id": retraining_job.job_id,
            "trigger_reason": trigger_reason,
            "triggered_at": retraining_job.created_at.isoformat(),
            "status": retraining_job.status.value,
        }

    async def run_auto_retraining_check(self) -> Dict[str, any]:
        """
        Run automatic retraining check and trigger if needed

        This is the main entry point for scheduled retraining checks.

        Returns:
            dict: Check and trigger result
        """
        logger.info("[RETRAINER] Running auto-retraining check")

        # Step 1: Auto-label new data
        labeling_result = await self.auto_labeler.run_auto_labeling()
        logger.info(
            f"[RETRAINER] Auto-labeling: "
            f"success={labeling_result.get('success')}, "
            f"labeled={labeling_result.get('labeled_counts', {}).get('total', 0)}"
        )

        # Step 2: Process user feedback
        feedback_result = await self.feedback_collector.process_feedback_for_labeling()
        logger.info(
            f"[RETRAINER] Feedback processing: "
            f"processed={feedback_result.get('processed_count', 0)}"
        )

        # Step 3: Evaluate current performance
        performance_result = (
            await self.performance_monitor.evaluate_current_performance()
        )
        logger.info(
            f"[RETRAINER] Performance evaluation: "
            f"success={performance_result.get('success')}, "
            f"degraded={performance_result.get('performance_degraded')}"
        )

        # Step 4: Detect data drift
        drift_result = await self.drift_detector.detect_all_features_drift()
        logger.info(
            f"[RETRAINER] Drift detection: "
            f"drift_detected={drift_result.get('drift_detected')}, "
            f"features_drifted={drift_result.get('features_drifted')}"
        )

        # Step 5: Check retraining conditions
        conditions = await self.check_retraining_conditions()

        # Step 6: Trigger retraining if needed
        if conditions["should_retrain"]:
            # Determine primary trigger reason
            trigger_reason = (
                conditions["trigger_reasons"][0]
                if conditions["trigger_reasons"]
                else "manual"
            )

            notes = (
                f"Automatic retraining triggered. "
                f"Reasons: {', '.join(conditions['trigger_reasons'])}. "
                f"Details: {conditions['details']}"
            )

            trigger_result = await self.trigger_retraining(
                trigger_reason=trigger_reason,
                triggered_by="auto_retrainer",
                notes=notes,
            )

            logger.info(
                f"[RETRAINER] Retraining triggered: job_id={trigger_result['job_id']}"
            )

            return {
                "retraining_triggered": True,
                "job_id": trigger_result["job_id"],
                "trigger_reasons": conditions["trigger_reasons"],
                "conditions": conditions["conditions"],
                "labeling_result": labeling_result,
                "feedback_result": feedback_result,
                "performance_result": performance_result,
                "drift_result": drift_result,
            }
        else:
            logger.info("[RETRAINER] Retraining not needed at this time")

            return {
                "retraining_triggered": False,
                "conditions": conditions["conditions"],
                "message": "No retraining conditions met",
                "labeling_result": labeling_result,
                "feedback_result": feedback_result,
                "performance_result": performance_result,
                "drift_result": drift_result,
            }

    async def update_job_status(
        self,
        job_id: UUID,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        model_version_id: Optional[UUID] = None,
        metrics: Optional[Dict] = None,
    ) -> Dict[str, any]:
        """
        Update retraining job status

        Args:
            job_id: Retraining job ID
            status: New status (RetrainStatus enum value)
            started_at: Training start time
            completed_at: Training completion time
            error_message: Error message if failed
            model_version_id: New model version ID if successful
            metrics: Training metrics

        Returns:
            dict: Update result
        """
        # Get job
        from sqlalchemy import select

        query = select(RetrainingJob).where(RetrainingJob.job_id == job_id)
        result = await self.db_session.execute(query)
        job = result.scalar_one_or_none()

        if not job:
            logger.error(f"[RETRAINER] Job not found: {job_id}")
            return {
                "success": False,
                "error": "job_not_found",
            }

        # Update status
        job.status = RetrainStatus(status)
        if started_at:
            job.started_at = started_at
        if completed_at:
            job.completed_at = completed_at
        if error_message:
            # Append to logs
            job.logs = f"{job.logs or ''}\n[ERROR] {error_message}"
        if model_version_id:
            job.new_model_version_id = model_version_id
        if metrics:
            job.metrics = metrics

        await self.db_session.commit()
        await self.db_session.refresh(job)

        logger.info(f"[RETRAINER] Job {job_id} status updated: {status}")

        return {
            "success": True,
            "job_id": job_id,
            "status": status,
        }

    async def get_retraining_schedule_status(self) -> Dict[str, any]:
        """
        Get retraining schedule and status

        Returns:
            dict: Schedule status
        """
        # Get pending/running jobs
        from sqlalchemy import select

        pending_query = select(RetrainingJob).where(
            RetrainingJob.status.in_([RetrainStatus.PENDING, RetrainStatus.RUNNING])
        )
        pending_result = await self.db_session.execute(pending_query)
        pending_jobs = pending_result.scalars().all()

        # Get recent completed jobs
        completed_query = (
            select(RetrainingJob)
            .where(RetrainingJob.status == RetrainStatus.COMPLETED)
            .order_by(RetrainingJob.completed_at.desc())
            .limit(5)
        )
        completed_result = await self.db_session.execute(completed_query)
        completed_jobs = completed_result.scalars().all()

        return {
            "pending_jobs": len(
                [j for j in pending_jobs if j.status == RetrainStatus.PENDING]
            ),
            "running_jobs": len(
                [j for j in pending_jobs if j.status == RetrainStatus.RUNNING]
            ),
            "recent_completed": [
                {
                    "job_id": job.job_id,
                    "completed_at": job.completed_at.isoformat()
                    if job.completed_at
                    else None,
                    "model_version_id": job.new_model_version_id,
                    "trigger_reason": job.trigger_reason,
                }
                for job in completed_jobs
            ],
        }
