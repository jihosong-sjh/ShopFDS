"""
데이터 전처리 파이프라인

FDS 거래 데이터를 ML 모델 학습에 적합한 형태로 변환
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    학습 데이터 전처리 파이프라인

    거래 데이터, 사용자 행동 로그, 위험 요인을 결합하여
    ML 모델 학습에 적합한 형태로 변환
    """

    def __init__(self, scaler: Optional[StandardScaler] = None):
        """
        Args:
            scaler: 사전 학습된 StandardScaler (None이면 새로 생성)
        """
        self.scaler = scaler or StandardScaler()
        self.label_encoders: Dict[str, LabelEncoder] = {}

    def preprocess(
        self, df: pd.DataFrame, fit_scaler: bool = True, remove_outliers: bool = False
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        데이터 전처리 메인 파이프라인

        Args:
            df: 원본 데이터프레임 (transaction + features)
            fit_scaler: True이면 스케일러 학습, False이면 기존 스케일러 사용
            remove_outliers: True이면 이상치 제거, False이면 건너뜀 (기본값: False)

        Returns:
            (전처리된 특성 DataFrame, 레이블 Series)
        """
        logger.info(f"전처리 시작: {len(df)}개 샘플")

        # 1. 결측치 처리
        df = self._handle_missing_values(df)

        # 2. 이상치 제거 (선택적)
        if remove_outliers:
            df = self._remove_outliers(df)

        # 3. 범주형 변수 인코딩
        df = self._encode_categorical_features(df, fit=fit_scaler)

        # 4. 날짜/시간 특성 변환
        df = self._transform_datetime_features(df)

        # 5. 레이블 분리
        if "is_fraud" in df.columns:
            y = df["is_fraud"].astype(int)
            X = df.drop(columns=["is_fraud"])
        else:
            y = pd.Series()
            X = df

        # 6. 수치형 특성 정규화
        numeric_columns = X.select_dtypes(include=[np.number]).columns.tolist()

        if fit_scaler:
            X[numeric_columns] = self.scaler.fit_transform(X[numeric_columns])
        else:
            X[numeric_columns] = self.scaler.transform(X[numeric_columns])

        logger.info(f"전처리 완료: {len(X)}개 샘플, {len(X.columns)}개 특성")

        return X, y

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        결측치 처리

        - 수치형: 중앙값으로 대체
        - 범주형: 'unknown'으로 대체
        """
        df = df.copy()

        # 수치형 컬럼 결측치 → 중앙값
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if df[col].isnull().any():
                median_value = df[col].median()
                df[col].fillna(median_value, inplace=True)
                logger.debug(f"컬럼 '{col}': 결측치 {df[col].isnull().sum()}개 → 중앙값 {median_value}로 대체")

        # 범주형 컬럼 결측치 → 'unknown'
        categorical_columns = df.select_dtypes(include=["object", "category"]).columns
        for col in categorical_columns:
            if df[col].isnull().any():
                df[col].fillna("unknown", inplace=True)
                logger.debug(f"컬럼 '{col}': 결측치를 'unknown'으로 대체")

        return df

    def _remove_outliers(
        self, df: pd.DataFrame, z_threshold: float = 3.0
    ) -> pd.DataFrame:
        """
        이상치 제거 (Z-score 방법)

        Args:
            df: 데이터프레임
            z_threshold: Z-score 임계값 (기본값 3.0)

        Returns:
            이상치가 제거된 데이터프레임
        """
        df = df.copy()
        numeric_columns = df.select_dtypes(include=[np.number]).columns

        # 'is_fraud' 레이블은 제외
        numeric_columns = [col for col in numeric_columns if col != "is_fraud"]

        # Z-score 계산
        z_scores = np.abs((df[numeric_columns] - df[numeric_columns].mean()) / df[numeric_columns].std())

        # 임계값 초과하는 행 제거
        outlier_mask = (z_scores < z_threshold).all(axis=1)
        original_len = len(df)
        df = df[outlier_mask]

        removed_count = original_len - len(df)
        if removed_count > 0:
            logger.info(f"이상치 제거: {removed_count}개 샘플 ({removed_count/original_len*100:.2f}%)")

        return df

    def _encode_categorical_features(
        self, df: pd.DataFrame, fit: bool = True
    ) -> pd.DataFrame:
        """
        범주형 변수 인코딩 (Label Encoding)

        Args:
            df: 데이터프레임
            fit: True이면 인코더 학습, False이면 기존 인코더 사용

        Returns:
            인코딩된 데이터프레임
        """
        df = df.copy()
        categorical_columns = df.select_dtypes(include=["object", "category"]).columns

        for col in categorical_columns:
            if col == "is_fraud":  # 레이블은 건너뜀
                continue

            if fit:
                # 인코더 새로 생성 및 학습
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
            else:
                # 기존 인코더 사용
                if col in self.label_encoders:
                    le = self.label_encoders[col]
                    # 학습 데이터에 없던 값 처리
                    df[col] = df[col].apply(
                        lambda x: le.transform([str(x)])[0]
                        if str(x) in le.classes_
                        else -1
                    )
                else:
                    logger.warning(f"컬럼 '{col}'의 인코더가 없습니다. 건너뜁니다.")

        return df

    def _transform_datetime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        날짜/시간 특성 변환

        - 시간대 (0-23)
        - 요일 (0=월요일, 6=일요일)
        - 주말 여부
        - 월 (1-12)
        """
        df = df.copy()

        # datetime 컬럼 찾기
        datetime_columns = df.select_dtypes(include=["datetime64"]).columns

        for col in datetime_columns:
            # 시간대
            df[f"{col}_hour"] = df[col].dt.hour

            # 요일 (0=월요일, 6=일요일)
            df[f"{col}_weekday"] = df[col].dt.weekday

            # 주말 여부
            df[f"{col}_is_weekend"] = df[col].dt.weekday.isin([5, 6]).astype(int)

            # 월
            df[f"{col}_month"] = df[col].dt.month

            # 원본 컬럼 삭제
            df = df.drop(columns=[col])

        return df


def load_training_data(
    db_session: Session,
    start_date: datetime,
    end_date: datetime,
    include_fraud_cases: bool = True,
) -> pd.DataFrame:
    """
    데이터베이스에서 학습 데이터 로드

    Args:
        db_session: 데이터베이스 세션
        start_date: 학습 데이터 시작일
        end_date: 학습 데이터 종료일
        include_fraud_cases: 확정된 사기 케이스 포함 여부

    Returns:
        학습 데이터 DataFrame
    """
    logger.info(f"학습 데이터 로드: {start_date.date()} ~ {end_date.date()}")

    # SQL 쿼리로 거래 데이터 조회
    # 실제 구현 시 FDS 서비스 데이터베이스에서 조회
    query = f"""
    SELECT
        t.id AS transaction_id,
        t.user_id,
        t.amount,
        t.ip_address,
        t.device_type,
        t.risk_score,
        t.risk_level,
        t.created_at,
        CASE
            WHEN fc.status = 'confirmed' THEN 1
            ELSE 0
        END AS is_fraud
    FROM transactions t
    LEFT JOIN fraud_cases fc ON t.id = fc.transaction_id
    WHERE t.created_at BETWEEN '{start_date}' AND '{end_date}'
    """

    if include_fraud_cases:
        query += " AND (fc.id IS NOT NULL OR t.risk_level = 'low')"

    # DataFrame으로 변환
    df = pd.read_sql(query, db_session.bind)

    logger.info(f"로드 완료: {len(df)}개 샘플")

    if include_fraud_cases:
        fraud_count = df["is_fraud"].sum()
        normal_count = len(df) - fraud_count
        logger.info(
            f"사기: {fraud_count}개 ({fraud_count/len(df)*100:.2f}%), "
            f"정상: {normal_count}개 ({normal_count/len(df)*100:.2f}%)"
        )

    return df


def split_train_test(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.2,
    random_state: int = 42,
    stratify: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    학습/테스트 데이터 분할

    Args:
        X: 특성 데이터
        y: 레이블 데이터
        test_size: 테스트 세트 비율 (기본값 0.2)
        random_state: 난수 시드
        stratify: 레이블 비율 유지 여부

    Returns:
        (X_train, X_test, y_train, y_test)
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y if stratify and len(y.unique()) > 1 else None,
    )

    logger.info(
        f"데이터 분할 완료: Train={len(X_train)}개, Test={len(X_test)}개"
    )

    if len(y_train) > 0:
        fraud_train = y_train.sum()
        fraud_test = y_test.sum()
        logger.info(
            f"Train - 사기: {fraud_train}개 ({fraud_train/len(y_train)*100:.2f}%)"
        )
        logger.info(
            f"Test - 사기: {fraud_test}개 ({fraud_test/len(y_test)*100:.2f}%)"
        )

    return X_train, X_test, y_train, y_test


def handle_imbalanced_data(
    X: pd.DataFrame, y: pd.Series, method: str = "smote"
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    불균형 데이터 처리

    Args:
        X: 특성 데이터
        y: 레이블 데이터
        method: 처리 방법 ('smote', 'undersample', 'oversample')

    Returns:
        (리샘플링된 X, 리샘플링된 y)
    """
    from imblearn.over_sampling import SMOTE
    from imblearn.under_sampling import RandomUnderSampler
    from imblearn.over_sampling import RandomOverSampler

    original_len = len(X)
    fraud_count = y.sum()
    normal_count = len(y) - fraud_count

    logger.info(
        f"불균형 데이터 처리 시작 ({method}): "
        f"정상={normal_count}, 사기={fraud_count}, 비율={fraud_count/normal_count:.4f}"
    )

    if method == "smote":
        # SMOTE (Synthetic Minority Over-sampling Technique)
        sampler = SMOTE(random_state=42)
    elif method == "undersample":
        # 다수 클래스 언더샘플링
        sampler = RandomUnderSampler(random_state=42)
    elif method == "oversample":
        # 소수 클래스 오버샘플링
        sampler = RandomOverSampler(random_state=42)
    else:
        raise ValueError(f"지원하지 않는 방법: {method}")

    X_resampled, y_resampled = sampler.fit_resample(X, y)

    new_fraud_count = y_resampled.sum()
    new_normal_count = len(y_resampled) - new_fraud_count

    logger.info(
        f"불균형 데이터 처리 완료: "
        f"{original_len}개 → {len(X_resampled)}개, "
        f"정상={new_normal_count}, 사기={new_fraud_count}, 비율={new_fraud_count/new_normal_count:.4f}"
    )

    return pd.DataFrame(X_resampled, columns=X.columns), pd.Series(y_resampled, name=y.name)


if __name__ == "__main__":
    # 테스트 코드 예시
    logging.basicConfig(level=logging.INFO)

    # 샘플 데이터 생성
    sample_data = pd.DataFrame({
        "amount": [100, 200, 50000, 150, 300],
        "risk_score": [10, 25, 95, 15, 30],
        "device_type": ["mobile", "desktop", "mobile", "tablet", "desktop"],
        "created_at": pd.to_datetime([
            "2025-01-01 10:00:00",
            "2025-01-02 14:30:00",
            "2025-01-03 02:00:00",
            "2025-01-04 16:45:00",
            "2025-01-05 20:15:00",
        ]),
        "is_fraud": [0, 0, 1, 0, 0],
    })

    # 전처리
    preprocessor = DataPreprocessor()
    X, y = preprocessor.preprocess(sample_data, fit_scaler=True)

    print("\n전처리 결과:")
    print(X.head())
    print("\n레이블:")
    print(y.head())
