"""
TorchServe 배포 설정 모듈

PyTorch 모델을 TorchServe로 배포하여 프로덕션 추론 서버 구축
- Model Archive (.mar) 생성
- TorchServe 설정 파일 생성
- 배치 추론 설정 (배치 크기 50)
- Health Check 및 모니터링
"""

import subprocess
from pathlib import Path
from typing import Optional, List
import logging
import yaml

logger = logging.getLogger(__name__)


class TorchServeDeployer:
    """
    TorchServe 모델 배포 클래스

    Features:
    - Model Archive (.mar) 생성
    - config.properties 설정
    - 배치 추론 설정 (batch_size=50, max_batch_delay=50ms)
    - Health Check 엔드포인트
    - Prometheus 메트릭 노출
    """

    def __init__(self, model_store_path: Path, log_dir: Path):
        """
        Args:
            model_store_path: 모델 아카이브 저장 경로
            log_dir: TorchServe 로그 디렉토리
        """
        self.model_store_path = model_store_path
        self.log_dir = log_dir

        # 디렉토리 생성
        self.model_store_path.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        logger.info("[INIT] TorchServe deployer initialized")
        logger.info(f"  Model Store: {self.model_store_path}")
        logger.info(f"  Log Directory: {self.log_dir}")

    def create_model_archive(
        self,
        model_name: str,
        model_file: Path,
        handler: str,
        serialized_file: Optional[Path] = None,
        extra_files: Optional[List[Path]] = None,
        version: str = "1.0",
        requirements_file: Optional[Path] = None,
    ) -> Path:
        """
        PyTorch 모델을 TorchServe Model Archive (.mar)로 패키징

        Args:
            model_name: 모델 이름 (API 엔드포인트명)
            model_file: 모델 정의 파이썬 파일 (.py)
            handler: 커스텀 핸들러 파일 경로 또는 내장 핸들러명
                - 내장: "image_classifier", "text_classifier", "object_detector"
                - 커스텀: "path/to/custom_handler.py"
            serialized_file: 학습된 모델 파일 (.pt, .pth)
            extra_files: 추가 파일 (전처리 스크립트, 설정 파일 등)
            version: 모델 버전
            requirements_file: 의존성 파일 (requirements.txt)

        Returns:
            생성된 .mar 파일 경로

        Example:
            >>> deployer = TorchServeDeployer(Path("./model_store"), Path("./logs"))
            >>> mar_path = deployer.create_model_archive(
            ...     model_name="fraud_detector",
            ...     model_file=Path("./model.py"),
            ...     handler="custom_handler.py",
            ...     serialized_file=Path("./model.pth"),
            ...     version="1.0"
            ... )
        """
        logger.info(f"[MAR] Creating model archive: {model_name} v{version}...")

        mar_path = self.model_store_path / f"{model_name}.mar"

        # torch-model-archiver 명령어 구성
        cmd = [
            "torch-model-archiver",
            "--model-name",
            model_name,
            "--version",
            version,
            "--model-file",
            str(model_file),
            "--handler",
            str(handler),
            "--export-path",
            str(self.model_store_path),
            "--force",  # 기존 파일 덮어쓰기
        ]

        if serialized_file:
            cmd.extend(["--serialized-file", str(serialized_file)])

        if extra_files:
            extra_files_str = ",".join([str(f) for f in extra_files])
            cmd.extend(["--extra-files", extra_files_str])

        if requirements_file:
            cmd.extend(["--requirements-file", str(requirements_file)])

        try:
            subprocess.run(
                cmd, capture_output=True, text=True, check=True, encoding="utf-8"
            )
            logger.info(f"[OK] Model archive created: {mar_path}")
            return mar_path

        except subprocess.CalledProcessError as e:
            logger.error(f"[FAIL] Failed to create model archive: {e.stderr}")
            raise

    def create_config_properties(
        self,
        config_path: Path,
        inference_address: str = "http://0.0.0.0:8080",
        management_address: str = "http://0.0.0.0:8081",
        metrics_address: str = "http://0.0.0.0:8082",
        enable_metrics_api: bool = True,
        metrics_format: str = "prometheus",
        number_of_workers: int = 4,
        job_queue_size: int = 100,
        batch_size: int = 50,
        max_batch_delay: int = 50,
        response_timeout: int = 120,
    ) -> None:
        """
        TorchServe config.properties 생성

        Args:
            config_path: 설정 파일 저장 경로
            inference_address: 추론 API 주소
            management_address: 관리 API 주소
            metrics_address: 메트릭 API 주소
            enable_metrics_api: Prometheus 메트릭 활성화
            metrics_format: 메트릭 포맷 (prometheus 또는 log)
            number_of_workers: 워커 프로세스 수
            job_queue_size: 작업 큐 크기
            batch_size: 배치 추론 크기 (50 권장)
            max_batch_delay: 최대 배치 지연 시간 (ms)
            response_timeout: 응답 타임아웃 (초)

        Note:
            - batch_size=50: 동시 요청 50개 이상 시 배치 추론 활성화
            - max_batch_delay=50ms: 배치 수집 최대 대기 시간
            - 1,000 TPS 부하에서 P95 50ms 달성 목표
        """
        logger.info(
            f"[CONFIG] Creating TorchServe config.properties at {config_path}..."
        )

        config = {
            "inference_address": inference_address,
            "management_address": management_address,
            "metrics_address": metrics_address,
            "enable_metrics_api": str(enable_metrics_api).lower(),
            "metrics_format": metrics_format,
            "number_of_netty_threads": number_of_workers,
            "job_queue_size": job_queue_size,
            "default_workers_per_model": number_of_workers,
            "default_response_timeout": response_timeout,
            "model_store": str(self.model_store_path),
            "load_models": "all",  # 시작 시 모든 모델 로드
            # 배치 추론 설정
            "default_batch_size": batch_size,
            "max_batch_delay": max_batch_delay,
            # 로깅 설정
            "log_location": str(self.log_dir),
            "metrics_location": str(self.log_dir / "metrics"),
        }

        config_content = "\n".join([f"{key}={value}" for key, value in config.items()])

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_content)

        logger.info("[OK] config.properties created")
        logger.info(f"  Batch size: {batch_size}")
        logger.info(f"  Max batch delay: {max_batch_delay}ms")
        logger.info(f"  Workers: {number_of_workers}")

    def create_model_config(
        self,
        model_name: str,
        config_path: Path,
        min_workers: int = 2,
        max_workers: int = 4,
        batch_size: int = 50,
        max_batch_delay: int = 50,
        response_timeout: int = 120,
    ) -> None:
        """
        개별 모델 설정 파일 생성 (model-config.yaml)

        Args:
            model_name: 모델 이름
            config_path: 설정 파일 저장 경로
            min_workers: 최소 워커 수
            max_workers: 최대 워커 수
            batch_size: 배치 크기
            max_batch_delay: 최대 배치 지연 시간 (ms)
            response_timeout: 응답 타임아웃 (초)
        """
        logger.info(f"[MODEL CONFIG] Creating model config for {model_name}...")

        config = {
            "minWorkers": min_workers,
            "maxWorkers": max_workers,
            "batchSize": batch_size,
            "maxBatchDelay": max_batch_delay,
            "responseTimeout": response_timeout,
        }

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump({model_name: config}, f, default_flow_style=False)

        logger.info(f"[OK] Model config created: {config_path}")

    def create_custom_handler(self, handler_path: Path) -> None:
        """
        커스텀 TorchServe 핸들러 템플릿 생성

        Args:
            handler_path: 핸들러 파일 저장 경로

        Note:
            - 배치 추론 지원
            - 전처리/후처리 커스터마이징
            - Feature Engineering 통합
        """
        logger.info(f"[HANDLER] Creating custom handler template at {handler_path}...")

        handler_template = '''"""
TorchServe Custom Handler for FDS Fraud Detection

Batch Inference 지원, Feature Engineering 통합
"""

import torch
import numpy as np
import logging
from ts.torch_handler.base_handler import BaseHandler

logger = logging.getLogger(__name__)


class FraudDetectionHandler(BaseHandler):
    """
    FDS 사기 탐지 모델 핸들러

    Features:
    - 배치 추론 지원 (batch_size=50)
    - Feature Engineering 자동 적용
    - 출력 후처리 (확률 -> 리스크 점수)
    """

    def __init__(self):
        super().__init__()
        self.initialized = False

    def initialize(self, context):
        """
        핸들러 초기화 (모델 로드, 설정 로드)

        Args:
            context: TorchServe context
        """
        self.manifest = context.manifest
        properties = context.system_properties
        model_dir = properties.get("model_dir")

        # 모델 로드
        serialized_file = self.manifest["model"]["serializedFile"]
        model_pt_path = f"{model_dir}/{serialized_file}"

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.model = torch.jit.load(model_pt_path, map_location=self.device)
        self.model.eval()

        logger.info(f"[INIT] Model loaded from {model_pt_path}")
        logger.info(f"[INIT] Using device: {self.device}")

        self.initialized = True

    def preprocess(self, data):
        """
        전처리: 입력 데이터를 텐서로 변환 + Feature Engineering

        Args:
            data: 요청 데이터 리스트

        Returns:
            전처리된 텐서
        """
        # JSON 데이터 파싱
        features_list = []
        for row in data:
            body = row.get("body")
            if isinstance(body, (bytes, bytearray)):
                body = body.decode("utf-8")

            import json
            features = json.loads(body)

            # Feature Engineering 적용 (예시)
            feature_vector = [
                features.get("amount", 0),
                features.get("velocity_24h", 0),
                features.get("device_risk_score", 0),
                # ... 추가 특징들
            ]
            features_list.append(feature_vector)

        # 텐서 변환
        features_tensor = torch.tensor(
            features_list, dtype=torch.float32, device=self.device
        )

        logger.debug(f"[PREPROCESS] Batch size: {len(features_list)}")
        return features_tensor

    def inference(self, model_input):
        """
        추론 실행 (배치 추론)

        Args:
            model_input: 전처리된 텐서

        Returns:
            모델 출력
        """
        with torch.no_grad():
            model_output = self.model(model_input)

        logger.debug(f"[INFERENCE] Output shape: {model_output.shape}")
        return model_output

    def postprocess(self, inference_output):
        """
        후처리: 확률 -> 리스크 점수 변환

        Args:
            inference_output: 모델 출력

        Returns:
            JSON 응답 리스트
        """
        # 확률을 리스크 점수로 변환 (0-100)
        probabilities = torch.softmax(inference_output, dim=1)
        fraud_probs = probabilities[:, 1].cpu().numpy()  # 사기 클래스 확률

        results = []
        for prob in fraud_probs:
            risk_score = int(prob * 100)
            risk_level = "low" if risk_score < 30 else "medium" if risk_score < 70 else "high"

            results.append({
                "risk_score": risk_score,
                "risk_level": risk_level,
                "fraud_probability": float(prob),
            })

        logger.debug(f"[POSTPROCESS] Processed {len(results)} results")
        return results
'''

        with open(handler_path, "w", encoding="utf-8") as f:
            f.write(handler_template)

        logger.info("[OK] Custom handler template created")

    def start_torchserve(
        self, config_path: Path, foreground: bool = False
    ) -> subprocess.Popen:
        """
        TorchServe 서버 시작

        Args:
            config_path: config.properties 경로
            foreground: True면 포그라운드 실행, False면 백그라운드

        Returns:
            프로세스 객체 (백그라운드 실행 시)
        """
        logger.info("[START] Starting TorchServe server...")

        cmd = [
            "torchserve",
            "--start",
            "--model-store",
            str(self.model_store_path),
            "--ts-config",
            str(config_path),
        ]

        if foreground:
            cmd.append("--foreground")

        try:
            if foreground:
                subprocess.run(cmd, check=True)
                return None
            else:
                process = subprocess.Popen(cmd)
                logger.info(f"[OK] TorchServe started (PID: {process.pid})")
                logger.info(
                    "  Inference API: http://0.0.0.0:8080/predictions/<model_name>"
                )
                logger.info("  Management API: http://0.0.0.0:8081")
                logger.info("  Metrics API: http://0.0.0.0:8082/metrics")
                return process

        except subprocess.CalledProcessError as e:
            logger.error(f"[FAIL] Failed to start TorchServe: {e}")
            raise

    def stop_torchserve(self) -> None:
        """
        TorchServe 서버 중지
        """
        logger.info("[STOP] Stopping TorchServe server...")

        try:
            subprocess.run(["torchserve", "--stop"], check=True)
            logger.info("[OK] TorchServe stopped")

        except subprocess.CalledProcessError as e:
            logger.error(f"[FAIL] Failed to stop TorchServe: {e}")
            raise


# 사용 예시
if __name__ == "__main__":
    # TorchServe 배포 설정
    deployer = TorchServeDeployer(
        model_store_path=Path("./model_store"), log_dir=Path("./logs")
    )

    # 1. 커스텀 핸들러 생성
    handler_path = Path("./fraud_handler.py")
    deployer.create_custom_handler(handler_path)

    # 2. Model Archive 생성
    mar_path = deployer.create_model_archive(
        model_name="fraud_detector",
        model_file=Path("./model_definition.py"),
        handler=str(handler_path),
        serialized_file=Path("./model.pt"),
        version="1.0",
    )

    # 3. TorchServe 설정 생성
    config_path = Path("./config.properties")
    deployer.create_config_properties(
        config_path,
        batch_size=50,  # 배치 크기 50
        max_batch_delay=50,  # 최대 50ms 대기
        number_of_workers=4,
    )

    # 4. 모델별 설정 생성
    model_config_path = Path("./model-config.yaml")
    deployer.create_model_config(
        model_name="fraud_detector", config_path=model_config_path, batch_size=50
    )

    # 5. TorchServe 시작
    # deployer.start_torchserve(config_path, foreground=False)

    print("[OK] TorchServe deployment setup completed")
    print(
        "Run: torchserve --start --model-store ./model_store --ts-config ./config.properties"
    )
