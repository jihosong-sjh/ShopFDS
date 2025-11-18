"""
Random Forest Model for Fraud Detection

Random Forest는 앙상블 모델의 기본 구성 요소로, 다음과 같은 특징을 가집니다:
- 여러 Decision Tree의 투표를 통한 안정적인 예측
- Feature Importance 분석 가능
- 과적합 방지 (배깅 기법)
- 해석 가능성 높음

모델 가중치: 30% (앙상블 내)
"""

import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import confusion_matrix
import joblib
from pathlib import Path


logger = logging.getLogger(__name__)


class RandomForestFraudModel:
    """
    Random Forest 기반 사기 탐지 모델

    하이퍼파라미터:
    - n_estimators: 200 (트리 개수)
    - max_depth: 20 (최대 깊이)
    - min_samples_split: 10 (분할 최소 샘플)
    - min_samples_leaf: 4 (리프 최소 샘플)
    - max_features: sqrt (분할 시 고려할 최대 특징 수)
    - class_weight: balanced (불균형 데이터 대응)
    """

    def __init__(
        self,
        n_estimators: int = 200,
        max_depth: int = 20,
        min_samples_split: int = 10,
        min_samples_leaf: int = 4,
        max_features: str = "sqrt",
        class_weight: str = "balanced",
        random_state: int = 42,
        n_jobs: int = -1,
    ):
        """
        Args:
            n_estimators: 트리 개수 (많을수록 성능 향상, 시간 증가)
            max_depth: 트리 최대 깊이 (과적합 방지)
            min_samples_split: 노드 분할 최소 샘플 수
            min_samples_leaf: 리프 노드 최소 샘플 수
            max_features: 분할 시 고려할 최대 특징 수
            class_weight: 클래스 가중치 (balanced로 불균형 대응)
            random_state: 재현성을 위한 시드
            n_jobs: 병렬 작업 수 (-1 = 모든 코어 사용)
        """
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            max_features=max_features,
            class_weight=class_weight,
            random_state=random_state,
            n_jobs=n_jobs,
            verbose=1,
        )
        self.feature_names: Optional[list] = None
        self.is_trained = False

    def train(self, X_train: pd.DataFrame, y_train: pd.Series) -> Dict[str, Any]:
        """
        Random Forest 모델 학습

        Args:
            X_train: 학습 특징 데이터
            y_train: 학습 레이블 (0: 정상, 1: 사기)

        Returns:
            학습 결과 메트릭
        """
        logger.info(
            f"[Random Forest] Training started: {len(X_train)} samples, "
            f"{X_train.shape[1]} features"
        )

        # Feature 이름 저장
        self.feature_names = X_train.columns.tolist()

        # 학습 실행
        self.model.fit(X_train, y_train)
        self.is_trained = True

        # 학습 데이터 성능 평가
        train_predictions = self.model.predict(X_train)
        train_proba = self.model.predict_proba(X_train)[:, 1]

        # Feature Importance 추출
        feature_importances = self._get_feature_importances()

        logger.info("[Random Forest] Training completed successfully")

        return {
            "model_type": "random_forest",
            "n_estimators": self.model.n_estimators,
            "max_depth": self.model.max_depth,
            "n_features": len(self.feature_names),
            "train_accuracy": float(np.mean(train_predictions == y_train)),
            "feature_importances": feature_importances,
            "oob_score": float(self.model.oob_score_)
            if hasattr(self.model, "oob_score_")
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

        return self.model.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        사기 확률 예측 (0.0 ~ 1.0)

        Args:
            X: 예측할 특징 데이터

        Returns:
            사기 확률 배열 (클래스 1의 확률)
        """
        if not self.is_trained:
            raise ValueError("Model is not trained yet. Call train() first.")

        # 클래스 1 (사기)의 확률만 반환
        return self.model.predict_proba(X)[:, 1]

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
            f"[Random Forest] Evaluation: Accuracy={accuracy:.4f}, "
            f"Precision={precision:.4f}, Recall={recall:.4f}, F1={f1_score:.4f}"
        )

        return {
            "model_type": "random_forest",
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

    def _get_feature_importances(self) -> Dict[str, float]:
        """
        Feature Importance 추출 (상위 20개)

        Returns:
            특징 이름 -> 중요도 매핑
        """
        if not self.is_trained or self.feature_names is None:
            return {}

        importances = self.model.feature_importances_

        # 특징별 중요도 매핑
        feature_importance_dict = {
            name: float(importance)
            for name, importance in zip(self.feature_names, importances)
        }

        # 중요도 높은 순으로 정렬하여 상위 20개만 반환
        sorted_features = sorted(
            feature_importance_dict.items(), key=lambda x: x[1], reverse=True
        )[:20]

        return dict(sorted_features)

    def get_feature_importances_full(self) -> pd.DataFrame:
        """
        모든 Feature Importance 반환 (DataFrame 형태)

        Returns:
            특징 이름과 중요도를 포함한 DataFrame
        """
        if not self.is_trained or self.feature_names is None:
            return pd.DataFrame()

        importances = self.model.feature_importances_

        df = pd.DataFrame({"feature": self.feature_names, "importance": importances})

        # 중요도 높은 순으로 정렬
        df = df.sort_values("importance", ascending=False).reset_index(drop=True)

        return df

    def hyperparameter_tuning(
        self, X_train: pd.DataFrame, y_train: pd.Series, cv: int = 5
    ) -> Dict[str, Any]:
        """
        Grid Search로 하이퍼파라미터 튜닝

        Args:
            X_train: 학습 특징 데이터
            y_train: 학습 레이블
            cv: Cross-validation 폴드 수

        Returns:
            최적 파라미터와 성능
        """
        logger.info("[Random Forest] Starting hyperparameter tuning...")

        param_grid = {
            "n_estimators": [100, 200, 300],
            "max_depth": [15, 20, 25],
            "min_samples_split": [5, 10, 15],
            "min_samples_leaf": [2, 4, 6],
            "max_features": ["sqrt", "log2"],
        }

        grid_search = GridSearchCV(
            estimator=self.model,
            param_grid=param_grid,
            cv=cv,
            scoring="f1",
            n_jobs=-1,
            verbose=2,
        )

        grid_search.fit(X_train, y_train)

        # 최적 모델로 업데이트
        self.model = grid_search.best_estimator_
        self.feature_names = X_train.columns.tolist()
        self.is_trained = True

        logger.info(f"[Random Forest] Best parameters: {grid_search.best_params_}")

        return {
            "best_params": grid_search.best_params_,
            "best_score": float(grid_search.best_score_),
            "cv_results": grid_search.cv_results_,
        }

    def save(self, filepath: str) -> None:
        """
        모델 저장

        Args:
            filepath: 저장할 파일 경로 (.pkl)
        """
        if not self.is_trained:
            raise ValueError("Model is not trained yet. Call train() first.")

        # 디렉토리 생성
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        # 모델 저장
        model_data = {
            "model": self.model,
            "feature_names": self.feature_names,
            "is_trained": self.is_trained,
        }

        joblib.dump(model_data, filepath)
        logger.info(f"[Random Forest] Model saved to {filepath}")

    def load(self, filepath: str) -> None:
        """
        모델 로드

        Args:
            filepath: 로드할 파일 경로 (.pkl)
        """
        model_data = joblib.load(filepath)

        self.model = model_data["model"]
        self.feature_names = model_data["feature_names"]
        self.is_trained = model_data["is_trained"]

        logger.info(f"[Random Forest] Model loaded from {filepath}")


def train_random_forest(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[RandomForestFraudModel, Dict[str, Any]]:
    """
    Random Forest 모델 학습 및 평가 (편의 함수)

    Args:
        X_train: 학습 특징 데이터
        y_train: 학습 레이블
        X_test: 테스트 특징 데이터
        y_test: 테스트 레이블
        config: 모델 설정 (옵션)

    Returns:
        (학습된 모델, 평가 결과)
    """
    # 모델 초기화
    model = RandomForestFraudModel(**(config or {}))

    # 학습
    train_metrics = model.train(X_train, y_train)

    # 평가
    eval_metrics = model.evaluate(X_test, y_test)

    # 결과 통합
    results = {"train_metrics": train_metrics, "eval_metrics": eval_metrics}

    return model, results
