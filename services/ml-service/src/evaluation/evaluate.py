"""
모델 평가 스크립트

정확도, 정밀도, 재현율, F1 스코어 등 성능 지표 계산 및 시각화
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    roc_curve,
    precision_recall_curve,
    confusion_matrix,
    classification_report,
)
from sqlalchemy.orm import Session

# 프로젝트 내부 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent))

from models.ml_model import MLModel, get_production_model

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """
    ML 모델 평가 클래스

    다양한 성능 지표를 계산하고 시각화
    """

    def __init__(self):
        self.metrics: Dict[str, float] = {}
        self.confusion_matrix: Optional[np.ndarray] = None

    def evaluate(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: Optional[np.ndarray] = None,
    ) -> Dict[str, float]:
        """
        모델 평가 메트릭 계산

        Args:
            y_true: 실제 레이블
            y_pred: 예측 레이블
            y_proba: 예측 확률 (Optional, ROC-AUC 계산용)

        Returns:
            평가 메트릭 딕셔너리
        """
        logger.info(f"모델 평가 시작: {len(y_true)}개 샘플")

        # 기본 메트릭
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        # Confusion Matrix
        self.confusion_matrix = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = self.confusion_matrix.ravel()

        # 추가 메트릭
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0  # 정상 거래 정확도
        false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else 0
        false_negative_rate = fn / (fn + tp) if (fn + tp) > 0 else 0

        self.metrics = {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "specificity": float(specificity),
            "false_positive_rate": float(false_positive_rate),
            "false_negative_rate": float(false_negative_rate),
            "true_positives": int(tp),
            "false_positives": int(fp),
            "true_negatives": int(tn),
            "false_negatives": int(fn),
        }

        # ROC-AUC (확률 예측이 있는 경우)
        if y_proba is not None:
            roc_auc = roc_auc_score(y_true, y_proba)
            self.metrics["roc_auc"] = float(roc_auc)

        logger.info(
            f"평가 완료: Accuracy={accuracy:.4f}, Precision={precision:.4f}, "
            f"Recall={recall:.4f}, F1={f1:.4f}"
        )

        return self.metrics

    def print_classification_report(
        self, y_true: np.ndarray, y_pred: np.ndarray
    ) -> None:
        """
        Classification Report 출력

        Args:
            y_true: 실제 레이블
            y_pred: 예측 레이블
        """
        print("\n" + "=" * 60)
        print("Classification Report")
        print("=" * 60)
        print(classification_report(y_true, y_pred, target_names=["정상", "사기"]))

    def print_confusion_matrix(self) -> None:
        """Confusion Matrix 출력"""
        if self.confusion_matrix is None:
            logger.warning("Confusion Matrix가 계산되지 않았습니다.")
            return

        tn, fp, fn, tp = self.confusion_matrix.ravel()

        print("\n" + "=" * 60)
        print("Confusion Matrix")
        print("=" * 60)
        print(f"{'':20} | {'예측: 정상':>15} | {'예측: 사기':>15}")
        print("-" * 60)
        print(f"{'실제: 정상':20} | {tn:>15} (TN) | {fp:>15} (FP)")
        print(f"{'실제: 사기':20} | {fn:>15} (FN) | {tp:>15} (TP)")
        print("=" * 60)

        # 설명
        print("\n[지표 설명]")
        print(f"- True Negatives (TN): 정상 거래를 정상으로 올바르게 분류 ({tn}개)")
        print(f"- False Positives (FP): 정상 거래를 사기로 잘못 분류 (오탐, {fp}개)")
        print(f"- False Negatives (FN): 사기 거래를 정상으로 잘못 분류 (미탐, {fn}개)")
        print(f"- True Positives (TP): 사기 거래를 사기로 올바르게 분류 ({tp}개)")

    def print_metrics_summary(self) -> None:
        """평가 메트릭 요약 출력"""
        if not self.metrics:
            logger.warning("평가 메트릭이 계산되지 않았습니다.")
            return

        print("\n" + "=" * 60)
        print("Evaluation Metrics Summary")
        print("=" * 60)

        # 주요 지표
        print(f"Accuracy (정확도):        {self.metrics['accuracy']:.4f}")
        print(f"Precision (정밀도):       {self.metrics['precision']:.4f}")
        print(f"Recall (재현율):          {self.metrics['recall']:.4f}")
        print(f"F1 Score:                 {self.metrics['f1_score']:.4f}")

        if "roc_auc" in self.metrics:
            print(f"ROC-AUC:                  {self.metrics['roc_auc']:.4f}")

        # 추가 지표
        print(f"\nSpecificity (특이도):     {self.metrics['specificity']:.4f}")
        print(f"False Positive Rate:      {self.metrics['false_positive_rate']:.4f}")
        print(f"False Negative Rate:      {self.metrics['false_negative_rate']:.4f}")

        print("=" * 60)

        # 비즈니스 관점 해석
        print("\n[비즈니스 관점 해석]")
        print(
            f"- 사기 탐지율: {self.metrics['recall']*100:.2f}% "
            f"(실제 사기 중 {self.metrics['true_positives']}개 탐지, "
            f"{self.metrics['false_negatives']}개 미탐)"
        )
        print(
            f"- 오탐율: {self.metrics['false_positive_rate']*100:.2f}% "
            f"(정상 거래 {self.metrics['false_positives']}개를 사기로 오판)"
        )
        print(
            f"- 정밀도: {self.metrics['precision']*100:.2f}% "
            f"(사기로 판정한 것 중 실제 사기 비율)"
        )

    def plot_confusion_matrix(
        self, save_path: Optional[Path] = None, show: bool = True
    ) -> None:
        """
        Confusion Matrix 시각화

        Args:
            save_path: 저장 경로 (None이면 저장하지 않음)
            show: plt.show() 호출 여부
        """
        if self.confusion_matrix is None:
            logger.warning("Confusion Matrix가 계산되지 않았습니다.")
            return

        plt.figure(figsize=(8, 6))
        sns.heatmap(
            self.confusion_matrix,
            annot=True,
            fmt="d",
            cmap="Blues",
            xticklabels=["정상", "사기"],
            yticklabels=["정상", "사기"],
            cbar_kws={"label": "Count"},
        )
        plt.title("Confusion Matrix", fontsize=16, fontweight="bold")
        plt.xlabel("Predicted Label", fontsize=12)
        plt.ylabel("True Label", fontsize=12)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            logger.info(f"Confusion Matrix 저장: {save_path}")

        if show:
            plt.show()

    def plot_roc_curve(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        save_path: Optional[Path] = None,
        show: bool = True,
    ) -> None:
        """
        ROC Curve 시각화

        Args:
            y_true: 실제 레이블
            y_proba: 예측 확률
            save_path: 저장 경로
            show: plt.show() 호출 여부
        """
        fpr, tpr, thresholds = roc_curve(y_true, y_proba)
        roc_auc = roc_auc_score(y_true, y_proba)

        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, color="darkorange", lw=2, label=f"ROC curve (AUC = {roc_auc:.4f})")
        plt.plot([0, 1], [0, 1], color="navy", lw=2, linestyle="--", label="Random")
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel("False Positive Rate", fontsize=12)
        plt.ylabel("True Positive Rate (Recall)", fontsize=12)
        plt.title("Receiver Operating Characteristic (ROC) Curve", fontsize=16, fontweight="bold")
        plt.legend(loc="lower right")
        plt.grid(alpha=0.3)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            logger.info(f"ROC Curve 저장: {save_path}")

        if show:
            plt.show()

    def plot_precision_recall_curve(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        save_path: Optional[Path] = None,
        show: bool = True,
    ) -> None:
        """
        Precision-Recall Curve 시각화

        Args:
            y_true: 실제 레이블
            y_proba: 예측 확률
            save_path: 저장 경로
            show: plt.show() 호출 여부
        """
        precision, recall, thresholds = precision_recall_curve(y_true, y_proba)

        plt.figure(figsize=(8, 6))
        plt.plot(recall, precision, color="blue", lw=2)
        plt.xlabel("Recall", fontsize=12)
        plt.ylabel("Precision", fontsize=12)
        plt.title("Precision-Recall Curve", fontsize=16, fontweight="bold")
        plt.grid(alpha=0.3)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            logger.info(f"Precision-Recall Curve 저장: {save_path}")

        if show:
            plt.show()


def evaluate_model(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: Optional[np.ndarray] = None,
    print_report: bool = True,
    plot_charts: bool = False,
    output_dir: Optional[Path] = None,
) -> Dict[str, float]:
    """
    모델 평가 메인 함수

    Args:
        y_true: 실제 레이블
        y_pred: 예측 레이블
        y_proba: 예측 확률
        print_report: 리포트 출력 여부
        plot_charts: 차트 생성 여부
        output_dir: 차트 저장 디렉토리

    Returns:
        평가 메트릭 딕셔너리
    """
    evaluator = ModelEvaluator()
    metrics = evaluator.evaluate(y_true, y_pred, y_proba)

    if print_report:
        evaluator.print_classification_report(y_true, y_pred)
        evaluator.print_confusion_matrix()
        evaluator.print_metrics_summary()

    if plot_charts:
        show_plots = output_dir is None  # 저장 경로가 없으면 화면에 표시

        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        # Confusion Matrix
        cm_path = output_dir / "confusion_matrix.png" if output_dir else None
        evaluator.plot_confusion_matrix(save_path=cm_path, show=show_plots)

        # ROC Curve (확률 예측이 있는 경우)
        if y_proba is not None:
            roc_path = output_dir / "roc_curve.png" if output_dir else None
            evaluator.plot_roc_curve(y_true, y_proba, save_path=roc_path, show=show_plots)

            pr_path = output_dir / "precision_recall_curve.png" if output_dir else None
            evaluator.plot_precision_recall_curve(
                y_true, y_proba, save_path=pr_path, show=show_plots
            )

    return metrics


def compare_models(
    models_data: List[Dict[str, Any]],
    metric: str = "f1_score",
) -> pd.DataFrame:
    """
    여러 모델 성능 비교

    Args:
        models_data: 모델 데이터 리스트
            [
                {
                    "name": "Model A",
                    "y_true": [...],
                    "y_pred": [...],
                    "y_proba": [...],  # Optional
                },
                ...
            ]
        metric: 비교 기준 메트릭

    Returns:
        모델별 성능 비교 DataFrame
    """
    logger.info(f"{len(models_data)}개 모델 성능 비교")

    results = []

    for model_data in models_data:
        name = model_data["name"]
        y_true = model_data["y_true"]
        y_pred = model_data["y_pred"]
        y_proba = model_data.get("y_proba")

        # 평가
        metrics = evaluate_model(
            y_true, y_pred, y_proba, print_report=False, plot_charts=False
        )

        results.append({
            "Model": name,
            **metrics,
        })

    df_comparison = pd.DataFrame(results).sort_values(metric, ascending=False)

    print("\n" + "=" * 80)
    print("Model Comparison")
    print("=" * 80)
    print(df_comparison.to_string(index=False))
    print("=" * 80)

    return df_comparison


if __name__ == "__main__":
    # 테스트 코드 예시
    logging.basicConfig(level=logging.INFO)

    # 샘플 데이터
    np.random.seed(42)
    y_true = np.array([0, 0, 1, 1, 0, 1, 0, 0, 1, 0] * 10)
    y_pred = np.array([0, 0, 1, 0, 0, 1, 0, 0, 1, 0] * 10)
    y_proba = np.random.rand(100)

    # 단일 모델 평가
    print("\n[단일 모델 평가]")
    metrics = evaluate_model(
        y_true,
        y_pred,
        y_proba,
        print_report=True,
        plot_charts=False,
    )

    # 여러 모델 비교
    print("\n[여러 모델 비교]")
    models_data = [
        {
            "name": "Model A",
            "y_true": y_true,
            "y_pred": y_pred,
            "y_proba": y_proba,
        },
        {
            "name": "Model B",
            "y_true": y_true,
            "y_pred": np.array([0, 0, 1, 1, 0, 1, 1, 0, 1, 0] * 10),
            "y_proba": np.random.rand(100),
        },
    ]

    df_comparison = compare_models(models_data, metric="f1_score")
