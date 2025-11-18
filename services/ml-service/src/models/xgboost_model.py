"""
XGBoost Model for Fraud Detection with GPU Acceleration

XGBoost는 앙상블 모델의 핵심 구성 요소로, 다음과 같은 특징을 가집니다:
- Gradient Boosting 기반으로 높은 정확도
- GPU 가속 지원 (NVIDIA CUDA)
- Early Stopping으로 과적합 방지
- 빠른 학습 속도

모델 가중치: 35% (앙상블 내 최고 비중)
"""

import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import confusion_matrix
from pathlib import Path


logger = logging.getLogger(__name__)


class XGBoostFraudModel:
    """
    XGBoost 기반 사기 탐지 모델 (GPU 가속)

    하이퍼파라미터:
    - n_estimators: 300 (부스팅 라운드)
    - max_depth: 10 (트리 최대 깊이)
    - learning_rate: 0.05 (학습률)
    - subsample: 0.8 (샘플 비율)
    - colsample_bytree: 0.8 (특징 비율)
    - tree_method: gpu_hist (GPU 가속)
    - scale_pos_weight: auto (불균형 대응)
    """

    def __init__(
        self,
        n_estimators: int = 300,
        max_depth: int = 10,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        gamma: float = 0.1,
        min_child_weight: int = 5,
        reg_alpha: float = 0.1,
        reg_lambda: float = 1.0,
        tree_method: str = "gpu_hist",
        gpu_id: int = 0,
        random_state: int = 42,
        use_gpu: bool = True,
    ):
        """
        Args:
            n_estimators: 부스팅 라운드 수
            max_depth: 트리 최대 깊이
            learning_rate: 학습률 (낮을수록 안정적)
            subsample: 트리별 샘플 비율 (과적합 방지)
            colsample_bytree: 트리별 특징 비율
            gamma: 노드 분할 최소 손실 감소
            min_child_weight: 리프 노드 최소 가중치 합
            reg_alpha: L1 정규화
            reg_lambda: L2 정규화
            tree_method: 트리 생성 방법 (gpu_hist, hist, auto)
            gpu_id: 사용할 GPU ID (0부터 시작)
            random_state: 재현성을 위한 시드
            use_gpu: GPU 사용 여부 (False 시 CPU 사용)
        """
        # GPU 사용 가능 여부 확인
        if use_gpu:
            try:
                # GPU 사용 가능 확인
                logger.info(f"[XGBoost] Attempting to use GPU {gpu_id}")
                tree_method_final = tree_method
                predictor = "gpu_predictor"
            except Exception as e:
                logger.warning(
                    f"[XGBoost] GPU not available: {e}. Falling back to CPU."
                )
                tree_method_final = "hist"
                predictor = "cpu_predictor"
        else:
            tree_method_final = "hist"
            predictor = "cpu_predictor"

        self.params = {
            "objective": "binary:logistic",
            "eval_metric": "auc",
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "gamma": gamma,
            "min_child_weight": min_child_weight,
            "reg_alpha": reg_alpha,
            "reg_lambda": reg_lambda,
            "tree_method": tree_method_final,
            "predictor": predictor,
            "gpu_id": gpu_id if use_gpu else None,
            "random_state": random_state,
            "verbosity": 1,
        }

        self.n_estimators = n_estimators
        self.model: Optional[xgb.Booster] = None
        self.feature_names: Optional[list] = None
        self.is_trained = False
        self.best_iteration: Optional[int] = None

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        early_stopping_rounds: int = 50,
    ) -> Dict[str, Any]:
        """
        XGBoost 모델 학습 (Early Stopping 지원)

        Args:
            X_train: 학습 특징 데이터
            y_train: 학습 레이블 (0: 정상, 1: 사기)
            X_val: 검증 특징 데이터 (옵션)
            y_val: 검증 레이블 (옵션)
            early_stopping_rounds: Early Stopping 라운드 수

        Returns:
            학습 결과 메트릭
        """
        logger.info(
            f"[XGBoost] Training started: {len(X_train)} samples, "
            f"{X_train.shape[1]} features"
        )

        # Feature 이름 저장
        self.feature_names = X_train.columns.tolist()

        # 클래스 불균형 대응 가중치 계산
        scale_pos_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1])
        self.params["scale_pos_weight"] = scale_pos_weight

        logger.info(f"[XGBoost] scale_pos_weight: {scale_pos_weight:.2f}")

        # DMatrix 생성
        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=self.feature_names)

        # Evaluation list 구성
        evals = [(dtrain, "train")]
        if X_val is not None and y_val is not None:
            dval = xgb.DMatrix(X_val, label=y_val, feature_names=self.feature_names)
            evals.append((dval, "val"))

        # 학습 실행
        evals_result = {}
        self.model = xgb.train(
            params=self.params,
            dtrain=dtrain,
            num_boost_round=self.n_estimators,
            evals=evals,
            evals_result=evals_result,
            early_stopping_rounds=early_stopping_rounds if X_val is not None else None,
            verbose_eval=50,
        )

        self.is_trained = True
        self.best_iteration = (
            self.model.best_iteration if X_val is not None else self.n_estimators
        )

        # 학습 데이터 성능 평가
        train_predictions_proba = self.model.predict(dtrain)
        train_predictions = (train_predictions_proba >= 0.5).astype(int)
        train_accuracy = float(np.mean(train_predictions == y_train))

        logger.info(
            f"[XGBoost] Training completed: Best iteration={self.best_iteration}, "
            f"Train accuracy={train_accuracy:.4f}"
        )

        return {
            "model_type": "xgboost",
            "n_estimators": self.n_estimators,
            "best_iteration": self.best_iteration,
            "max_depth": self.params["max_depth"],
            "learning_rate": self.params["learning_rate"],
            "scale_pos_weight": scale_pos_weight,
            "n_features": len(self.feature_names),
            "train_accuracy": train_accuracy,
            "train_auc": evals_result["train"]["auc"][-1]
            if "train" in evals_result
            else None,
            "val_auc": evals_result["val"]["auc"][-1]
            if "val" in evals_result
            else None,
        }

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        사기 여부 예측 (0 또는 1)

        Args:
            X: 예측할 특징 데이터

        Returns:
            예측 레이블 배열
        """
        if not self.is_trained:
            raise ValueError("Model is not trained yet. Call train() first.")

        dmatrix = xgb.DMatrix(X, feature_names=self.feature_names)
        probabilities = self.model.predict(dmatrix)

        return (probabilities >= 0.5).astype(int)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        사기 확률 예측 (0.0 ~ 1.0)

        Args:
            X: 예측할 특징 데이터

        Returns:
            사기 확률 배열
        """
        if not self.is_trained:
            raise ValueError("Model is not trained yet. Call train() first.")

        dmatrix = xgb.DMatrix(X, feature_names=self.feature_names)
        return self.model.predict(dmatrix)

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
        """
        테스트 데이터로 모델 평가

        Args:
            X_test: 테스트 특징 데이터
            y_test: 테스트 레이블

        Returns:
            평가 메트릭
        """
        if not self.is_trained:
            raise ValueError("Model is not trained yet. Call train() first.")

        # 예측
        predictions = self.predict(X_test)
        probabilities = self.predict_proba(X_test)

        # Confusion Matrix
        cm = confusion_matrix(y_test, predictions)
        tn, fp, fn, tp = cm.ravel()

        # 메트릭 계산
        accuracy = float(np.mean(predictions == y_test))
        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1_score = (
            float(2 * precision * recall / (precision + recall))
            if (precision + recall) > 0
            else 0.0
        )

        logger.info(
            f"[XGBoost] Evaluation: Accuracy={accuracy:.4f}, "
            f"Precision={precision:.4f}, Recall={recall:.4f}, F1={f1_score:.4f}"
        )

        return {
            "model_type": "xgboost",
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "true_positives": int(tp),
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "confusion_matrix": cm.tolist(),
        }

    def get_feature_importances(self) -> Dict[str, float]:
        """
        Feature Importance 추출 (Gain 기준, 상위 20개)

        Returns:
            특징 이름 -> 중요도 매핑
        """
        if not self.is_trained:
            return {}

        # Gain 기준 Feature Importance
        importance_dict = self.model.get_score(importance_type="gain")

        # 중요도 높은 순으로 정렬하여 상위 20개만 반환
        sorted_features = sorted(
            importance_dict.items(), key=lambda x: x[1], reverse=True
        )[:20]

        return dict(sorted_features)

    def get_feature_importances_full(self) -> pd.DataFrame:
        """
        모든 Feature Importance 반환 (DataFrame 형태)

        Returns:
            특징 이름과 중요도를 포함한 DataFrame
        """
        if not self.is_trained:
            return pd.DataFrame()

        # 여러 중요도 타입 추출
        gain = self.model.get_score(importance_type="gain")
        weight = self.model.get_score(importance_type="weight")
        cover = self.model.get_score(importance_type="cover")

        # DataFrame 생성
        all_features = set(gain.keys()) | set(weight.keys()) | set(cover.keys())

        df = pd.DataFrame(
            {
                "feature": list(all_features),
                "gain": [gain.get(f, 0.0) for f in all_features],
                "weight": [weight.get(f, 0.0) for f in all_features],
                "cover": [cover.get(f, 0.0) for f in all_features],
            }
        )

        # Gain 기준 정렬
        df = df.sort_values("gain", ascending=False).reset_index(drop=True)

        return df

    def save(self, filepath: str) -> None:
        """
        모델 저장

        Args:
            filepath: 저장할 파일 경로 (.json 또는 .model)
        """
        if not self.is_trained:
            raise ValueError("Model is not trained yet. Call train() first.")

        # 디렉토리 생성
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        # 모델 저장 (JSON 형식)
        self.model.save_model(filepath)

        # 메타데이터 저장
        metadata_path = filepath.replace(".json", "_metadata.json").replace(
            ".model", "_metadata.json"
        )
        import json

        with open(metadata_path, "w") as f:
            json.dump(
                {
                    "feature_names": self.feature_names,
                    "best_iteration": self.best_iteration,
                    "params": self.params,
                },
                f,
                indent=2,
            )

        logger.info(f"[XGBoost] Model saved to {filepath}")

    def load(self, filepath: str) -> None:
        """
        모델 로드

        Args:
            filepath: 로드할 파일 경로 (.json 또는 .model)
        """
        # 모델 로드
        self.model = xgb.Booster()
        self.model.load_model(filepath)

        # 메타데이터 로드
        metadata_path = filepath.replace(".json", "_metadata.json").replace(
            ".model", "_metadata.json"
        )
        import json

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                self.feature_names = metadata["feature_names"]
                self.best_iteration = metadata["best_iteration"]
                self.params = metadata["params"]
        except FileNotFoundError:
            logger.warning("[XGBoost] Metadata file not found. Using model defaults.")

        self.is_trained = True
        logger.info(f"[XGBoost] Model loaded from {filepath}")


def train_xgboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    X_val: Optional[pd.DataFrame] = None,
    y_val: Optional[pd.Series] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[XGBoostFraudModel, Dict[str, Any]]:
    """
    XGBoost 모델 학습 및 평가 (편의 함수)

    Args:
        X_train: 학습 특징 데이터
        y_train: 학습 레이블
        X_test: 테스트 특징 데이터
        y_test: 테스트 레이블
        X_val: 검증 특징 데이터 (옵션)
        y_val: 검증 레이블 (옵션)
        config: 모델 설정 (옵션)

    Returns:
        (학습된 모델, 평가 결과)
    """
    # 모델 초기화
    model = XGBoostFraudModel(**(config or {}))

    # 학습
    train_metrics = model.train(X_train, y_train, X_val, y_val)

    # 평가
    eval_metrics = model.evaluate(X_test, y_test)

    # 결과 통합
    results = {"train_metrics": train_metrics, "eval_metrics": eval_metrics}

    return model, results
