"""
Ensemble Model for Fraud Detection

4개의 ML 모델을 가중 투표 방식으로 결합하여 정밀한 사기 탐지를 수행합니다.

모델 가중치:
- Random Forest: 30%
- XGBoost: 35% (최고 비중)
- Autoencoder: 25%
- LSTM: 10%

목표 성능:
- F1 Score: 0.95 이상
- 오탐률(False Positive Rate): 6% 이하
- 미탐률(False Negative Rate): 12.6% 이하
"""

import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from pathlib import Path
import joblib

from src.models.random_forest_model import RandomForestFraudModel
from src.models.xgboost_model import XGBoostFraudModel
from src.models.autoencoder_model import AutoencoderFraudModel
from src.models.lstm_model import LSTMFraudModel


logger = logging.getLogger(__name__)


class EnsembleFraudModel:
    """
    앙상블 사기 탐지 모델

    4개 모델의 예측 확률을 가중 평균하여 최종 예측 수행
    """

    def __init__(
        self,
        rf_weight: float = 0.30,
        xgb_weight: float = 0.35,
        ae_weight: float = 0.25,
        lstm_weight: float = 0.10,
        threshold: float = 0.5,
    ):
        """
        Args:
            rf_weight: Random Forest 가중치
            xgb_weight: XGBoost 가중치
            ae_weight: Autoencoder 가중치
            lstm_weight: LSTM 가중치
            threshold: 사기 판정 임계값 (0.0 ~ 1.0)
        """
        # 가중치 검증 (합이 1.0)
        total_weight = rf_weight + xgb_weight + ae_weight + lstm_weight
        if not np.isclose(total_weight, 1.0):
            raise ValueError(
                f"Weights must sum to 1.0, got {total_weight}. "
                f"RF={rf_weight}, XGB={xgb_weight}, AE={ae_weight}, LSTM={lstm_weight}"
            )

        self.weights = {
            "random_forest": rf_weight,
            "xgboost": xgb_weight,
            "autoencoder": ae_weight,
            "lstm": lstm_weight,
        }
        self.threshold = threshold

        # 개별 모델
        self.models: Dict[str, Any] = {
            "random_forest": None,
            "xgboost": None,
            "autoencoder": None,
            "lstm": None,
        }

        self.is_trained = False

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        model_configs: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        모든 개별 모델 학습

        Args:
            X_train: 학습 특징 데이터
            y_train: 학습 레이블
            X_val: 검증 특징 데이터 (옵션)
            y_val: 검증 레이블 (옵션)
            model_configs: 각 모델별 설정 (옵션)

        Returns:
            학습 결과 메트릭
        """
        logger.info(
            f"[Ensemble] Training started: {len(X_train)} samples, "
            f"{X_train.shape[1]} features"
        )

        model_configs = model_configs or {}
        train_metrics = {}

        # 1. Random Forest 학습
        logger.info("[Ensemble] Training Random Forest...")
        rf_config = model_configs.get("random_forest", {})
        self.models["random_forest"] = RandomForestFraudModel(**rf_config)
        rf_metrics = self.models["random_forest"].train(X_train, y_train)
        train_metrics["random_forest"] = rf_metrics

        # 2. XGBoost 학습
        logger.info("[Ensemble] Training XGBoost...")
        xgb_config = model_configs.get("xgboost", {})
        self.models["xgboost"] = XGBoostFraudModel(**xgb_config)
        xgb_metrics = self.models["xgboost"].train(X_train, y_train, X_val, y_val)
        train_metrics["xgboost"] = xgb_metrics

        # 3. Autoencoder 학습
        logger.info("[Ensemble] Training Autoencoder...")
        ae_config = model_configs.get("autoencoder", {})
        self.models["autoencoder"] = AutoencoderFraudModel(**ae_config)
        ae_metrics = self.models["autoencoder"].train(X_train, y_train)
        train_metrics["autoencoder"] = ae_metrics

        # 4. LSTM 학습
        logger.info("[Ensemble] Training LSTM...")
        lstm_config = model_configs.get("lstm", {})
        self.models["lstm"] = LSTMFraudModel(**lstm_config)
        lstm_metrics = self.models["lstm"].train(X_train, y_train)
        train_metrics["lstm"] = lstm_metrics

        self.is_trained = True

        logger.info("[Ensemble] All models trained successfully")

        return {
            "model_type": "ensemble",
            "weights": self.weights,
            "threshold": self.threshold,
            "n_samples": len(X_train),
            "n_features": X_train.shape[1],
            "individual_metrics": train_metrics,
        }

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        사기 여부 예측 (0 또는 1)

        Args:
            X: 예측할 특징 데이터

        Returns:
            예측 레이블 배열
        """
        probabilities = self.predict_proba(X)
        return (probabilities >= self.threshold).astype(int)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        사기 확률 예측 (가중 평균)

        Args:
            X: 예측할 특징 데이터

        Returns:
            사기 확률 배열 (0.0 ~ 1.0)
        """
        if not self.is_trained:
            raise ValueError("Ensemble model is not trained yet. Call train() first.")

        # 각 모델의 예측 확률
        proba_rf = self.models["random_forest"].predict_proba(X)
        proba_xgb = self.models["xgboost"].predict_proba(X)
        proba_ae = self.models["autoencoder"].predict_proba(X)
        proba_lstm = self.models["lstm"].predict_proba(X)

        # 가중 평균
        ensemble_proba = (
            self.weights["random_forest"] * proba_rf
            + self.weights["xgboost"] * proba_xgb
            + self.weights["autoencoder"] * proba_ae
            + self.weights["lstm"] * proba_lstm
        )

        return ensemble_proba

    def predict_with_breakdown(self, X: pd.DataFrame) -> Dict[str, np.ndarray]:
        """
        각 모델의 예측 확률 및 최종 앙상블 결과 반환

        Args:
            X: 예측할 특징 데이터

        Returns:
            모델별 확률 및 앙상블 결과
        """
        if not self.is_trained:
            raise ValueError("Ensemble model is not trained yet. Call train() first.")

        return {
            "random_forest_proba": self.models["random_forest"].predict_proba(X),
            "xgboost_proba": self.models["xgboost"].predict_proba(X),
            "autoencoder_proba": self.models["autoencoder"].predict_proba(X),
            "lstm_proba": self.models["lstm"].predict_proba(X),
            "ensemble_proba": self.predict_proba(X),
            "ensemble_prediction": self.predict(X),
        }

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
        """
        테스트 데이터로 앙상블 모델 평가

        Args:
            X_test: 테스트 특징 데이터
            y_test: 테스트 레이블

        Returns:
            평가 메트릭 (개별 모델 + 앙상블)
        """
        if not self.is_trained:
            raise ValueError("Ensemble model is not trained yet. Call train() first.")

        logger.info(f"[Ensemble] Evaluating on {len(X_test)} samples")

        # 앙상블 예측
        ensemble_predictions = self.predict(X_test)
        ensemble_proba = self.predict_proba(X_test)

        # Confusion Matrix
        from sklearn.metrics import confusion_matrix

        cm = confusion_matrix(y_test, ensemble_predictions)
        tn, fp, fn, tp = cm.ravel()

        # 메트릭 계산
        accuracy = float(np.mean(ensemble_predictions == y_test))
        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1_score = (
            float(2 * precision * recall / (precision + recall))
            if (precision + recall) > 0
            else 0.0
        )

        # 오탐률, 미탐률
        fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0  # False Positive Rate
        fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0  # False Negative Rate

        # 개별 모델 평가
        individual_metrics = {}
        for model_name, model in self.models.items():
            try:
                individual_metrics[model_name] = model.evaluate(X_test, y_test)
            except Exception as e:
                logger.warning(f"[Ensemble] Failed to evaluate {model_name}: {e}")
                individual_metrics[model_name] = {}

        logger.info(
            f"[Ensemble] Evaluation completed: Accuracy={accuracy:.4f}, "
            f"Precision={precision:.4f}, Recall={recall:.4f}, F1={f1_score:.4f}, "
            f"FPR={fpr:.4f}, FNR={fnr:.4f}"
        )

        return {
            "model_type": "ensemble",
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "false_positive_rate": fpr,
            "false_negative_rate": fnr,
            "true_positives": int(tp),
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "confusion_matrix": cm.tolist(),
            "threshold": self.threshold,
            "weights": self.weights,
            "individual_metrics": individual_metrics,
        }

    def optimize_threshold(
        self, X_val: pd.DataFrame, y_val: pd.Series, target_metric: str = "f1"
    ) -> float:
        """
        검증 데이터로 최적 임계값 탐색

        Args:
            X_val: 검증 특징 데이터
            y_val: 검증 레이블
            target_metric: 최적화할 메트릭 (f1, precision, recall)

        Returns:
            최적 임계값
        """
        logger.info(f"[Ensemble] Optimizing threshold for {target_metric}")

        # 예측 확률
        proba = self.predict_proba(X_val)

        # 임계값 범위 탐색 (0.3 ~ 0.7, 0.01 간격)
        best_threshold = 0.5
        best_score = 0.0

        for threshold in np.arange(0.3, 0.71, 0.01):
            predictions = (proba >= threshold).astype(int)

            # 메트릭 계산
            from sklearn.metrics import confusion_matrix

            cm = confusion_matrix(y_val, predictions)
            tn, fp, fn, tp = cm.ravel()

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (
                2 * precision * recall / (precision + recall)
                if (precision + recall) > 0
                else 0.0
            )

            # 목표 메트릭 선택
            if target_metric == "f1":
                score = f1
            elif target_metric == "precision":
                score = precision
            elif target_metric == "recall":
                score = recall
            else:
                score = f1

            # 최적 임계값 업데이트
            if score > best_score:
                best_score = score
                best_threshold = threshold

        self.threshold = best_threshold

        logger.info(
            f"[Ensemble] Optimal threshold: {best_threshold:.2f} "
            f"({target_metric}={best_score:.4f})"
        )

        return best_threshold

    def save(self, dirpath: str) -> None:
        """
        앙상블 모델 전체 저장

        Args:
            dirpath: 저장할 디렉토리 경로
        """
        if not self.is_trained:
            raise ValueError("Ensemble model is not trained yet. Call train() first.")

        dirpath_obj = Path(dirpath)
        dirpath_obj.mkdir(parents=True, exist_ok=True)

        # 개별 모델 저장
        self.models["random_forest"].save(str(dirpath_obj / "random_forest.pkl"))
        self.models["xgboost"].save(str(dirpath_obj / "xgboost.json"))
        self.models["autoencoder"].save(str(dirpath_obj / "autoencoder.pt"))
        self.models["lstm"].save(str(dirpath_obj / "lstm.pt"))

        # 앙상블 메타데이터 저장
        metadata = {
            "weights": self.weights,
            "threshold": self.threshold,
            "is_trained": self.is_trained,
        }
        joblib.dump(metadata, dirpath_obj / "ensemble_metadata.pkl")

        logger.info(f"[Ensemble] Model saved to {dirpath}")

    def load(self, dirpath: str) -> None:
        """
        앙상블 모델 전체 로드

        Args:
            dirpath: 로드할 디렉토리 경로
        """
        dirpath_obj = Path(dirpath)

        # 개별 모델 로드
        self.models["random_forest"] = RandomForestFraudModel()
        self.models["random_forest"].load(str(dirpath_obj / "random_forest.pkl"))

        self.models["xgboost"] = XGBoostFraudModel()
        self.models["xgboost"].load(str(dirpath_obj / "xgboost.json"))

        self.models["autoencoder"] = AutoencoderFraudModel()
        self.models["autoencoder"].load(str(dirpath_obj / "autoencoder.pt"))

        self.models["lstm"] = LSTMFraudModel()
        self.models["lstm"].load(str(dirpath_obj / "lstm.pt"))

        # 앙상블 메타데이터 로드
        metadata = joblib.load(dirpath_obj / "ensemble_metadata.pkl")
        self.weights = metadata["weights"]
        self.threshold = metadata["threshold"]
        self.is_trained = metadata["is_trained"]

        logger.info(f"[Ensemble] Model loaded from {dirpath}")


def train_ensemble(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    X_val: Optional[pd.DataFrame] = None,
    y_val: Optional[pd.Series] = None,
    model_configs: Optional[Dict[str, Dict[str, Any]]] = None,
    optimize_threshold: bool = True,
) -> Tuple[EnsembleFraudModel, Dict[str, Any]]:
    """
    앙상블 모델 학습 및 평가 (편의 함수)

    Args:
        X_train: 학습 특징 데이터
        y_train: 학습 레이블
        X_test: 테스트 특징 데이터
        y_test: 테스트 레이블
        X_val: 검증 특징 데이터 (옵션)
        y_val: 검증 레이블 (옵션)
        model_configs: 각 모델별 설정 (옵션)
        optimize_threshold: 임계값 최적화 여부

    Returns:
        (학습된 앙상블 모델, 평가 결과)
    """
    # 모델 초기화
    ensemble = EnsembleFraudModel()

    # 학습
    train_metrics = ensemble.train(X_train, y_train, X_val, y_val, model_configs)

    # 임계값 최적화 (검증 데이터 있는 경우)
    if optimize_threshold and X_val is not None and y_val is not None:
        optimal_threshold = ensemble.optimize_threshold(
            X_val, y_val, target_metric="f1"
        )
        train_metrics["optimal_threshold"] = optimal_threshold

    # 평가
    eval_metrics = ensemble.evaluate(X_test, y_test)

    # 결과 통합
    results = {"train_metrics": train_metrics, "eval_metrics": eval_metrics}

    return ensemble, results
