"""
XAI Service - SHAP/LIME 기반 설명 가능한 AI 서비스

SHAP (SHapley Additive exPlanations) 및 LIME (Local Interpretable Model-agnostic Explanations)를
사용하여 ML 모델의 예측 결과에 대한 설명을 생성합니다.

주요 기능:
1. SHAP TreeExplainer: Random Forest, XGBoost 등 트리 기반 모델 설명
2. SHAP DeepExplainer: Neural Network (Autoencoder, LSTM) 설명
3. LIME: 모델 비의존적 로컬 설명
4. Feature 기여도 계산 (워터폴 차트 데이터)
5. 타임아웃 처리 (5초 제한)
6. SHAP 값 검증 (feature 값과 일치 확인)

목표:
- SHAP 분석: 95%가 5초 이내 완료
- 상위 5개 위험 요인 제공
- 워터폴 차트 데이터 생성
"""

import logging
import time
import traceback
from typing import Dict, Any, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid

# SHAP and LIME imports (conditional to handle if not installed)
try:
    import shap

    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logging.warning("[XAI] SHAP not installed. Install with: pip install shap")

try:
    from lime import lime_tabular

    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False
    logging.warning("[XAI] LIME not installed. Install with: pip install lime")

from src.models.xai_explanation import XAIExplanation

logger = logging.getLogger(__name__)


class XAIService:
    """
    XAI 분석 서비스

    SHAP/LIME을 사용하여 ML 모델의 예측 결과를 설명합니다.
    """

    def __init__(
        self,
        timeout_seconds: int = 5,
        enable_shap: bool = True,
        enable_lime: bool = True,
        max_display_features: int = 5,
    ):
        """
        Args:
            timeout_seconds: SHAP/LIME 계산 타임아웃 (초)
            enable_shap: SHAP 분석 활성화
            enable_lime: LIME 분석 활성화
            max_display_features: 상위 위험 요인 표시 개수
        """
        self.timeout_seconds = timeout_seconds
        self.enable_shap = enable_shap and SHAP_AVAILABLE
        self.enable_lime = enable_lime and LIME_AVAILABLE
        self.max_display_features = max_display_features

        # 캐시된 explainer (모델 로드 시 설정)
        self.tree_explainer: Optional[Any] = None
        self.deep_explainer: Optional[Any] = None
        self.lime_explainer: Optional[Any] = None

        # Feature 이름 (모델 로드 시 설정)
        self.feature_names: Optional[List[str]] = None
        self.feature_count: Optional[int] = None

    def initialize_explainers(
        self,
        tree_model: Optional[Any] = None,
        deep_model: Optional[Any] = None,
        feature_names: Optional[List[str]] = None,
        training_data: Optional[pd.DataFrame] = None,
    ) -> None:
        """
        Explainer 초기화

        Args:
            tree_model: 트리 기반 모델 (Random Forest, XGBoost)
            deep_model: 딥러닝 모델 (Autoencoder, LSTM)
            feature_names: Feature 이름 목록
            training_data: 학습 데이터 (LIME 배경 데이터)
        """
        self.feature_names = feature_names
        self.feature_count = len(feature_names) if feature_names else 0

        # SHAP TreeExplainer 초기화 (Random Forest, XGBoost)
        if self.enable_shap and tree_model is not None and SHAP_AVAILABLE:
            try:
                logger.info("[XAI] Initializing SHAP TreeExplainer...")
                self.tree_explainer = shap.TreeExplainer(tree_model)
                logger.info("[XAI] SHAP TreeExplainer initialized successfully")
            except Exception as e:
                logger.error(f"[XAI] Failed to initialize TreeExplainer: {e}")
                self.tree_explainer = None

        # SHAP DeepExplainer 초기화 (Neural Networks)
        if (
            self.enable_shap
            and deep_model is not None
            and training_data is not None
            and SHAP_AVAILABLE
        ):
            try:
                logger.info("[XAI] Initializing SHAP DeepExplainer...")
                # DeepExplainer는 배경 데이터 샘플 필요 (예: 100개)
                background_data = training_data.sample(
                    min(100, len(training_data)), random_state=42
                ).values
                self.deep_explainer = shap.DeepExplainer(deep_model, background_data)
                logger.info("[XAI] SHAP DeepExplainer initialized successfully")
            except Exception as e:
                logger.error(f"[XAI] Failed to initialize DeepExplainer: {e}")
                self.deep_explainer = None

        # LIME Explainer 초기화
        if self.enable_lime and training_data is not None and LIME_AVAILABLE:
            try:
                logger.info("[XAI] Initializing LIME Explainer...")
                self.lime_explainer = lime_tabular.LimeTabularExplainer(
                    training_data.values,
                    feature_names=feature_names or list(range(training_data.shape[1])),
                    class_names=["정상", "사기"],
                    mode="classification",
                    random_state=42,
                )
                logger.info("[XAI] LIME Explainer initialized successfully")
            except Exception as e:
                logger.error(f"[XAI] Failed to initialize LIME Explainer: {e}")
                self.lime_explainer = None

    async def explain_prediction(
        self,
        transaction_id: uuid.UUID,
        features: pd.DataFrame,
        model: Any,
        model_type: str = "tree",
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        거래 예측 결과에 대한 XAI 분석 수행

        Args:
            transaction_id: 거래 ID
            features: 입력 특징 데이터 (1행)
            model: ML 모델 (예측에 사용)
            model_type: 모델 타입 ("tree" or "deep")
            db_session: 데이터베이스 세션 (결과 저장용)

        Returns:
            {
                "transaction_id": UUID,
                "shap_values": [...],
                "lime_explanation": {...},
                "top_risk_factors": [...],
                "explanation_time_ms": int,
                "generated_at": datetime
            }
        """
        start_time = time.time()

        # 입력 검증
        if features.shape[0] != 1:
            raise ValueError(
                f"features must contain exactly 1 row, got {features.shape[0]}"
            )

        result = {
            "transaction_id": str(transaction_id),
            "shap_values": None,
            "lime_explanation": None,
            "top_risk_factors": [],
            "explanation_time_ms": 0,
            "generated_at": datetime.utcnow().isoformat(),
        }

        # T079: SHAP 분석 (TreeExplainer 또는 DeepExplainer)
        shap_values = None
        base_value = None

        if self.enable_shap:
            try:
                if model_type == "tree" and self.tree_explainer is not None:
                    shap_values, base_value = await self._compute_shap_tree(features)
                elif model_type == "deep" and self.deep_explainer is not None:
                    shap_values, base_value = await self._compute_shap_deep(features)
                else:
                    logger.warning(
                        f"[XAI] No SHAP explainer available for model_type={model_type}"
                    )
            except Exception as e:
                logger.error(f"[XAI] SHAP computation failed: {e}")
                logger.debug(traceback.format_exc())

        # SHAP 값을 결과에 저장
        if shap_values is not None:
            result["shap_values"] = self._format_shap_values(
                shap_values, base_value, features
            )

        # T080: LIME 분석 (로컬 모델 근사)
        if self.enable_lime and self.lime_explainer is not None:
            try:
                lime_exp = await self._compute_lime(features, model)
                result["lime_explanation"] = lime_exp
            except Exception as e:
                logger.error(f"[XAI] LIME computation failed: {e}")
                logger.debug(traceback.format_exc())

        # T081: Feature 기여도 계산 (워터폴 차트 데이터)
        if result["shap_values"]:
            result["top_risk_factors"] = self._compute_top_risk_factors(
                result["shap_values"]
            )

        # T087: SHAP 값 검증 (feature 값과 일치 확인)
        if result["shap_values"]:
            validation_result = self._validate_shap_values(
                result["shap_values"], features
            )
            result["validation"] = validation_result

        # 총 소요 시간
        elapsed_ms = int((time.time() - start_time) * 1000)
        result["explanation_time_ms"] = elapsed_ms

        logger.info(
            f"[XAI] Explanation generated for transaction {transaction_id} in {elapsed_ms}ms"
        )

        # 데이터베이스 저장 (옵션)
        if db_session:
            await self._save_explanation(transaction_id, result, db_session)

        return result

    async def _compute_shap_tree(
        self, features: pd.DataFrame
    ) -> Tuple[Optional[np.ndarray], Optional[float]]:
        """
        T079: SHAP TreeExplainer 계산 (타임아웃 5초)

        Args:
            features: 입력 특징 데이터

        Returns:
            (shap_values, base_value) 튜플
        """
        if not SHAP_AVAILABLE or self.tree_explainer is None:
            return None, None

        def _compute():
            explanation = self.tree_explainer(features)
            # TreeExplainer는 클래스별 SHAP 값 반환 (shape: [1, features, 2])
            # 사기 클래스(인덱스 1)만 사용
            shap_values = (
                explanation.values[0, :, 1]
                if len(explanation.values.shape) == 3
                else explanation.values[0]
            )
            base_value = (
                explanation.base_values[0, 1]
                if len(explanation.base_values.shape) == 2
                else explanation.base_values[0]
            )
            return shap_values, base_value

        # T082: 타임아웃 처리 (5초)
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_compute)
                shap_values, base_value = future.result(timeout=self.timeout_seconds)
                return shap_values, base_value
        except FuturesTimeoutError:
            logger.warning(
                f"[XAI] SHAP TreeExplainer timeout after {self.timeout_seconds}s"
            )
            return None, None
        except Exception as e:
            logger.error(f"[XAI] SHAP TreeExplainer error: {e}")
            return None, None

    async def _compute_shap_deep(
        self, features: pd.DataFrame
    ) -> Tuple[Optional[np.ndarray], Optional[float]]:
        """
        T079: SHAP DeepExplainer 계산 (타임아웃 5초)

        Args:
            features: 입력 특징 데이터

        Returns:
            (shap_values, base_value) 튜플
        """
        if not SHAP_AVAILABLE or self.deep_explainer is None:
            return None, None

        def _compute():
            explanation = self.deep_explainer.shap_values(features.values)
            # DeepExplainer 결과: [classes, samples, features]
            shap_values = (
                explanation[1][0] if isinstance(explanation, list) else explanation[0]
            )
            base_value = (
                self.deep_explainer.expected_value[1]
                if isinstance(self.deep_explainer.expected_value, list)
                else self.deep_explainer.expected_value
            )
            return shap_values, base_value

        # T082: 타임아웃 처리 (5초)
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_compute)
                shap_values, base_value = future.result(timeout=self.timeout_seconds)
                return shap_values, base_value
        except FuturesTimeoutError:
            logger.warning(
                f"[XAI] SHAP DeepExplainer timeout after {self.timeout_seconds}s"
            )
            return None, None
        except Exception as e:
            logger.error(f"[XAI] SHAP DeepExplainer error: {e}")
            return None, None

    async def _compute_lime(
        self, features: pd.DataFrame, model: Any
    ) -> Optional[Dict[str, Any]]:
        """
        T080: LIME 로컬 모델 근사 계산

        Args:
            features: 입력 특징 데이터
            model: 예측 모델 (predict_proba 메서드 필요)

        Returns:
            LIME 설명 결과
        """
        if not LIME_AVAILABLE or self.lime_explainer is None:
            return None

        def _compute():
            # LIME은 단일 인스턴스에 대해 설명 생성
            instance = features.values[0]

            # predict_proba 함수 정의
            def predict_fn(X):
                df = pd.DataFrame(X, columns=features.columns)
                if hasattr(model, "predict_proba"):
                    return model.predict_proba(df)
                else:
                    # predict만 있는 경우 [1-pred, pred]로 변환
                    preds = model.predict(df)
                    return np.column_stack([1 - preds, preds])

            # LIME 설명 생성
            explanation = self.lime_explainer.explain_instance(
                instance,
                predict_fn,
                num_features=self.max_display_features,
                top_labels=1,
            )

            # 결과 파싱
            lime_result = {
                "prediction": float(explanation.predict_proba[1]),
                "local_prediction": float(explanation.local_pred[1]),
                "score": float(explanation.score),
                "intercept": float(explanation.intercept[1]),
                "explanations": [],
            }

            # Feature 기여도
            for feature_idx, weight in explanation.as_list(label=1):
                lime_result["explanations"].append(
                    {"feature": str(feature_idx), "weight": float(weight)}
                )

            return lime_result

        # T082: 타임아웃 처리 (5초)
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_compute)
                result = future.result(timeout=self.timeout_seconds)
                return result
        except FuturesTimeoutError:
            logger.warning(f"[XAI] LIME timeout after {self.timeout_seconds}s")
            return None
        except Exception as e:
            logger.error(f"[XAI] LIME error: {e}")
            return None

    def _format_shap_values(
        self,
        shap_values: np.ndarray,
        base_value: float,
        features: pd.DataFrame,
    ) -> List[Dict[str, Any]]:
        """
        SHAP 값을 워터폴 차트 형식으로 변환

        Args:
            shap_values: SHAP 값 배열
            base_value: 기본 값 (평균 예측)
            features: 입력 특징

        Returns:
            [{feature, value, shap_value, contribution}, ...]
        """
        feature_names = (
            self.feature_names if self.feature_names else list(features.columns)
        )
        feature_values = features.values[0]

        formatted = []
        for i, (fname, fvalue, svalue) in enumerate(
            zip(feature_names, feature_values, shap_values)
        ):
            formatted.append(
                {
                    "feature": fname,
                    "value": float(fvalue),
                    "shap_value": float(svalue),
                    "contribution": float(svalue),  # 기여도 (양수: 위험 증가, 음수: 위험 감소)
                    "rank": i + 1,
                }
            )

        # 절대값 기준 내림차순 정렬
        formatted.sort(key=lambda x: abs(x["contribution"]), reverse=True)

        # 순위 재할당
        for i, item in enumerate(formatted):
            item["rank"] = i + 1

        # 기본 값 추가
        formatted.insert(
            0,
            {
                "feature": "base_value",
                "value": float(base_value),
                "shap_value": 0.0,
                "contribution": 0.0,
                "rank": 0,
            },
        )

        return formatted

    def _compute_top_risk_factors(
        self, shap_values: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        T081: 상위 위험 요인 계산 (워터폴 차트 데이터)

        Args:
            shap_values: 포맷된 SHAP 값 목록

        Returns:
            상위 N개 위험 요인 [{factor, contribution, rank}, ...]
        """
        # base_value 제외
        risk_factors = [item for item in shap_values if item["feature"] != "base_value"]

        # 절대값 기준 상위 N개
        top_n = sorted(
            risk_factors, key=lambda x: abs(x["contribution"]), reverse=True
        )[: self.max_display_features]

        # 순위 재할당
        result = []
        for i, item in enumerate(top_n):
            result.append(
                {
                    "factor": item["feature"],
                    "value": item["value"],
                    "contribution": item["contribution"],
                    "rank": i + 1,
                    "impact": "위험 증가" if item["contribution"] > 0 else "위험 감소",
                }
            )

        return result

    def _validate_shap_values(
        self, shap_values: List[Dict[str, Any]], features: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        T087: SHAP 값 검증 (feature 값과 일치 확인)

        Args:
            shap_values: 포맷된 SHAP 값 목록
            features: 입력 특징 데이터

        Returns:
            검증 결과 {valid: bool, mismatches: [...]}
        """
        mismatches = []

        for item in shap_values:
            if item["feature"] == "base_value":
                continue

            feature_name = item["feature"]
            shap_feature_value = item["value"]

            # 원본 features에서 값 확인
            if feature_name in features.columns:
                original_value = features[feature_name].values[0]

                # 부동소수점 비교 (소수점 6자리)
                if not np.isclose(shap_feature_value, original_value, rtol=1e-5):
                    mismatches.append(
                        {
                            "feature": feature_name,
                            "shap_value": float(shap_feature_value),
                            "original_value": float(original_value),
                        }
                    )
            else:
                mismatches.append(
                    {
                        "feature": feature_name,
                        "error": "Feature not found in original data",
                    }
                )

        return {
            "valid": len(mismatches) == 0,
            "mismatches": mismatches,
            "total_features": len(shap_values) - 1,  # base_value 제외
        }

    async def _save_explanation(
        self,
        transaction_id: uuid.UUID,
        result: Dict[str, Any],
        db_session: AsyncSession,
    ) -> None:
        """
        XAI 분석 결과를 데이터베이스에 저장

        Args:
            transaction_id: 거래 ID
            result: XAI 분석 결과
            db_session: 데이터베이스 세션
        """
        try:
            explanation = XAIExplanation(
                explanation_id=uuid.uuid4(),
                transaction_id=transaction_id,
                shap_values=result.get("shap_values"),
                lime_explanation=result.get("lime_explanation"),
                top_risk_factors=result.get("top_risk_factors"),
                explanation_time_ms=result.get("explanation_time_ms"),
                generated_at=datetime.utcnow(),
            )

            db_session.add(explanation)
            await db_session.commit()
            await db_session.refresh(explanation)

            logger.info(f"[XAI] Explanation saved to DB: {explanation.explanation_id}")
        except Exception as e:
            logger.error(f"[XAI] Failed to save explanation to DB: {e}")
            await db_session.rollback()

    async def get_explanation_by_transaction(
        self, transaction_id: uuid.UUID, db_session: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """
        거래 ID로 저장된 XAI 분석 결과 조회

        Args:
            transaction_id: 거래 ID
            db_session: 데이터베이스 세션

        Returns:
            XAI 분석 결과 또는 None
        """
        try:
            stmt = select(XAIExplanation).where(
                XAIExplanation.transaction_id == transaction_id
            )
            result = await db_session.execute(stmt)
            explanation = result.scalars().first()

            if explanation:
                return {
                    "explanation_id": str(explanation.explanation_id),
                    "transaction_id": str(explanation.transaction_id),
                    "shap_values": explanation.shap_values,
                    "lime_explanation": explanation.lime_explanation,
                    "top_risk_factors": explanation.top_risk_factors,
                    "explanation_time_ms": explanation.explanation_time_ms,
                    "generated_at": explanation.generated_at.isoformat(),
                }
            else:
                return None
        except Exception as e:
            logger.error(f"[XAI] Failed to retrieve explanation: {e}")
            return None
