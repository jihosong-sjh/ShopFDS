"""
LSTM Model for Fraud Detection (Time Series Pattern Analysis)

LSTM은 시계열 패턴을 분석하는 순환 신경망으로, 다음과 같은 특징을 가집니다:
- 사용자의 거래 시퀀스에서 패턴 학습
- 급격한 행동 변화 탐지 (계정 탈취 징후)
- 시간적 의존성 고려
- PyTorch 기반 딥러닝 모델

모델 가중치: 10% (앙상블 내)
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


class LSTMNetwork(nn.Module):
    """
    LSTM 신경망 구조

    LSTM Layers: 2층 (hidden_size=64, dropout=0.3)
    FC Layers: 32 -> 1 (Sigmoid 출력)
    """

    def __init__(
        self,
        input_size: int,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.3,
    ):
        """
        Args:
            input_size: 입력 특징 차원
            hidden_size: LSTM 은닉 상태 크기
            num_layers: LSTM 레이어 수
            dropout: 드롭아웃 비율
        """
        super(LSTMNetwork, self).__init__()

        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # LSTM 레이어
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        # Fully Connected 레이어
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        """
        순전파

        Args:
            x: (batch_size, seq_len, input_size)

        Returns:
            (batch_size, 1) 사기 확률
        """
        # LSTM 출력: (batch_size, seq_len, hidden_size)
        lstm_out, (hn, cn) = self.lstm(x)

        # 마지막 시간 스텝의 은닉 상태 사용
        last_hidden = lstm_out[:, -1, :]

        # FC 레이어
        output = self.fc(last_hidden)

        return output


class LSTMFraudModel:
    """
    LSTM 기반 사기 탐지 모델

    사용자의 최근 거래 시퀀스를 분석하여 사기 여부 판단
    """

    def __init__(
        self,
        sequence_length: int = 10,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.3,
        learning_rate: float = 0.001,
        batch_size: int = 128,
        epochs: int = 30,
        device: str = "auto",
        random_state: int = 42,
    ):
        """
        Args:
            sequence_length: 시퀀스 길이 (과거 거래 수)
            hidden_size: LSTM 은닉 상태 크기
            num_layers: LSTM 레이어 수
            dropout: 드롭아웃 비율
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

        logger.info(f"[LSTM] Using device: {self.device}")

        self.sequence_length = sequence_length
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        self.random_state = random_state

        # 모델 및 상태
        self.model: Optional[LSTMNetwork] = None
        self.scaler = StandardScaler()
        self.feature_names: Optional[list] = None
        self.is_trained = False

        # 시드 고정
        torch.manual_seed(random_state)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(random_state)

    def _create_sequences(
        self, X: np.ndarray, y: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        시퀀스 데이터 생성

        Args:
            X: 특징 데이터 (n_samples, n_features)
            y: 레이블 (n_samples,)

        Returns:
            (X_seq, y_seq) 시퀀스 데이터
        """
        X_seq = []
        y_seq = [] if y is not None else None

        for i in range(len(X) - self.sequence_length + 1):
            X_seq.append(X[i : i + self.sequence_length])
            if y is not None:
                # 시퀀스의 마지막 레이블 사용
                y_seq.append(y[i + self.sequence_length - 1])

        X_seq = np.array(X_seq)
        y_seq = np.array(y_seq) if y is not None else None

        return X_seq, y_seq

    def train(self, X_train: pd.DataFrame, y_train: pd.Series) -> Dict[str, Any]:
        """
        LSTM 모델 학습

        Args:
            X_train: 학습 특징 데이터
            y_train: 학습 레이블 (0: 정상, 1: 사기)

        Returns:
            학습 결과 메트릭
        """
        logger.info(
            f"[LSTM] Training started: {len(X_train)} samples, "
            f"{X_train.shape[1]} features, seq_len={self.sequence_length}"
        )

        # Feature 이름 저장
        self.feature_names = X_train.columns.tolist()

        # 데이터 정규화
        X_train_scaled = self.scaler.fit_transform(X_train)
        y_train_np = y_train.values

        # 시퀀스 생성
        X_seq, y_seq = self._create_sequences(X_train_scaled, y_train_np)
        logger.info(f"[LSTM] Created {len(X_seq)} sequences")

        # PyTorch Tensor 변환
        X_tensor = torch.FloatTensor(X_seq).to(self.device)
        y_tensor = torch.FloatTensor(y_seq).unsqueeze(1).to(self.device)

        dataset = TensorDataset(X_tensor, y_tensor)
        dataloader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)

        # 모델 초기화
        input_size = X_train.shape[1]
        self.model = LSTMNetwork(
            input_size=input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            dropout=self.dropout,
        ).to(self.device)

        # 옵티마이저 및 손실 함수
        optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)
        criterion = nn.BCELoss()

        # 클래스 불균형 대응 가중치
        pos_weight = (y_seq == 0).sum() / (y_seq == 1).sum()
        criterion_weighted = nn.BCEWithLogitsLoss(
            pos_weight=torch.tensor([pos_weight]).to(self.device)
        )

        # 학습 루프
        self.model.train()
        train_losses = []
        train_accuracies = []

        for epoch in range(self.epochs):
            epoch_loss = 0.0
            correct = 0
            total = 0

            for batch_X, batch_y in dataloader:
                # Forward pass
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)

                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                # 메트릭 계산
                epoch_loss += loss.item()
                predictions = (outputs >= 0.5).float()
                correct += (predictions == batch_y).sum().item()
                total += batch_y.size(0)

            avg_loss = epoch_loss / len(dataloader)
            accuracy = correct / total

            train_losses.append(avg_loss)
            train_accuracies.append(accuracy)

            if (epoch + 1) % 5 == 0:
                logger.info(
                    f"[LSTM] Epoch {epoch + 1}/{self.epochs}, "
                    f"Loss: {avg_loss:.4f}, Accuracy: {accuracy:.4f}"
                )

        self.is_trained = True

        logger.info(
            f"[LSTM] Training completed: Final loss={train_losses[-1]:.4f}, "
            f"Accuracy={train_accuracies[-1]:.4f}"
        )

        return {
            "model_type": "lstm",
            "sequence_length": self.sequence_length,
            "hidden_size": self.hidden_size,
            "num_layers": self.num_layers,
            "epochs": self.epochs,
            "final_loss": train_losses[-1],
            "final_accuracy": train_accuracies[-1],
            "n_features": len(self.feature_names),
            "n_sequences": len(X_seq),
            "train_losses": train_losses,
            "train_accuracies": train_accuracies,
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

        probabilities = self.predict_proba(X)
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

        self.model.eval()

        # 데이터 정규화
        X_scaled = self.scaler.transform(X)

        # 시퀀스 생성
        X_seq, _ = self._create_sequences(X_scaled, None)

        # PyTorch Tensor 변환
        X_tensor = torch.FloatTensor(X_seq).to(self.device)

        # 예측
        with torch.no_grad():
            outputs = self.model(X_tensor)
            probabilities = outputs.cpu().numpy().flatten()

        return probabilities

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

        # 데이터 정규화
        X_test_scaled = self.scaler.transform(X_test)
        y_test_np = y_test.values

        # 시퀀스 생성
        X_seq, y_seq = self._create_sequences(X_test_scaled, y_test_np)

        # 예측
        X_tensor = torch.FloatTensor(X_seq).to(self.device)

        self.model.eval()
        with torch.no_grad():
            outputs = self.model(X_tensor)
            probabilities = outputs.cpu().numpy().flatten()
            predictions = (probabilities >= 0.5).astype(int)

        # Confusion Matrix
        cm = confusion_matrix(y_seq, predictions)
        tn, fp, fn, tp = cm.ravel()

        # 메트릭 계산
        accuracy = float(np.mean(predictions == y_seq))
        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1_score = (
            float(2 * precision * recall / (precision + recall))
            if (precision + recall) > 0
            else 0.0
        )

        logger.info(
            f"[LSTM] Evaluation: Accuracy={accuracy:.4f}, "
            f"Precision={precision:.4f}, Recall={recall:.4f}, F1={f1_score:.4f}"
        )

        return {
            "model_type": "lstm",
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "true_positives": int(tp),
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "confusion_matrix": cm.tolist(),
            "n_sequences": len(X_seq),
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
                "feature_names": self.feature_names,
                "sequence_length": self.sequence_length,
                "hidden_size": self.hidden_size,
                "num_layers": self.num_layers,
                "dropout": self.dropout,
                "input_size": len(self.feature_names),
            },
            filepath,
        )

        logger.info(f"[LSTM] Model saved to {filepath}")

    def load(self, filepath: str) -> None:
        """
        모델 로드

        Args:
            filepath: 로드할 파일 경로 (.pt)
        """
        checkpoint = torch.load(filepath, map_location=self.device)

        # 모델 재구성
        input_size = checkpoint["input_size"]
        self.sequence_length = checkpoint["sequence_length"]
        self.hidden_size = checkpoint["hidden_size"]
        self.num_layers = checkpoint["num_layers"]
        self.dropout = checkpoint["dropout"]

        self.model = LSTMNetwork(
            input_size=input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            dropout=self.dropout,
        ).to(self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])

        # Scaler 재구성
        self.scaler.mean_ = checkpoint["scaler_mean"]
        self.scaler.scale_ = checkpoint["scaler_scale"]

        # 기타 메타데이터
        self.feature_names = checkpoint["feature_names"]
        self.is_trained = True

        logger.info(f"[LSTM] Model loaded from {filepath}")


def train_lstm(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[LSTMFraudModel, Dict[str, Any]]:
    """
    LSTM 모델 학습 및 평가 (편의 함수)

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
    model = LSTMFraudModel(**(config or {}))

    # 학습
    train_metrics = model.train(X_train, y_train)

    # 평가
    eval_metrics = model.evaluate(X_test, y_test)

    # 결과 통합
    results = {"train_metrics": train_metrics, "eval_metrics": eval_metrics}

    return model, results
