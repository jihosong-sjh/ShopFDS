"""
Model Performance Monitoring

This module monitors ML model performance metrics in production
to detect performance degradation and trigger retraining.

Key Metrics:
- F1 Score
- Precision
- Recall
- Accuracy
- False Positive Rate
- False Negative Rate
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List
import numpy as np

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.transaction import Transaction
from src.models.fraud_label import FraudLabel
from src.models.performance_log import PerformanceLog

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitors ML model performance in production"""

    def __init__(
        self,
        db_session: AsyncSession,
        f1_threshold: float = 0.85,
        precision_threshold: float = 0.90,
        recall_threshold: float = 0.80,
        evaluation_period_days: int = 7,
    ):
        """
        Initialize PerformanceMonitor

        Args:
            db_session: Database session
            f1_threshold: Minimum acceptable F1 score
            precision_threshold: Minimum acceptable precision
            recall_threshold: Minimum acceptable recall
            evaluation_period_days: Days to evaluate performance
        """
        self.db_session = db_session
        self.f1_threshold = f1_threshold
        self.precision_threshold = precision_threshold
        self.recall_threshold = recall_threshold
        self.evaluation_period_days = evaluation_period_days

    async def get_predictions_and_labels(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> tuple:
        """
        Get predictions and ground truth labels for evaluation

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            tuple: (predictions, labels, transaction_ids)
        """
        # Query transactions with both ML predictions and ground truth labels
        query = (
            select(Transaction, FraudLabel)
            .join(FraudLabel, Transaction.fraud_label_id == FraudLabel.id)
            .where(
                and_(
                    Transaction.created_at >= start_date,
                    Transaction.created_at < end_date,
                    Transaction.fds_decision.isnot(None),
                    FraudLabel.label_source.in_(
                        [
                            "chargeback",
                            "user_report",
                            "manual_review",
                        ]
                    ),
                )
            )
        )
        result = await self.db_session.execute(query)
        rows = result.all()

        predictions = []
        labels = []
        transaction_ids = []

        for transaction, fraud_label in rows:
            # ML prediction (from FDS decision)
            # Assume 'block' or 'additional_auth_required' = fraud prediction
            predicted_fraud = transaction.fds_decision in [
                "block",
                "additional_auth_required",
            ]

            # Ground truth label
            actual_fraud = fraud_label.is_fraud

            predictions.append(1 if predicted_fraud else 0)
            labels.append(1 if actual_fraud else 0)
            transaction_ids.append(transaction.id)

        return np.array(predictions), np.array(labels), transaction_ids

    def calculate_metrics(
        self,
        predictions: np.ndarray,
        labels: np.ndarray,
    ) -> Dict[str, float]:
        """
        Calculate performance metrics

        Args:
            predictions: Model predictions (0 or 1)
            labels: Ground truth labels (0 or 1)

        Returns:
            dict: Performance metrics
        """
        if len(predictions) == 0 or len(labels) == 0:
            logger.warning("[PERF] No data for metric calculation")
            return {
                "accuracy": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0,
                "false_positive_rate": 0.0,
                "false_negative_rate": 0.0,
                "true_positives": 0,
                "false_positives": 0,
                "true_negatives": 0,
                "false_negatives": 0,
                "sample_size": 0,
            }

        # Confusion matrix
        true_positives = np.sum((predictions == 1) & (labels == 1))
        false_positives = np.sum((predictions == 1) & (labels == 0))
        true_negatives = np.sum((predictions == 0) & (labels == 0))
        false_negatives = np.sum((predictions == 0) & (labels == 1))

        # Calculate metrics
        total = len(predictions)
        accuracy = (true_positives + true_negatives) / total

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0.0
        )

        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )

        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        false_positive_rate = (
            false_positives / (false_positives + true_negatives)
            if (false_positives + true_negatives) > 0
            else 0.0
        )

        false_negative_rate = (
            false_negatives / (false_negatives + true_positives)
            if (false_negatives + true_positives) > 0
            else 0.0
        )

        return {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1_score, 4),
            "false_positive_rate": round(false_positive_rate, 4),
            "false_negative_rate": round(false_negative_rate, 4),
            "true_positives": int(true_positives),
            "false_positives": int(false_positives),
            "true_negatives": int(true_negatives),
            "false_negatives": int(false_negatives),
            "sample_size": total,
        }

    async def evaluate_current_performance(self) -> Dict[str, any]:
        """
        Evaluate current model performance

        Returns:
            dict: Performance evaluation result
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=self.evaluation_period_days)

        logger.info(
            f"[PERF] Evaluating performance from {start_date.date()} to {end_date.date()}"
        )

        # Get predictions and labels
        predictions, labels, transaction_ids = await self.get_predictions_and_labels(
            start_date, end_date
        )

        if len(predictions) < 50:
            logger.warning(
                f"[PERF] Insufficient data for evaluation (n={len(predictions)})"
            )
            return {
                "success": False,
                "reason": "insufficient_data",
                "sample_size": len(predictions),
                "minimum_required": 50,
            }

        # Calculate metrics
        metrics = self.calculate_metrics(predictions, labels)

        # Check if performance is below threshold
        f1_degraded = metrics["f1_score"] < self.f1_threshold
        precision_degraded = metrics["precision"] < self.precision_threshold
        recall_degraded = metrics["recall"] < self.recall_threshold

        performance_degraded = f1_degraded or precision_degraded or recall_degraded

        # Create performance log
        performance_log = PerformanceLog(
            evaluated_at=datetime.utcnow(),
            period_start=start_date,
            period_end=end_date,
            sample_size=metrics["sample_size"],
            f1_score=metrics["f1_score"],
            precision=metrics["precision"],
            recall=metrics["recall"],
            accuracy=metrics["accuracy"],
            false_positive_rate=metrics["false_positive_rate"],
            false_negative_rate=metrics["false_negative_rate"],
            true_positives=metrics["true_positives"],
            false_positives=metrics["false_positives"],
            true_negatives=metrics["true_negatives"],
            false_negatives=metrics["false_negatives"],
            performance_degraded=performance_degraded,
        )
        self.db_session.add(performance_log)
        await self.db_session.commit()
        await self.db_session.refresh(performance_log)

        logger.info(
            f"[PERF] Performance evaluation complete: "
            f"F1={metrics['f1_score']:.4f}, "
            f"Precision={metrics['precision']:.4f}, "
            f"Recall={metrics['recall']:.4f}, "
            f"Degraded={performance_degraded}"
        )

        return {
            "success": True,
            "performance_degraded": performance_degraded,
            "metrics": metrics,
            "thresholds": {
                "f1_score": self.f1_threshold,
                "precision": self.precision_threshold,
                "recall": self.recall_threshold,
            },
            "degradation_details": {
                "f1_below_threshold": f1_degraded,
                "precision_below_threshold": precision_degraded,
                "recall_below_threshold": recall_degraded,
            },
            "log_id": performance_log.id,
            "evaluated_at": performance_log.evaluated_at.isoformat(),
        }

    async def get_performance_history(self, days: int = 30) -> List[Dict]:
        """
        Get performance monitoring history

        Args:
            days: Number of days to look back

        Returns:
            list: Performance history
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        query = (
            select(PerformanceLog)
            .where(PerformanceLog.evaluated_at >= start_date)
            .order_by(PerformanceLog.evaluated_at.desc())
        )
        result = await self.db_session.execute(query)
        performance_logs = result.scalars().all()

        history = []
        for log in performance_logs:
            history.append(
                {
                    "id": log.id,
                    "evaluated_at": log.evaluated_at.isoformat(),
                    "period_start": log.period_start.isoformat(),
                    "period_end": log.period_end.isoformat(),
                    "sample_size": log.sample_size,
                    "f1_score": log.f1_score,
                    "precision": log.precision,
                    "recall": log.recall,
                    "accuracy": log.accuracy,
                    "performance_degraded": log.performance_degraded,
                }
            )

        return history

    async def get_performance_trend(self, days: int = 30) -> Dict[str, any]:
        """
        Get performance trend analysis

        Args:
            days: Number of days to analyze

        Returns:
            dict: Trend analysis
        """
        history = await self.get_performance_history(days)

        if len(history) < 2:
            return {
                "trend": "insufficient_data",
                "data_points": len(history),
            }

        # Extract F1 scores
        f1_scores = [log["f1_score"] for log in history]

        # Calculate trend
        recent_avg = np.mean(f1_scores[:3]) if len(f1_scores) >= 3 else f1_scores[0]
        overall_avg = np.mean(f1_scores)

        trend = "stable"
        if recent_avg < overall_avg - 0.05:
            trend = "declining"
        elif recent_avg > overall_avg + 0.05:
            trend = "improving"

        # Count degraded evaluations
        degraded_count = sum(1 for log in history if log["performance_degraded"])

        return {
            "trend": trend,
            "recent_f1_avg": round(recent_avg, 4),
            "overall_f1_avg": round(overall_avg, 4),
            "degraded_evaluations": degraded_count,
            "total_evaluations": len(history),
            "retraining_recommended": degraded_count >= 3 or trend == "declining",
        }

    async def get_performance_summary(self) -> Dict[str, any]:
        """
        Get current performance summary

        Returns:
            dict: Performance summary
        """
        # Get latest performance log
        latest_query = (
            select(PerformanceLog).order_by(PerformanceLog.evaluated_at.desc()).limit(1)
        )
        latest_result = await self.db_session.execute(latest_query)
        latest_log = latest_result.scalar_one_or_none()

        if not latest_log:
            return {
                "status": "no_data",
                "message": "No performance evaluations yet",
            }

        # Get trend
        trend = await self.get_performance_trend(30)

        return {
            "status": "ok" if not latest_log.performance_degraded else "degraded",
            "last_evaluation": latest_log.evaluated_at.isoformat(),
            "current_metrics": {
                "f1_score": latest_log.f1_score,
                "precision": latest_log.precision,
                "recall": latest_log.recall,
                "accuracy": latest_log.accuracy,
            },
            "thresholds": {
                "f1_score": self.f1_threshold,
                "precision": self.precision_threshold,
                "recall": self.recall_threshold,
            },
            "trend": trend,
            "retraining_recommended": (
                latest_log.performance_degraded or trend.get("retraining_recommended")
            ),
        }
