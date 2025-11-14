"""
Feature Engineering

FDS 거래 데이터로부터 ML 모델 학습에 유용한 특성(Feature)을 생성
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class FeatureEngine:
    """
    Feature Engineering 엔진

    거래 데이터, 사용자 행동 로그, 위험 요인으로부터
    사기 탐지에 유용한 특성을 추출
    """

    def __init__(self):
        self.feature_columns: List[str] = []

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        모든 특성 생성 파이프라인

        Args:
            df: 원본 거래 데이터

        Returns:
            특성이 추가된 DataFrame
        """
        logger.info(f"Feature Engineering 시작: {len(df)}개 샘플")

        # 1. 기본 거래 특성
        df = self._create_transaction_features(df)

        # 2. 사용자 행동 특성
        df = self._create_user_behavior_features(df)

        # 3. 시간 기반 특성
        df = self._create_temporal_features(df)

        # 4. 위험 패턴 특성
        df = self._create_risk_pattern_features(df)

        # 5. 집계 특성 (사용자별, IP별)
        df = self._create_aggregated_features(df)

        logger.info(f"Feature Engineering 완료: {len(df.columns)}개 특성")

        return df

    def _create_transaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        기본 거래 특성

        - 거래 금액 로그 변환
        - 거래 금액 범위 (소액/중액/고액)
        """
        df = df.copy()

        # 거래 금액 로그 변환 (0 처리)
        df["amount_log"] = np.log1p(df["amount"])

        # 거래 금액 범위
        df["amount_range"] = pd.cut(
            df["amount"],
            bins=[0, 10000, 50000, 100000, float("inf")],
            labels=["소액", "중액", "고액", "초고액"],
        )

        # 소수점 자리수 (비정상적 금액 탐지)
        df["amount_decimal_places"] = (
            df["amount"].astype(str).str.split(".").str[1].str.len().fillna(0)
        )

        logger.debug("거래 특성 생성 완료")

        return df

    def _create_user_behavior_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        사용자 행동 특성

        - 사용자별 거래 횟수
        - 사용자별 평균 거래 금액
        - 평소 패턴 대비 이탈도
        """
        df = df.copy()

        # 사용자별 거래 횟수
        user_transaction_count = df.groupby("user_id").size()
        df["user_transaction_count"] = df["user_id"].map(user_transaction_count)

        # 사용자별 평균 거래 금액
        user_avg_amount = df.groupby("user_id")["amount"].mean()
        df["user_avg_amount"] = df["user_id"].map(user_avg_amount)

        # 현재 거래 금액이 평균 대비 몇 배인지
        df["amount_vs_avg_ratio"] = df["amount"] / (df["user_avg_amount"] + 1)

        # 사용자별 표준편차
        user_std_amount = df.groupby("user_id")["amount"].std().fillna(0)
        df["user_std_amount"] = df["user_id"].map(user_std_amount)

        # Z-score (평소 패턴 대비 이탈도)
        df["amount_z_score"] = (df["amount"] - df["user_avg_amount"]) / (
            df["user_std_amount"] + 1
        )

        logger.debug("사용자 행동 특성 생성 완료")

        return df

    def _create_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        시간 기반 특성

        - 시간대 (새벽/아침/낮/저녁/밤)
        - 비정상 시간대 거래 여부
        - 거래 간 시간 간격
        """
        df = df.copy()

        # created_at이 datetime 타입인지 확인
        if "created_at" in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df["created_at"]):
                df["created_at"] = pd.to_datetime(df["created_at"])

            # 시간대 분류
            df["hour_of_day"] = df["created_at"].dt.hour
            df["time_period"] = pd.cut(
                df["hour_of_day"],
                bins=[-1, 6, 12, 18, 24],
                labels=["새벽", "아침", "낮", "저녁"],
            )

            # 비정상 시간대 (새벽 2-6시)
            df["is_abnormal_time"] = (
                (df["hour_of_day"] >= 2) & (df["hour_of_day"] < 6)
            ).astype(int)

            # 요일
            df["day_of_week"] = df["created_at"].dt.dayofweek

            # 주말 여부
            df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

            # 사용자별 이전 거래 이후 경과 시간 (초)
            df = df.sort_values(["user_id", "created_at"])
            df["time_since_last_transaction"] = df.groupby("user_id")[
                "created_at"
            ].diff().dt.total_seconds().fillna(0)

        logger.debug("시간 특성 생성 완료")

        return df

    def _create_risk_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        위험 패턴 특성

        - IP 주소 변경 빈도
        - 디바이스 변경 빈도
        - 지역 불일치 패턴
        """
        df = df.copy()

        # IP 주소별 거래 횟수
        ip_transaction_count = df.groupby("ip_address").size()
        df["ip_transaction_count"] = df["ip_address"].map(ip_transaction_count)

        # 사용자별 고유 IP 개수
        user_unique_ips = df.groupby("user_id")["ip_address"].nunique()
        df["user_unique_ips"] = df["user_id"].map(user_unique_ips)

        # 사용자별 고유 디바이스 개수
        if "device_type" in df.columns:
            user_unique_devices = df.groupby("user_id")["device_type"].nunique()
            df["user_unique_devices"] = df["user_id"].map(user_unique_devices)

        # IP 주소가 여러 사용자에게 사용되는지 (공용 IP)
        ip_user_count = df.groupby("ip_address")["user_id"].nunique()
        df["ip_user_count"] = df["ip_address"].map(ip_user_count)
        df["is_shared_ip"] = (df["ip_user_count"] > 5).astype(int)

        logger.debug("위험 패턴 특성 생성 완료")

        return df

    def _create_aggregated_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        집계 특성

        - 최근 1시간/24시간/7일간 거래 횟수
        - 최근 거래 금액 총합
        - Velocity 체크 특성
        """
        df = df.copy()

        if "created_at" in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df["created_at"]):
                df["created_at"] = pd.to_datetime(df["created_at"])

            # 현재 시간 기준으로 정렬
            df = df.sort_values("created_at")

            # 최근 1시간 거래 횟수 (사용자별)
            df["transactions_last_1h"] = self._count_recent_transactions(
                df, "user_id", hours=1
            )

            # 최근 24시간 거래 횟수 (사용자별)
            df["transactions_last_24h"] = self._count_recent_transactions(
                df, "user_id", hours=24
            )

            # 최근 1시간 거래 금액 총합 (사용자별)
            df["amount_sum_last_1h"] = self._sum_recent_amounts(
                df, "user_id", hours=1
            )

            # 최근 1시간 거래 횟수 (IP별)
            df["ip_transactions_last_1h"] = self._count_recent_transactions(
                df, "ip_address", hours=1
            )

        logger.debug("집계 특성 생성 완료")

        return df

    def _count_recent_transactions(
        self, df: pd.DataFrame, group_col: str, hours: int
    ) -> pd.Series:
        """
        최근 N시간 내 거래 횟수 계산

        Args:
            df: 데이터프레임
            group_col: 그룹화 컬럼 (user_id, ip_address 등)
            hours: 시간 범위

        Returns:
            거래 횟수 Series
        """
        df = df.sort_values(["created_at"])
        counts = []

        for idx, row in df.iterrows():
            current_time = row["created_at"]
            time_window_start = current_time - timedelta(hours=hours)

            # 동일 그룹 + 시간 범위 내 거래 필터링
            mask = (
                (df[group_col] == row[group_col])
                & (df["created_at"] >= time_window_start)
                & (df["created_at"] < current_time)
            )

            count = df[mask].shape[0]
            counts.append(count)

        return pd.Series(counts, index=df.index)

    def _sum_recent_amounts(
        self, df: pd.DataFrame, group_col: str, hours: int
    ) -> pd.Series:
        """
        최근 N시간 내 거래 금액 총합 계산

        Args:
            df: 데이터프레임
            group_col: 그룹화 컬럼
            hours: 시간 범위

        Returns:
            거래 금액 총합 Series
        """
        df = df.sort_values(["created_at"])
        amounts = []

        for idx, row in df.iterrows():
            current_time = row["created_at"]
            time_window_start = current_time - timedelta(hours=hours)

            # 동일 그룹 + 시간 범위 내 거래 필터링
            mask = (
                (df[group_col] == row[group_col])
                & (df["created_at"] >= time_window_start)
                & (df["created_at"] < current_time)
            )

            total_amount = df[mask]["amount"].sum()
            amounts.append(total_amount)

        return pd.Series(amounts, index=df.index)


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Feature Engineering 메인 함수

    Args:
        df: 원본 거래 데이터

    Returns:
        특성이 추가된 DataFrame
    """
    engine = FeatureEngine()
    return engine.create_features(df)


def get_feature_importance_names() -> List[str]:
    """
    생성된 특성 이름 목록 반환

    Returns:
        특성 이름 리스트
    """
    return [
        # 거래 특성
        "amount",
        "amount_log",
        "amount_range",
        "amount_decimal_places",
        # 사용자 행동 특성
        "user_transaction_count",
        "user_avg_amount",
        "amount_vs_avg_ratio",
        "user_std_amount",
        "amount_z_score",
        # 시간 특성
        "hour_of_day",
        "time_period",
        "is_abnormal_time",
        "day_of_week",
        "is_weekend",
        "time_since_last_transaction",
        # 위험 패턴 특성
        "ip_transaction_count",
        "user_unique_ips",
        "user_unique_devices",
        "ip_user_count",
        "is_shared_ip",
        # 집계 특성
        "transactions_last_1h",
        "transactions_last_24h",
        "amount_sum_last_1h",
        "ip_transactions_last_1h",
    ]


if __name__ == "__main__":
    # 테스트 코드 예시
    logging.basicConfig(level=logging.INFO)

    # 샘플 데이터 생성
    sample_data = pd.DataFrame({
        "user_id": ["user1", "user1", "user2", "user1", "user3"],
        "amount": [100, 200, 50000, 150, 300],
        "ip_address": ["192.168.1.1", "192.168.1.1", "10.0.0.1", "192.168.1.2", "10.0.0.1"],
        "device_type": ["mobile", "desktop", "mobile", "mobile", "desktop"],
        "created_at": pd.to_datetime([
            "2025-01-01 10:00:00",
            "2025-01-01 10:30:00",
            "2025-01-01 02:00:00",
            "2025-01-01 14:00:00",
            "2025-01-01 20:15:00",
        ]),
    })

    # Feature Engineering
    df_with_features = create_features(sample_data)

    print("\nFeature Engineering 결과:")
    print(df_with_features.columns.tolist())
    print("\n샘플 데이터:")
    print(df_with_features.head())
