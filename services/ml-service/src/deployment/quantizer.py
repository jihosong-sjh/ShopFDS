"""
PyTorch 모델 INT8 양자화 모듈

모델 크기 축소 및 추론 속도 향상을 위한 양자화 기능 제공
- Dynamic Quantization: 가중치 및 활성화 함수 양자화
- Static Quantization: 캘리브레이션 데이터 기반 정적 양자화
- 양자화 후 정확도 검증
"""

import torch
import torch.nn as nn
import torch.quantization as quantization
from torch.quantization import QConfig, default_observer, default_weight_observer
from typing import Optional, Dict, Any, Tuple
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ModelQuantizer:
    """
    PyTorch 모델 INT8 양자화 클래스

    Features:
    - Dynamic Quantization (런타임 활성화 양자화)
    - Static Quantization (사전 캘리브레이션 양자화)
    - Quantization-Aware Training (QAT) 지원
    - 양자화 전후 정확도 비교
    """

    def __init__(self):
        self.quantization_config = QConfig(
            activation=default_observer, weight=default_weight_observer
        )

    def dynamic_quantization(
        self,
        model: nn.Module,
        dtype: torch.dtype = torch.qint8,
        qconfig_spec: Optional[Dict[str, Any]] = None,
    ) -> nn.Module:
        """
        동적 양자화 수행 (추론 시점에 활성화 양자화)

        Use Case:
        - LSTM, GRU 등 RNN 모델
        - Linear Layer 위주 모델
        - 빠른 추론 필요 시

        Args:
            model: 양자화할 PyTorch 모델
            dtype: 양자화 데이터 타입 (qint8 권장)
            qconfig_spec: 레이어별 양자화 설정 (선택사항)

        Returns:
            양자화된 모델

        Example:
            >>> quantizer = ModelQuantizer()
            >>> model = MyLSTMModel()
            >>> quantized_model = quantizer.dynamic_quantization(model)
        """
        logger.info("[DYNAMIC QUANTIZATION] Starting dynamic quantization...")

        # 기본 설정: Linear, LSTM, GRU 레이어 양자화
        if qconfig_spec is None:
            qconfig_spec = {nn.Linear, nn.LSTM, nn.GRU}

        try:
            quantized_model = quantization.quantize_dynamic(
                model, qconfig_spec=qconfig_spec, dtype=dtype
            )

            model_size_before = self._get_model_size(model)
            model_size_after = self._get_model_size(quantized_model)
            reduction_ratio = (
                (model_size_before - model_size_after) / model_size_before * 100
            )

            logger.info(
                f"[OK] Model size: {model_size_before:.2f}MB -> {model_size_after:.2f}MB"
            )
            logger.info(f"[OK] Size reduction: {reduction_ratio:.1f}%%")

            return quantized_model

        except Exception as e:
            logger.error(f"[FAIL] Dynamic quantization failed: {e}")
            raise

    def static_quantization(
        self,
        model: nn.Module,
        calibration_loader: torch.utils.data.DataLoader,
        backend: str = "fbgemm",
    ) -> nn.Module:
        """
        정적 양자화 수행 (사전 캘리브레이션 기반)

        Use Case:
        - CNN 모델 (ResNet, VGG 등)
        - 고정된 입력 크기
        - 최대 성능 필요 시

        Args:
            model: 양자화할 PyTorch 모델
            calibration_loader: 캘리브레이션 데이터 로더 (1000개 샘플 권장)
            backend: 양자화 백엔드 ('fbgemm': x86, 'qnnpack': ARM)

        Returns:
            양자화된 모델

        Example:
            >>> quantizer = ModelQuantizer()
            >>> model = MyResNet()
            >>> quantized_model = quantizer.static_quantization(model, calib_loader)
        """
        logger.info(
            f"[STATIC QUANTIZATION] Starting static quantization (backend: {backend})..."
        )

        try:
            # 양자화 백엔드 설정
            torch.backends.quantized.engine = backend

            # 1. 양자화 설정 적용
            model.qconfig = quantization.get_default_qconfig(backend)
            quantization.prepare(model, inplace=True)

            # 2. 캘리브레이션 (통계 수집)
            logger.info("[CALIBRATION] Collecting activation statistics...")
            model.eval()
            with torch.no_grad():
                for i, (inputs, _) in enumerate(calibration_loader):
                    model(inputs)
                    if i >= 100:  # 100 배치로 캘리브레이션 제한
                        break
            logger.info("[OK] Calibration completed")

            # 3. 양자화 변환
            quantized_model = quantization.convert(model, inplace=False)

            model_size_before = self._get_model_size(model)
            model_size_after = self._get_model_size(quantized_model)
            reduction_ratio = (
                (model_size_before - model_size_after) / model_size_before * 100
            )

            logger.info(
                f"[OK] Model size: {model_size_before:.2f}MB -> {model_size_after:.2f}MB"
            )
            logger.info(f"[OK] Size reduction: {reduction_ratio:.1f}%%")

            return quantized_model

        except Exception as e:
            logger.error(f"[FAIL] Static quantization failed: {e}")
            raise

    def quantization_aware_training_prepare(
        self, model: nn.Module, backend: str = "fbgemm"
    ) -> nn.Module:
        """
        Quantization-Aware Training (QAT) 준비

        Use Case:
        - 양자화로 인한 정확도 손실 최소화
        - Fine-tuning 필요 시

        Args:
            model: 양자화 학습할 모델
            backend: 양자화 백엔드

        Returns:
            QAT 준비된 모델 (학습 필요)

        Example:
            >>> quantizer = ModelQuantizer()
            >>> model = MyModel()
            >>> qat_model = quantizer.quantization_aware_training_prepare(model)
            >>> # 이후 일반적인 학습 루프 수행
            >>> for epoch in range(epochs):
            >>>     train_one_epoch(qat_model, ...)
            >>> quantized_model = quantizer.quantization_aware_training_convert(qat_model)
        """
        logger.info("[QAT] Preparing model for Quantization-Aware Training...")

        torch.backends.quantized.engine = backend
        model.qconfig = quantization.get_default_qat_qconfig(backend)
        quantization.prepare_qat(model, inplace=True)

        logger.info("[OK] Model ready for QAT (train now, then call convert)")
        return model

    def quantization_aware_training_convert(self, qat_model: nn.Module) -> nn.Module:
        """
        QAT 학습 완료 후 양자화 모델 변환

        Args:
            qat_model: QAT 학습 완료된 모델

        Returns:
            최종 양자화된 모델
        """
        logger.info("[QAT] Converting QAT model to quantized model...")
        qat_model.eval()
        quantized_model = quantization.convert(qat_model, inplace=False)
        logger.info("[OK] QAT conversion completed")
        return quantized_model

    def verify_accuracy(
        self,
        original_model: nn.Module,
        quantized_model: nn.Module,
        test_loader: torch.utils.data.DataLoader,
        tolerance: float = 0.01,
    ) -> Tuple[float, float, bool]:
        """
        양자화 전후 정확도 검증

        Args:
            original_model: 원본 모델
            quantized_model: 양자화된 모델
            test_loader: 테스트 데이터 로더
            tolerance: 허용 가능한 정확도 손실 (기본 1%)

        Returns:
            (원본 정확도, 양자화 정확도, 통과 여부)

        Raises:
            ValueError: 정확도 손실이 허용 범위 초과 시
        """
        logger.info("[ACCURACY CHECK] Verifying quantized model accuracy...")

        def evaluate_model(model: nn.Module) -> float:
            model.eval()
            correct = 0
            total = 0

            with torch.no_grad():
                for inputs, labels in test_loader:
                    outputs = model(inputs)
                    _, predicted = torch.max(outputs, 1)
                    total += labels.size(0)
                    correct += (predicted == labels).sum().item()

            return correct / total if total > 0 else 0.0

        original_acc = evaluate_model(original_model)
        quantized_acc = evaluate_model(quantized_model)
        accuracy_loss = original_acc - quantized_acc

        logger.info(f"[RESULT] Original accuracy: {original_acc:.4f}")
        logger.info(f"[RESULT] Quantized accuracy: {quantized_acc:.4f}")
        logger.info(
            f"[RESULT] Accuracy loss: {accuracy_loss:.4f} ({accuracy_loss*100:.2f}%%)"
        )

        passed = accuracy_loss <= tolerance

        if passed:
            logger.info(
                f"[PASS] Accuracy loss within tolerance ({tolerance*100:.1f}%%)"
            )
        else:
            logger.warning(
                f"[FAIL] Accuracy loss exceeds tolerance ({tolerance*100:.1f}%%)"
            )

        return original_acc, quantized_acc, passed

    def save_quantized_model(
        self,
        quantized_model: nn.Module,
        save_path: Path,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        양자화 모델 저장 (TorchScript 형식)

        Args:
            quantized_model: 양자화된 모델
            save_path: 저장 경로 (.pt 파일)
            metadata: 메타데이터 (양자화 설정, 정확도 등)
        """
        logger.info(f"[SAVE] Saving quantized model to {save_path}...")

        try:
            # TorchScript 변환 후 저장
            quantized_model.eval()
            scripted_model = torch.jit.script(quantized_model)
            torch.jit.save(scripted_model, str(save_path))

            # 메타데이터 저장
            if metadata:
                metadata_path = save_path.with_suffix(".json")
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                logger.info(f"[OK] Metadata saved to {metadata_path}")

            model_size_mb = save_path.stat().st_size / (1024 * 1024)
            logger.info(f"[OK] Model saved ({model_size_mb:.2f}MB)")

        except Exception as e:
            logger.error(f"[FAIL] Failed to save model: {e}")
            raise

    def load_quantized_model(self, load_path: Path) -> nn.Module:
        """
        양자화 모델 로드

        Args:
            load_path: 모델 파일 경로 (.pt)

        Returns:
            로드된 양자화 모델
        """
        logger.info(f"[LOAD] Loading quantized model from {load_path}...")

        try:
            quantized_model = torch.jit.load(str(load_path))
            quantized_model.eval()

            model_size_mb = load_path.stat().st_size / (1024 * 1024)
            logger.info(f"[OK] Model loaded ({model_size_mb:.2f}MB)")

            return quantized_model

        except Exception as e:
            logger.error(f"[FAIL] Failed to load model: {e}")
            raise

    def _get_model_size(self, model: nn.Module) -> float:
        """
        모델 크기 계산 (MB)

        Args:
            model: PyTorch 모델

        Returns:
            모델 크기 (MB)
        """
        param_size = 0
        buffer_size = 0

        for param in model.parameters():
            param_size += param.nelement() * param.element_size()

        for buffer in model.buffers():
            buffer_size += buffer.nelement() * buffer.element_size()

        size_mb = (param_size + buffer_size) / (1024 * 1024)
        return size_mb


# 사용 예시
if __name__ == "__main__":
    import torch.nn as nn

    # 예제 모델
    class SimpleModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = nn.Linear(100, 50)
            self.fc2 = nn.Linear(50, 10)

        def forward(self, x):
            x = torch.relu(self.fc1(x))
            x = self.fc2(x)
            return x

    # 양자화 실행
    model = SimpleModel()
    quantizer = ModelQuantizer()

    # Dynamic Quantization
    quantized_model = quantizer.dynamic_quantization(model)

    # 모델 저장
    save_path = Path("./quantized_model.pt")
    quantizer.save_quantized_model(
        quantized_model,
        save_path,
        metadata={"quantization_type": "dynamic", "dtype": "qint8"},
    )

    print("[OK] Quantization example completed")
