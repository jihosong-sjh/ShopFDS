"""
Feedback Collector for User Fraud Reports

This module collects and processes user feedback on fraudulent transactions
for ML model improvement and retraining.

Business Logic:
- Collects user fraud reports from customers and merchants
- Validates and enriches feedback data
- Stores feedback for model retraining
- Provides analytics on feedback trends
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.transaction import Transaction
from src.models.fraud_label import FraudLabel, LabelSource
from src.models.fraud_feedback import FraudFeedback

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """Collects and processes user fraud feedback"""

    def __init__(
        self,
        db_session: AsyncSession,
        min_feedback_count: int = 50,
        feedback_confidence: float = 0.9,
    ):
        """
        Initialize FeedbackCollector

        Args:
            db_session: Database session
            min_feedback_count: Minimum feedback count to trigger retraining
            feedback_confidence: Confidence score for user feedback labels
        """
        self.db_session = db_session
        self.min_feedback_count = min_feedback_count
        self.feedback_confidence = feedback_confidence

    async def submit_fraud_report(
        self,
        transaction_id: UUID,
        user_id: UUID,
        report_type: str,
        reason: str,
        additional_info: Optional[Dict] = None,
    ) -> Dict[str, any]:
        """
        Submit a fraud report for a transaction

        Args:
            transaction_id: Transaction ID
            user_id: User submitting the report
            report_type: Type of report (customer, merchant, security_team)
            reason: Reason for fraud report
            additional_info: Additional information

        Returns:
            dict: Report submission result
        """
        # Check if transaction exists
        transaction_query = select(Transaction).where(Transaction.id == transaction_id)
        transaction_result = await self.db_session.execute(transaction_query)
        transaction = transaction_result.scalar_one_or_none()

        if not transaction:
            logger.error(f"[FEEDBACK] Transaction not found: {transaction_id}")
            return {
                "success": False,
                "error": "transaction_not_found",
            }

        # Check if already reported
        existing_feedback_query = select(FraudFeedback).where(
            and_(
                FraudFeedback.transaction_id == transaction_id,
                FraudFeedback.user_id == user_id,
            )
        )
        existing_result = await self.db_session.execute(existing_feedback_query)
        existing_feedback = existing_result.scalar_one_or_none()

        if existing_feedback:
            logger.warning(
                f"[FEEDBACK] Transaction {transaction_id} already reported by user {user_id}"
            )
            return {
                "success": False,
                "error": "already_reported",
                "feedback_id": existing_feedback.id,
            }

        # Create feedback record
        feedback = FraudFeedback(
            transaction_id=transaction_id,
            user_id=user_id,
            report_type=report_type,
            reason=reason,
            additional_info=additional_info or {},
            reported_at=datetime.utcnow(),
        )
        self.db_session.add(feedback)

        # Update transaction fraud_reported flag
        transaction.fraud_reported = True
        transaction.fraud_report_date = datetime.utcnow()
        transaction.fraud_report_reason = reason

        await self.db_session.commit()
        await self.db_session.refresh(feedback)

        logger.info(
            f"[FEEDBACK] Fraud report submitted: {feedback.id} "
            f"(transaction: {transaction_id}, user: {user_id})"
        )

        return {
            "success": True,
            "feedback_id": feedback.id,
            "transaction_id": transaction_id,
        }

    async def process_feedback_for_labeling(self) -> Dict[str, any]:
        """
        Process fraud feedback and create labels for ML training

        Returns:
            dict: Processing results
        """
        # Find unprocessed feedback
        feedback_query = select(FraudFeedback).where(FraudFeedback.processed.is_(False))
        feedback_result = await self.db_session.execute(feedback_query)
        feedbacks = feedback_result.scalars().all()

        labeled_count = 0
        for feedback in feedbacks:
            # Check if transaction already has a label
            label_query = select(FraudLabel).where(
                FraudLabel.transaction_id == feedback.transaction_id
            )
            label_result = await self.db_session.execute(label_query)
            existing_label = label_result.scalar_one_or_none()

            if existing_label:
                # Update existing label if from user report
                if existing_label.label_source == LabelSource.USER_REPORT:
                    existing_label.confidence_score = min(
                        1.0, existing_label.confidence_score + 0.05
                    )
                    existing_label.notes = (
                        f"{existing_label.notes}; Additional report: {feedback.reason}"
                    )
                    feedback.processed = True
                    labeled_count += 1
            else:
                # Create new label
                fraud_label = FraudLabel(
                    transaction_id=feedback.transaction_id,
                    is_fraud=True,
                    label_source=LabelSource.USER_REPORT,
                    confidence_score=self.feedback_confidence,
                    labeled_by=str(feedback.user_id),
                    labeled_at=datetime.utcnow(),
                    notes=f"User fraud report: {feedback.reason}",
                )
                self.db_session.add(fraud_label)

                # Update transaction
                transaction_query = select(Transaction).where(
                    Transaction.id == feedback.transaction_id
                )
                transaction_result = await self.db_session.execute(transaction_query)
                transaction = transaction_result.scalar_one()
                transaction.fraud_label_id = fraud_label.id

                feedback.processed = True
                labeled_count += 1

        await self.db_session.commit()

        logger.info(
            f"[FEEDBACK] Processed {labeled_count} feedback records for labeling"
        )

        return {
            "success": True,
            "processed_count": labeled_count,
        }

    async def get_feedback_statistics(self, days: int = 30) -> Dict[str, any]:
        """
        Get feedback statistics for the specified period

        Args:
            days: Number of days to look back

        Returns:
            dict: Feedback statistics
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # Count feedback by type
        type_query = (
            select(
                FraudFeedback.report_type,
                func.count(FraudFeedback.id),
            )
            .where(FraudFeedback.reported_at >= start_date)
            .group_by(FraudFeedback.report_type)
        )
        type_result = await self.db_session.execute(type_query)
        feedback_by_type = dict(type_result.all())

        # Count processed vs unprocessed
        processed_query = select(func.count(FraudFeedback.id)).where(
            and_(
                FraudFeedback.reported_at >= start_date,
                FraudFeedback.processed.is_(True),
            )
        )
        processed_result = await self.db_session.execute(processed_query)
        processed_count = processed_result.scalar() or 0

        unprocessed_query = select(func.count(FraudFeedback.id)).where(
            and_(
                FraudFeedback.reported_at >= start_date,
                FraudFeedback.processed.is_(False),
            )
        )
        unprocessed_result = await self.db_session.execute(unprocessed_query)
        unprocessed_count = unprocessed_result.scalar() or 0

        total_count = processed_count + unprocessed_count

        # Common fraud reasons
        reason_query = (
            select(
                FraudFeedback.reason,
                func.count(FraudFeedback.id),
            )
            .where(FraudFeedback.reported_at >= start_date)
            .group_by(FraudFeedback.reason)
            .order_by(func.count(FraudFeedback.id).desc())
            .limit(10)
        )
        reason_result = await self.db_session.execute(reason_query)
        top_reasons = dict(reason_result.all())

        return {
            "period_days": days,
            "total_feedback": total_count,
            "processed_feedback": processed_count,
            "unprocessed_feedback": unprocessed_count,
            "feedback_by_type": feedback_by_type,
            "top_fraud_reasons": top_reasons,
            "ready_for_retraining": unprocessed_count >= self.min_feedback_count,
        }

    async def get_disputed_predictions(self) -> List[Dict]:
        """
        Get transactions where user feedback contradicts ML prediction

        Returns:
            list: Disputed predictions
        """
        # Find transactions with user feedback but ML predicted safe
        dispute_query = (
            select(Transaction, FraudFeedback, FraudLabel)
            .join(FraudFeedback, Transaction.id == FraudFeedback.transaction_id)
            .join(FraudLabel, Transaction.fraud_label_id == FraudLabel.id)
            .where(
                and_(
                    FraudLabel.label_source == LabelSource.ML_PREDICTION,
                    FraudLabel.is_fraud.is_(False),
                    Transaction.fraud_reported.is_(True),
                )
            )
        )
        dispute_result = await self.db_session.execute(dispute_query)
        disputes = dispute_result.all()

        disputed_list = []
        for transaction, feedback, label in disputes:
            disputed_list.append(
                {
                    "transaction_id": transaction.id,
                    "amount": float(transaction.amount),
                    "ml_prediction": "safe",
                    "user_feedback": "fraud",
                    "reason": feedback.reason,
                    "reported_at": feedback.reported_at.isoformat(),
                    "fds_risk_score": transaction.fds_risk_score,
                }
            )

        logger.info(f"[FEEDBACK] Found {len(disputed_list)} disputed predictions")

        return disputed_list

    async def check_retraining_threshold(self) -> Dict[str, any]:
        """
        Check if we have enough unprocessed feedback to trigger retraining

        Returns:
            dict: Retraining threshold status
        """
        unprocessed_query = select(func.count(FraudFeedback.id)).where(
            FraudFeedback.processed.is_(False)
        )
        unprocessed_result = await self.db_session.execute(unprocessed_query)
        unprocessed_count = unprocessed_result.scalar() or 0

        threshold_met = unprocessed_count >= self.min_feedback_count

        logger.info(
            f"[FEEDBACK] Unprocessed feedback count: {unprocessed_count}/{self.min_feedback_count} "
            f"(threshold met: {threshold_met})"
        )

        return {
            "unprocessed_count": unprocessed_count,
            "threshold": self.min_feedback_count,
            "threshold_met": threshold_met,
        }
