"""
OTP (One-Time Password) 생성 및 검증 유틸리티

추가 인증이 필요한 의심 거래 시 사용되는 OTP 관리
"""
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict
import redis.asyncio as aioredis

from config import get_settings


class OTPService:
    """OTP 생성, 저장, 검증 서비스"""

    def __init__(self, redis_client: aioredis.Redis):
        """
        Args:
            redis_client: Redis 클라이언트 인스턴스
        """
        self.redis = redis_client
        self.settings = get_settings()

        # OTP 설정
        self.otp_length = 6  # OTP 길이
        self.otp_expiry_seconds = 300  # 5분 유효
        self.max_attempts = 3  # 최대 시도 횟수

    def _generate_otp_code(self) -> str:
        """
        6자리 숫자 OTP 코드 생성

        Returns:
            str: 6자리 OTP 코드 (예: "123456")
        """
        return ''.join(secrets.choice(string.digits) for _ in range(self.otp_length))

    def _get_otp_key(self, user_id: str, purpose: str) -> str:
        """
        Redis 키 생성

        Args:
            user_id: 사용자 ID
            purpose: OTP 목적 (예: "transaction", "login")

        Returns:
            str: Redis 키
        """
        return f"otp:{purpose}:{user_id}"

    def _get_attempt_key(self, user_id: str, purpose: str) -> str:
        """
        OTP 시도 횟수 추적을 위한 Redis 키 생성

        Args:
            user_id: 사용자 ID
            purpose: OTP 목적

        Returns:
            str: Redis 키
        """
        return f"otp_attempts:{purpose}:{user_id}"

    async def generate_otp(
        self,
        user_id: str,
        purpose: str = "transaction",
        metadata: Optional[Dict] = None
    ) -> Dict[str, str]:
        """
        OTP 생성 및 Redis에 저장

        Args:
            user_id: 사용자 ID
            purpose: OTP 목적 (기본값: "transaction")
            metadata: 추가 메타데이터 (예: 주문 ID, IP 주소 등)

        Returns:
            dict: {"otp_code": str, "expires_at": str, "attempts_remaining": int}
        """
        otp_code = self._generate_otp_code()
        otp_key = self._get_otp_key(user_id, purpose)
        attempt_key = self._get_attempt_key(user_id, purpose)

        # OTP 데이터 구성
        otp_data = {
            "code": otp_code,
            "created_at": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "purpose": purpose,
        }

        # 메타데이터 추가
        if metadata:
            otp_data.update(metadata)

        # Redis에 저장 (만료 시간 설정)
        import json
        await self.redis.setex(
            otp_key,
            self.otp_expiry_seconds,
            json.dumps(otp_data)
        )

        # 시도 횟수 초기화
        await self.redis.setex(
            attempt_key,
            self.otp_expiry_seconds,
            str(self.max_attempts)
        )

        expires_at = datetime.utcnow() + timedelta(seconds=self.otp_expiry_seconds)

        return {
            "otp_code": otp_code,
            "expires_at": expires_at.isoformat(),
            "attempts_remaining": self.max_attempts
        }

    async def verify_otp(
        self,
        user_id: str,
        otp_code: str,
        purpose: str = "transaction"
    ) -> Dict[str, any]:
        """
        OTP 검증

        Args:
            user_id: 사용자 ID
            otp_code: 사용자가 입력한 OTP 코드
            purpose: OTP 목적

        Returns:
            dict: {
                "valid": bool,
                "message": str,
                "attempts_remaining": int,
                "metadata": dict (검증 성공 시)
            }
        """
        otp_key = self._get_otp_key(user_id, purpose)
        attempt_key = self._get_attempt_key(user_id, purpose)

        # OTP 데이터 조회
        otp_data_str = await self.redis.get(otp_key)
        if not otp_data_str:
            return {
                "valid": False,
                "message": "OTP가 만료되었거나 존재하지 않습니다",
                "attempts_remaining": 0
            }

        # 시도 횟수 확인
        attempts_str = await self.redis.get(attempt_key)
        if not attempts_str:
            return {
                "valid": False,
                "message": "OTP가 만료되었습니다",
                "attempts_remaining": 0
            }

        attempts_remaining = int(attempts_str)
        if attempts_remaining <= 0:
            # 시도 횟수 초과 - OTP 삭제
            await self.redis.delete(otp_key)
            await self.redis.delete(attempt_key)
            return {
                "valid": False,
                "message": "최대 시도 횟수를 초과했습니다. 새로운 OTP를 요청하세요",
                "attempts_remaining": 0
            }

        # OTP 검증
        import json
        otp_data = json.loads(otp_data_str)
        stored_code = otp_data.get("code")

        if stored_code == otp_code:
            # 검증 성공 - OTP 삭제 (일회용)
            await self.redis.delete(otp_key)
            await self.redis.delete(attempt_key)

            # 메타데이터 반환
            metadata = {k: v for k, v in otp_data.items() if k not in ["code"]}

            return {
                "valid": True,
                "message": "OTP 검증 성공",
                "attempts_remaining": attempts_remaining,
                "metadata": metadata
            }
        else:
            # 검증 실패 - 시도 횟수 감소
            attempts_remaining -= 1
            if attempts_remaining > 0:
                await self.redis.setex(
                    attempt_key,
                    self.otp_expiry_seconds,
                    str(attempts_remaining)
                )
            else:
                # 시도 횟수 소진 - OTP 삭제
                await self.redis.delete(otp_key)
                await self.redis.delete(attempt_key)

            return {
                "valid": False,
                "message": f"잘못된 OTP 코드입니다",
                "attempts_remaining": attempts_remaining
            }

    async def cancel_otp(self, user_id: str, purpose: str = "transaction") -> bool:
        """
        OTP 취소 (Redis에서 삭제)

        Args:
            user_id: 사용자 ID
            purpose: OTP 목적

        Returns:
            bool: 삭제 성공 여부
        """
        otp_key = self._get_otp_key(user_id, purpose)
        attempt_key = self._get_attempt_key(user_id, purpose)

        result1 = await self.redis.delete(otp_key)
        result2 = await self.redis.delete(attempt_key)

        return result1 > 0 or result2 > 0

    async def get_otp_status(
        self,
        user_id: str,
        purpose: str = "transaction"
    ) -> Optional[Dict[str, any]]:
        """
        현재 OTP 상태 조회

        Args:
            user_id: 사용자 ID
            purpose: OTP 목적

        Returns:
            dict 또는 None: {
                "exists": bool,
                "attempts_remaining": int,
                "expires_in_seconds": int
            }
        """
        otp_key = self._get_otp_key(user_id, purpose)
        attempt_key = self._get_attempt_key(user_id, purpose)

        # OTP 존재 여부 확인
        otp_exists = await self.redis.exists(otp_key)
        if not otp_exists:
            return None

        # 시도 횟수 조회
        attempts_str = await self.redis.get(attempt_key)
        attempts_remaining = int(attempts_str) if attempts_str else 0

        # 만료 시간 조회 (TTL)
        ttl = await self.redis.ttl(otp_key)

        return {
            "exists": True,
            "attempts_remaining": attempts_remaining,
            "expires_in_seconds": ttl if ttl > 0 else 0
        }


# 전역 OTP 서비스 인스턴스 (의존성 주입용)
_otp_service_instance: Optional[OTPService] = None


async def get_otp_service(redis_client: aioredis.Redis = None) -> OTPService:
    """
    OTP 서비스 인스턴스 반환 (싱글톤 패턴)

    Args:
        redis_client: Redis 클라이언트 (선택적)

    Returns:
        OTPService: OTP 서비스 인스턴스
    """
    global _otp_service_instance

    if _otp_service_instance is None:
        if redis_client is None:
            # Redis 클라이언트 생성
            from utils.redis_client import get_redis
            redis_client = await get_redis()

        _otp_service_instance = OTPService(redis_client)

    return _otp_service_instance
