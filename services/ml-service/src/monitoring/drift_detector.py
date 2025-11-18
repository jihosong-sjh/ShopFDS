"""
Data Drift Detection using Kolmogorov-Smirnov Test

This module detects data drift in transaction features to trigger
model retraining when the data distribution changes significantly.

Statistical Method:
- Kolmogorov-Smirnov (KS) test for continuous features
- Chi-square test for categorical features
- Population Stability Index (PSI) for overall drift
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import stats

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.transaction import Transaction
from src.models.data_drift_log import DataDriftLog

logger = logging.getLogger(__name__)


class DriftDetector:
    """Detects data drift in transaction features"""

    def __init__(
        self,
        db_session: AsyncSession,
        ks_threshold: float = 0.05,
        psi_threshold: float = 0.1,
        reference_period_days: int = 90,
        detection_period_days: int = 7,
    ):
        """
        Initialize DriftDetector

        Args:
            db_session: Database session
            ks_threshold: KS test p-value threshold (default: 0.05)
            psi_threshold: PSI threshold for drift alert (default: 0.1)
            reference_period_days: Days for reference distribution (default: 90)
            detection_period_days: Days for current distribution (default: 7)
        """
        self.db_session = db_session
        self.ks_threshold = ks_threshold
        self.psi_threshold = psi_threshold
        self.reference_period_days = reference_period_days
        self.detection_period_days = detection_period_days

    async def get_feature_distribution(
        self,
        feature_name: str,
        start_date: datetime,
        end_date: datetime,
    ) -> np.ndarray:
        """
        Get feature distribution for a time period

        Args:
            feature_name: Name of the feature
            start_date: Start date
            end_date: End date

        Returns:
            np.ndarray: Feature values
        """
        # Map feature name to database column
        feature_mapping = {
            "amount": Transaction.amount,
            "fds_risk_score": Transaction.fds_risk_score,
            # Add more features as needed
        }

        if feature_name not in feature_mapping:
            raise ValueError(f"Unknown feature: {feature_name}")

        column = feature_mapping[feature_name]

        # Query feature values
        query = select(column).where(
            and_(
                Transaction.created_at >= start_date,
                Transaction.created_at < end_date,
                column.isnot(None),
            )
        )
        result = await self.db_session.execute(query)
        values = [float(row[0]) for row in result.all()]

        return np.array(values)

    def calculate_ks_statistic(
        self,
        reference_data: np.ndarray,
        current_data: np.ndarray,
    ) -> Tuple[float, float]:
        """
        Calculate Kolmogorov-Smirnov statistic

        Args:
            reference_data: Reference distribution
            current_data: Current distribution

        Returns:
            tuple: (KS statistic, p-value)
        """
        if len(reference_data) == 0 or len(current_data) == 0:
            logger.warning("[DRIFT] Empty data for KS test")
            return 0.0, 1.0

        ks_statistic, p_value = stats.ks_2samp(reference_data, current_data)

        logger.info(f"[DRIFT] KS Statistic: {ks_statistic:.4f}, p-value: {p_value:.4f}")

        return ks_statistic, p_value

    def calculate_psi(
        self,
        reference_data: np.ndarray,
        current_data: np.ndarray,
        bins: int = 10,
    ) -> float:
        """
        Calculate Population Stability Index (PSI)

        PSI = sum((actual% - expected%) * ln(actual% / expected%))

        PSI < 0.1: No significant change
        0.1 <= PSI < 0.2: Moderate change
        PSI >= 0.2: Significant change (retraining recommended)

        Args:
            reference_data: Reference distribution (expected)
            current_data: Current distribution (actual)
            bins: Number of bins for discretization

        Returns:
            float: PSI value
        """
        if len(reference_data) == 0 or len(current_data) == 0:
            logger.warning("[DRIFT] Empty data for PSI calculation")
            return 0.0

        # Create bins based on reference data
        _, bin_edges = np.histogram(reference_data, bins=bins)

        # Calculate distribution for reference and current data
        reference_counts, _ = np.histogram(reference_data, bins=bin_edges)
        current_counts, _ = np.histogram(current_data, bins=bin_edges)

        # Convert to percentages (add small epsilon to avoid division by zero)
        epsilon = 1e-10
        reference_pct = (reference_counts + epsilon) / (
            len(reference_data) + epsilon * bins
        )
        current_pct = (current_counts + epsilon) / (len(current_data) + epsilon * bins)

        # Calculate PSI
        psi = np.sum(
            (current_pct - reference_pct) * np.log(current_pct / reference_pct)
        )

        logger.info(f"[DRIFT] PSI: {psi:.4f}")

        return psi

    async def detect_feature_drift(self, feature_name: str) -> Dict[str, any]:
        """
        Detect drift for a specific feature

        Args:
            feature_name: Name of the feature

        Returns:
            dict: Drift detection result
        """
        now = datetime.utcnow()

        # Reference period (e.g., 90 days ago)
        reference_end = now - timedelta(days=self.detection_period_days)
        reference_start = reference_end - timedelta(days=self.reference_period_days)

        # Current period (e.g., last 7 days)
        current_start = now - timedelta(days=self.detection_period_days)
        current_end = now

        # Get distributions
        reference_data = await self.get_feature_distribution(
            feature_name, reference_start, reference_end
        )
        current_data = await self.get_feature_distribution(
            feature_name, current_start, current_end
        )

        if len(reference_data) < 100 or len(current_data) < 100:
            logger.warning(
                f"[DRIFT] Insufficient data for {feature_name} "
                f"(reference: {len(reference_data)}, current: {len(current_data)})"
            )
            return {
                "feature_name": feature_name,
                "drift_detected": False,
                "reason": "insufficient_data",
            }

        # Calculate KS statistic
        ks_statistic, p_value = self.calculate_ks_statistic(
            reference_data, current_data
        )

        # Calculate PSI
        psi = self.calculate_psi(reference_data, current_data)

        # Determine if drift is detected
        ks_drift = p_value < self.ks_threshold
        psi_drift = psi >= self.psi_threshold

        drift_detected = ks_drift or psi_drift

        # Calculate distribution statistics
        reference_stats = {
            "mean": float(np.mean(reference_data)),
            "std": float(np.std(reference_data)),
            "min": float(np.min(reference_data)),
            "max": float(np.max(reference_data)),
        }

        current_stats = {
            "mean": float(np.mean(current_data)),
            "std": float(np.std(current_data)),
            "min": float(np.min(current_data)),
            "max": float(np.max(current_data)),
        }

        logger.info(
            f"[DRIFT] Feature: {feature_name}, "
            f"Drift detected: {drift_detected} "
            f"(KS: {ks_drift}, PSI: {psi_drift})"
        )

        return {
            "feature_name": feature_name,
            "drift_detected": drift_detected,
            "ks_statistic": ks_statistic,
            "ks_p_value": p_value,
            "ks_drift": ks_drift,
            "psi": psi,
            "psi_drift": psi_drift,
            "reference_stats": reference_stats,
            "current_stats": current_stats,
            "reference_sample_size": len(reference_data),
            "current_sample_size": len(current_data),
        }

    async def detect_all_features_drift(
        self, features: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """
        Detect drift across all monitored features

        Args:
            features: List of features to monitor (default: all critical features)

        Returns:
            dict: Overall drift detection result
        """
        if features is None:
            features = [
                "amount",
                "fds_risk_score",
            ]

        logger.info(f"[DRIFT] Starting drift detection for features: {features}")

        feature_results = []
        drift_detected_count = 0

        for feature_name in features:
            try:
                result = await self.detect_feature_drift(feature_name)
                feature_results.append(result)
                if result.get("drift_detected"):
                    drift_detected_count += 1
            except Exception as e:
                logger.error(
                    f"[DRIFT] Error detecting drift for {feature_name}: {str(e)}"
                )
                feature_results.append(
                    {
                        "feature_name": feature_name,
                        "drift_detected": False,
                        "error": str(e),
                    }
                )

        # Overall drift status
        overall_drift = drift_detected_count > 0

        # Create drift log
        drift_log = DataDriftLog(
            detected_at=datetime.utcnow(),
            drift_detected=overall_drift,
            features_monitored=len(features),
            features_drifted=drift_detected_count,
            drift_details={
                "features": feature_results,
                "ks_threshold": self.ks_threshold,
                "psi_threshold": self.psi_threshold,
            },
        )
        self.db_session.add(drift_log)
        await self.db_session.commit()
        await self.db_session.refresh(drift_log)

        logger.info(
            f"[DRIFT] Overall drift detection: {overall_drift} "
            f"({drift_detected_count}/{len(features)} features drifted)"
        )

        return {
            "drift_detected": overall_drift,
            "features_monitored": len(features),
            "features_drifted": drift_detected_count,
            "feature_results": feature_results,
            "log_id": drift_log.id,
            "detected_at": drift_log.detected_at.isoformat(),
        }

    async def get_drift_history(self, days: int = 30) -> List[Dict]:
        """
        Get drift detection history

        Args:
            days: Number of days to look back

        Returns:
            list: Drift detection history
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        query = (
            select(DataDriftLog)
            .where(DataDriftLog.detected_at >= start_date)
            .order_by(DataDriftLog.detected_at.desc())
        )
        result = await self.db_session.execute(query)
        drift_logs = result.scalars().all()

        history = []
        for log in drift_logs:
            history.append(
                {
                    "id": log.id,
                    "detected_at": log.detected_at.isoformat(),
                    "drift_detected": log.drift_detected,
                    "features_monitored": log.features_monitored,
                    "features_drifted": log.features_drifted,
                    "drift_details": log.drift_details,
                }
            )

        return history

    async def get_drift_summary(self) -> Dict[str, any]:
        """
        Get drift summary statistics

        Returns:
            dict: Drift summary
        """
        # Count recent drifts (last 30 days)
        recent_date = datetime.utcnow() - timedelta(days=30)

        drift_count_query = select(func.count(DataDriftLog.id)).where(
            and_(
                DataDriftLog.detected_at >= recent_date,
                DataDriftLog.drift_detected == True,
            )
        )
        drift_count_result = await self.db_session.execute(drift_count_query)
        drift_count = drift_count_result.scalar() or 0

        # Get last drift
        last_drift_query = (
            select(DataDriftLog)
            .where(DataDriftLog.drift_detected == True)
            .order_by(DataDriftLog.detected_at.desc())
            .limit(1)
        )
        last_drift_result = await self.db_session.execute(last_drift_query)
        last_drift = last_drift_result.scalar_one_or_none()

        return {
            "recent_drift_count_30d": drift_count,
            "last_drift_detected_at": (
                last_drift.detected_at.isoformat() if last_drift else None
            ),
            "last_drift_features": (
                last_drift.features_drifted if last_drift else None
            ),
            "retraining_recommended": drift_count >= 3,  # 3 drifts in 30 days
        }
