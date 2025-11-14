"""
Isolation Forest 학습 스크립트

비지도 학습 기반 이상 탐지 모델
정상 거래 패턴을 학습하여 이상 거래를 탐지
"""

import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sqlalchemy.orm import Session

# 프로젝트 내부 모듈
import sys
sys.path.append(str(Path(__file__).parent.parent))

from data.preprocessing import DataPreprocessor, load_training_data, split_train_test
from data.feature_engineering import create_features
from models.ml_model import MLModel, ModelType, DeploymentStatus

logger = logging.getLogger(__name__)


class IsolationForestTrainer:
    """
    Isolation Forest 모델 학습 클래스

    정상 거래 패턴을 학습하여 이상 거래를 탐지하는 비지도 학습 모델
    """

    def __init__(
        self,
        contamination: float = 0.1,
        n_estimators: int = 100,
        max_samples: int = 256,
        random_state: int = 42,
    ):
        """
        Args:
            contamination: 데이터에서 이상치 비율 추정값 (기본값 0.1 = 10%)
            n_estimators: 트리 개수 (기본값 100)
            max_samples: 각 트리에 사용할 샘플 수 (기본값 256)
            random_state: 난수 시드
        """
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.random_state = random_state

        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            max_samples=max_samples,
            random_state=random_state,
            n_jobs=-1,  # 모든 CPU 코어 사용
        )

        self.preprocessor: Optional[DataPreprocessor] = None
        self.feature_columns: Optional[list] = None

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: Optional[pd.Series] = None,
    ) -> Dict[str, float]:
        """
        모델 학습

        Args:
            X_train: 학습 데이터 (특성)
            y_train: 레이블 (Isolation Forest는 비지도 학습이므로 사용하지 않음)

        Returns:
            학습 메트릭
        """
        logger.info(f"Isolation Forest 학습 시작: {len(X_train)}개 샘플, {X_train.shape[1]}개 특성")

        # 특성 컬럼 저장
        self.feature_columns = X_train.columns.tolist()

        # 모델 학습
        self.model.fit(X_train)

        # 학습 데이터에 대한 예측 (이상치 점수)
        scores = self.model.decision_function(X_train)
        predictions = self.model.predict(X_train)  # 1: 정상, -1: 이상

        # 이상치 개수
        anomaly_count = (predictions == -1).sum()
        anomaly_ratio = anomaly_count / len(predictions)

        logger.info(
            f"학습 완료: 이상치 {anomaly_count}개 ({anomaly_ratio*100:.2f}%)"
        )

        return {
            "anomaly_count": int(anomaly_count),
            "anomaly_ratio": float(anomaly_ratio),
            "score_mean": float(scores.mean()),
            "score_std": float(scores.std()),
        }

    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        예측 수행

        Args:
            X: 예측할 데이터

        Returns:
            (예측 레이블, 이상치 점수)
            - 예측 레이블: 1 (정상), -1 (이상)
            - 이상치 점수: 음수일수록 이상, 양수일수록 정상
        """
        predictions = self.model.predict(X)
        scores = self.model.decision_function(X)

        return predictions, scores

    def evaluate(
        self, X_test: pd.DataFrame, y_test: pd.Series
    ) -> Dict[str, float]:
        """
        모델 평가

        Args:
            X_test: 테스트 데이터
            y_test: 테스트 레이블 (0: 정상, 1: 사기)

        Returns:
            평가 메트릭
        """
        logger.info(f"모델 평가 시작: {len(X_test)}개 샘플")

        # 예측
        predictions, scores = self.predict(X_test)

        # Isolation Forest 출력 (-1: 이상, 1: 정상)을 (1: 사기, 0: 정상)으로 변환
        y_pred = (predictions == -1).astype(int)

        # 평가 메트릭 계산
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average="binary", zero_division=0
        )

        # Confusion Matrix
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        accuracy = (tp + tn) / (tp + tn + fp + fn)

        # 탐지율 및 오탐율
        detection_rate = recall  # 실제 사기 중 탐지 비율
        false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else 0

        logger.info(f"평가 완료: Precision={precision:.4f}, Recall={recall:.4f}, F1={f1:.4f}")
        logger.info(f"탐지율={detection_rate:.4f}, 오탐율={false_positive_rate:.4f}")

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
            "detection_rate": float(detection_rate),
            "false_positive_rate": float(false_positive_rate),
            "true_positives": int(tp),
            "false_positives": int(fp),
            "true_negatives": int(tn),
            "false_negatives": int(fn),
        }

    def save_model(self, model_path: Path) -> None:
        """
        모델 저장

        Args:
            model_path: 모델 저장 경로
        """
        model_path.parent.mkdir(parents=True, exist_ok=True)

        # 모델 + 전처리기 + 특성 컬럼 저장
        model_data = {
            "model": self.model,
            "preprocessor": self.preprocessor,
            "feature_columns": self.feature_columns,
            "contamination": self.contamination,
            "n_estimators": self.n_estimators,
            "max_samples": self.max_samples,
        }

        with open(model_path, "wb") as f:
            pickle.dump(model_data, f)

        logger.info(f"모델 저장 완료: {model_path}")

    @classmethod
    def load_model(cls, model_path: Path) -> "IsolationForestTrainer":
        """
        저장된 모델 로드

        Args:
            model_path: 모델 파일 경로

        Returns:
            IsolationForestTrainer 인스턴스
        """
        with open(model_path, "rb") as f:
            model_data = pickle.load(f)

        trainer = cls(
            contamination=model_data["contamination"],
            n_estimators=model_data["n_estimators"],
            max_samples=model_data["max_samples"],
        )

        trainer.model = model_data["model"]
        trainer.preprocessor = model_data["preprocessor"]
        trainer.feature_columns = model_data["feature_columns"]

        logger.info(f"모델 로드 완료: {model_path}")

        return trainer


def train_isolation_forest(
    db_session: Session,
    start_date: datetime,
    end_date: datetime,
    model_name: str = "IsolationForest",
    version: str = "1.0.0",
    contamination: float = 0.1,
    n_estimators: int = 100,
    output_dir: str = "models/isolation_forest",
) -> Tuple[IsolationForestTrainer, MLModel, Dict[str, float]]:
    """
    Isolation Forest 모델 학습 메인 함수

    Args:
        db_session: 데이터베이스 세션
        start_date: 학습 데이터 시작일
        end_date: 학습 데이터 종료일
        model_name: 모델 이름
        version: 모델 버전
        contamination: 이상치 비율
        n_estimators: 트리 개수
        output_dir: 모델 저장 디렉토리

    Returns:
        (학습된 모델, MLModel 메타데이터, 평가 메트릭)
    """
    logger.info("=" * 60)
    logger.info("Isolation Forest 학습 파이프라인 시작")
    logger.info("=" * 60)

    # 1. 데이터 로드
    logger.info("Step 1/6: 학습 데이터 로드")
    df = load_training_data(db_session, start_date, end_date, include_fraud_cases=True)

    # 2. Feature Engineering
    logger.info("Step 2/6: Feature Engineering")
    df = create_features(df)

    # 3. 데이터 전처리
    logger.info("Step 3/6: 데이터 전처리")
    preprocessor = DataPreprocessor()
    X, y = preprocessor.preprocess(df, fit_scaler=True)

    # 4. Train/Test 분할
    logger.info("Step 4/6: Train/Test 분할")
    X_train, X_test, y_train, y_test = split_train_test(
        X, y, test_size=0.2, random_state=42, stratify=True
    )

    # 5. 모델 학습
    logger.info("Step 5/6: 모델 학습")
    trainer = IsolationForestTrainer(
        contamination=contamination,
        n_estimators=n_estimators,
    )
    trainer.preprocessor = preprocessor
    train_metrics = trainer.train(X_train, y_train)

    # 6. 모델 평가
    logger.info("Step 6/6: 모델 평가")
    test_metrics = trainer.evaluate(X_test, y_test)

    # 7. 모델 저장
    output_path = Path(output_dir) / f"{model_name}-v{version}.pkl"
    trainer.save_model(output_path)

    # 8. MLModel 메타데이터 생성
    ml_model = MLModel(
        name=f"{model_name}-v{version}",
        version=version,
        model_type=ModelType.ISOLATION_FOREST,
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
    logger.info("Isolation Forest 학습 완료")
    logger.info(f"모델 경로: {output_path}")
    logger.info(f"F1 Score: {test_metrics['f1_score']:.4f}")
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

    # 샘플 데이터로 테스트
    print("Isolation Forest 학습 스크립트 테스트")

    # 실제 사용 시:
    # from sqlalchemy import create_engine
    # from sqlalchemy.orm import sessionmaker
    #
    # engine = create_engine("postgresql://user:password@localhost/fds")
    # Session = sessionmaker(bind=engine)
    # db_session = Session()
    #
    # trainer, ml_model, metrics = train_isolation_forest(
    #     db_session=db_session,
    #     start_date=datetime(2025, 1, 1),
    #     end_date=datetime(2025, 11, 13),
    #     contamination=0.05,
    #     n_estimators=200,
    # )
    #
    # # 데이터베이스에 모델 메타데이터 저장
    # db_session.add(ml_model)
    # db_session.commit()

    print("스크립트 로드 완료")
