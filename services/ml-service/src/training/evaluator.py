"""
Model Evaluation Metrics

ML 모델의 성능을 평가하기 위한 다양한 메트릭을 계산합니다.

주요 메트릭:
1. Precision: 사기로 예측한 것 중 실제 사기 비율
2. Recall: 실제 사기 중 탐지한 비율
3. F1 Score: Precision과 Recall의 조화 평균
4. ROC-AUC: 전체 임계값에 대한 성능
5. Confusion Matrix: TP, TN, FP, FN
"""

import logging
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
    precision_recall_curve,
    roc_curve,
)


logger = logging.getLogger(__name__)


class ModelEvaluator:
    """
    모델 평가 클래스

    다양한 메트릭을 계산하고 종합 리포트를 생성합니다.
    """

    def __init__(self):
        """초기화"""
        pass

    def evaluate(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        모델 성능 평가 (종합)

        Args:
            y_true: 실제 레이블 (0: 정상, 1: 사기)
            y_pred: 예측 레이블
            y_proba: 예측 확률 (옵션)

        Returns:
            평가 메트릭 딕셔너리
        """
        logger.info(f"[Evaluator] Evaluating {len(y_true)} samples")

        # 기본 메트릭
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        # Confusion Matrix
        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel()

        # False Positive Rate, False Negative Rate
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

        # ROC-AUC (확률이 있는 경우)
        roc_auc = None
        if y_proba is not None:
            try:
                roc_auc = roc_auc_score(y_true, y_proba)
            except Exception as e:
                logger.warning(f"[Evaluator] Failed to calculate ROC-AUC: {e}")

        # 결과 딕셔너리
        metrics = {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "roc_auc": float(roc_auc) if roc_auc is not None else None,
            "false_positive_rate": float(fpr),
            "false_negative_rate": float(fnr),
            "true_positives": int(tp),
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "confusion_matrix": cm.tolist(),
            "total_samples": len(y_true),
            "fraud_samples": int((y_true == 1).sum()),
            "normal_samples": int((y_true == 0).sum()),
        }

        logger.info(
            f"[Evaluator] Metrics: Accuracy={accuracy:.4f}, Precision={precision:.4f}, "
            f"Recall={recall:.4f}, F1={f1:.4f}, FPR={fpr:.4f}, FNR={fnr:.4f}"
        )

        return metrics

    def evaluate_at_thresholds(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        thresholds: Optional[np.ndarray] = None,
    ) -> pd.DataFrame:
        """
        여러 임계값에서 메트릭 계산

        Args:
            y_true: 실제 레이블
            y_proba: 예측 확률
            thresholds: 임계값 배열 (None이면 0.1 ~ 0.9, 0.1 간격)

        Returns:
            임계값별 메트릭 DataFrame
        """
        if thresholds is None:
            thresholds = np.arange(0.1, 1.0, 0.1)

        logger.info(f"[Evaluator] Evaluating at {len(thresholds)} thresholds")

        results = []

        for threshold in thresholds:
            y_pred = (y_proba >= threshold).astype(int)

            precision = precision_score(y_true, y_pred, zero_division=0)
            recall = recall_score(y_true, y_pred, zero_division=0)
            f1 = f1_score(y_true, y_pred, zero_division=0)

            cm = confusion_matrix(y_true, y_pred)
            tn, fp, fn, tp = cm.ravel()

            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

            results.append(
                {
                    "threshold": float(threshold),
                    "precision": float(precision),
                    "recall": float(recall),
                    "f1_score": float(f1),
                    "false_positive_rate": float(fpr),
                    "true_positives": int(tp),
                    "false_positives": int(fp),
                }
            )

        results_df = pd.DataFrame(results)

        return results_df

    def generate_report(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: Optional[np.ndarray] = None,
        target_names: Optional[list] = None,
    ) -> str:
        """
        분류 리포트 생성 (텍스트 형식)

        Args:
            y_true: 실제 레이블
            y_pred: 예측 레이블
            y_proba: 예측 확률 (옵션)
            target_names: 클래스 이름 (기본: ["Normal", "Fraud"])

        Returns:
            분류 리포트 텍스트
        """
        target_names = target_names or ["Normal", "Fraud"]

        report = classification_report(
            y_true, y_pred, target_names=target_names, digits=4
        )

        # 추가 메트릭
        metrics = self.evaluate(y_true, y_pred, y_proba)

        report += f"\n\n=== Additional Metrics ===\n"
        report += (
            f"ROC-AUC Score: {metrics['roc_auc']:.4f}\n" if metrics["roc_auc"] else ""
        )
        report += f"False Positive Rate: {metrics['false_positive_rate']:.4f}\n"
        report += f"False Negative Rate: {metrics['false_negative_rate']:.4f}\n"
        report += f"\nTotal Samples: {metrics['total_samples']}\n"
        report += f"Fraud Samples: {metrics['fraud_samples']} ({metrics['fraud_samples']/metrics['total_samples']:.2%})\n"

        return report


def evaluate_model(
    y_true: np.ndarray, y_pred: np.ndarray, y_proba: Optional[np.ndarray] = None
) -> Dict[str, Any]:
    """
    모델 평가 (편의 함수)

    Args:
        y_true: 실제 레이블
        y_pred: 예측 레이블
        y_proba: 예측 확률 (옵션)

    Returns:
        평가 메트릭

    Example:
        >>> y_true = np.array([0, 0, 1, 1, 1])
        >>> y_pred = np.array([0, 1, 1, 1, 0])
        >>> y_proba = np.array([0.1, 0.6, 0.9, 0.8, 0.3])
        >>> metrics = evaluate_model(y_true, y_pred, y_proba)
        >>> print(f"F1 Score: {metrics['f1_score']:.4f}")
    """
    evaluator = ModelEvaluator()
    return evaluator.evaluate(y_true, y_pred, y_proba)


def find_optimal_threshold(
    y_true: np.ndarray, y_proba: np.ndarray, metric: str = "f1"
) -> float:
    """
    최적 임계값 찾기

    Args:
        y_true: 실제 레이블
        y_proba: 예측 확률
        metric: 최적화할 메트릭 (f1, precision, recall)

    Returns:
        최적 임계값

    Example:
        >>> y_true = np.array([0, 0, 1, 1, 1])
        >>> y_proba = np.array([0.1, 0.4, 0.7, 0.8, 0.6])
        >>> optimal_threshold = find_optimal_threshold(y_true, y_proba, metric="f1")
        >>> print(f"Optimal threshold: {optimal_threshold:.2f}")
    """
    evaluator = ModelEvaluator()
    thresholds = np.arange(0.1, 1.0, 0.01)

    results = evaluator.evaluate_at_thresholds(y_true, y_proba, thresholds)

    # 메트릭 선택
    if metric == "f1":
        metric_col = "f1_score"
    elif metric == "precision":
        metric_col = "precision"
    elif metric == "recall":
        metric_col = "recall"
    else:
        raise ValueError(f"Unknown metric: {metric}")

    # 최적 임계값
    best_idx = results[metric_col].idxmax()
    optimal_threshold = results.loc[best_idx, "threshold"]

    logger.info(
        f"[Evaluator] Optimal threshold: {optimal_threshold:.2f} "
        f"({metric}={results.loc[best_idx, metric_col]:.4f})"
    )

    return float(optimal_threshold)
