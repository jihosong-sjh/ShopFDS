"""
Bot Detection Service

봇 탐지 및 추가 인증 트리거 서비스
"""

from typing import Dict, Any, Optional
from enum import Enum


class AuthMethod(str, Enum):
    """추가 인증 방법"""

    OTP = "otp"  # SMS/Email OTP
    CAPTCHA = "captcha"  # reCAPTCHA, hCaptcha
    BIOMETRIC = "biometric"  # 생체 인증
    NONE = "none"  # 추가 인증 불필요


class BotDetectionService:
    """봇 탐지 및 추가 인증 결정 서비스"""

    # 봇 점수 임계값
    LOW_RISK_THRESHOLD = 30  # 0-30: 정상 사용자
    MEDIUM_RISK_THRESHOLD = 70  # 31-70: 의심스러운 행동
    HIGH_RISK_THRESHOLD = 90  # 71-90: 봇 가능성 높음
    # 91-100: 확실한 봇 → 즉시 차단

    def __init__(self):
        pass

    def determine_auth_requirement(
        self, bot_score: int, risk_factors: list[str]
    ) -> Dict[str, Any]:
        """
        봇 점수 및 위험 요인 기반 추가 인증 필요 여부 결정

        Args:
            bot_score: 봇 점수 (0-100)
            risk_factors: 위험 요인 리스트

        Returns:
            추가 인증 정보
                - requires_auth: 추가 인증 필요 여부
                - auth_method: 권장 인증 방법
                - risk_level: 위험 수준
                - should_block: 즉시 차단 여부 (봇 점수 > 90)
        """
        # 위험 수준 결정
        if bot_score <= self.LOW_RISK_THRESHOLD:
            risk_level = "low"
            requires_auth = False
            auth_method = AuthMethod.NONE
        elif bot_score <= self.MEDIUM_RISK_THRESHOLD:
            risk_level = "medium"
            requires_auth = False  # Medium risk는 모니터링만
            auth_method = AuthMethod.NONE
        elif bot_score <= self.HIGH_RISK_THRESHOLD:
            risk_level = "high"
            requires_auth = True
            auth_method = self._select_auth_method(bot_score, risk_factors)
        else:  # bot_score > 90
            risk_level = "critical"
            requires_auth = True
            auth_method = AuthMethod.OTP  # 가장 강력한 인증
            should_block = True
            return {
                "requires_auth": requires_auth,
                "auth_method": auth_method.value,
                "risk_level": risk_level,
                "should_block": True,
                "block_reason": "봇 확률 매우 높음 (점수: {})".format(bot_score),
                "recommended_action": "즉시 거래 차단 및 보안팀 검토 필요",
            }

        return {
            "requires_auth": requires_auth,
            "auth_method": auth_method.value,
            "risk_level": risk_level,
            "should_block": False,
            "recommended_action": self._get_recommended_action(risk_level),
        }

    def _select_auth_method(
        self, bot_score: int, risk_factors: list[str]
    ) -> AuthMethod:
        """
        봇 점수 및 위험 요인 기반 최적 인증 방법 선택

        Args:
            bot_score: 봇 점수
            risk_factors: 위험 요인 리스트

        Returns:
            권장 인증 방법
        """
        # 봇 점수가 매우 높으면 OTP 사용
        if bot_score > 85:
            return AuthMethod.OTP

        # 마우스 관련 위험 요인이 많으면 CAPTCHA 효과적
        mouse_risk_count = sum(
            1 for factor in risk_factors if "마우스" in factor or "움직임" in factor
        )
        if mouse_risk_count >= 2:
            return AuthMethod.CAPTCHA

        # 키보드 관련 위험 요인이 많으면 OTP 사용 (키보드 봇 우회 가능)
        keyboard_risk_count = sum(
            1 for factor in risk_factors if "타이핑" in factor or "키보드" in factor
        )
        if keyboard_risk_count >= 2:
            return AuthMethod.OTP

        # 기본값: CAPTCHA (사용자 경험 좋음)
        return AuthMethod.CAPTCHA

    def _get_recommended_action(self, risk_level: str) -> str:
        """
        위험 수준별 권장 조치

        Args:
            risk_level: 위험 수준

        Returns:
            권장 조치 설명
        """
        recommendations = {
            "low": "정상 거래 진행",
            "medium": "거래 모니터링 (추가 조치 불필요)",
            "high": "추가 인증 요구 (OTP 또는 CAPTCHA)",
            "critical": "즉시 거래 차단 및 보안팀 검토",
        }
        return recommendations.get(risk_level, "알 수 없는 위험 수준")

    def should_trigger_captcha(self, bot_score: int) -> bool:
        """
        CAPTCHA 트리거 여부

        Args:
            bot_score: 봇 점수

        Returns:
            CAPTCHA 필요 여부
        """
        # 봇 점수 71-85 범위에서 CAPTCHA 권장
        return 71 <= bot_score <= 85

    def should_trigger_otp(self, bot_score: int) -> bool:
        """
        OTP 트리거 여부

        Args:
            bot_score: 봇 점수

        Returns:
            OTP 필요 여부
        """
        # 봇 점수 > 85일 때 OTP 권장
        return bot_score > 85

    def should_block_transaction(self, bot_score: int) -> bool:
        """
        거래 차단 여부

        Args:
            bot_score: 봇 점수

        Returns:
            거래 차단 필요 여부
        """
        # 봇 점수 > 90일 때 즉시 차단
        return bot_score > 90

    def get_auth_challenge_message(self, auth_method: str, bot_score: int) -> str:
        """
        사용자에게 표시할 인증 안내 메시지

        Args:
            auth_method: 인증 방법
            bot_score: 봇 점수

        Returns:
            안내 메시지
        """
        if auth_method == AuthMethod.CAPTCHA.value:
            return "보안 확인을 위해 CAPTCHA 인증이 필요합니다."
        elif auth_method == AuthMethod.OTP.value:
            return "보안 확인을 위해 휴대전화 인증이 필요합니다."
        elif auth_method == AuthMethod.BIOMETRIC.value:
            return "보안 확인을 위해 생체 인증이 필요합니다."
        else:
            return "추가 인증이 필요합니다."

    def log_bot_detection(
        self,
        session_id: str,
        user_id: Optional[str],
        bot_score: int,
        risk_factors: list[str],
        action_taken: str,
    ) -> Dict[str, Any]:
        """
        봇 탐지 로그 생성 (모니터링/감사용)

        Args:
            session_id: 세션 ID
            user_id: 사용자 ID
            bot_score: 봇 점수
            risk_factors: 위험 요인
            action_taken: 수행된 조치

        Returns:
            로그 데이터
        """
        return {
            "event_type": "bot_detection",
            "session_id": session_id,
            "user_id": user_id,
            "bot_score": bot_score,
            "risk_factors": risk_factors,
            "action_taken": action_taken,
            "severity": self._get_severity(bot_score),
        }

    def _get_severity(self, bot_score: int) -> str:
        """
        봇 점수 기반 심각도 수준

        Args:
            bot_score: 봇 점수

        Returns:
            심각도 (info, warning, error, critical)
        """
        if bot_score <= 30:
            return "info"
        elif bot_score <= 70:
            return "warning"
        elif bot_score <= 90:
            return "error"
        else:
            return "critical"
