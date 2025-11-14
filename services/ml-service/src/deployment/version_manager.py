"""
MLflow 기반 ML 모델 버전 관리 시스템

기능:
- 모델 등록 및 버전 관리
- 모델 메타데이터 추적 (성능 지표, 학습 파라미터)
- 모델 아티팩트 저장 및 로드
- 프로덕션/스테이징/개발 환경별 모델 관리
"""

import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4

import mlflow
import mlflow.sklearn
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from src.models.ml_model import MLModel, DeploymentStatus


class ModelVersionManager:
    """MLflow 기반 모델 버전 관리자"""

    def __init__(
        self,
        db_session: AsyncSession,
        mlflow_tracking_uri: str = "http://localhost:5000",
        artifact_location: str = "./mlruns",
    ):
        """
        Args:
            db_session: 데이터베이스 세션
            mlflow_tracking_uri: MLflow 트래킹 서버 URI
            artifact_location: 모델 아티팩트 저장 경로
        """
        self.db_session = db_session
        self.mlflow_tracking_uri = mlflow_tracking_uri
        self.artifact_location = artifact_location

        # MLflow 설정
        mlflow.set_tracking_uri(mlflow_tracking_uri)
        os.makedirs(artifact_location, exist_ok=True)

    async def register_model(
        self,
        model: Any,
        model_name: str,
        model_type: str,
        version: str,
        training_data_start: str,
        training_data_end: str,
        metrics: Dict[str, float],
        params: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> MLModel:
        """
        새로운 모델을 MLflow에 등록하고 DB에 메타데이터 저장

        Args:
            model: 학습된 모델 객체 (scikit-learn, LightGBM 등)
            model_name: 모델 이름 (예: "IsolationForest-v1.0")
            model_type: 모델 유형 (isolation_forest, lightgbm 등)
            version: 버전 (Semantic Versioning)
            training_data_start: 학습 데이터 시작일 (YYYY-MM-DD)
            training_data_end: 학습 데이터 종료일 (YYYY-MM-DD)
            metrics: 성능 지표 (accuracy, precision, recall, f1_score)
            params: 학습 파라미터 (선택)
            tags: 추가 태그 (선택)

        Returns:
            MLModel: 생성된 모델 메타데이터 객체
        """
        # MLflow 실험 시작
        experiment_name = f"FDS-{model_type}"
        mlflow.set_experiment(experiment_name)

        with mlflow.start_run(run_name=f"{model_name}-{version}"):
            # 파라미터 로깅
            if params:
                mlflow.log_params(params)

            # 메트릭 로깅
            mlflow.log_metrics(metrics)

            # 태그 설정
            if tags:
                mlflow.set_tags(tags)
            mlflow.set_tag("version", version)
            mlflow.set_tag("model_type", model_type)
            mlflow.set_tag("training_period", f"{training_data_start} to {training_data_end}")

            # 모델 저장 (MLflow Model Registry에 등록)
            if model_type in ["isolation_forest", "random_forest"]:
                model_info = mlflow.sklearn.log_model(
                    sk_model=model,
                    artifact_path="model",
                    registered_model_name=model_name,
                )
            elif model_type == "lightgbm":
                model_info = mlflow.lightgbm.log_model(
                    lgb_model=model,
                    artifact_path="model",
                    registered_model_name=model_name,
                )
            else:
                # 기타 모델은 pickle로 저장
                model_path = Path(self.artifact_location) / f"{model_name}-{version}.pkl"
                with open(model_path, "wb") as f:
                    pickle.dump(model, f)
                mlflow.log_artifact(str(model_path), "model")
                model_info = None

            # MLflow Run ID 가져오기
            run_id = mlflow.active_run().info.run_id
            model_uri = f"runs:/{run_id}/model" if model_info else str(model_path)

        # DB에 모델 메타데이터 저장
        ml_model = MLModel(
            id=uuid4(),
            name=model_name,
            version=version,
            model_type=model_type,
            training_data_start=datetime.strptime(training_data_start, "%Y-%m-%d").date(),
            training_data_end=datetime.strptime(training_data_end, "%Y-%m-%d").date(),
            trained_at=datetime.utcnow(),
            accuracy=metrics.get("accuracy"),
            precision=metrics.get("precision"),
            recall=metrics.get("recall"),
            f1_score=metrics.get("f1_score"),
            deployment_status=DeploymentStatus.DEVELOPMENT,
            deployed_at=None,
            model_path=model_uri,
        )

        self.db_session.add(ml_model)
        await self.db_session.commit()
        await self.db_session.refresh(ml_model)

        return ml_model

    async def load_model(
        self,
        model_id: Optional[UUID] = None,
        model_name: Optional[str] = None,
        version: Optional[str] = None,
        deployment_status: Optional[DeploymentStatus] = None,
    ) -> tuple[Any, MLModel]:
        """
        MLflow에서 모델 로드

        Args:
            model_id: 모델 ID (우선순위 1)
            model_name: 모델 이름 (우선순위 2)
            version: 버전 (model_name과 함께 사용)
            deployment_status: 배포 상태 (기본값: PRODUCTION)

        Returns:
            tuple[모델 객체, MLModel 메타데이터]
        """
        # DB에서 모델 메타데이터 조회
        query = select(MLModel)

        if model_id:
            query = query.where(MLModel.id == model_id)
        elif model_name and version:
            query = query.where(
                and_(MLModel.name == model_name, MLModel.version == version)
            )
        elif model_name:
            # 버전 지정 없으면 최신 버전 사용
            query = (
                query.where(MLModel.name == model_name)
                .where(MLModel.deployment_status == (deployment_status or DeploymentStatus.PRODUCTION))
                .order_by(MLModel.trained_at.desc())
            )
        elif deployment_status:
            query = (
                query.where(MLModel.deployment_status == deployment_status)
                .order_by(MLModel.trained_at.desc())
            )
        else:
            raise ValueError("model_id, model_name, 또는 deployment_status 중 하나는 필수입니다")

        result = await self.db_session.execute(query)
        ml_model = result.scalars().first()

        if not ml_model:
            raise ValueError("모델을 찾을 수 없습니다")

        # MLflow에서 모델 로드
        model_path = ml_model.model_path

        if model_path.startswith("runs:/"):
            # MLflow 모델 레지스트리에서 로드
            if ml_model.model_type in ["isolation_forest", "random_forest"]:
                model = mlflow.sklearn.load_model(model_path)
            elif ml_model.model_type == "lightgbm":
                model = mlflow.lightgbm.load_model(model_path)
            else:
                raise ValueError(f"지원하지 않는 모델 타입: {ml_model.model_type}")
        else:
            # 로컬 파일에서 로드
            with open(model_path, "rb") as f:
                model = pickle.load(f)

        return model, ml_model

    async def promote_to_staging(self, model_id: UUID) -> MLModel:
        """
        모델을 스테이징 환경으로 승격

        Args:
            model_id: 모델 ID

        Returns:
            MLModel: 업데이트된 모델 메타데이터
        """
        # 기존 스테이징 모델을 개발 상태로 변경
        await self.db_session.execute(
            update(MLModel)
            .where(MLModel.deployment_status == DeploymentStatus.STAGING)
            .values(deployment_status=DeploymentStatus.DEVELOPMENT)
        )

        # 지정된 모델을 스테이징으로 승격
        await self.db_session.execute(
            update(MLModel)
            .where(MLModel.id == model_id)
            .values(deployment_status=DeploymentStatus.STAGING)
        )

        await self.db_session.commit()

        # 업데이트된 모델 조회
        result = await self.db_session.execute(select(MLModel).where(MLModel.id == model_id))
        return result.scalars().first()

    async def promote_to_production(self, model_id: UUID) -> MLModel:
        """
        모델을 프로덕션 환경으로 승격

        Args:
            model_id: 모델 ID

        Returns:
            MLModel: 업데이트된 모델 메타데이터
        """
        # 기존 프로덕션 모델을 은퇴 상태로 변경
        await self.db_session.execute(
            update(MLModel)
            .where(MLModel.deployment_status == DeploymentStatus.PRODUCTION)
            .values(deployment_status=DeploymentStatus.RETIRED)
        )

        # 지정된 모델을 프로덕션으로 승격
        await self.db_session.execute(
            update(MLModel)
            .where(MLModel.id == model_id)
            .values(
                deployment_status=DeploymentStatus.PRODUCTION,
                deployed_at=datetime.utcnow(),
            )
        )

        await self.db_session.commit()

        # 업데이트된 모델 조회
        result = await self.db_session.execute(select(MLModel).where(MLModel.id == model_id))
        return result.scalars().first()

    async def retire_model(self, model_id: UUID) -> MLModel:
        """
        모델을 은퇴 상태로 변경

        Args:
            model_id: 모델 ID

        Returns:
            MLModel: 업데이트된 모델 메타데이터
        """
        await self.db_session.execute(
            update(MLModel)
            .where(MLModel.id == model_id)
            .values(deployment_status=DeploymentStatus.RETIRED)
        )

        await self.db_session.commit()

        result = await self.db_session.execute(select(MLModel).where(MLModel.id == model_id))
        return result.scalars().first()

    async def list_models(
        self,
        deployment_status: Optional[DeploymentStatus] = None,
        model_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[MLModel]:
        """
        모델 목록 조회

        Args:
            deployment_status: 배포 상태 필터 (선택)
            model_type: 모델 타입 필터 (선택)
            limit: 조회 개수 제한 (기본값: 10)

        Returns:
            List[MLModel]: 모델 목록
        """
        query = select(MLModel).order_by(MLModel.trained_at.desc()).limit(limit)

        if deployment_status:
            query = query.where(MLModel.deployment_status == deployment_status)
        if model_type:
            query = query.where(MLModel.model_type == model_type)

        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def get_production_model(self, model_type: Optional[str] = None) -> Optional[MLModel]:
        """
        현재 프로덕션 모델 조회

        Args:
            model_type: 모델 타입 (선택)

        Returns:
            Optional[MLModel]: 프로덕션 모델 또는 None
        """
        query = select(MLModel).where(MLModel.deployment_status == DeploymentStatus.PRODUCTION)

        if model_type:
            query = query.where(MLModel.model_type == model_type)

        result = await self.db_session.execute(query)
        return result.scalars().first()

    async def compare_models(
        self,
        model_id_1: UUID,
        model_id_2: UUID,
    ) -> Dict[str, Any]:
        """
        두 모델의 성능 지표 비교

        Args:
            model_id_1: 첫 번째 모델 ID
            model_id_2: 두 번째 모델 ID

        Returns:
            Dict[str, Any]: 비교 결과
        """
        # 두 모델 조회
        result = await self.db_session.execute(
            select(MLModel).where(MLModel.id.in_([model_id_1, model_id_2]))
        )
        models = {m.id: m for m in result.scalars().all()}

        if len(models) != 2:
            raise ValueError("두 모델을 모두 찾을 수 없습니다")

        model_1 = models[model_id_1]
        model_2 = models[model_id_2]

        return {
            "model_1": {
                "id": str(model_1.id),
                "name": model_1.name,
                "version": model_1.version,
                "accuracy": float(model_1.accuracy) if model_1.accuracy else None,
                "precision": float(model_1.precision) if model_1.precision else None,
                "recall": float(model_1.recall) if model_1.recall else None,
                "f1_score": float(model_1.f1_score) if model_1.f1_score else None,
                "deployment_status": model_1.deployment_status.value,
            },
            "model_2": {
                "id": str(model_2.id),
                "name": model_2.name,
                "version": model_2.version,
                "accuracy": float(model_2.accuracy) if model_2.accuracy else None,
                "precision": float(model_2.precision) if model_2.precision else None,
                "recall": float(model_2.recall) if model_2.recall else None,
                "f1_score": float(model_2.f1_score) if model_2.f1_score else None,
                "deployment_status": model_2.deployment_status.value,
            },
            "comparison": {
                "accuracy_diff": (
                    float(model_2.accuracy - model_1.accuracy)
                    if model_1.accuracy and model_2.accuracy
                    else None
                ),
                "precision_diff": (
                    float(model_2.precision - model_1.precision)
                    if model_1.precision and model_2.precision
                    else None
                ),
                "recall_diff": (
                    float(model_2.recall - model_1.recall)
                    if model_1.recall and model_2.recall
                    else None
                ),
                "f1_score_diff": (
                    float(model_2.f1_score - model_1.f1_score)
                    if model_1.f1_score and model_2.f1_score
                    else None
                ),
            },
            "recommendation": self._generate_recommendation(model_1, model_2),
        }

    def _generate_recommendation(self, model_1: MLModel, model_2: MLModel) -> str:
        """
        모델 비교 결과에 따른 권장 사항 생성

        Args:
            model_1: 첫 번째 모델
            model_2: 두 번째 모델

        Returns:
            str: 권장 사항 메시지
        """
        if not model_1.f1_score or not model_2.f1_score:
            return "F1 스코어가 없어 비교할 수 없습니다"

        f1_diff = model_2.f1_score - model_1.f1_score

        if f1_diff > 0.05:
            return f"모델 2가 F1 스코어가 {f1_diff:.2%} 더 높습니다. 승격을 권장합니다."
        elif f1_diff < -0.05:
            return f"모델 1이 F1 스코어가 {-f1_diff:.2%} 더 높습니다. 모델 2 승격을 권장하지 않습니다."
        else:
            return "두 모델의 성능이 유사합니다. 추가 검증이 필요합니다."
