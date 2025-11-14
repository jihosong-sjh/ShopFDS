"""
모델 재학습 파이프라인 통합 테스트 (T126)

검증 항목:
1. Isolation Forest 학습 파이프라인
2. LightGBM 학습 파이프라인
3. 데이터 로드 및 전처리
4. Feature Engineering
5. 모델 평가 및 저장
6. 버전 관리 통합
"""

import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
from uuid import UUID, uuid4

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# ML Service imports
from src.models.ml_model import MLModel, ModelType, DeploymentStatus, Base as MLBase
from src.training.train_isolation_forest import (
    IsolationForestTrainer,
    train_isolation_forest,
)
from src.training.train_lightgbm import LightGBMTrainer, train_lightgbm
from src.data.preprocessing import DataPreprocessor, load_training_data
from src.data.feature_engineering import create_features
from src.deployment.version_manager import ModelVersionManager


# 테스트용 인메모리 데이터베이스
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def async_db_session():
    """비동기 데이터베이스 세션 (테스트용)"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(MLBase.metadata.create_all)

    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def sync_db_session():
    """동기 데이터베이스 세션 (학습용)"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    MLBase.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    engine.dispose()


@pytest.fixture
def sample_training_data() -> pd.DataFrame:
    """
    샘플 학습 데이터 생성 (DataFrame 직접 생성)

    정상 거래 80%, 사기 거래 20%
    """
    np.random.seed(42)
    n_samples = 1000

    # 거래 데이터 생성
    data = []
    for i in range(n_samples):
        is_fraud = i < 200  # 처음 200개는 사기

        # 거래 특성 생성
        if is_fraud:
            # 사기 거래: 고액, 높은 속도, 해외 IP
            amount = np.random.uniform(500, 5000)
            velocity_1h = np.random.uniform(5, 20)
            is_foreign_ip = True if np.random.random() < 0.8 else False
            failed_login_attempts = np.random.randint(2, 10)
            risk_score = np.random.uniform(70, 100)
        else:
            # 정상 거래: 일반 금액, 낮은 속도, 국내 IP
            amount = np.random.uniform(10, 500)
            velocity_1h = np.random.uniform(0, 3)
            is_foreign_ip = True if np.random.random() < 0.1 else False
            failed_login_attempts = np.random.randint(0, 2)
            risk_score = np.random.uniform(0, 30)

        # IP 주소 생성 (해외 IP 여부에 따라)
        if is_foreign_ip:
            ip_address = f"203.{np.random.randint(0, 255)}.{np.random.randint(0, 255)}.{np.random.randint(1, 255)}"
        else:
            ip_address = f"192.168.{np.random.randint(0, 255)}.{np.random.randint(1, 255)}"

        data.append(
            {
                "transaction_id": f"TX{i:04d}",
                "user_id": str(uuid4()),
                "amount": float(amount),
                "created_at": datetime.utcnow() - timedelta(days=np.random.randint(0, 30)),
                "is_fraud": is_fraud,
                "risk_score": risk_score,
                "ip_address": ip_address,
                "velocity_1h": velocity_1h,
                "is_foreign_ip": is_foreign_ip,
                "failed_login_attempts": failed_login_attempts,
                "device_type": np.random.choice(["mobile", "desktop", "tablet"]),
                "payment_method": np.random.choice(["credit_card", "debit_card", "paypal"]),
            }
        )

    return pd.DataFrame(data)


@pytest.mark.asyncio
class TestIsolationForestPipeline:
    """Isolation Forest 학습 파이프라인 테스트"""

    def test_isolation_forest_training(
        self, sample_training_data: pd.DataFrame, tmp_path: Path
    ):
        """
        Isolation Forest 전체 학습 파이프라인 검증

        검증:
        1. 데이터 로드
        2. Feature Engineering
        3. 전처리
        4. 모델 학습
        5. 평가
        6. 저장
        """
        print("\n=== Isolation Forest 학습 파이프라인 테스트 ===")

        # Step 1: Feature Engineering
        print("Step 1: Feature Engineering")
        df_with_features = create_features(sample_training_data)
        assert len(df_with_features) == len(sample_training_data)
        assert "hour_of_day" in df_with_features.columns
        assert "day_of_week" in df_with_features.columns

        # Step 2: 전처리
        print("Step 2: 데이터 전처리")
        preprocessor = DataPreprocessor()
        X, y = preprocessor.preprocess(df_with_features, fit_scaler=True)
        assert X.shape[0] == len(sample_training_data)
        assert y.sum() == 200  # 사기 거래 200개

        # Step 3: 모델 학습
        print("Step 3: 모델 학습")
        trainer = IsolationForestTrainer(contamination=0.2, n_estimators=50, random_state=42)
        trainer.preprocessor = preprocessor

        train_metrics = trainer.train(X, y)
        assert "anomaly_count" in train_metrics
        assert "anomaly_ratio" in train_metrics
        assert train_metrics["anomaly_ratio"] > 0.1  # 최소 10% 이상 이상치 탐지

        # Step 4: 예측
        print("Step 4: 예측 수행")
        predictions, scores = trainer.predict(X)
        assert len(predictions) == len(X)
        assert len(scores) == len(X)
        assert set(predictions).issubset({-1, 1})  # -1: 이상, 1: 정상

        # Step 5: 평가
        print("Step 5: 모델 평가")
        eval_metrics = trainer.evaluate(X, y)
        assert "accuracy" in eval_metrics
        assert "precision" in eval_metrics
        assert "recall" in eval_metrics
        assert "f1_score" in eval_metrics
        assert 0 <= eval_metrics["accuracy"] <= 1

        print(f"평가 결과: F1={eval_metrics['f1_score']:.4f}, "
              f"Precision={eval_metrics['precision']:.4f}, "
              f"Recall={eval_metrics['recall']:.4f}")

        # Step 6: 모델 저장 및 로드
        print("Step 6: 모델 저장 및 로드")
        model_path = tmp_path / "isolation_forest_test.pkl"
        trainer.save_model(model_path)
        assert model_path.exists()

        # 로드 검증
        loaded_trainer = IsolationForestTrainer.load_model(model_path)
        assert loaded_trainer.contamination == trainer.contamination
        assert loaded_trainer.n_estimators == trainer.n_estimators

        # 로드된 모델로 예측
        loaded_predictions, loaded_scores = loaded_trainer.predict(X)
        np.testing.assert_array_equal(predictions, loaded_predictions)
        np.testing.assert_array_almost_equal(scores, loaded_scores, decimal=5)

        print("테스트 통과: Isolation Forest 학습 파이프라인")


@pytest.mark.asyncio
class TestLightGBMPipeline:
    """LightGBM 학습 파이프라인 테스트"""

    def test_lightgbm_training(
        self, sample_training_data: pd.DataFrame, tmp_path: Path
    ):
        """
        LightGBM 전체 학습 파이프라인 검증

        검증:
        1. Feature Engineering
        2. 전처리
        3. Train/Val/Test 분할
        4. 모델 학습 (Early Stopping)
        5. 평가
        6. Feature Importance
        7. 저장 및 로드
        """
        print("\n=== LightGBM 학습 파이프라인 테스트 ===")

        # Step 1: Feature Engineering
        print("Step 1: Feature Engineering")
        df_with_features = create_features(sample_training_data)

        # Step 2: 전처리
        print("Step 2: 데이터 전처리")
        preprocessor = DataPreprocessor()
        X, y = preprocessor.preprocess(df_with_features, fit_scaler=True)

        # Step 3: Train/Val/Test 분할
        print("Step 3: Train/Val/Test 분할")
        from src.data.preprocessing import split_train_test

        X_temp, X_test, y_temp, y_test = split_train_test(
            X, y, test_size=0.2, random_state=42, stratify=True
        )
        X_train, X_val, y_train, y_val = split_train_test(
            X_temp, y_temp, test_size=0.2, random_state=42, stratify=True
        )

        print(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

        # Step 4: 모델 학습
        print("Step 4: 모델 학습")
        trainer = LightGBMTrainer(
            num_leaves=15,
            learning_rate=0.1,
            n_estimators=50,
            class_weight="balanced",
            random_state=42,
        )
        trainer.preprocessor = preprocessor

        train_metrics = trainer.train(X_train, y_train, X_val, y_val, early_stopping_rounds=10)
        assert "best_iteration" in train_metrics
        assert "best_score" in train_metrics

        # Step 5: 예측
        print("Step 5: 예측 수행")
        y_pred, y_proba = trainer.predict(X_test, threshold=0.5)
        assert len(y_pred) == len(X_test)
        assert len(y_proba) == len(X_test)
        assert set(y_pred).issubset({0, 1})

        # Step 6: 평가
        print("Step 6: 모델 평가")
        eval_metrics = trainer.evaluate(X_test, y_test, threshold=0.5)
        assert "roc_auc" in eval_metrics
        assert "f1_score" in eval_metrics
        assert 0 <= eval_metrics["roc_auc"] <= 1

        print(f"평가 결과: ROC-AUC={eval_metrics['roc_auc']:.4f}, "
              f"F1={eval_metrics['f1_score']:.4f}, "
              f"Precision={eval_metrics['precision']:.4f}, "
              f"Recall={eval_metrics['recall']:.4f}")

        # Step 7: Feature Importance
        print("Step 7: Feature Importance 조회")
        feature_importance = trainer.get_feature_importance(top_n=10)
        assert len(feature_importance) > 0
        assert "feature" in feature_importance.columns
        assert "importance" in feature_importance.columns
        print("Top 5 Features:")
        print(feature_importance.head())

        # Step 8: 모델 저장 및 로드
        print("Step 8: 모델 저장 및 로드")
        model_path = tmp_path / "lightgbm_test"
        trainer.save_model(model_path)

        lgb_model_file = model_path.with_suffix(".txt")
        metadata_file = model_path.with_suffix(".pkl")
        assert lgb_model_file.exists()
        assert metadata_file.exists()

        # 로드 검증
        loaded_trainer = LightGBMTrainer.load_model(model_path)
        assert loaded_trainer.best_iteration == trainer.best_iteration

        # 로드된 모델로 예측
        loaded_pred, loaded_proba = loaded_trainer.predict(X_test, threshold=0.5)
        np.testing.assert_array_equal(y_pred, loaded_pred)
        np.testing.assert_array_almost_equal(y_proba, loaded_proba, decimal=5)

        print("테스트 통과: LightGBM 학습 파이프라인")


@pytest.mark.asyncio
class TestVersionManagementIntegration:
    """버전 관리 통합 테스트"""

    async def test_model_registration_and_versioning(
        self, async_db_session: AsyncSession, tmp_path: Path
    ):
        """
        모델 등록 및 버전 관리 통합 검증

        검증:
        1. 모델 등록 (MLflow)
        2. 모델 로드
        3. 프로덕션 승격
        4. 모델 비교
        """
        print("\n=== 버전 관리 통합 테스트 ===")

        version_manager = ModelVersionManager(async_db_session)

        # Step 1: 모델 메타데이터 생성
        print("Step 1: 모델 메타데이터 생성")
        model_v1 = MLModel(
            id=uuid4(),
            name="TestModel-v1.0.0",
            version="1.0.0",
            model_type=ModelType.ISOLATION_FOREST,
            training_data_start=datetime.utcnow().date() - timedelta(days=30),
            training_data_end=datetime.utcnow().date(),
            trained_at=datetime.utcnow(),
            accuracy=0.85,
            precision=0.82,
            recall=0.88,
            f1_score=0.85,
            deployment_status=DeploymentStatus.DEVELOPMENT,
            model_path=str(tmp_path / "model_v1.pkl"),
        )

        async_db_session.add(model_v1)
        await async_db_session.commit()
        await async_db_session.refresh(model_v1)

        print(f"모델 등록: {model_v1.name}, F1={model_v1.f1_score:.4f}")

        # Step 2: 스테이징 배포
        print("Step 2: 스테이징 배포")
        model_v1 = await version_manager.promote_to_staging(model_v1.id)
        await async_db_session.refresh(model_v1)
        assert model_v1.deployment_status == DeploymentStatus.STAGING
        assert model_v1.id is not None

        # Step 3: 프로덕션 승격
        print("Step 3: 프로덕션 승격")
        model_v1 = await version_manager.promote_to_production(model_v1.id)
        await async_db_session.refresh(model_v1)
        assert model_v1.deployment_status == DeploymentStatus.PRODUCTION
        assert model_v1.deployed_at is not None

        # Step 4: 새로운 버전 등록
        print("Step 4: 새로운 버전 등록 (v1.1.0)")
        model_v1_1 = MLModel(
            id=uuid4(),
            name="TestModel-v1.1.0",
            version="1.1.0",
            model_type=ModelType.ISOLATION_FOREST,
            training_data_start=datetime.utcnow().date() - timedelta(days=30),
            training_data_end=datetime.utcnow().date(),
            trained_at=datetime.utcnow(),
            accuracy=0.88,
            precision=0.86,
            recall=0.90,
            f1_score=0.88,
            deployment_status=DeploymentStatus.DEVELOPMENT,
            model_path=str(tmp_path / "model_v1_1.pkl"),
        )

        async_db_session.add(model_v1_1)
        await async_db_session.commit()
        await async_db_session.refresh(model_v1_1)

        print(f"모델 등록: {model_v1_1.name}, F1={model_v1_1.f1_score:.4f}")

        # Step 5: 모델 비교
        print("Step 5: 모델 비교")
        comparison = await version_manager.compare_models(model_v1.id, model_v1_1.id)

        assert "model_1" in comparison
        assert "model_2" in comparison
        assert "comparison" in comparison

        print("모델 비교 결과:")
        print(f"  모델 1 (v1.0.0): F1={comparison['model_1']['f1_score']:.4f}")
        print(f"  모델 2 (v1.1.0): F1={comparison['model_2']['f1_score']:.4f}")
        print(f"  F1 차이: {comparison['comparison']['f1_score_diff']:.4f}")

        # Step 6: 현재 프로덕션 모델 조회
        print("Step 6: 현재 프로덕션 모델 조회")
        current_prod = await version_manager.get_production_model(
            model_type=ModelType.ISOLATION_FOREST.value
        )

        assert current_prod is not None
        assert current_prod.id == model_v1.id
        assert current_prod.version == "1.0.0"

        print(f"현재 프로덕션 모델: {current_prod.name} (v{current_prod.version})")
        print("테스트 통과: 버전 관리 통합")


@pytest.mark.asyncio
class TestEndToEndTrainingPipeline:
    """엔드투엔드 학습 파이프라인 테스트"""

    async def test_complete_training_workflow(
        self, async_db_session: AsyncSession,
        sample_training_data: pd.DataFrame, tmp_path: Path
    ):
        """
        전체 학습 워크플로우 검증 (데이터 → 학습 → 평가 → 등록 → 배포)

        시나리오:
        1. 샘플 데이터 로드
        2. Isolation Forest 학습
        3. LightGBM 학습
        4. 두 모델 비교
        5. 더 나은 모델을 프로덕션에 배포
        """
        print("\n=== 엔드투엔드 학습 파이프라인 테스트 ===")

        # Step 1: Isolation Forest 학습
        print("Step 1: Isolation Forest 학습")
        df_if = create_features(sample_training_data.copy())
        preprocessor_if = DataPreprocessor()
        X_if, y_if = preprocessor_if.preprocess(df_if, fit_scaler=True)

        trainer_if = IsolationForestTrainer(contamination=0.2, n_estimators=50, random_state=42)
        trainer_if.preprocessor = preprocessor_if
        trainer_if.train(X_if, y_if)
        metrics_if = trainer_if.evaluate(X_if, y_if)

        model_if_path = tmp_path / "isolation_forest_final.pkl"
        trainer_if.save_model(model_if_path)

        print(f"Isolation Forest: F1={metrics_if['f1_score']:.4f}")

        # Step 2: LightGBM 학습
        print("Step 2: LightGBM 학습")
        df_lgb = create_features(sample_training_data.copy())
        preprocessor_lgb = DataPreprocessor()
        X_lgb, y_lgb = preprocessor_lgb.preprocess(df_lgb, fit_scaler=True)

        from src.data.preprocessing import split_train_test
        X_train, X_test, y_train, y_test = split_train_test(
            X_lgb, y_lgb, test_size=0.2, random_state=42, stratify=True
        )

        trainer_lgb = LightGBMTrainer(
            num_leaves=15, learning_rate=0.1, n_estimators=50, random_state=42
        )
        trainer_lgb.preprocessor = preprocessor_lgb
        trainer_lgb.train(X_train, y_train)
        metrics_lgb = trainer_lgb.evaluate(X_test, y_test)

        model_lgb_path = tmp_path / "lightgbm_final"
        trainer_lgb.save_model(model_lgb_path)

        print(f"LightGBM: F1={metrics_lgb['f1_score']:.4f}, ROC-AUC={metrics_lgb['roc_auc']:.4f}")

        # Step 3: 모델 메타데이터 등록
        print("Step 3: 모델 메타데이터 등록")
        ml_model_if = MLModel(
            id=uuid4(),
            name="IsolationForest-v1.0.0",
            version="1.0.0",
            model_type=ModelType.ISOLATION_FOREST,
            training_data_start=datetime.utcnow().date() - timedelta(days=30),
            training_data_end=datetime.utcnow().date(),
            trained_at=datetime.utcnow(),
            accuracy=metrics_if["accuracy"],
            precision=metrics_if["precision"],
            recall=metrics_if["recall"],
            f1_score=metrics_if["f1_score"],
            deployment_status=DeploymentStatus.DEVELOPMENT,
            model_path=str(model_if_path),
        )

        ml_model_lgb = MLModel(
            id=uuid4(),
            name="LightGBM-v1.0.0",
            version="1.0.0",
            model_type=ModelType.LIGHTGBM,
            training_data_start=datetime.utcnow().date() - timedelta(days=30),
            training_data_end=datetime.utcnow().date(),
            trained_at=datetime.utcnow(),
            accuracy=metrics_lgb["accuracy"],
            precision=metrics_lgb["precision"],
            recall=metrics_lgb["recall"],
            f1_score=metrics_lgb["f1_score"],
            deployment_status=DeploymentStatus.DEVELOPMENT,
            model_path=str(model_lgb_path),
        )

        async_db_session.add_all([ml_model_if, ml_model_lgb])
        await async_db_session.commit()

        # Step 4: 모델 비교 및 최적 모델 선택
        print("Step 4: 모델 비교")
        version_manager = ModelVersionManager(async_db_session)
        comparison = await version_manager.compare_models(ml_model_if.id, ml_model_lgb.id)

        f1_if = comparison["model_1"]["f1_score"]
        f1_lgb = comparison["model_2"]["f1_score"]

        print(f"모델 비교: IF F1={f1_if:.4f} vs LightGBM F1={f1_lgb:.4f}")

        # Step 5: 더 나은 모델을 프로덕션 배포
        print("Step 5: 프로덕션 배포")
        if f1_lgb > f1_if:
            best_model_id = ml_model_lgb.id
            best_model_name = "LightGBM"
        else:
            best_model_id = ml_model_if.id
            best_model_name = "IsolationForest"

        await version_manager.promote_to_staging(best_model_id)
        prod_model = await version_manager.promote_to_production(best_model_id)
        await async_db_session.refresh(prod_model)

        print(f"최적 모델 배포: {best_model_name} (F1={max(f1_if, f1_lgb):.4f})")
        print(f"배포 상태: {prod_model.deployment_status.value}")

        assert prod_model.deployment_status == DeploymentStatus.PRODUCTION

        print("테스트 통과: 엔드투엔드 학습 파이프라인")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
