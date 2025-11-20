"""
Autoencoder Model for Fraud Detection (Anomaly Detection)

Autoencoder는 비정상 거래를 탐지하는 비지도 학습 모델로, 다음과 같은 특징을 가집니다:
- 정상 거래 패턴을 학습하여 압축 및 복원
- Reconstruction Error가 높은 거래를 사기로 판단
- 새로운 사기 패턴 탐지에 효과적
- PyTorch 기반 딥러닝 모델

모델 가중치: 25% (앙상블 내)
"""

import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix
from pathlib import Path


logger = logging.getLogger(__name__)


class AutoencoderNetwork(nn.Module):
    """
    Autoencoder 신경망 구조

    인코더: 입력 -> 128 -> 64 -> 32 -> 16 (잠재 공간)
    디코더: 16 -> 32 -> 64 -> 128 -> 출력
    """

    def __init__(self, input_dim: int, latent_dim: int = 16):
        """
        Args:
            input_dim: 입력 특징 차원
            latent_dim: 잠재 공간 차원 (병목 계층)
        """
        super(AutoencoderNetwork, self).__init__()

        # Encoder (인코더)
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.BatchNorm1d(32),
            nn.Linear(32, latent_dim),
            nn.ReLU(),
        )

        # Decoder (디코더)
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.ReLU(),
            nn.BatchNorm1d(32),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(0.2),
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.BatchNorm1d(128),
            nn.Dropout(0.2),
            nn.Linear(128, input_dim),
        )

    def forward(self, x):
        """순전파"""
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded


class AutoencoderFraudModel:
    """
    Autoencoder 기반 사기 탐지 모델

    정상 거래로 학습한 후, Reconstruction Error가 높은 거래를 사기로 판단
    """

    def __init__(
        self,
        latent_dim: int = 16,
        learning_rate: float = 0.001,
        batch_size: int = 256,
        epochs: int = 50,
        device: str = "auto",
        random_state: int = 42,
    ):
        """
        Args:
            latent_dim: 잠재 공간 차원
            learning_rate: 학습률
            batch_size: 배치 크기
            epochs: 학습 에포크 수
            device: 디바이스 (auto, cpu, cuda)
            random_state: 재현성을 위한 시드
        """
        # 디바이스 설정
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        logger.info(f"[Autoencoder] Using device: {self.device}")

        self.latent_dim = latent_dim
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        self.random_state = random_state

        # 모델 및 상태
        self.model: Optional[AutoencoderNetwork] = None
        self.scaler = StandardScaler()
        self.threshold: Optional[float] = None  # Reconstruction Error 임계값
        self.feature_names: Optional[list] = None
        self.is_trained = False

        # 시드 고정
        torch.manual_seed(random_state)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(random_state)

    def train(self, X_train: pd.DataFrame, y_train: pd.Series) -> Dict[str, Any]:
        """
        Autoencoder 모델 학습 (정상 거래만 사용)

        Args:
            X_train: 학습 특징 데이터
            y_train: 학습 레이블 (0: 정상, 1: 사기)

        Returns:
            학습 결과 메트릭
        """
        logger.info(
            f"[Autoencoder] Training started: {len(X_train)} samples, "
            f"{X_train.shape[1]} features"
        )

        # Feature 이름 저장
        self.feature_names = X_train.columns.tolist()

        # 정상 거래만 추출 (비지도 학습)
        X_normal = X_train[y_train == 0]
        logger.info(
            f"[Autoencoder] Using {len(X_normal)} normal transactions for training"
        )

        # 데이터 정규화
        X_normal_scaled = self.scaler.fit_transform(X_normal)

        # PyTorch Tensor 변환
        X_tensor = torch.FloatTensor(X_normal_scaled).to(self.device)
        dataset = TensorDataset(X_tensor, X_tensor)  # Input = Output (Autoencoder)
        dataloader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)

        # 모델 초기화
        input_dim = X_train.shape[1]
        self.model = AutoencoderNetwork(input_dim, self.latent_dim).to(self.device)

        # 옵티마이저 및 손실 함수
        optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)
        criterion = nn.MSELoss()

        # 학습 루프
        self.model.train()
        train_losses = []

        for epoch in range(self.epochs):
            epoch_loss = 0.0
            for batch_X, batch_y in dataloader:
                # Forward pass
                reconstructed = self.model(batch_X)
                loss = criterion(reconstructed, batch_y)

                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()

            avg_loss = epoch_loss / len(dataloader)
            train_losses.append(avg_loss)

            if (epoch + 1) % 10 == 0:
                logger.info(
                    f"[Autoencoder] Epoch {epoch + 1}/{self.epochs}, Loss: {avg_loss:.6f}"
                )

        # Reconstruction Error 임계값 계산 (95th percentile)
        self.model.eval()
        with torch.no_grad():
            X_train_scaled = self.scaler.transform(X_train)
            X_train_tensor = torch.FloatTensor(X_train_scaled).to(self.device)
            reconstructed = self.model(X_train_tensor).cpu().numpy()
            reconstruction_errors = np.mean(
                (X_train_scaled - reconstructed) ** 2, axis=1
            )

            # 95th percentile을 임계값으로 설정
            self.threshold = float(np.percentile(reconstruction_errors, 95))

        self.is_trained = True

        logger.info(
            f"[Autoencoder] Training completed: Final loss={train_losses[-1]:.6f}, "
            f"Threshold={self.threshold:.6f}"
        )

        return {
            "model_type": "autoencoder",
            "latent_dim": self.latent_dim,
            "epochs": self.epochs,
            "final_loss": train_losses[-1],
            "threshold": self.threshold,
            "n_features": len(self.feature_names),
            "train_losses": train_losses,
        }

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        사기 여부 예측 (0 또는 1)

        Reconstruction Error가 임계값보다 크면 사기(1)

        Args:
            X: 예측할 특징 데이터

        Returns:
            예측 레이블 배열
        """
        if not self.is_trained:
            raise ValueError("Model is not trained yet. Call train() first.")

        reconstruction_errors = self._get_reconstruction_errors(X)

        # 임계값보다 큰 경우 사기(1)
        return (reconstruction_errors > self.threshold).astype(int)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        사기 확률 예측 (0.0 ~ 1.0)

        Reconstruction Error를 정규화하여 확률로 변환

        Args:
            X: 예측할 특징 데이터

        Returns:
            사기 확률 배열
        """
        if not self.is_trained:
            raise ValueError("Model is not trained yet. Call train() first.")

        reconstruction_errors = self._get_reconstruction_errors(X)

        # Reconstruction Error를 [0, 1] 범위로 정규화
        # Sigmoid 변환: 1 / (1 + exp(-k * (error - threshold)))
        k = 10.0  # 기울기 조정 파라미터
        probabilities = 1 / (1 + np.exp(-k * (reconstruction_errors - self.threshold)))

        return probabilities

    def _get_reconstruction_errors(self, X: pd.DataFrame) -> np.ndarray:
        """
        Reconstruction Error 계산

        Args:
            X: 특징 데이터

        Returns:
            샘플별 Reconstruction Error 배열
        """
        self.model.eval()
        with torch.no_grad():
            X_scaled = self.scaler.transform(X)
            X_tensor = torch.FloatTensor(X_scaled).to(self.device)
            reconstructed = self.model(X_tensor).cpu().numpy()

            # MSE per sample
            reconstruction_errors = np.mean((X_scaled - reconstructed) ** 2, axis=1)

        return reconstruction_errors

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
        self.predict_proba(X_test)

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

        # Reconstruction Error 통계
        reconstruction_errors = self._get_reconstruction_errors(X_test)
        normal_errors = reconstruction_errors[y_test == 0]
        fraud_errors = reconstruction_errors[y_test == 1]

        logger.info(
            f"[Autoencoder] Evaluation: Accuracy={accuracy:.4f}, "
            f"Precision={precision:.4f}, Recall={recall:.4f}, F1={f1_score:.4f}"
        )

        return {
            "model_type": "autoencoder",
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "true_positives": int(tp),
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "confusion_matrix": cm.tolist(),
            "threshold": self.threshold,
            "mean_normal_error": float(np.mean(normal_errors))
            if len(normal_errors) > 0
            else 0.0,
            "mean_fraud_error": float(np.mean(fraud_errors))
            if len(fraud_errors) > 0
            else 0.0,
        }

    def save(self, filepath: str) -> None:
        """
        모델 저장

        Args:
            filepath: 저장할 파일 경로 (.pt)
        """
        if not self.is_trained:
            raise ValueError("Model is not trained yet. Call train() first.")

        # 디렉토리 생성
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        # 모델 상태 저장
        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "scaler_mean": self.scaler.mean_,
                "scaler_scale": self.scaler.scale_,
                "threshold": self.threshold,
                "feature_names": self.feature_names,
                "latent_dim": self.latent_dim,
                "input_dim": len(self.feature_names),
            },
            filepath,
        )

        logger.info(f"[Autoencoder] Model saved to {filepath}")

    def load(self, filepath: str) -> None:
        """
        모델 로드

        Args:
            filepath: 로드할 파일 경로 (.pt)
        """
        checkpoint = torch.load(filepath, map_location=self.device)

        # 모델 재구성
        input_dim = checkpoint["input_dim"]
        self.latent_dim = checkpoint["latent_dim"]
        self.model = AutoencoderNetwork(input_dim, self.latent_dim).to(self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])

        # Scaler 재구성
        self.scaler.mean_ = checkpoint["scaler_mean"]
        self.scaler.scale_ = checkpoint["scaler_scale"]

        # 기타 메타데이터
        self.threshold = checkpoint["threshold"]
        self.feature_names = checkpoint["feature_names"]
        self.is_trained = True

        logger.info(f"[Autoencoder] Model loaded from {filepath}")


def train_autoencoder(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[AutoencoderFraudModel, Dict[str, Any]]:
    """
    Autoencoder 모델 학습 및 평가 (편의 함수)

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
    model = AutoencoderFraudModel(**(config or {}))

    # 학습
    train_metrics = model.train(X_train, y_train)

    # 평가
    eval_metrics = model.evaluate(X_test, y_test)

    # 결과 통합
    results = {"train_metrics": train_metrics, "eval_metrics": eval_metrics}

    return model, results
