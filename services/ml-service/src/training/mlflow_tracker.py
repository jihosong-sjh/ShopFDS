"""
MLflow Experiment Tracking Integration

MLflow를 사용하여 ML 실험을 추적하고 모델을 관리합니다.

주요 기능:
1. 실험 생성 및 관리
2. 학습 파라미터 및 메트릭 로깅
3. 모델 아티팩트 저장 및 버전 관리
4. 비교 및 분석
"""

import logging
from typing import Dict, Any, Optional
import mlflow
import mlflow.sklearn
import mlflow.xgboost
import mlflow.pytorch


logger = logging.getLogger(__name__)


class MLflowTracker:
    """
    MLflow 실험 추적 클래스
    """

    def __init__(
        self,
        tracking_uri: Optional[str] = None,
        experiment_name: str = "fraud-detection-ensemble",
    ):
        """
        Args:
            tracking_uri: MLflow Tracking Server URI (None이면 로컬)
            experiment_name: 실험 이름
        """
        self.tracking_uri = tracking_uri or "file:./mlruns"
        self.experiment_name = experiment_name

        # MLflow 설정
        mlflow.set_tracking_uri(self.tracking_uri)
        mlflow.set_experiment(self.experiment_name)

        logger.info(
            f"[MLflow] Tracking URI: {self.tracking_uri}, "
            f"Experiment: {self.experiment_name}"
        )

    def start_run(self, run_name: Optional[str] = None) -> str:
        """
        MLflow 실행 시작

        Args:
            run_name: 실행 이름 (옵션)

        Returns:
            Run ID
        """
        run = mlflow.start_run(run_name=run_name)
        logger.info(f"[MLflow] Started run: {run.info.run_id}")
        return run.info.run_id

    def log_params(self, params: Dict[str, Any]) -> None:
        """파라미터 로깅"""
        mlflow.log_params(params)
        logger.debug(f"[MLflow] Logged {len(params)} parameters")

    def log_metrics(
        self, metrics: Dict[str, float], step: Optional[int] = None
    ) -> None:
        """메트릭 로깅"""
        mlflow.log_metrics(metrics, step=step)
        logger.debug(f"[MLflow] Logged {len(metrics)} metrics")

    def log_model(self, model, model_name: str, model_type: str = "sklearn") -> None:
        """
        모델 아티팩트 로깅

        Args:
            model: 모델 객체
            model_name: 모델 이름
            model_type: 모델 타입 (sklearn, xgboost, pytorch)
        """
        if model_type == "sklearn":
            mlflow.sklearn.log_model(model, model_name)
        elif model_type == "xgboost":
            mlflow.xgboost.log_model(model, model_name)
        elif model_type == "pytorch":
            mlflow.pytorch.log_model(model, model_name)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

        logger.info(f"[MLflow] Logged model: {model_name} (type: {model_type})")

    def log_artifact(self, local_path: str) -> None:
        """아티팩트 파일 로깅"""
        mlflow.log_artifact(local_path)
        logger.debug(f"[MLflow] Logged artifact: {local_path}")

    def end_run(self) -> None:
        """실행 종료"""
        mlflow.end_run()
        logger.info("[MLflow] Ended run")

    def log_ensemble_training(
        self,
        params: Dict[str, Any],
        train_metrics: Dict[str, Any],
        eval_metrics: Dict[str, Any],
        models: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        앙상블 학습 전체 과정 로깅

        Args:
            params: 학습 파라미터
            train_metrics: 학습 메트릭
            eval_metrics: 평가 메트릭
            models: 모델 딕셔너리 (옵션)

        Returns:
            Run ID
        """
        run_id = self.start_run(run_name="ensemble_training")

        try:
            # 파라미터 로깅
            self.log_params(params)

            # 학습 메트릭 로깅
            if "individual_metrics" in train_metrics:
                for model_name, metrics in train_metrics["individual_metrics"].items():
                    for key, value in metrics.items():
                        if isinstance(value, (int, float)):
                            mlflow.log_metric(f"train_{model_name}_{key}", value)

            # 평가 메트릭 로깅
            for key, value in eval_metrics.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(f"eval_{key}", value)

            # 개별 모델 메트릭 로깅
            if "individual_metrics" in eval_metrics:
                for model_name, metrics in eval_metrics["individual_metrics"].items():
                    for key, value in metrics.items():
                        if isinstance(value, (int, float)):
                            mlflow.log_metric(f"eval_{model_name}_{key}", value)

            # 모델 저장 (옵션)
            if models:
                for model_name, model_obj in models.items():
                    try:
                        if model_name == "random_forest":
                            self.log_model(model_obj.model, model_name, "sklearn")
                        elif model_name == "xgboost":
                            self.log_model(model_obj.model, model_name, "xgboost")
                        elif model_name in ["autoencoder", "lstm"]:
                            self.log_model(model_obj.model, model_name, "pytorch")
                    except Exception as e:
                        logger.warning(f"[MLflow] Failed to log {model_name}: {e}")

            logger.info(
                f"[MLflow] Ensemble training logged successfully (run_id: {run_id})"
            )

        finally:
            self.end_run()

        return run_id


def track_experiment(
    experiment_name: str,
    params: Dict[str, Any],
    metrics: Dict[str, Any],
    model: Optional[Any] = None,
    model_name: Optional[str] = None,
    artifacts: Optional[Dict[str, str]] = None,
) -> str:
    """
    ML 실험 추적 (편의 함수)

    Args:
        experiment_name: 실험 이름
        params: 파라미터
        metrics: 메트릭
        model: 모델 (옵션)
        model_name: 모델 이름 (옵션)
        artifacts: 아티팩트 경로 딕셔너리 (옵션)

    Returns:
        Run ID
    """
    tracker = MLflowTracker(experiment_name=experiment_name)
    run_id = tracker.start_run()

    try:
        tracker.log_params(params)
        tracker.log_metrics(metrics)

        if model and model_name:
            tracker.log_model(model, model_name)

        if artifacts:
            for artifact_path in artifacts.values():
                tracker.log_artifact(artifact_path)

    finally:
        tracker.end_run()

    return run_id
