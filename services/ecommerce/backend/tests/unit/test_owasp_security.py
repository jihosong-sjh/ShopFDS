"""
OWASP Top 10 보안 검사 유틸리티 유닛 테스트
"""

import pytest
from src.utils.owasp_security import OWASPSecurityChecker


class TestSQLInjectionCheck:
    """SQL Injection 검사 테스트"""

    def test_detect_union_select(self):
        """UNION SELECT 공격 패턴 탐지"""
        malicious = "admin' UNION SELECT * FROM users--"
        result = OWASPSecurityChecker.check_sql_injection(malicious)

        assert result["safe"] is False
        assert result["vulnerability"] == "SQL Injection"
        assert len(result["detected_patterns"]) > 0

    def test_detect_or_equals(self):
        """OR 1=1 공격 패턴 탐지"""
        malicious = "admin' OR '1'='1"
        result = OWASPSecurityChecker.check_sql_injection(malicious)

        assert result["safe"] is False

    def test_detect_drop_table(self):
        """DROP TABLE 공격 패턴 탐지"""
        malicious = "'; DROP TABLE users;--"
        result = OWASPSecurityChecker.check_sql_injection(malicious)

        assert result["safe"] is False

    def test_safe_input(self):
        """안전한 입력 통과"""
        safe = "홍길동"
        result = OWASPSecurityChecker.check_sql_injection(safe)

        assert result["safe"] is True
        assert len(result["detected_patterns"]) == 0


class TestXSSCheck:
    """XSS (Cross-Site Scripting) 검사 테스트"""

    def test_detect_script_tag(self):
        """<script> 태그 탐지"""
        malicious = "<script>alert('XSS')</script>"
        result = OWASPSecurityChecker.check_xss(malicious)

        assert result["safe"] is False
        assert result["vulnerability"] == "Cross-Site Scripting (XSS)"

    def test_detect_javascript_protocol(self):
        """javascript: 프로토콜 탐지"""
        malicious = "<a href='javascript:alert(1)'>클릭</a>"
        result = OWASPSecurityChecker.check_xss(malicious)

        assert result["safe"] is False

    def test_detect_event_handler(self):
        """이벤트 핸들러 탐지"""
        malicious = "<img src=x onerror='alert(1)'>"
        result = OWASPSecurityChecker.check_xss(malicious)

        assert result["safe"] is False

    def test_detect_iframe(self):
        """iframe 태그 탐지"""
        malicious = "<iframe src='http://evil.com'></iframe>"
        result = OWASPSecurityChecker.check_xss(malicious)

        assert result["safe"] is False

    def test_safe_html(self):
        """안전한 HTML 통과"""
        safe = "안녕하세요, <strong>반갑습니다</strong>"
        result = OWASPSecurityChecker.check_xss(safe)

        # <strong>은 허용될 수 있지만 이벤트 핸들러는 없어야 함
        assert result["safe"] is True


class TestCommandInjectionCheck:
    """Command Injection 검사 테스트"""

    def test_detect_semicolon(self):
        """세미콜론을 이용한 명령어 체인 탐지"""
        malicious = "file.txt; rm -rf /"
        result = OWASPSecurityChecker.check_command_injection(malicious)

        assert result["safe"] is False

    def test_detect_pipe(self):
        """파이프를 이용한 명령어 체인 탐지"""
        malicious = "file.txt | cat /etc/passwd"
        result = OWASPSecurityChecker.check_command_injection(malicious)

        assert result["safe"] is False

    def test_detect_command_substitution(self):
        """커맨드 치환 탐지"""
        malicious = "$(whoami)"
        result = OWASPSecurityChecker.check_command_injection(malicious)

        assert result["safe"] is False

    def test_safe_filename(self):
        """안전한 파일명 통과"""
        safe = "report_2025.pdf"
        result = OWASPSecurityChecker.check_command_injection(safe)

        assert result["safe"] is True


class TestPathTraversalCheck:
    """Path Traversal 검사 테스트"""

    def test_detect_dot_dot_slash(self):
        """../ 패턴 탐지"""
        malicious = "../../../etc/passwd"
        result = OWASPSecurityChecker.check_path_traversal(malicious)

        assert result["safe"] is False

    def test_detect_url_encoded(self):
        """URL 인코딩된 .. 탐지"""
        malicious = "%2e%2e/etc/passwd"
        result = OWASPSecurityChecker.check_path_traversal(malicious)

        assert result["safe"] is False

    def test_safe_path(self):
        """안전한 경로 통과"""
        safe = "/uploads/images/photo.jpg"
        result = OWASPSecurityChecker.check_path_traversal(safe)

        assert result["safe"] is True


class TestSSRFCheck:
    """SSRF (Server-Side Request Forgery) 검사 테스트"""

    def test_detect_localhost(self):
        """localhost 접근 탐지"""
        malicious = "http://localhost:8000/admin"
        result = OWASPSecurityChecker.check_ssrf(malicious)

        assert result["safe"] is False
        assert result["vulnerability"] == "Server-Side Request Forgery (SSRF)"

    def test_detect_127_0_0_1(self):
        """127.0.0.1 접근 탐지"""
        malicious = "http://127.0.0.1:6379/keys"
        result = OWASPSecurityChecker.check_ssrf(malicious)

        assert result["safe"] is False

    def test_detect_private_network(self):
        """사설 네트워크 접근 탐지"""
        malicious = "http://192.168.1.1/admin"
        result = OWASPSecurityChecker.check_ssrf(malicious)

        assert result["safe"] is False

    def test_safe_external_url(self):
        """안전한 외부 URL 통과"""
        safe = "https://api.example.com/data"
        result = OWASPSecurityChecker.check_ssrf(safe)

        assert result["safe"] is True


class TestSanitization:
    """입력 정제 테스트"""

    def test_sanitize_html(self):
        """HTML 이스케이프 처리"""
        unsafe = "<script>alert('XSS')</script>"
        safe = OWASPSecurityChecker.sanitize_html(unsafe)

        assert "<script>" not in safe
        assert "&lt;script&gt;" in safe
        assert "alert" in safe  # 텍스트는 유지

    def test_sanitize_quotes(self):
        """따옴표 이스케이프 처리"""
        unsafe = "It's a <b>test</b>"
        safe = OWASPSecurityChecker.sanitize_html(unsafe)

        assert "&lt;b&gt;" in safe
        assert "It&#x27;s" in safe or "It's" in safe  # 둘 다 가능


class TestCSRFToken:
    """CSRF 토큰 생성 및 검증 테스트"""

    def test_generate_csrf_token(self):
        """CSRF 토큰 생성"""
        token = OWASPSecurityChecker.generate_csrf_token()

        assert len(token) > 20  # 충분한 길이
        assert isinstance(token, str)

    def test_validate_matching_tokens(self):
        """동일한 토큰 검증 (정상)"""
        token = OWASPSecurityChecker.generate_csrf_token()
        is_valid = OWASPSecurityChecker.validate_csrf_token(token, token)

        assert is_valid is True

    def test_validate_different_tokens(self):
        """다른 토큰 검증 (실패)"""
        token1 = OWASPSecurityChecker.generate_csrf_token()
        token2 = OWASPSecurityChecker.generate_csrf_token()
        is_valid = OWASPSecurityChecker.validate_csrf_token(token1, token2)

        assert is_valid is False


class TestComprehensiveCheck:
    """종합 보안 검사 테스트"""

    def test_comprehensive_check_safe_data(self):
        """안전한 데이터 종합 검사"""
        safe_data = {
            "username": "홍길동",
            "email": "hong@example.com",
            "age": "30",
        }

        result = OWASPSecurityChecker.comprehensive_security_check(safe_data)

        assert result["overall_safe"] is True
        assert len(result["checks"]) == 0

    def test_comprehensive_check_sql_injection(self):
        """SQL Injection이 포함된 데이터 검사"""
        malicious_data = {
            "username": "admin' OR '1'='1",
            "email": "test@example.com",
        }

        result = OWASPSecurityChecker.comprehensive_security_check(malicious_data)

        assert result["overall_safe"] is False
        assert len(result["checks"]) > 0
        assert any("SQL Injection" in check["vulnerability"] for check in result["checks"])

    def test_comprehensive_check_xss(self):
        """XSS가 포함된 데이터 검사"""
        malicious_data = {
            "comment": "<script>alert('XSS')</script>",
            "username": "test",
        }

        result = OWASPSecurityChecker.comprehensive_security_check(malicious_data)

        assert result["overall_safe"] is False
        assert any("XSS" in check["vulnerability"] for check in result["checks"])

    def test_comprehensive_check_path_traversal(self):
        """Path Traversal이 포함된 데이터 검사"""
        malicious_data = {
            "file_path": "../../../etc/passwd",
            "username": "test",
        }

        result = OWASPSecurityChecker.comprehensive_security_check(malicious_data)

        assert result["overall_safe"] is False
        assert any("Path Traversal" in check["vulnerability"] for check in result["checks"])

    def test_comprehensive_check_ssrf(self):
        """SSRF가 포함된 데이터 검사"""
        malicious_data = {
            "callback_url": "http://localhost:8000/admin",
            "username": "test",
        }

        result = OWASPSecurityChecker.comprehensive_security_check(malicious_data)

        assert result["overall_safe"] is False
        assert any("SSRF" in check["vulnerability"] for check in result["checks"])


class TestSecurityReport:
    """보안 리포트 생성 테스트"""

    def test_generate_security_report(self):
        """보안 리포트 생성"""
        report = OWASPSecurityChecker.generate_security_report()

        assert "timestamp" in report
        assert report["owasp_version"] == "2021"
        assert len(report["security_controls"]) == 10  # OWASP Top 10

    def test_report_includes_all_categories(self):
        """리포트가 모든 OWASP Top 10 카테고리를 포함하는지 확인"""
        report = OWASPSecurityChecker.generate_security_report()
        categories = [control["category"] for control in report["security_controls"]]

        # 주요 카테고리 확인
        assert "Broken Access Control" in categories
        assert "Injection" in categories
        assert "Cryptographic Failures" in categories
        assert "Server-Side Request Forgery (SSRF)" in categories

    def test_report_has_recommendations(self):
        """리포트에 권장 사항이 포함되어 있는지 확인"""
        report = OWASPSecurityChecker.generate_security_report()

        assert "recommendations" in report
        assert len(report["recommendations"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
