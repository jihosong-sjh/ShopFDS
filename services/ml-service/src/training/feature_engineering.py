"""
Feature Engineering for Fraud Detection

사기 탐지를 위한 고급 특징 생성 파이프라인입니다.
Raw 거래 데이터에서 ML 모델 학습에 필요한 다양한 특징을 추출합니다.

주요 특징 카테고리:
1. 거래 특징: 금액, 시간대, 결제 수단
2. 사용자 행동 특징: 거래 빈도, 평균 금액, 속도
3. 네트워크 특징: IP, GeoIP, Device 패턴
4. 시계열 특징: 시간대별 패턴, 이상치
5. 집계 특징: 윈도우별 통계 (1시간, 24시간, 7일)
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler, LabelEncoder


logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    사기 탐지 특징 생성 파이프라인

    입력: Raw 거래 데이터
    출력: ML 모델용 특징 DataFrame
    """

    def __init__(self):
        """초기화"""
        self.scalers: Dict[str, StandardScaler] = {}
        self.encoders: Dict[str, LabelEncoder] = {}
        self.feature_names: List[str] = []
        self.is_fitted = False

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        특징 생성 및 변환 (학습 데이터용)

        Args:
            df: 거래 데이터 DataFrame

        Returns:
            특징 DataFrame
        """
        logger.info(
            f"[FeatureEngineer] Fitting and transforming {len(df)} transactions"
        )

        # 1. 기본 특징 추출
        df_features = self._extract_basic_features(df)

        # 2. 시간 특징 추출
        df_features = self._extract_time_features(df_features)

        # 3. 사용자 행동 특징 추출
        df_features = self._extract_user_behavior_features(df_features)

        # 4. 네트워크 특징 추출
        df_features = self._extract_network_features(df_features)

        # 5. 집계 특징 추출
        df_features = self._extract_aggregation_features(df_features)

        # 6. 범주형 특징 인코딩
        df_features = self._encode_categorical_features(df_features, fit=True)

        # 7. 수치형 특징 스케일링
        df_features = self._scale_numeric_features(df_features, fit=True)

        self.feature_names = df_features.columns.tolist()
        self.is_fitted = True

        logger.info(f"[FeatureEngineer] Generated {len(self.feature_names)} features")

        return df_features

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        특징 변환 (테스트 데이터용)

        Args:
            df: 거래 데이터 DataFrame

        Returns:
            특징 DataFrame
        """
        if not self.is_fitted:
            raise ValueError(
                "FeatureEngineer is not fitted. Call fit_transform() first."
            )

        logger.info(f"[FeatureEngineer] Transforming {len(df)} transactions")

        # 동일한 파이프라인 적용 (fit=False)
        df_features = self._extract_basic_features(df)
        df_features = self._extract_time_features(df_features)
        df_features = self._extract_user_behavior_features(df_features)
        df_features = self._extract_network_features(df_features)
        df_features = self._extract_aggregation_features(df_features)
        df_features = self._encode_categorical_features(df_features, fit=False)
        df_features = self._scale_numeric_features(df_features, fit=False)

        # 학습 시와 동일한 특징만 선택
        df_features = df_features[self.feature_names]

        return df_features

    def _extract_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        기본 거래 특징 추출

        - 거래 금액 (amount)
        - 거래 금액 로그 변환 (amount_log)
        - 결제 수단 (payment_method)
        - 배송지 국가 (shipping_country)
        - 결제 카드 발급국 (card_country)
        """
        df_copy = df.copy()

        # 금액 로그 변환 (0 방지)
        df_copy["amount_log"] = np.log1p(df_copy.get("amount", 0))

        # 결제 수단 (credit_card, debit_card, paypal 등)
        if "payment_method" not in df_copy.columns:
            df_copy["payment_method"] = "unknown"

        # 국가 정보
        if "shipping_country" not in df_copy.columns:
            df_copy["shipping_country"] = "unknown"

        if "card_country" not in df_copy.columns:
            df_copy["card_country"] = "unknown"

        # 국가 불일치 여부
        df_copy["country_mismatch"] = (
            df_copy["shipping_country"] != df_copy["card_country"]
        ).astype(int)

        return df_copy

    def _extract_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        시간 특징 추출

        - 시간대 (hour_of_day: 0-23)
        - 요일 (day_of_week: 0-6)
        - 주말 여부 (is_weekend)
        - 심야 시간대 여부 (is_late_night: 0-6시)
        """
        df_copy = df.copy()

        # created_at을 datetime으로 변환
        if "created_at" in df_copy.columns:
            df_copy["created_at"] = pd.to_datetime(df_copy["created_at"])
        else:
            # 현재 시간 사용 (fallback)
            df_copy["created_at"] = pd.Timestamp.now()

        # 시간 특징
        df_copy["hour_of_day"] = df_copy["created_at"].dt.hour
        df_copy["day_of_week"] = df_copy["created_at"].dt.dayofweek  # 0=월요일
        df_copy["day_of_month"] = df_copy["created_at"].dt.day
        df_copy["month"] = df_copy["created_at"].dt.month

        # 주말 여부 (5=토요일, 6=일요일)
        df_copy["is_weekend"] = (df_copy["day_of_week"] >= 5).astype(int)

        # 심야 시간대 (0-6시)
        df_copy["is_late_night"] = (
            (df_copy["hour_of_day"] >= 0) & (df_copy["hour_of_day"] < 6)
        ).astype(int)

        # 피크 시간대 (18-22시)
        df_copy["is_peak_hour"] = (
            (df_copy["hour_of_day"] >= 18) & (df_copy["hour_of_day"] < 22)
        ).astype(int)

        return df_copy

    def _extract_user_behavior_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        사용자 행동 특징 추출

        - 사용자별 거래 빈도
        - 사용자별 평균 거래 금액
        - 사용자별 표준편차 (변동성)
        - 사용자별 최대/최소 금액
        """
        df_copy = df.copy()

        if "user_id" not in df_copy.columns:
            logger.warning(
                "[FeatureEngineer] user_id not found. Skipping user behavior features."
            )
            return df_copy

        # 사용자별 집계
        user_stats = (
            df_copy.groupby("user_id")["amount"]
            .agg(
                [
                    ("user_tx_count", "count"),
                    ("user_avg_amount", "mean"),
                    ("user_std_amount", "std"),
                    ("user_max_amount", "max"),
                    ("user_min_amount", "min"),
                ]
            )
            .reset_index()
        )

        # NaN 처리 (표준편차가 없는 경우)
        user_stats["user_std_amount"].fillna(0, inplace=True)

        # 원본 데이터에 병합
        df_copy = df_copy.merge(user_stats, on="user_id", how="left")

        # 현재 거래 금액과 평균 간 차이
        df_copy["amount_deviation_from_user_avg"] = (
            df_copy["amount"] - df_copy["user_avg_amount"]
        ) / (df_copy["user_std_amount"] + 1e-6)

        return df_copy

    def _extract_network_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        네트워크 특징 추출

        - IP 주소 특징
        - Device ID 특징
        - Browser/OS 특징
        """
        df_copy = df.copy()

        # IP 주소 특징 (예: 10.0.0.1 -> 10)
        if "ip_address" in df_copy.columns:
            df_copy["ip_first_octet"] = df_copy["ip_address"].apply(
                lambda x: int(x.split(".")[0]) if isinstance(x, str) and "." in x else 0
            )
        else:
            df_copy["ip_first_octet"] = 0

        # Device ID 빈도
        if "device_id" in df_copy.columns:
            device_counts = df_copy["device_id"].value_counts().to_dict()
            df_copy["device_frequency"] = df_copy["device_id"].map(device_counts)
        else:
            df_copy["device_frequency"] = 1

        # Browser/OS (범주형 → 인코딩 단계에서 처리)
        if "browser" not in df_copy.columns:
            df_copy["browser"] = "unknown"

        if "os" not in df_copy.columns:
            df_copy["os"] = "unknown"

        return df_copy

    def _extract_aggregation_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        시간 윈도우별 집계 특징 추출

        - 1시간 내 거래 수/총액
        - 24시간 내 거래 수/총액
        - 7일 내 거래 수/총액
        """
        df_copy = df.copy()

        if "user_id" not in df_copy.columns or "created_at" not in df_copy.columns:
            logger.warning(
                "[FeatureEngineer] user_id or created_at not found. Skipping aggregation features."
            )
            return df_copy

        # 시간 정렬
        df_copy = df_copy.sort_values("created_at")

        # 윈도우별 집계 (rolling 사용)
        for window_hours in [1, 24, 168]:  # 1시간, 24시간, 7일
            window_name = f"{window_hours}h"

            # 사용자별 윈도우 집계
            df_copy[f"tx_count_{window_name}"] = (
                df_copy.groupby("user_id")["amount"]
                .transform(
                    lambda x: x.rolling(
                        window=f"{window_hours}H", closed="left"
                    ).count()
                )
                .fillna(0)
            )

            df_copy[f"tx_sum_{window_name}"] = (
                df_copy.groupby("user_id")["amount"]
                .transform(
                    lambda x: x.rolling(window=f"{window_hours}H", closed="left").sum()
                )
                .fillna(0)
            )

        # 거래 속도 (시간당 거래 수)
        df_copy["tx_velocity_1h"] = df_copy["tx_count_1h"]
        df_copy["tx_velocity_24h"] = df_copy["tx_count_24h"] / 24.0

        return df_copy

    def _encode_categorical_features(
        self, df: pd.DataFrame, fit: bool = False
    ) -> pd.DataFrame:
        """
        범주형 특징 인코딩 (Label Encoding)

        Args:
            df: 특징 DataFrame
            fit: 인코더를 새로 학습할지 여부

        Returns:
            인코딩된 DataFrame
        """
        df_copy = df.copy()

        categorical_cols = [
            "payment_method",
            "shipping_country",
            "card_country",
            "browser",
            "os",
        ]

        for col in categorical_cols:
            if col not in df_copy.columns:
                continue

            if fit:
                # 인코더 학습
                self.encoders[col] = LabelEncoder()
                df_copy[col] = self.encoders[col].fit_transform(
                    df_copy[col].astype(str)
                )
            else:
                # 기존 인코더 사용 (unknown 값 처리)
                if col in self.encoders:
                    known_labels = set(self.encoders[col].classes_)
                    df_copy[col] = (
                        df_copy[col]
                        .astype(str)
                        .apply(lambda x: x if x in known_labels else "unknown")
                    )
                    df_copy[col] = self.encoders[col].transform(df_copy[col])
                else:
                    df_copy[col] = 0  # fallback

        return df_copy

    def _scale_numeric_features(
        self, df: pd.DataFrame, fit: bool = False
    ) -> pd.DataFrame:
        """
        수치형 특징 스케일링 (StandardScaler)

        Args:
            df: 특징 DataFrame
            fit: 스케일러를 새로 학습할지 여부

        Returns:
            스케일링된 DataFrame
        """
        df_copy = df.copy()

        # 스케일링 제외 열 (이미 정규화된 특징)
        exclude_cols = [
            "user_id",
            "device_id",
            "created_at",
            "is_weekend",
            "is_late_night",
            "is_peak_hour",
            "country_mismatch",
        ]

        # 수치형 열 선택
        numeric_cols = df_copy.select_dtypes(include=[np.number]).columns.tolist()
        numeric_cols = [col for col in numeric_cols if col not in exclude_cols]

        if fit:
            # 스케일러 학습
            self.scalers["numeric"] = StandardScaler()
            df_copy[numeric_cols] = self.scalers["numeric"].fit_transform(
                df_copy[numeric_cols]
            )
        else:
            # 기존 스케일러 사용
            if "numeric" in self.scalers:
                df_copy[numeric_cols] = self.scalers["numeric"].transform(
                    df_copy[numeric_cols]
                )

        return df_copy

    def get_feature_names(self) -> List[str]:
        """생성된 특징 이름 목록 반환"""
        return self.feature_names


def engineer_features(
    train_df: pd.DataFrame, test_df: Optional[pd.DataFrame] = None
) -> tuple:
    """
    특징 생성 (편의 함수)

    Args:
        train_df: 학습 거래 데이터
        test_df: 테스트 거래 데이터 (옵션)

    Returns:
        (train_features, test_features, engineer) 또는 (train_features, None, engineer)

    Example:
        >>> train_df = load_transactions(start_date="2024-01-01", end_date="2024-10-01")
        >>> test_df = load_transactions(start_date="2024-10-01", end_date="2024-11-01")
        >>> X_train, X_test, engineer = engineer_features(train_df, test_df)
        >>> print(f"Generated {len(engineer.get_feature_names())} features")
    """
    engineer = FeatureEngineer()

    # 학습 데이터 변환
    train_features = engineer.fit_transform(train_df)

    # 테스트 데이터 변환 (옵션)
    test_features = None
    if test_df is not None:
        test_features = engineer.transform(test_df)

    return train_features, test_features, engineer
