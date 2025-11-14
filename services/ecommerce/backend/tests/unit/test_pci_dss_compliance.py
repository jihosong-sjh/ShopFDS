"""
PCI-DSS 준수 검증 유틸리티 유닛 테스트
"""

import pytest
from src.utils.pci_dss_compliance import PCIDSSCompliance, SecureLogger
import logging


class TestPCIDSSCompliance:
    """PCIDSSCompliance 클래스 테스트"""

    def test_validate_payment_data_with_prohibited_fields(self):
        """금지된 카드 데이터 필드 검증"""
        # 실제 카드 번호 포함 (금지!)
        payment_data = {
            "card_number": "4111111111111111",
            "cvv": "123",
            "card_expiry": "12/25",
        }

        result = PCIDSSCompliance.validate_payment_data(payment_data)

        assert result["compliant"] is False
        assert len(result["violations"]) >= 2  # card_number, cvv 금지
        assert any("card_number" in v for v in result["violations"])
        assert any("cvv" in v.lower() for v in result["violations"])

    def test_validate_payment_data_with_tokenized_data(self):
        """토큰화된 결제 데이터 검증 (정상)"""
        payment_data = {
            "card_token": "tok_1A2B3C4D5E6F7G8H9I0J",
            "card_last_four": "1111",
            "card_brand": "VISA",
            "amount": 50000,
        }

        result = PCIDSSCompliance.validate_payment_data(payment_data)

        assert result["compliant"] is True
        assert len(result["violations"]) == 0

    def test_validate_payment_data_with_invalid_token(self):
        """유효하지 않은 토큰 형식 검증"""
        # 토큰에 실제 카드 번호가 포함된 경우
        payment_data = {
            "card_token": "4111111111111111",  # 실제 카드 번호처럼 보임
            "card_last_four": "1111",
        }

        result = PCIDSSCompliance.validate_payment_data(payment_data)

        assert result["compliant"] is False
        assert any("유효하지 않은 토큰" in v for v in result["violations"])

    def test_validate_payment_data_with_sensitive_patterns(self):
        """민감 데이터 패턴 탐지"""
        payment_data = {
            "card_token": "tok_valid",
            "notes": "Customer card: 4111111111111111, CVV: 123",  # 주석에 카드 정보
        }

        result = PCIDSSCompliance.validate_payment_data(payment_data)

        assert result["compliant"] is False
        assert any("민감 데이터 패턴" in v for v in result["violations"])

    def test_validate_payment_data_with_invalid_last_four(self):
        """card_last_four 형식 오류 검증"""
        payment_data = {
            "card_token": "tok_valid",
            "card_last_four": "11",  # 4자리가 아님
        }

        result = PCIDSSCompliance.validate_payment_data(payment_data)

        assert result["compliant"] is False
        assert any("card_last_four" in v for v in result["violations"])

    def test_is_valid_token(self):
        """토큰 유효성 검증 로직"""
        # 유효한 토큰
        assert PCIDSSCompliance._is_valid_token("tok_1A2B3C4D5E6F7G8H9I0J") is True
        assert PCIDSSCompliance._is_valid_token("stripe_token_abcdef123456") is True

        # 유효하지 않은 토큰
        assert PCIDSSCompliance._is_valid_token("short") is False  # 너무 짧음
        assert PCIDSSCompliance._is_valid_token("4111111111111111") is False  # 카드 번호


class TestSanitizeLogData:
    """로그 데이터 마스킹 테스트"""

    def test_sanitize_dict_with_sensitive_keys(self):
        """딕셔너리의 민감 키 마스킹"""
        data = {
            "user_id": "123",
            "password": "secret123",
            "card_token": "tok_sensitive",
            "order_amount": 50000,
        }

        sanitized = PCIDSSCompliance.sanitize_log_data(data)

        assert sanitized["user_id"] == "123"  # 안전한 필드는 그대로
        assert sanitized["order_amount"] == 50000
        assert sanitized["password"] == "********"  # 민감 필드는 마스킹
        assert sanitized["card_token"] == "********"

    def test_sanitize_nested_dict(self):
        """중첩 딕셔너리 마스킹"""
        data = {
            "user": {
                "id": "123",
                "password": "secret",
            },
            "payment": {
                "card_token": "tok_123",
                "amount": 100,
            },
        }

        sanitized = PCIDSSCompliance.sanitize_log_data(data)

        assert sanitized["user"]["id"] == "123"
        assert sanitized["user"]["password"] == "********"
        assert sanitized["payment"]["card_token"] == "********"
        assert sanitized["payment"]["amount"] == 100

    def test_sanitize_list(self):
        """리스트 마스킹"""
        data = [
            {"password": "secret1"},
            {"password": "secret2"},
            {"amount": 100},
        ]

        sanitized = PCIDSSCompliance.sanitize_log_data(data)

        assert sanitized[0]["password"] == "********"
        assert sanitized[1]["password"] == "********"
        assert sanitized[2]["amount"] == 100

    def test_sanitize_string_with_patterns(self):
        """문자열 내 민감 패턴 마스킹"""
        text = "User paid with card 4111111111111111, CVV: 123"
        sanitized = PCIDSSCompliance.sanitize_log_data(text)

        assert "4111111111111111" not in sanitized
        assert "123" not in sanitized
        assert "************" in sanitized  # 마스킹된 부분

    def test_sanitize_safe_fields(self):
        """안전한 필드는 마스킹하지 않음"""
        data = {
            "card_last_four": "1111",
            "card_brand": "VISA",
            "user_id": "123",
        }

        sanitized = PCIDSSCompliance.sanitize_log_data(data)

        assert sanitized["card_last_four"] == "1111"
        assert sanitized["card_brand"] == "VISA"
        assert sanitized["user_id"] == "123"


class TestSecureLogger:
    """SecureLogger 클래스 테스트"""

    def test_secure_logger_info(self, caplog):
        """INFO 로그 민감 정보 마스킹"""
        logger = logging.getLogger("test_logger")
        secure_logger = SecureLogger(logger)

        with caplog.at_level(logging.INFO):
            secure_logger.info(
                "Payment processed",
                extra={"card_token": "tok_secret", "amount": 100}
            )

        # 핵심: 민감 정보가 로그에 없는지만 확인
        assert "tok_secret" not in caplog.text
        assert "Payment processed" in caplog.text

    def test_secure_logger_error(self, caplog):
        """ERROR 로그 민감 정보 마스킹"""
        logger = logging.getLogger("test_logger_error")
        secure_logger = SecureLogger(logger)

        with caplog.at_level(logging.ERROR):
            secure_logger.error(
                "Payment failed",
                extra={"password": "secret123", "user_id": "456"}
            )

        # 핵심: 민감 정보가 로그에 없는지만 확인
        assert "secret123" not in caplog.text
        assert "Payment failed" in caplog.text


class TestComplianceReport:
    """PCI-DSS 준수 리포트 테스트"""

    def test_generate_compliance_report(self):
        """준수 리포트 생성"""
        report = PCIDSSCompliance.generate_compliance_report()

        assert "timestamp" in report
        assert report["pci_dss_version"] == "3.2.1"
        assert len(report["compliance_checks"]) >= 6
        assert "recommendations" in report

        # 모든 체크 항목에 필수 필드가 있는지 확인
        for check in report["compliance_checks"]:
            assert "requirement" in check
            assert "status" in check
            assert "description" in check
            assert "implementation" in check

    def test_report_includes_all_requirements(self):
        """리포트가 모든 주요 요구사항을 포함하는지 확인"""
        report = PCIDSSCompliance.generate_compliance_report()
        requirements = [check["requirement"] for check in report["compliance_checks"]]

        # 주요 요구사항 확인
        assert any("카드 데이터 저장" in req for req in requirements)
        assert any("민감 데이터 로그" in req for req in requirements)
        assert any("HTTPS" in req or "암호화" in req for req in requirements)
        assert any("접근 제어" in req for req in requirements)


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_payment_data(self):
        """빈 결제 데이터"""
        result = PCIDSSCompliance.validate_payment_data({})

        assert result["compliant"] is True  # 위반 사항 없음
        assert len(result["warnings"]) > 0  # 경고는 있음 (card_token 없음)

    def test_sanitize_none_value(self):
        """None 값 처리"""
        sanitized = PCIDSSCompliance.sanitize_log_data(None)
        assert sanitized is None

    def test_sanitize_number(self):
        """숫자 처리"""
        sanitized = PCIDSSCompliance.sanitize_log_data(12345)
        assert sanitized == 12345

    def test_sanitize_boolean(self):
        """불리언 처리"""
        sanitized = PCIDSSCompliance.sanitize_log_data(True)
        assert sanitized is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
