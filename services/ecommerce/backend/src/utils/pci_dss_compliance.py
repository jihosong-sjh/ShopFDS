"""
PCI-DSS 준수 검증 유틸리티

PCI-DSS (Payment Card Industry Data Security Standard) 요구사항:
1. 카드 데이터 저장 금지 (결제 정보 토큰화 필수)
2. 민감 데이터 로그 금지
3. 전송 중 데이터 암호화 (HTTPS)
4. 저장된 데이터 암호화
5. 접근 제어 및 감사 로그
"""

import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PCIDSSCompliance:
    """PCI-DSS 준수 사항 검증 클래스"""

    # 민감 데이터 패턴 (정규식) - 데이터 전체 문자열에서만 검사
    SENSITIVE_PATTERNS = {
        "card_number": r"\b\d{13,19}\b",  # 신용카드 번호 (13-19자리)
        "card_expiry": r"\b\d{2}[/-]\d{2,4}\b",  # 만료일 (MM/YY, MM/YYYY)
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",  # 주민등록번호 형식
        "password": r"(password|passwd|pwd)\s*[=:]\s*[\S]+",  # 비밀번호
    }

    # 허용되지 않는 카드 데이터 필드
    PROHIBITED_CARD_FIELDS = [
        "card_number",
        "cvv",
        "cvc",
        "cvv2",
        "cid",
        "card_verification_value",
        "card_security_code",
        "full_track_data",
        "magnetic_stripe_data",
        "chip_data",
        "pin_block",
    ]

    @classmethod
    def validate_payment_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        결제 데이터가 PCI-DSS를 준수하는지 검증

        Args:
            data: 검증할 결제 데이터 딕셔너리

        Returns:
            검증 결과 딕셔너리
            {
                "compliant": bool,
                "violations": List[str],
                "warnings": List[str]
            }
        """
        violations = []
        warnings = []

        # 1. 금지된 카드 데이터 필드 검사
        for field in cls.PROHIBITED_CARD_FIELDS:
            if field in data:
                violations.append(f"금지된 필드 발견: '{field}' - 카드 데이터는 반드시 토큰화되어야 합니다")

        # 2. 민감 데이터 패턴 검사
        data_str = str(data)
        for pattern_name, pattern in cls.SENSITIVE_PATTERNS.items():
            matches = re.findall(pattern, data_str, re.IGNORECASE)
            if matches:
                violations.append(
                    f"민감 데이터 패턴 발견: {pattern_name} - " f"{len(matches)}개 일치 항목"
                )

        # 3. 토큰화 검증
        if "card_token" in data:
            token = data["card_token"]
            if not cls._is_valid_token(token):
                violations.append(
                    f"유효하지 않은 토큰 형식: {token[:10]}... - " "토큰은 원본 카드 번호를 포함해서는 안 됩니다"
                )
        else:
            warnings.append("card_token 필드가 없습니다 - " "결제 정보는 반드시 토큰화되어야 합니다")

        # 4. 카드 마지막 4자리 검증
        if "card_last_four" in data:
            last_four = data["card_last_four"]
            if not re.match(r"^\d{4}$", str(last_four)):
                violations.append(
                    f"card_last_four 형식 오류: {last_four} - " "정확히 4자리 숫자여야 합니다"
                )

        is_compliant = len(violations) == 0

        return {
            "compliant": is_compliant,
            "violations": violations,
            "warnings": warnings,
            "timestamp": datetime.utcnow().isoformat(),
        }

    @classmethod
    def _is_valid_token(cls, token: str) -> bool:
        """
        토큰이 유효한 형식인지 검증

        유효한 토큰 조건:
        - 길이가 16자 이상
        - 연속된 숫자 13자 이상 포함 안 함 (카드 번호 아님)
        """
        if len(token) < 16:
            return False

        # 연속된 숫자 13자 이상 포함 시 실제 카드 번호일 가능성
        if re.search(r"\d{13,}", token):
            return False

        return True

    @classmethod
    def sanitize_log_data(cls, data: Any, mask_char: str = "*") -> Any:
        """
        로그 데이터에서 민감 정보 제거/마스킹

        Args:
            data: 로그에 기록할 데이터 (dict, list, str 등)
            mask_char: 마스킹에 사용할 문자

        Returns:
            민감 정보가 제거/마스킹된 데이터
        """
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                key_lower = key.lower()

                # 민감 필드명 확인 (정확한 일치만)
                is_sensitive = False

                # 완전 일치 민감 키워드
                sensitive_keywords = [
                    "password",
                    "passwd",
                    "pwd",
                    "secret",
                    "token",
                    "cvv",
                    "cvc",
                    "pin",
                    "ssn",
                ]
                if any(
                    key_lower == s or key_lower.endswith("_" + s)
                    for s in sensitive_keywords
                ):
                    is_sensitive = True

                # 카드 관련 (안전한 필드 제외)
                if "card" in key_lower and key_lower not in [
                    "card_last_four",
                    "card_brand",
                    "card_type",
                ]:
                    is_sensitive = True

                if is_sensitive:
                    sanitized[key] = mask_char * 8  # 민감 필드는 마스킹
                else:
                    # 재귀적으로 처리
                    sanitized[key] = cls.sanitize_log_data(value, mask_char)
            return sanitized

        elif isinstance(data, list):
            return [cls.sanitize_log_data(item, mask_char) for item in data]

        elif isinstance(data, str):
            # 문자열 내 민감 패턴 마스킹 (13자리 이상 연속 숫자만)
            sanitized = data

            # 카드 번호 패턴만 마스킹 (13-19자리)
            sanitized = re.sub(r"\b\d{13,19}\b", mask_char * 12, sanitized)

            # CVV: 123 형식만 마스킹
            sanitized = re.sub(
                r"(cvv|cvc)[:\s]*\d{3,4}\b",
                lambda m: m.group(0).split(":")[0] + ": " + (mask_char * 3),
                sanitized,
                flags=re.IGNORECASE,
            )

            return sanitized

        else:
            return data

    @classmethod
    def generate_compliance_report(cls) -> Dict[str, Any]:
        """
        PCI-DSS 준수 현황 리포트 생성

        Returns:
            준수 현황 리포트
        """
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "pci_dss_version": "3.2.1",
            "compliance_checks": [
                {
                    "requirement": "1. 카드 데이터 저장 금지",
                    "status": "구현됨",
                    "description": "모든 카드 데이터는 토큰화되어 저장됩니다. "
                    "Payment 모델은 card_token만 저장하며, "
                    "실제 카드 번호는 저장하지 않습니다.",
                    "implementation": "services/ecommerce/backend/src/models/payment.py",
                },
                {
                    "requirement": "2. 민감 데이터 로그 금지",
                    "status": "구현됨",
                    "description": "로깅 미들웨어에서 자동으로 민감 정보를 마스킹합니다. "
                    "카드 번호, 비밀번호, CVV 등은 로그에 기록되지 않습니다.",
                    "implementation": "services/ecommerce/backend/src/utils/logging.py",
                },
                {
                    "requirement": "3. 전송 중 데이터 암호화 (HTTPS)",
                    "status": "구현 필요",
                    "description": "프로덕션 환경에서 HTTPS 적용 필요",
                    "implementation": "infrastructure/nginx/nginx.conf (SSL 인증서)",
                },
                {
                    "requirement": "4. 저장된 데이터 암호화",
                    "status": "부분 구현",
                    "description": "토큰화로 카드 데이터 보호. " "추가: 데이터베이스 컬럼 레벨 암호화 권장",
                    "implementation": "PostgreSQL pgcrypto 확장 사용 권장",
                },
                {
                    "requirement": "5. 접근 제어",
                    "status": "구현됨",
                    "description": "RBAC(역할 기반 접근 제어) 구현. " "관리자만 민감 데이터 접근 가능",
                    "implementation": "services/ecommerce/backend/src/middleware/authorization.py",
                },
                {
                    "requirement": "6. 감사 로그",
                    "status": "구현됨",
                    "description": "모든 결제 거래는 Transaction 테이블에 기록되며, "
                    "사용자 행동은 UserBehaviorLog에 저장됩니다.",
                    "implementation": "services/fds/src/models/transaction.py",
                },
            ],
            "recommendations": [
                "프로덕션 환경에서 HTTPS 적용 (Let's Encrypt 인증서)",
                "PostgreSQL pgcrypto 확장으로 데이터베이스 암호화 강화",
                "정기 보안 감사 (분기별)",
                "침투 테스트 수행 (반기별)",
                "PCI-DSS QSA(Qualified Security Assessor) 인증 획득",
            ],
        }

        return report


class SecureLogger:
    """PCI-DSS 준수 로거 래퍼"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def info(self, message: str, extra: Optional[Dict] = None):
        """민감 정보를 마스킹한 후 INFO 로그 기록"""
        sanitized_extra = PCIDSSCompliance.sanitize_log_data(extra) if extra else None
        self.logger.info(message, extra=sanitized_extra)

    def error(self, message: str, extra: Optional[Dict] = None):
        """민감 정보를 마스킹한 후 ERROR 로그 기록"""
        sanitized_extra = PCIDSSCompliance.sanitize_log_data(extra) if extra else None
        self.logger.error(message, extra=sanitized_extra)

    def warning(self, message: str, extra: Optional[Dict] = None):
        """민감 정보를 마스킹한 후 WARNING 로그 기록"""
        sanitized_extra = PCIDSSCompliance.sanitize_log_data(extra) if extra else None
        self.logger.warning(message, extra=sanitized_extra)

    def debug(self, message: str, extra: Optional[Dict] = None):
        """민감 정보를 마스킹한 후 DEBUG 로그 기록"""
        sanitized_extra = PCIDSSCompliance.sanitize_log_data(extra) if extra else None
        self.logger.debug(message, extra=sanitized_extra)


# 사용 예시
if __name__ == "__main__":
    # 1. 결제 데이터 검증
    payment_data_bad = {
        "card_number": "4111111111111111",  # 금지!
        "cvv": "123",  # 금지!
        "card_expiry": "12/25",
    }

    payment_data_good = {
        "card_token": "tok_1A2B3C4D5E6F7G8H9I0J",  # 토큰화됨 - 허용
        "card_last_four": "1111",
        "card_brand": "VISA",
    }

    print("=== PCI-DSS 검증: 나쁜 예시 ===")
    result_bad = PCIDSSCompliance.validate_payment_data(payment_data_bad)
    print(f"준수 여부: {result_bad['compliant']}")
    print(f"위반 사항: {result_bad['violations']}")

    print("\n=== PCI-DSS 검증: 좋은 예시 ===")
    result_good = PCIDSSCompliance.validate_payment_data(payment_data_good)
    print(f"준수 여부: {result_good['compliant']}")
    print(f"경고 사항: {result_good['warnings']}")

    # 2. 로그 데이터 마스킹
    print("\n=== 로그 데이터 마스킹 ===")
    sensitive_log = {
        "user_id": "123",
        "card_token": "tok_sensitive",
        "password": "secret123",
        "order_amount": 50000,
    }
    sanitized = PCIDSSCompliance.sanitize_log_data(sensitive_log)
    print(f"원본: {sensitive_log}")
    print(f"마스킹: {sanitized}")

    # 3. 준수 리포트 생성
    print("\n=== PCI-DSS 준수 리포트 ===")
    report = PCIDSSCompliance.generate_compliance_report()
    print(f"버전: {report['pci_dss_version']}")
    print(f"검사 항목 수: {len(report['compliance_checks'])}")
    for check in report["compliance_checks"]:
        print(f"- {check['requirement']}: {check['status']}")
