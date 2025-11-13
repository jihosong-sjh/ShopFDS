"""
Pydantic 스키마: FDS API 요청/응답 모델

이 모듈은 FDS API의 요청과 응답을 위한 Pydantic 스키마를 정의합니다.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class DeviceTypeEnum(str, Enum):
    """디바이스 유형"""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"
    UNKNOWN = "unknown"


class RiskLevelEnum(str, Enum):
    """위험 수준"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DecisionEnum(str, Enum):
    """의사결정"""
    APPROVE = "approve"                      # 자동 승인
    ADDITIONAL_AUTH_REQUIRED = "additional_auth_required"  # 추가 인증 필요
    BLOCKED = "blocked"                      # 차단


class SeverityEnum(str, Enum):
    """위험 요인 심각도"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ============================================================================
# Request Schemas
# ============================================================================

class DeviceFingerprint(BaseModel):
    """디바이스 지문 정보"""
    device_type: DeviceTypeEnum
    os: Optional[str] = None
    browser: Optional[str] = None


class ShippingInfo(BaseModel):
    """배송 정보"""
    name: str
    address: str
    phone: str


class PaymentInfo(BaseModel):
    """결제 정보"""
    method: str = Field(..., description="결제 수단 (예: credit_card)")
    card_bin: Optional[str] = Field(None, description="카드 BIN (앞 6자리)")
    card_last_four: str = Field(..., description="카드 마지막 4자리")


class SessionContext(BaseModel):
    """세션 컨텍스트"""
    session_id: str
    session_duration_seconds: Optional[int] = None
    pages_visited: Optional[int] = None
    products_viewed: Optional[int] = None
    cart_additions: Optional[int] = None


class FDSEvaluationRequest(BaseModel):
    """
    FDS 평가 요청

    이커머스 서비스에서 FDS 서비스로 전송하는 거래 평가 요청
    """
    transaction_id: UUID = Field(..., description="거래 고유 ID (멱등성 보장)")
    user_id: UUID = Field(..., description="사용자 ID")
    order_id: UUID = Field(..., description="주문 ID")
    amount: Decimal = Field(..., gt=0, description="거래 금액 (KRW)")
    currency: str = Field(default="KRW", description="통화 코드")

    # 접속 정보
    ip_address: str = Field(..., description="접속 IP 주소")
    user_agent: str = Field(..., description="User-Agent 헤더")
    device_fingerprint: DeviceFingerprint

    # 배송 및 결제 정보
    shipping_info: ShippingInfo
    payment_info: PaymentInfo

    # 세션 컨텍스트 (선택적)
    session_context: Optional[SessionContext] = None

    # 타임스탬프
    timestamp: datetime = Field(..., description="거래 발생 시각 (ISO 8601)")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        """타임스탬프가 현재 시각 ±5분 이내인지 검증"""
        from datetime import timedelta
        now = datetime.utcnow()
        if abs((now - v.replace(tzinfo=None)).total_seconds()) > 300:  # 5분
            raise ValueError("타임스탬프는 현재 시각 ±5분 이내여야 합니다")
        return v


# ============================================================================
# Response Schemas
# ============================================================================

class RiskFactor(BaseModel):
    """위험 요인"""
    factor_type: str = Field(..., description="요인 유형")
    factor_score: int = Field(..., ge=0, le=100, description="요인별 위험 점수")
    description: str = Field(..., description="요인 설명")
    severity: SeverityEnum = Field(..., description="심각도")
    model_version: Optional[str] = Field(None, description="ML 모델 버전 (ML 요인인 경우)")
    source: Optional[str] = Field(None, description="출처 (CTI 요인인 경우)")


class EvaluationMetadata(BaseModel):
    """평가 메타데이터"""
    evaluation_time_ms: int = Field(..., description="총 평가 시간 (ms)")
    rule_engine_time_ms: Optional[int] = Field(None, description="룰 엔진 실행 시간 (ms)")
    ml_engine_time_ms: Optional[int] = Field(None, description="ML 엔진 실행 시간 (ms)")
    cti_check_time_ms: Optional[int] = Field(None, description="CTI 확인 시간 (ms)")
    timestamp: datetime = Field(..., description="평가 완료 시각")


class RecommendedAction(BaseModel):
    """권장 조치"""
    action: DecisionEnum = Field(..., description="의사결정")
    reason: str = Field(..., description="결정 사유")
    additional_auth_required: bool = Field(..., description="추가 인증 필요 여부")
    auth_methods: Optional[List[str]] = Field(None, description="인증 방법 (추가 인증 필요 시)")
    auth_timeout_seconds: Optional[int] = Field(None, description="인증 타임아웃 (초)")
    manual_review_required: Optional[bool] = Field(None, description="수동 검토 필요 여부")
    review_queue_id: Optional[str] = Field(None, description="검토 큐 ID (차단 시)")


class FDSEvaluationResponse(BaseModel):
    """
    FDS 평가 응답

    FDS 서비스에서 이커머스 서비스로 반환하는 평가 결과
    """
    transaction_id: UUID = Field(..., description="거래 ID")
    risk_score: int = Field(..., ge=0, le=100, description="위험 점수 (0-100)")
    risk_level: RiskLevelEnum = Field(..., description="위험 수준")
    decision: DecisionEnum = Field(..., description="의사결정")
    risk_factors: List[RiskFactor] = Field(default_factory=list, description="위험 요인 목록")
    evaluation_metadata: EvaluationMetadata = Field(..., description="평가 메타데이터")
    recommended_action: RecommendedAction = Field(..., description="권장 조치")

    @property
    def requires_verification(self) -> bool:
        """추가 인증 필요 여부 (recommended_action.additional_auth_required의 별칭)"""
        return self.recommended_action.additional_auth_required


class FDSErrorResponse(BaseModel):
    """FDS 에러 응답"""
    error_code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    details: Optional[dict] = Field(None, description="추가 상세 정보")
