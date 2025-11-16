"""
ML 기반 이상 탐지 엔진

기능:
- ML 모델을 사용한 이상 거래 탐지
- Isolation Forest, LightGBM 모델 지원
- 카나리 배포 지원 (트래픽 분할)
- 실시간 특징 추출 및 예측
"""

import hashlib
import pickle
from typing import Dict, Any, Optional
from datetime import datetime

import numpy as np


class MLEngine:
    """ML 기반 이상 탐지 엔진"""

    def __init__(
        self,
        model_path: Optional[str] = None,
        canary_enabled: bool = False,
        canary_model_path: Optional[str] = None,
        canary_traffic_percentage: int = 0,
    ):
        """
        Args:
            model_path: 프로덕션 모델 파일 경로
            canary_enabled: 카나리 배포 활성화 여부
            canary_model_path: 카나리 모델 파일 경로 (선택)
            canary_traffic_percentage: 카나리 트래픽 비율 (0-100)
        """
        self.model_path = model_path
        self.canary_enabled = canary_enabled
        self.canary_model_path = canary_model_path
        self.canary_traffic_percentage = canary_traffic_percentage

        # 모델 로드
        self.production_model = None
        self.canary_model = None

        if model_path:
            self.production_model = self._load_model(model_path)

        if canary_enabled and canary_model_path:
            self.canary_model = self._load_model(canary_model_path)

        # 통계
        self.production_requests = 0
        self.canary_requests = 0

    def _load_model(self, model_path: str) -> Any:
        """
        모델 로드

        Args:
            model_path: 모델 파일 경로

        Returns:
            Any: 로드된 모델 객체
        """
        try:
            with open(model_path, "rb") as f:
                model = pickle.load(f)
            return model
        except FileNotFoundError:
            raise ValueError(f"모델 파일을 찾을 수 없습니다: {model_path}")
        except Exception as e:
            raise ValueError(f"모델 로드 실패: {str(e)}")

    async def evaluate(
        self,
        transaction_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        ML 모델을 사용한 이상 거래 탐지

        Args:
            transaction_data: 거래 데이터
                - transaction_id: 거래 ID
                - user_id: 사용자 ID
                - amount: 거래 금액
                - ip_address: IP 주소
                - device_type: 디바이스 유형
                - user_behavior: 사용자 행동 데이터
                - 기타 특징

        Returns:
            Dict[str, Any]: ML 평가 결과
                - anomaly_score: 이상 점수 (0-100)
                - is_anomaly: 이상 여부 (True/False)
                - confidence: 신뢰도 (0-1)
                - model_used: 사용된 모델 ("production" 또는 "canary")
                - features_used: 사용된 특징 목록
        """
        # 특징 추출
        features = self._extract_features(transaction_data)

        # 카나리 배포 활성화 시 트래픽 분할
        model_used = "production"
        model = self.production_model

        if self.canary_enabled and self.canary_model:
            transaction_id = transaction_data.get("transaction_id", "")
            is_canary = self._should_use_canary(transaction_id)

            if is_canary:
                model_used = "canary"
                model = self.canary_model
                self.canary_requests += 1
            else:
                self.production_requests += 1
        else:
            self.production_requests += 1

        if not model:
            return {
                "anomaly_score": 0,
                "is_anomaly": False,
                "confidence": 0.0,
                "model_used": "none",
                "features_used": list(features.keys()),
                "error": "모델이 로드되지 않았습니다",
            }

        # 모델 예측
        try:
            # 특징 벡터 생성
            feature_vector = np.array([list(features.values())])

            # Isolation Forest 예측
            if hasattr(model, "decision_function"):
                # Isolation Forest: decision_function 사용 (낮을수록 이상)
                anomaly_scores = model.decision_function(feature_vector)
                anomaly_score_raw = anomaly_scores[0]

                # 점수를 0-100 범위로 정규화 (-1 ~ 0.5 범위 가정)
                # -1 (이상) → 100, 0.5 (정상) → 0
                anomaly_score = max(0, min(100, int((0.5 - anomaly_score_raw) * 100)))

                # 예측 (-1: 이상, 1: 정상)
                predictions = model.predict(feature_vector)
                is_anomaly = predictions[0] == -1

                # 신뢰도 계산 (0-1 범위)
                confidence = abs(anomaly_score_raw) / 1.5

            elif hasattr(model, "predict_proba"):
                # LightGBM 등: predict_proba 사용
                probabilities = model.predict_proba(feature_vector)
                anomaly_probability = probabilities[0][1]  # 사기 확률

                anomaly_score = int(anomaly_probability * 100)
                is_anomaly = anomaly_probability > 0.5
                confidence = max(anomaly_probability, 1 - anomaly_probability)

            else:
                # 기타 모델: predict만 사용
                predictions = model.predict(feature_vector)
                is_anomaly = predictions[0] == 1

                anomaly_score = 100 if is_anomaly else 0
                confidence = 0.5  # 신뢰도 정보 없음

            return {
                "anomaly_score": anomaly_score,
                "is_anomaly": bool(is_anomaly),
                "confidence": round(confidence, 4),
                "model_used": model_used,
                "features_used": list(features.keys()),
                "feature_importance": self._get_feature_importance(model, features),
            }

        except Exception as e:
            return {
                "anomaly_score": 0,
                "is_anomaly": False,
                "confidence": 0.0,
                "model_used": model_used,
                "features_used": list(features.keys()),
                "error": f"예측 실패: {str(e)}",
            }

    def _extract_features(self, transaction_data: Dict[str, Any]) -> Dict[str, float]:
        """
        거래 데이터에서 ML 특징 추출

        Args:
            transaction_data: 거래 데이터

        Returns:
            Dict[str, float]: 추출된 특징 (키: 특징명, 값: 숫자)
        """
        features = {}

        # 거래 금액
        features["amount"] = float(transaction_data.get("amount", 0))
        features["amount_log"] = np.log1p(features["amount"])

        # 디바이스 유형 (원핫 인코딩)
        device_type = transaction_data.get("device_type", "unknown")
        features["device_desktop"] = 1.0 if device_type == "desktop" else 0.0
        features["device_mobile"] = 1.0 if device_type == "mobile" else 0.0
        features["device_tablet"] = 1.0 if device_type == "tablet" else 0.0

        # 사용자 행동 특징
        user_behavior = transaction_data.get("user_behavior", {})

        # 최근 거래 빈도 (24시간 내)
        features["transactions_24h"] = float(
            user_behavior.get("recent_transaction_count", 0)
        )

        # 평균 거래 금액
        features["avg_transaction_amount"] = float(
            user_behavior.get("avg_transaction_amount", 0)
        )

        # 금액 편차 (현재 거래 금액 - 평균)
        if features["avg_transaction_amount"] > 0:
            features["amount_deviation_ratio"] = (
                features["amount"] / features["avg_transaction_amount"]
            )
        else:
            features["amount_deviation_ratio"] = 0.0

        # 계정 생성 후 경과 시간 (일)
        features["account_age_days"] = float(user_behavior.get("account_age_days", 0))

        # 로그인 빈도 (30일)
        features["login_count_30d"] = float(user_behavior.get("login_count_30d", 0))

        # 시간대 특징 (UTC 기준)
        current_hour = datetime.utcnow().hour
        features["hour"] = float(current_hour)
        features["is_night"] = 1.0 if (current_hour < 6 or current_hour > 22) else 0.0
        features["is_weekend"] = 1.0 if datetime.utcnow().weekday() >= 5 else 0.0

        # 지역 불일치 (등록 국가 vs 현재 국가)
        geolocation = transaction_data.get("geolocation", {})
        registered_country = user_behavior.get("registered_country", "")
        current_country = geolocation.get("country", "")
        features["location_mismatch"] = (
            1.0 if registered_country and current_country != registered_country else 0.0
        )

        # IP 평판 (CTI 점수)
        features["ip_reputation_score"] = float(
            transaction_data.get("ip_reputation_score", 0)
        )

        return features

    def _get_feature_importance(
        self,
        model: Any,
        features: Dict[str, float],
    ) -> Optional[Dict[str, float]]:
        """
        특징 중요도 추출 (LightGBM, RandomForest 등)

        Args:
            model: ML 모델
            features: 사용된 특징

        Returns:
            Optional[Dict[str, float]]: 특징 중요도 (키: 특징명, 값: 중요도)
        """
        if hasattr(model, "feature_importances_"):
            # RandomForest, LightGBM 등
            importances = model.feature_importances_
            feature_names = list(features.keys())

            if len(importances) == len(feature_names):
                return dict(zip(feature_names, importances.tolist()))

        return None

    def _should_use_canary(self, transaction_id: str) -> bool:
        """
        카나리 모델 사용 여부 결정 (해시 기반 일관된 라우팅)

        Args:
            transaction_id: 거래 ID

        Returns:
            bool: 카나리 모델 사용 여부
        """
        if not self.canary_enabled or self.canary_traffic_percentage <= 0:
            return False

        # 거래 ID 해시 기반 트래픽 분할
        hash_value = int(hashlib.sha256(transaction_id.encode()).hexdigest(), 16)
        return (hash_value % 100) < self.canary_traffic_percentage

    def reload_model(
        self,
        model_path: str,
        model_type: str = "production",
    ) -> Dict[str, Any]:
        """
        모델 재로드 (배포 후 또는 롤백 시)

        Args:
            model_path: 새 모델 파일 경로
            model_type: 모델 타입 ("production" 또는 "canary")

        Returns:
            Dict[str, Any]: 재로드 결과
        """
        try:
            new_model = self._load_model(model_path)

            if model_type == "production":
                self.production_model = new_model
                self.model_path = model_path
            elif model_type == "canary":
                self.canary_model = new_model
                self.canary_model_path = model_path
            else:
                raise ValueError(f"잘못된 모델 타입: {model_type}")

            return {
                "message": f"{model_type} 모델 재로드 성공",
                "model_path": model_path,
            }

        except Exception as e:
            return {
                "message": f"{model_type} 모델 재로드 실패",
                "error": str(e),
            }

    def enable_canary(
        self,
        canary_model_path: str,
        traffic_percentage: int,
    ) -> Dict[str, Any]:
        """
        카나리 배포 활성화

        Args:
            canary_model_path: 카나리 모델 경로
            traffic_percentage: 트래픽 비율 (0-100)

        Returns:
            Dict[str, Any]: 활성화 결과
        """
        try:
            self.canary_model = self._load_model(canary_model_path)
            self.canary_model_path = canary_model_path
            self.canary_traffic_percentage = traffic_percentage
            self.canary_enabled = True

            # 통계 초기화
            self.canary_requests = 0
            self.production_requests = 0

            return {
                "message": f"카나리 배포 활성화: {traffic_percentage}% 트래픽",
                "canary_model_path": canary_model_path,
                "traffic_percentage": traffic_percentage,
            }

        except Exception as e:
            return {
                "message": "카나리 배포 활성화 실패",
                "error": str(e),
            }

    def disable_canary(self) -> Dict[str, Any]:
        """
        카나리 배포 비활성화

        Returns:
            Dict[str, Any]: 비활성화 결과
        """
        self.canary_enabled = False
        self.canary_model = None
        self.canary_model_path = None
        self.canary_traffic_percentage = 0

        final_stats = {
            "production_requests": self.production_requests,
            "canary_requests": self.canary_requests,
        }

        # 통계 초기화
        self.production_requests = 0
        self.canary_requests = 0

        return {
            "message": "카나리 배포 비활성화",
            "final_stats": final_stats,
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        ML 엔진 통계 조회

        Returns:
            Dict[str, Any]: 통계 정보
        """
        return {
            "production_model_loaded": self.production_model is not None,
            "production_model_path": self.model_path,
            "production_requests": self.production_requests,
            "canary_enabled": self.canary_enabled,
            "canary_model_loaded": self.canary_model is not None,
            "canary_model_path": self.canary_model_path,
            "canary_traffic_percentage": self.canary_traffic_percentage,
            "canary_requests": self.canary_requests,
        }
