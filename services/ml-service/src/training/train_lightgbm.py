"""
LightGBM 학습 스크립트

지도 학습 기반 그래디언트 부스팅 모델
레이블된 사기 데이터로 학습하여 사기 거래를 분류
"""

import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sqlalchemy.orm import Session

# 프로젝트 내부 모듈
import sys

sys.path.append(str(Path(__file__).parent.parent))

from data.preprocessing import (
    DataPreprocessor,
    load_training_data,
    split_train_test,
    handle_imbalanced_data,
)
from data.feature_engineering import create_features
from models.ml_model import MLModel, ModelType, DeploymentStatus

logger = logging.getLogger(__name__)


class LightGBMTrainer:
    """
    LightGBM 모델 학습 클래스

    레이블된 사기 데이터로 학습하여 사기 거래를 분류하는 지도 학습 모델
    """

    def __init__(
        self,
        num_leaves: int = 31,
        max_depth: int = -1,
        learning_rate: float = 0.05,
        n_estimators: int = 100,
        class_weight: Optional[str] = "balanced",
        random_state: int = 42,
    ):
        """
        Args:
            num_leaves: 트리의 최대 리프 개수 (기본값 31)
            max_depth: 최대 깊이 (-1이면 제한 없음)
            learning_rate: 학습률 (기본값 0.05)
            n_estimators: 부스팅 라운드 수 (기본값 100)
            class_weight: 클래스 가중치 ('balanced' 또는 None)
            random_state: 난수 시드
        """
        self.num_leaves = num_leaves
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.n_estimators = n_estimators
        self.class_weight = class_weight
        self.random_state = random_state

        # LightGBM 파라미터
        self.params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "num_leaves": num_leaves,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "feature_fraction": 0.9,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
            "random_state": random_state,
        }

        if class_weight == "balanced":
            self.params["is_unbalance"] = True

        self.model: Optional[lgb.Booster] = None
        self.preprocessor: Optional[DataPreprocessor] = None
        self.feature_columns: Optional[list] = None
        self.best_iteration: int = 0

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        early_stopping_rounds: int = 50,
    ) -> Dict[str, float]:
        """
        모델 학습

        Args:
            X_train: 학습 데이터 (특성)
            y_train: 학습 레이블
            X_val: 검증 데이터 (Optional)
            y_val: 검증 레이블 (Optional)
            early_stopping_rounds: Early Stopping 라운드

        Returns:
            학습 메트릭
        """
        logger.info(f"LightGBM 학습 시작: {len(X_train)}개 샘플, {X_train.shape[1]}개 특성")

        # 특성 컬럼 저장
        self.feature_columns = X_train.columns.tolist()

        # LightGBM Dataset 생성
        train_data = lgb.Dataset(X_train, label=y_train)

        valid_sets = [train_data]
        valid_names = ["train"]

        if X_val is not None and y_val is not None:
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
            valid_sets.append(val_data)
            valid_names.append("valid")

        # 모델 학습
        callbacks = [
            lgb.log_evaluation(period=10),
        ]

        if X_val is not None:
            callbacks.append(lgb.early_stopping(stopping_rounds=early_stopping_rounds))

        self.model = lgb.train(
            self.params,
            train_data,
            num_boost_round=self.n_estimators,
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=callbacks,
        )

        self.best_iteration = self.model.best_iteration

        logger.info(
            f"학습 완료: Best iteration={self.best_iteration}, "
            f"Best score={self.model.best_score}"
        )

        return {
            "best_iteration": self.best_iteration,
            "best_score": self.model.best_score,
        }

    def predict(
        self, X: pd.DataFrame, threshold: float = 0.5
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        예측 수행

        Args:
            X: 예측할 데이터
            threshold: 분류 임계값 (기본값 0.5)

        Returns:
            (예측 레이블, 예측 확률)
        """
        if self.model is None:
            raise ValueError("모델이 학습되지 않았습니다. train()을 먼저 호출하세요.")

        # 확률 예측
        probabilities = self.model.predict(X, num_iteration=self.best_iteration)

        # 임계값 적용하여 레이블 예측
        predictions = (probabilities >= threshold).astype(int)

        return predictions, probabilities

    def evaluate(
        self, X_test: pd.DataFrame, y_test: pd.Series, threshold: float = 0.5
    ) -> Dict[str, float]:
        """
        모델 평가

        Args:
            X_test: 테스트 데이터
            y_test: 테스트 레이블
            threshold: 분류 임계값

        Returns:
            평가 메트릭
        """
        logger.info(f"모델 평가 시작: {len(X_test)}개 샘플")

        # 예측
        y_pred, y_proba = self.predict(X_test, threshold=threshold)

        # 평가 메트릭 계산
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average="binary", zero_division=0
        )

        # Confusion Matrix
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        accuracy = (tp + tn) / (tp + tn + fp + fn)

        # ROC-AUC
        roc_auc = roc_auc_score(y_test, y_proba)

        # 탐지율 및 오탐율
        detection_rate = recall
        false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else 0

        logger.info(
            f"평가 완료: Precision={precision:.4f}, Recall={recall:.4f}, "
            f"F1={f1:.4f}, ROC-AUC={roc_auc:.4f}"
        )

        # Classification Report
        print("\n=== Classification Report ===")
        print(classification_report(y_test, y_pred, target_names=["정상", "사기"]))

        # Confusion Matrix
        print("\n=== Confusion Matrix ===")
        print(f"True Negatives (정상→정상): {tn}")
        print(f"False Positives (정상→사기): {fp}")
        print(f"False Negatives (사기→정상): {fn}")
        print(f"True Positives (사기→사기): {tp}")

        return {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "roc_auc": float(roc_auc),
            "detection_rate": float(detection_rate),
            "false_positive_rate": float(false_positive_rate),
            "true_positives": int(tp),
            "false_positives": int(fp),
            "true_negatives": int(tn),
            "false_negatives": int(fn),
        }

    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """
        Feature Importance 조회

        Args:
            top_n: 상위 N개 특성

        Returns:
            Feature Importance DataFrame
        """
        if self.model is None:
            raise ValueError("모델이 학습되지 않았습니다.")

        importance = self.model.feature_importance(importance_type="gain")
        feature_names = self.feature_columns

        df_importance = pd.DataFrame(
            {
                "feature": feature_names,
                "importance": importance,
            }
        ).sort_values("importance", ascending=False)

        return df_importance.head(top_n)

    def save_model(self, model_path: Path) -> None:
        """
        모델 저장

        Args:
            model_path: 모델 저장 경로
        """
        model_path.parent.mkdir(parents=True, exist_ok=True)

        # LightGBM 모델 저장
        lgb_model_path = model_path.with_suffix(".txt")
        self.model.save_model(str(lgb_model_path))

        # 메타데이터 저장
        metadata_path = model_path.with_suffix(".pkl")
        metadata = {
            "init_params": {
                "num_leaves": self.num_leaves,
                "max_depth": self.max_depth,
                "learning_rate": self.learning_rate,
                "n_estimators": self.n_estimators,
                "class_weight": self.class_weight,
                "random_state": self.random_state,
            },
            "params": self.params,
            "preprocessor": self.preprocessor,
            "feature_columns": self.feature_columns,
            "best_iteration": self.best_iteration,
        }

        with open(metadata_path, "wb") as f:
            pickle.dump(metadata, f)

        logger.info(f"모델 저장 완료: {lgb_model_path}, {metadata_path}")

    @classmethod
    def load_model(cls, model_path: Path) -> "LightGBMTrainer":
        """
        저장된 모델 로드

        Args:
            model_path: 모델 파일 경로

        Returns:
            LightGBMTrainer 인스턴스
        """
        # LightGBM 모델 로드
        lgb_model_path = model_path.with_suffix(".txt")
        model = lgb.Booster(model_file=str(lgb_model_path))

        # 메타데이터 로드
        metadata_path = model_path.with_suffix(".pkl")
        with open(metadata_path, "rb") as f:
            metadata = pickle.load(f)

        # 이전 버전 호환성: init_params가 없으면 기본값 사용
        if "init_params" in metadata:
            trainer = cls(**metadata["init_params"])
        else:
            trainer = cls()

        trainer.model = model
        trainer.params = metadata.get("params", trainer.params)
        trainer.preprocessor = metadata["preprocessor"]
        trainer.feature_columns = metadata["feature_columns"]
        trainer.best_iteration = metadata["best_iteration"]

        logger.info(f"모델 로드 완료: {lgb_model_path}")

        return trainer


def train_lightgbm(
    db_session: Session,
    start_date: datetime,
    end_date: datetime,
    model_name: str = "LightGBM",
    version: str = "1.0.0",
    num_leaves: int = 31,
    learning_rate: float = 0.05,
    n_estimators: int = 100,
    use_smote: bool = True,
    output_dir: str = "models/lightgbm",
) -> Tuple[LightGBMTrainer, MLModel, Dict[str, float]]:
    """
    LightGBM 모델 학습 메인 함수

    Args:
        db_session: 데이터베이스 세션
        start_date: 학습 데이터 시작일
        end_date: 학습 데이터 종료일
        model_name: 모델 이름
        version: 모델 버전
        num_leaves: 트리 리프 개수
        learning_rate: 학습률
        n_estimators: 부스팅 라운드
        use_smote: SMOTE 사용 여부
        output_dir: 모델 저장 디렉토리

    Returns:
        (학습된 모델, MLModel 메타데이터, 평가 메트릭)
    """
    logger.info("=" * 60)
    logger.info("LightGBM 학습 파이프라인 시작")
    logger.info("=" * 60)

    # 1. 데이터 로드
    logger.info("Step 1/7: 학습 데이터 로드")
    df = load_training_data(db_session, start_date, end_date, include_fraud_cases=True)

    # 2. Feature Engineering
    logger.info("Step 2/7: Feature Engineering")
    df = create_features(df)

    # 3. 데이터 전처리
    logger.info("Step 3/7: 데이터 전처리")
    preprocessor = DataPreprocessor()
    X, y = preprocessor.preprocess(df, fit_scaler=True)

    # 4. Train/Validation/Test 분할
    logger.info("Step 4/7: Train/Validation/Test 분할")
    X_temp, X_test, y_temp, y_test = split_train_test(
        X, y, test_size=0.2, random_state=42, stratify=True
    )
    X_train, X_val, y_train, y_val = split_train_test(
        X_temp, y_temp, test_size=0.2, random_state=42, stratify=True
    )

    # 5. 불균형 데이터 처리 (SMOTE)
    if use_smote and y_train.sum() > 0:
        logger.info("Step 5/7: 불균형 데이터 처리 (SMOTE)")
        X_train, y_train = handle_imbalanced_data(X_train, y_train, method="smote")
    else:
        logger.info("Step 5/7: 불균형 데이터 처리 건너뜀")

    # 6. 모델 학습
    logger.info("Step 6/7: 모델 학습")
    trainer = LightGBMTrainer(
        num_leaves=num_leaves,
        learning_rate=learning_rate,
        n_estimators=n_estimators,
        class_weight="balanced",
    )
    trainer.preprocessor = preprocessor
    trainer.train(X_train, y_train, X_val, y_val, early_stopping_rounds=50)

    # 7. 모델 평가
    logger.info("Step 7/7: 모델 평가")
    test_metrics = trainer.evaluate(X_test, y_test, threshold=0.5)

    # Feature Importance 출력
    print("\n=== Top 20 Feature Importance ===")
    print(trainer.get_feature_importance(top_n=20))

    # 8. 모델 저장
    output_path = Path(output_dir) / f"{model_name}-v{version}"
    trainer.save_model(output_path)

    # 9. MLModel 메타데이터 생성
    ml_model = MLModel(
        name=f"{model_name}-v{version}",
        version=version,
        model_type=ModelType.LIGHTGBM,
        training_data_start=start_date.date(),
        training_data_end=end_date.date(),
        trained_at=datetime.utcnow(),
        accuracy=test_metrics["accuracy"],
        precision=test_metrics["precision"],
        recall=test_metrics["recall"],
        f1_score=test_metrics["f1_score"],
        deployment_status=DeploymentStatus.DEVELOPMENT,
        model_path=str(output_path),
    )

    logger.info("=" * 60)
    logger.info("LightGBM 학습 완료")
    logger.info(f"모델 경로: {output_path}")
    logger.info(f"F1 Score: {test_metrics['f1_score']:.4f}")
    logger.info(f"ROC-AUC: {test_metrics['roc_auc']:.4f}")
    logger.info(f"Precision: {test_metrics['precision']:.4f}")
    logger.info(f"Recall: {test_metrics['recall']:.4f}")
    logger.info("=" * 60)

    return trainer, ml_model, test_metrics


if __name__ == "__main__":
    # 테스트 실행 예시
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("LightGBM 학습 스크립트 테스트")

    # 실제 사용 시:
    # from sqlalchemy import create_engine
    # from sqlalchemy.orm import sessionmaker
    #
    # engine = create_engine("postgresql://user:password@localhost/fds")
    # Session = sessionmaker(bind=engine)
    # db_session = Session()
    #
    # trainer, ml_model, metrics = train_lightgbm(
    #     db_session=db_session,
    #     start_date=datetime(2025, 1, 1),
    #     end_date=datetime(2025, 11, 13),
    #     num_leaves=50,
    #     learning_rate=0.03,
    #     n_estimators=200,
    #     use_smote=True,
    # )
    #
    # # 데이터베이스에 모델 메타데이터 저장
    # db_session.add(ml_model)
    # db_session.commit()

    print("스크립트 로드 완료")
