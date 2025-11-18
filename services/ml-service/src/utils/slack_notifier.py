"""
Slack Notification System

Sends notifications to Slack for important ML events:
- Performance degradation
- Data drift detection
- Retraining completion
- Model deployment
"""

import logging
from typing import Dict, Optional
import requests

from src.config import get_settings

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Send notifications to Slack"""

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize SlackNotifier

        Args:
            webhook_url: Slack webhook URL (optional, uses config if not provided)
        """
        settings = get_settings()
        self.webhook_url = webhook_url or settings.SLACK_WEBHOOK_URL
        self.enabled = bool(self.webhook_url)

    def send_message(
        self,
        message: str,
        title: Optional[str] = None,
        color: str = "good",
        fields: Optional[list] = None,
    ) -> bool:
        """
        Send message to Slack

        Args:
            message: Message text
            title: Message title
            color: Color (good, warning, danger)
            fields: Additional fields

        Returns:
            bool: Success status
        """
        if not self.enabled:
            logger.warning(
                "[SLACK] Slack webhook not configured, skipping notification"
            )
            return False

        try:
            attachment = {
                "color": color,
                "text": message,
                "ts": int(datetime.utcnow().timestamp()),
            }

            if title:
                attachment["title"] = title

            if fields:
                attachment["fields"] = fields

            payload = {
                "attachments": [attachment],
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=5,
            )

            if response.status_code == 200:
                logger.info("[SLACK] Notification sent successfully")
                return True
            else:
                logger.error(
                    f"[SLACK] Failed to send notification: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"[SLACK] Error sending notification: {str(e)}")
            return False

    def notify_performance_degradation(
        self,
        current_f1: float,
        threshold: float,
        metrics: Dict,
    ) -> bool:
        """
        Notify performance degradation

        Args:
            current_f1: Current F1 score
            threshold: F1 threshold
            metrics: Performance metrics

        Returns:
            bool: Success status
        """

        message = (
            f"[ALERT] Model performance has degraded below threshold\n"
            f"Current F1 Score: {current_f1:.4f} (Threshold: {threshold:.4f})"
        )

        fields = [
            {
                "title": "F1 Score",
                "value": f"{current_f1:.4f}",
                "short": True,
            },
            {
                "title": "Precision",
                "value": f"{metrics.get('precision', 0):.4f}",
                "short": True,
            },
            {
                "title": "Recall",
                "value": f"{metrics.get('recall', 0):.4f}",
                "short": True,
            },
            {
                "title": "Accuracy",
                "value": f"{metrics.get('accuracy', 0):.4f}",
                "short": True,
            },
        ]

        return self.send_message(
            message=message,
            title="[CRITICAL] Model Performance Degradation",
            color="danger",
            fields=fields,
        )

    def notify_data_drift(
        self,
        features_drifted: int,
        total_features: int,
        drift_details: Dict,
    ) -> bool:
        """
        Notify data drift detection

        Args:
            features_drifted: Number of features with drift
            total_features: Total features monitored
            drift_details: Drift detection details

        Returns:
            bool: Success status
        """
        message = (
            f"[WARNING] Data drift detected\n"
            f"{features_drifted} out of {total_features} features showing drift"
        )

        fields = []
        for feature in drift_details.get("features", []):
            if feature.get("drift_detected"):
                fields.append(
                    {
                        "title": f"Feature: {feature['feature_name']}",
                        "value": (
                            f"KS p-value: {feature.get('ks_p_value', 0):.4f}, "
                            f"PSI: {feature.get('psi', 0):.4f}"
                        ),
                        "short": False,
                    }
                )

        return self.send_message(
            message=message,
            title="[WARNING] Data Drift Detected",
            color="warning",
            fields=fields,
        )

    def notify_retraining_started(
        self,
        job_id: str,
        trigger_reason: str,
    ) -> bool:
        """
        Notify retraining started

        Args:
            job_id: Retraining job ID
            trigger_reason: Trigger reason

        Returns:
            bool: Success status
        """
        message = (
            f"[INFO] Model retraining started\n"
            f"Job ID: {job_id}\n"
            f"Reason: {trigger_reason}"
        )

        return self.send_message(
            message=message,
            title="[INFO] Retraining Started",
            color="good",
        )

    def notify_retraining_completed(
        self,
        job_id: str,
        metrics: Dict,
        duration_minutes: Optional[float] = None,
    ) -> bool:
        """
        Notify retraining completed

        Args:
            job_id: Retraining job ID
            metrics: Training metrics
            duration_minutes: Training duration in minutes

        Returns:
            bool: Success status
        """
        message = f"[SUCCESS] Model retraining completed\n" f"Job ID: {job_id}"

        if duration_minutes:
            message += f"\nDuration: {duration_minutes:.1f} minutes"

        fields = [
            {
                "title": "F1 Score",
                "value": f"{metrics.get('f1_score', 0):.4f}",
                "short": True,
            },
            {
                "title": "Precision",
                "value": f"{metrics.get('precision', 0):.4f}",
                "short": True,
            },
            {
                "title": "Recall",
                "value": f"{metrics.get('recall', 0):.4f}",
                "short": True,
            },
            {
                "title": "Accuracy",
                "value": f"{metrics.get('accuracy', 0):.4f}",
                "short": True,
            },
        ]

        return self.send_message(
            message=message,
            title="[SUCCESS] Retraining Completed",
            color="good",
            fields=fields,
        )

    def notify_retraining_failed(
        self,
        job_id: str,
        error_message: str,
    ) -> bool:
        """
        Notify retraining failed

        Args:
            job_id: Retraining job ID
            error_message: Error message

        Returns:
            bool: Success status
        """
        message = (
            f"[ERROR] Model retraining failed\n"
            f"Job ID: {job_id}\n"
            f"Error: {error_message}"
        )

        return self.send_message(
            message=message,
            title="[ERROR] Retraining Failed",
            color="danger",
        )

    def notify_model_deployed(
        self,
        model_version: str,
        deployment_type: str,
        metrics: Dict,
    ) -> bool:
        """
        Notify model deployed

        Args:
            model_version: Model version
            deployment_type: Deployment type (canary, production, etc.)
            metrics: Model metrics

        Returns:
            bool: Success status
        """
        message = (
            f"[INFO] New model deployed\n"
            f"Version: {model_version}\n"
            f"Deployment: {deployment_type}"
        )

        fields = [
            {
                "title": "F1 Score",
                "value": f"{metrics.get('f1_score', 0):.4f}",
                "short": True,
            },
            {
                "title": "Precision",
                "value": f"{metrics.get('precision', 0):.4f}",
                "short": True,
            },
        ]

        return self.send_message(
            message=message,
            title="[INFO] Model Deployed",
            color="good",
            fields=fields,
        )


# Singleton instance
_slack_notifier = None


def get_slack_notifier() -> SlackNotifier:
    """Get Slack notifier singleton instance"""
    global _slack_notifier
    if _slack_notifier is None:
        _slack_notifier = SlackNotifier()
    return _slack_notifier
