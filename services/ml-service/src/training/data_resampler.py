"""
Data Resampling for Imbalanced Fraud Dataset

SMOTE (Synthetic Minority Over-sampling Technique)를 사용하여 사기 거래 데이터를 증강합니다.
사기 비율이 5%인 데이터를 40%로 증강하여 모델 학습 성능을 향상시킵니다.

주요 기능:
- SMOTE: 소수 클래스(사기) 합성 샘플 생성
- Random Undersampling: 다수 클래스(정상) 축소
- Combination: SMOTE + Undersampling 조합
"""

import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE, ADASYN
from imblearn.under_sampling import RandomUnderSampler
from imblearn.combine import SMOTETomek, SMOTEENN
from collections import Counter


logger = logging.getLogger(__name__)


class DataResampler:
    """
    불균형 데이터 리샘플링 클래스

    전략:
    1. SMOTE: 소수 클래스 오버샘플링 (사기 거래 합성 생성)
    2. Random Undersampling: 다수 클래스 언더샘플링 (정상 거래 축소)
    3. Combination: SMOTE + Tomek Links (노이즈 제거)
    """

    def __init__(
        self,
        strategy: str = "smote",
        target_ratio: float = 0.4,
        random_state: int = 42,
        k_neighbors: int = 5,
    ):
        """
        Args:
            strategy: 리샘플링 전략 (smote, undersample, combine, adasyn)
            target_ratio: 목표 사기 비율 (0.4 = 40%)
            random_state: 재현성을 위한 시드
            k_neighbors: SMOTE k-최근접 이웃 수
        """
        self.strategy = strategy
        self.target_ratio = target_ratio
        self.random_state = random_state
        self.k_neighbors = k_neighbors
        self.resampler = None

    def fit_resample(
        self, X: pd.DataFrame, y: pd.Series
    ) -> Tuple[pd.DataFrame, pd.Series, Dict[str, Any]]:
        """
        데이터 리샘플링 수행

        Args:
            X: 특징 데이터
            y: 레이블 (0: 정상, 1: 사기)

        Returns:
            (X_resampled, y_resampled, statistics)
        """
        # 원본 데이터 통계
        original_counts = Counter(y)
        original_fraud_ratio = original_counts[1] / len(y)

        logger.info(
            f"[DataResampler] Original data: {len(y)} samples, "
            f"Fraud ratio: {original_fraud_ratio:.2%} "
            f"(Normal: {original_counts[0]}, Fraud: {original_counts[1]})"
        )

        # 리샘플러 선택
        if self.strategy == "smote":
            self.resampler = SMOTE(
                sampling_strategy=self.target_ratio,
                random_state=self.random_state,
                k_neighbors=self.k_neighbors,
            )
        elif self.strategy == "adasyn":
            self.resampler = ADASYN(
                sampling_strategy=self.target_ratio,
                random_state=self.random_state,
                n_neighbors=self.k_neighbors,
            )
        elif self.strategy == "undersample":
            # 언더샘플링으로 목표 비율 달성
            self.resampler = RandomUnderSampler(
                sampling_strategy=1.0 / self.target_ratio - 1.0,  # 역수 관계
                random_state=self.random_state,
            )
        elif self.strategy == "combine":
            # SMOTE + Tomek Links (노이즈 제거)
            self.resampler = SMOTETomek(
                sampling_strategy=self.target_ratio,
                random_state=self.random_state,
                smote=SMOTE(
                    sampling_strategy=self.target_ratio,
                    random_state=self.random_state,
                    k_neighbors=self.k_neighbors,
                ),
            )
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

        # 리샘플링 수행
        X_resampled, y_resampled = self.resampler.fit_resample(X, y)

        # 리샘플링 후 통계
        resampled_counts = Counter(y_resampled)
        resampled_fraud_ratio = resampled_counts[1] / len(y_resampled)

        logger.info(
            f"[DataResampler] Resampled data: {len(y_resampled)} samples, "
            f"Fraud ratio: {resampled_fraud_ratio:.2%} "
            f"(Normal: {resampled_counts[0]}, Fraud: {resampled_counts[1]})"
        )

        # DataFrame 재구성 (Feature 이름 유지)
        X_resampled_df = pd.DataFrame(X_resampled, columns=X.columns)
        y_resampled_series = pd.Series(y_resampled, name=y.name)

        statistics = {
            "strategy": self.strategy,
            "target_ratio": self.target_ratio,
            "original_samples": len(y),
            "resampled_samples": len(y_resampled),
            "original_fraud_count": int(original_counts[1]),
            "resampled_fraud_count": int(resampled_counts[1]),
            "original_fraud_ratio": float(original_fraud_ratio),
            "resampled_fraud_ratio": float(resampled_fraud_ratio),
            "fraud_samples_added": int(resampled_counts[1] - original_counts[1]),
            "normal_samples_removed": int(original_counts[0] - resampled_counts[0]),
        }

        return X_resampled_df, y_resampled_series, statistics


def resample_fraud_data(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    strategy: str = "smote",
    target_ratio: float = 0.4,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.Series, Dict[str, Any]]:
    """
    사기 탐지 데이터 리샘플링 (편의 함수)

    Args:
        X_train: 학습 특징 데이터
        y_train: 학습 레이블
        strategy: 리샘플링 전략 (smote, undersample, combine, adasyn)
        target_ratio: 목표 사기 비율 (0.4 = 40%)
        random_state: 재현성을 위한 시드

    Returns:
        (X_resampled, y_resampled, statistics)

    Example:
        >>> X_train, y_train = load_training_data()
        >>> X_resampled, y_resampled, stats = resample_fraud_data(
        ...     X_train, y_train, strategy="smote", target_ratio=0.4
        ... )
        >>> print(f"Original fraud ratio: {stats['original_fraud_ratio']:.2%}")
        >>> print(f"Resampled fraud ratio: {stats['resampled_fraud_ratio']:.2%}")
    """
    resampler = DataResampler(
        strategy=strategy, target_ratio=target_ratio, random_state=random_state
    )

    return resampler.fit_resample(X_train, y_train)


class StratifiedResampler:
    """
    계층적 리샘플링 (사용자별/시간대별)

    사용자별로 독립적으로 리샘플링하여 데이터 누수 방지
    """

    def __init__(self, stratify_column: str, base_resampler: DataResampler):
        """
        Args:
            stratify_column: 계층화 기준 열 (예: user_id, time_bucket)
            base_resampler: 기본 리샘플러
        """
        self.stratify_column = stratify_column
        self.base_resampler = base_resampler

    def fit_resample(
        self, X: pd.DataFrame, y: pd.Series
    ) -> Tuple[pd.DataFrame, pd.Series, Dict[str, Any]]:
        """
        계층별로 리샘플링 수행

        Args:
            X: 특징 데이터 (stratify_column 포함)
            y: 레이블

        Returns:
            (X_resampled, y_resampled, statistics)
        """
        if self.stratify_column not in X.columns:
            raise ValueError(f"Stratify column {self.stratify_column} not found in X")

        logger.info(f"[StratifiedResampler] Stratifying by {self.stratify_column}")

        X_resampled_list = []
        y_resampled_list = []
        strata_stats = []

        # 계층별 리샘플링
        for stratum_value in X[self.stratify_column].unique():
            stratum_mask = X[self.stratify_column] == stratum_value
            X_stratum = X[stratum_mask].drop(columns=[self.stratify_column])
            y_stratum = y[stratum_mask]

            # 사기 거래가 충분히 있는 계층만 리샘플링
            fraud_count = (y_stratum == 1).sum()
            if fraud_count >= self.base_resampler.k_neighbors:
                try:
                    X_res, y_res, stats = self.base_resampler.fit_resample(
                        X_stratum, y_stratum
                    )
                    # Stratify column 복원
                    X_res[self.stratify_column] = stratum_value
                    X_resampled_list.append(X_res)
                    y_resampled_list.append(y_res)
                    strata_stats.append(stats)
                except Exception as e:
                    logger.warning(
                        f"[StratifiedResampler] Failed to resample stratum "
                        f"{stratum_value}: {e}. Using original data."
                    )
                    X_stratum[self.stratify_column] = stratum_value
                    X_resampled_list.append(X_stratum)
                    y_resampled_list.append(y_stratum)
            else:
                # 사기 거래가 부족하면 원본 데이터 유지
                logger.info(
                    f"[StratifiedResampler] Skipping stratum {stratum_value} "
                    f"(fraud count: {fraud_count} < {self.base_resampler.k_neighbors})"
                )
                X_stratum[self.stratify_column] = stratum_value
                X_resampled_list.append(X_stratum)
                y_resampled_list.append(y_stratum)

        # 결과 통합
        X_resampled = pd.concat(X_resampled_list, ignore_index=True)
        y_resampled = pd.concat(y_resampled_list, ignore_index=True)

        # 전체 통계
        overall_stats = {
            "stratify_column": self.stratify_column,
            "n_strata": len(strata_stats),
            "total_samples": len(y_resampled),
            "total_fraud_count": int((y_resampled == 1).sum()),
            "overall_fraud_ratio": float((y_resampled == 1).mean()),
            "strata_details": strata_stats,
        }

        logger.info(
            f"[StratifiedResampler] Completed: {len(y_resampled)} samples, "
            f"Fraud ratio: {overall_stats['overall_fraud_ratio']:.2%}"
        )

        return X_resampled, y_resampled, overall_stats


def resample_with_validation(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: Optional[pd.DataFrame] = None,
    y_val: Optional[pd.Series] = None,
    strategy: str = "smote",
    target_ratio: float = 0.4,
    random_state: int = 42,
) -> Tuple[
    pd.DataFrame, pd.Series, Optional[pd.DataFrame], Optional[pd.Series], Dict[str, Any]
]:
    """
    검증 데이터는 그대로 두고 학습 데이터만 리샘플링

    Args:
        X_train: 학습 특징 데이터
        y_train: 학습 레이블
        X_val: 검증 특징 데이터 (옵션)
        y_val: 검증 레이블 (옵션)
        strategy: 리샘플링 전략
        target_ratio: 목표 사기 비율
        random_state: 시드

    Returns:
        (X_train_res, y_train_res, X_val, y_val, statistics)
    """
    # 학습 데이터만 리샘플링
    X_train_resampled, y_train_resampled, stats = resample_fraud_data(
        X_train, y_train, strategy, target_ratio, random_state
    )

    # 검증 데이터 통계 추가
    if X_val is not None and y_val is not None:
        val_fraud_count = (y_val == 1).sum()
        val_fraud_ratio = val_fraud_count / len(y_val)

        stats["validation_samples"] = len(y_val)
        stats["validation_fraud_count"] = int(val_fraud_count)
        stats["validation_fraud_ratio"] = float(val_fraud_ratio)

        logger.info(
            f"[DataResampler] Validation data: {len(y_val)} samples, "
            f"Fraud ratio: {val_fraud_ratio:.2%}"
        )

    return X_train_resampled, y_train_resampled, X_val, y_val, stats
