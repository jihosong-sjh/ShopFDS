"""
Auto Labeling System for Chargeback Data

This module automatically labels transaction data based on chargeback
and fraud reports for ML model training.

Business Logic:
- Chargebacks are automatically labeled as fraud
- Manual fraud reports are labeled as fraud with confidence score
- Transactions older than 90 days with no chargeback are labeled as legitimate
- Minimum 100 chargebacks required to trigger auto-labeling
"""

import logging
from datetime import datetime, timedelta
from typing import Dict

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.transaction import Transaction
from src.models.fraud_label import FraudLabel

logger = logging.getLogger(__name__)


class AutoLabeler:
    """Automatically labels transactions based on chargeback and feedback data"""

    def __init__(
        self,
        db_session: AsyncSession,
        min_chargeback_count: int = 100,
        safe_period_days: int = 90,
    ):
        """
        Initialize AutoLabeler

        Args:
            db_session: Database session
            min_chargeback_count: Minimum chargebacks to trigger auto-labeling
            safe_period_days: Days to wait before labeling as legitimate
        """
        self.db_session = db_session
        self.min_chargeback_count = min_chargeback_count
        self.safe_period_days = safe_period_days

    async def check_chargeback_threshold(self) -> Dict[str, any]:
        """
        Check if we have enough chargebacks to trigger auto-labeling

        Returns:
            dict: Chargeback count and threshold status
        """
        # Count unlabeled chargebacks
        query = select(func.count(Transaction.id)).where(
            and_(
                Transaction.is_chargeback.is_(True),
                Transaction.fraud_label_id.is_(None),
            )
        )
        result = await self.db_session.execute(query)
        unlabeled_count = result.scalar() or 0

        # Count total chargebacks
        total_query = select(func.count(Transaction.id)).where(
            Transaction.is_chargeback.is_(True)
        )
        total_result = await self.db_session.execute(total_query)
        total_count = total_result.scalar() or 0

        threshold_met = unlabeled_count >= self.min_chargeback_count

        logger.info(
            f"[AUTO-LABELER] Chargeback count: {unlabeled_count}/{total_count} "
            f"(threshold: {self.min_chargeback_count}, met: {threshold_met})"
        )

        return {
            "unlabeled_count": unlabeled_count,
            "total_count": total_count,
            "threshold": self.min_chargeback_count,
            "threshold_met": threshold_met,
        }

    async def label_chargebacks(self) -> int:
        """
        Automatically label all chargeback transactions as fraud

        Returns:
            int: Number of transactions labeled
        """
        # Find unlabeled chargebacks
        query = select(Transaction).where(
            and_(
                Transaction.is_chargeback.is_(True),
                Transaction.fraud_label_id.is_(None),
            )
        )
        result = await self.db_session.execute(query)
        transactions = result.scalars().all()

        labeled_count = 0
        for transaction in transactions:
            # Create fraud label
            fraud_label = FraudLabel(
                transaction_id=transaction.id,
                is_fraud=True,
                label_source="chargeback",
                confidence_score=1.0,
                labeled_by="system",
                labeled_at=datetime.utcnow(),
                notes="Automatically labeled from chargeback data",
            )
            self.db_session.add(fraud_label)
            transaction.fraud_label_id = fraud_label.id
            labeled_count += 1

        await self.db_session.commit()

        logger.info(f"[AUTO-LABELER] Labeled {labeled_count} chargebacks as fraud")

        return labeled_count

    async def label_manual_reports(self) -> int:
        """
        Label transactions with manual fraud reports

        Returns:
            int: Number of transactions labeled
        """
        # Find transactions with fraud reports but no label
        query = select(Transaction).where(
            and_(
                Transaction.fraud_reported.is_(True),
                Transaction.fraud_label_id.is_(None),
            )
        )
        result = await self.db_session.execute(query)
        transactions = result.scalars().all()

        labeled_count = 0
        for transaction in transactions:
            # Create fraud label with slightly lower confidence
            fraud_label = FraudLabel(
                transaction_id=transaction.id,
                is_fraud=True,
                label_source="user_report",
                confidence_score=0.95,
                labeled_by="system",
                labeled_at=datetime.utcnow(),
                notes="Automatically labeled from user fraud report",
            )
            self.db_session.add(fraud_label)
            transaction.fraud_label_id = fraud_label.id
            labeled_count += 1

        await self.db_session.commit()

        logger.info(f"[AUTO-LABELER] Labeled {labeled_count} fraud reports as fraud")

        return labeled_count

    async def label_safe_transactions(self) -> int:
        """
        Label old transactions with no chargeback as legitimate

        Returns:
            int: Number of transactions labeled
        """
        safe_date = datetime.utcnow() - timedelta(days=self.safe_period_days)

        # Find old transactions with no chargeback or fraud report
        query = select(Transaction).where(
            and_(
                Transaction.created_at < safe_date,
                Transaction.is_chargeback.is_(False),
                Transaction.fraud_reported.is_(False),
                Transaction.fraud_label_id.is_(None),
            )
        )
        result = await self.db_session.execute(query)
        transactions = result.scalars().all()

        labeled_count = 0
        for transaction in transactions:
            # Create legitimate label
            fraud_label = FraudLabel(
                transaction_id=transaction.id,
                is_fraud=False,
                label_source="auto_safe_period",
                confidence_score=0.9,
                labeled_by="system",
                labeled_at=datetime.utcnow(),
                notes=f"Automatically labeled as legitimate after {self.safe_period_days} days with no chargeback",
            )
            self.db_session.add(fraud_label)
            transaction.fraud_label_id = fraud_label.id
            labeled_count += 1

        await self.db_session.commit()

        logger.info(
            f"[AUTO-LABELER] Labeled {labeled_count} old transactions as legitimate"
        )

        return labeled_count

    async def run_auto_labeling(self) -> Dict[str, any]:
        """
        Run complete auto-labeling pipeline

        Returns:
            dict: Labeling results and statistics
        """
        logger.info("[AUTO-LABELER] Starting auto-labeling pipeline")

        # Check threshold
        threshold_status = await self.check_chargeback_threshold()

        if not threshold_status["threshold_met"]:
            logger.warning(
                f"[AUTO-LABELER] Threshold not met "
                f"({threshold_status['unlabeled_count']}/{self.min_chargeback_count})"
            )
            return {
                "success": False,
                "reason": "threshold_not_met",
                "threshold_status": threshold_status,
                "labeled_counts": {
                    "chargebacks": 0,
                    "manual_reports": 0,
                    "safe_transactions": 0,
                },
            }

        # Label chargebacks
        chargeback_count = await self.label_chargebacks()

        # Label manual reports
        report_count = await self.label_manual_reports()

        # Label safe transactions
        safe_count = await self.label_safe_transactions()

        total_labeled = chargeback_count + report_count + safe_count

        logger.info(
            f"[AUTO-LABELER] Auto-labeling complete. "
            f"Total labeled: {total_labeled} "
            f"(chargebacks: {chargeback_count}, reports: {report_count}, safe: {safe_count})"
        )

        return {
            "success": True,
            "threshold_status": threshold_status,
            "labeled_counts": {
                "chargebacks": chargeback_count,
                "manual_reports": report_count,
                "safe_transactions": safe_count,
                "total": total_labeled,
            },
        }

    async def get_labeling_statistics(self) -> Dict[str, any]:
        """
        Get current labeling statistics

        Returns:
            dict: Labeling statistics
        """
        # Count labeled transactions by source
        fraud_query = select(
            FraudLabel.label_source, func.count(FraudLabel.id)
        ).group_by(FraudLabel.label_source)
        fraud_result = await self.db_session.execute(fraud_query)
        label_counts = dict(fraud_result.all())

        # Count unlabeled transactions
        unlabeled_query = select(func.count(Transaction.id)).where(
            Transaction.fraud_label_id.is_(None)
        )
        unlabeled_result = await self.db_session.execute(unlabeled_query)
        unlabeled_count = unlabeled_result.scalar() or 0

        # Total transactions
        total_query = select(func.count(Transaction.id))
        total_result = await self.db_session.execute(total_query)
        total_count = total_result.scalar() or 0

        labeled_count = total_count - unlabeled_count
        labeling_rate = (labeled_count / total_count * 100) if total_count > 0 else 0

        return {
            "total_transactions": total_count,
            "labeled_transactions": labeled_count,
            "unlabeled_transactions": unlabeled_count,
            "labeling_rate_percent": round(labeling_rate, 2),
            "label_counts_by_source": label_counts,
        }
