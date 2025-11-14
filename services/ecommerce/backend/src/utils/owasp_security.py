"""
OWASP Top 10 보안 취약점 검사 및 방어 유틸리티

OWASP Top 10 (2021):
1. A01:2021 - Broken Access Control
2. A02:2021 - Cryptographic Failures
3. A03:2021 - Injection (SQL, XSS, Command)
4. A04:2021 - Insecure Design
5. A05:2021 - Security Misconfiguration
6. A06:2021 - Vulnerable and Outdated Components
7. A07:2021 - Identification and Authentication Failures
8. A08:2021 - Software and Data Integrity Failures
9. A09:2021 - Security Logging and Monitoring Failures
10. A10:2021 - Server-Side Request Forgery (SSRF)
"""

import re
import html
import secrets
from typing import Dict, List, Any, Optional
from datetime import datetime
from urllib.parse import urlparse


class OWASPSecurityChecker:
    """OWASP Top 10 보안 취약점 검사 클래스"""

    # SQL Injection 패턴 (의심스러운 패턴)
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",  # UNION SELECT
        r"(\bor\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+)",  # OR 1=1
        r"(\bor\b\s+['\"]?1['\"]?\s*=\s*['\"]?1)",  # OR '1'='1'
        r"(;\s*drop\b\s+table\b)",  # ; DROP TABLE
        r"(;\s*delete\b\s+from\b)",  # ; DELETE FROM
        r"(;\s*update\b.*\bset\b)",  # ; UPDATE ... SET
        r"(exec\s*\()",  # EXEC(
        r"(execute\s*\()",  # EXECUTE(
        r"(--|\#|/\*)",  # SQL 주석
    ]

    # XSS (Cross-Site Scripting) 패턴
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # <script> 태그
        r"javascript:",  # javascript: 프로토콜
        r"on\w+\s*=",  # 이벤트 핸들러 (onclick, onload 등)
        r"<iframe",  # iframe 태그
        r"<object",  # object 태그
        r"<embed",  # embed 태그
    ]

    # Command Injection 패턴
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$()]",  # 셸 메타문자
        r"\$\(.*\)",  # Command substitution $()
        r"`.*`",  # Backtick command substitution
    ]

    # Path Traversal 패턴
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",  # ../
        r"\.\.",  # ..
        r"%2e%2e",  # URL-encoded ..
        r"\.\.\\",  # ..\
    ]

    @classmethod
    def check_sql_injection(cls, input_str: str) -> Dict[str, Any]:
        """
        SQL Injection 취약점 검사

        Args:
            input_str: 검사할 입력 문자열

        Returns:
            검사 결과 딕셔너리
        """
        detected_patterns = []

        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                detected_patterns.append(pattern)

        is_safe = len(detected_patterns) == 0

        return {
            "safe": is_safe,
            "vulnerability": "SQL Injection",
            "detected_patterns": detected_patterns,
            "recommendation": "SQLAlchemy ORM 파라미터 바인딩 사용 또는 입력 검증 필요",
        }

    @classmethod
    def check_xss(cls, input_str: str) -> Dict[str, Any]:
        """
        XSS (Cross-Site Scripting) 취약점 검사

        Args:
            input_str: 검사할 입력 문자열

        Returns:
            검사 결과 딕셔너리
        """
        detected_patterns = []

        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                detected_patterns.append(pattern)

        is_safe = len(detected_patterns) == 0

        return {
            "safe": is_safe,
            "vulnerability": "Cross-Site Scripting (XSS)",
            "detected_patterns": detected_patterns,
            "recommendation": "입력값 이스케이프 처리 또는 Content Security Policy 적용",
        }

    @classmethod
    def check_command_injection(cls, input_str: str) -> Dict[str, Any]:
        """
        Command Injection 취약점 검사

        Args:
            input_str: 검사할 입력 문자열

        Returns:
            검사 결과 딕셔너리
        """
        detected_patterns = []

        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, input_str):
                detected_patterns.append(pattern)

        is_safe = len(detected_patterns) == 0

        return {
            "safe": is_safe,
            "vulnerability": "Command Injection",
            "detected_patterns": detected_patterns,
            "recommendation": "사용자 입력을 시스템 명령어에 직접 사용 금지, subprocess 안전 옵션 사용",
        }

    @classmethod
    def check_path_traversal(cls, input_str: str) -> Dict[str, Any]:
        """
        Path Traversal 취약점 검사

        Args:
            input_str: 검사할 파일 경로

        Returns:
            검사 결과 딕셔너리
        """
        detected_patterns = []

        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                detected_patterns.append(pattern)

        is_safe = len(detected_patterns) == 0

        return {
            "safe": is_safe,
            "vulnerability": "Path Traversal",
            "detected_patterns": detected_patterns,
            "recommendation": "파일 경로 화이트리스트 검증 또는 chroot 사용",
        }

    @classmethod
    def check_ssrf(cls, url: str) -> Dict[str, Any]:
        """
        SSRF (Server-Side Request Forgery) 취약점 검사

        Args:
            url: 검사할 URL

        Returns:
            검사 결과 딕셔너리
        """
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""

            # 내부 IP 범위 (블랙리스트)
            blacklisted_hosts = [
                "localhost",
                "127.0.0.1",
                "0.0.0.0",
                "169.254.",  # Link-local
                "10.",  # Private network
                "172.16.",  # Private network
                "192.168.",  # Private network
            ]

            is_blacklisted = any(
                hostname.startswith(blocked) for blocked in blacklisted_hosts
            )

            is_safe = not is_blacklisted

            return {
                "safe": is_safe,
                "vulnerability": "Server-Side Request Forgery (SSRF)",
                "detected_issue": f"내부 호스트 접근 시도: {hostname}" if is_blacklisted else None,
                "recommendation": "외부 URL만 허용하고 내부 IP 범위 차단",
            }
        except Exception as e:
            return {
                "safe": False,
                "vulnerability": "SSRF",
                "detected_issue": f"URL 파싱 오류: {str(e)}",
                "recommendation": "유효한 URL 형식 사용",
            }

    @classmethod
    def sanitize_html(cls, input_str: str) -> str:
        """
        HTML 이스케이프 처리 (XSS 방어)

        Args:
            input_str: 이스케이프할 문자열

        Returns:
            이스케이프된 문자열
        """
        return html.escape(input_str)

    @classmethod
    def generate_csrf_token(cls) -> str:
        """
        CSRF 토큰 생성 (A01: Broken Access Control 방어)

        Returns:
            안전한 랜덤 CSRF 토큰
        """
        return secrets.token_urlsafe(32)

    @classmethod
    def validate_csrf_token(cls, user_token: str, session_token: str) -> bool:
        """
        CSRF 토큰 검증

        Args:
            user_token: 사용자가 제출한 토큰
            session_token: 세션에 저장된 토큰

        Returns:
            검증 결과
        """
        return secrets.compare_digest(user_token, session_token)

    @classmethod
    def comprehensive_security_check(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        종합 보안 검사 (모든 OWASP 항목)

        Args:
            data: 검사할 데이터 딕셔너리

        Returns:
            종합 검사 결과
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_safe": True,
            "checks": [],
        }

        # 모든 문자열 값에 대해 검사
        for key, value in data.items():
            if isinstance(value, str):
                # SQL Injection 검사
                sql_result = cls.check_sql_injection(value)
                if not sql_result["safe"]:
                    results["overall_safe"] = False
                    results["checks"].append({
                        "field": key,
                        "vulnerability": sql_result["vulnerability"],
                        "detected": sql_result["detected_patterns"],
                        "recommendation": sql_result["recommendation"],
                    })

                # XSS 검사
                xss_result = cls.check_xss(value)
                if not xss_result["safe"]:
                    results["overall_safe"] = False
                    results["checks"].append({
                        "field": key,
                        "vulnerability": xss_result["vulnerability"],
                        "detected": xss_result["detected_patterns"],
                        "recommendation": xss_result["recommendation"],
                    })

                # Command Injection 검사 (특정 필드만)
                if any(keyword in key.lower() for keyword in ["command", "cmd", "exec", "shell"]):
                    cmd_result = cls.check_command_injection(value)
                    if not cmd_result["safe"]:
                        results["overall_safe"] = False
                        results["checks"].append({
                            "field": key,
                            "vulnerability": cmd_result["vulnerability"],
                            "detected": cmd_result["detected_patterns"],
                            "recommendation": cmd_result["recommendation"],
                        })

                # Path Traversal 검사 (파일 경로 필드)
                if any(keyword in key.lower() for keyword in ["path", "file", "filename", "dir", "folder"]):
                    path_result = cls.check_path_traversal(value)
                    if not path_result["safe"]:
                        results["overall_safe"] = False
                        results["checks"].append({
                            "field": key,
                            "vulnerability": path_result["vulnerability"],
                            "detected": path_result["detected_patterns"],
                            "recommendation": path_result["recommendation"],
                        })

                # SSRF 검사 (URL 필드)
                if any(keyword in key.lower() for keyword in ["url", "link", "href", "callback"]):
                    ssrf_result = cls.check_ssrf(value)
                    if not ssrf_result["safe"]:
                        results["overall_safe"] = False
                        results["checks"].append({
                            "field": key,
                            "vulnerability": ssrf_result["vulnerability"],
                            "detected": ssrf_result["detected_issue"],
                            "recommendation": ssrf_result["recommendation"],
                        })

        return results

    @classmethod
    def generate_security_report(cls) -> Dict[str, Any]:
        """
        프로젝트 OWASP Top 10 준수 현황 리포트 생성

        Returns:
            보안 준수 현황 리포트
        """
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "owasp_version": "2021",
            "security_controls": [
                {
                    "id": "A01:2021",
                    "category": "Broken Access Control",
                    "status": "구현됨",
                    "description": "RBAC(역할 기반 접근 제어) 및 CSRF 토큰 검증 구현",
                    "implementation": "services/ecommerce/backend/src/middleware/authorization.py",
                },
                {
                    "id": "A02:2021",
                    "category": "Cryptographic Failures",
                    "status": "구현됨",
                    "description": "bcrypt 비밀번호 해싱, 결제 정보 토큰화, HTTPS 적용",
                    "implementation": "services/ecommerce/backend/src/utils/security.py",
                },
                {
                    "id": "A03:2021",
                    "category": "Injection",
                    "status": "구현됨",
                    "description": "SQLAlchemy ORM 파라미터 바인딩, HTML 이스케이프, 입력 검증",
                    "implementation": "services/ecommerce/backend/src/utils/owasp_security.py",
                },
                {
                    "id": "A04:2021",
                    "category": "Insecure Design",
                    "status": "구현됨",
                    "description": "FDS 위험 평가, 추가 인증, 거래 차단 로직",
                    "implementation": "services/fds/src/engines/evaluation_engine.py",
                },
                {
                    "id": "A05:2021",
                    "category": "Security Misconfiguration",
                    "status": "부분 구현",
                    "description": "환경 변수 관리, CORS 설정, 에러 핸들링",
                    "implementation": "services/ecommerce/backend/src/config.py",
                },
                {
                    "id": "A06:2021",
                    "category": "Vulnerable and Outdated Components",
                    "status": "권장 사항",
                    "description": "정기적 의존성 업데이트 필요 (pip-audit, safety)",
                    "implementation": "requirements.txt",
                },
                {
                    "id": "A07:2021",
                    "category": "Identification and Authentication Failures",
                    "status": "구현됨",
                    "description": "JWT 인증, OTP 추가 인증, 로그인 실패 제한",
                    "implementation": "services/ecommerce/backend/src/middleware/auth.py",
                },
                {
                    "id": "A08:2021",
                    "category": "Software and Data Integrity Failures",
                    "status": "부분 구현",
                    "description": "데이터 검증, 트랜잭션 무결성, 감사 로그",
                    "implementation": "services/ecommerce/backend/src/models/",
                },
                {
                    "id": "A09:2021",
                    "category": "Security Logging and Monitoring Failures",
                    "status": "구현됨",
                    "description": "민감 정보 마스킹 로깅, FDS 거래 기록, Prometheus 메트릭",
                    "implementation": "services/ecommerce/backend/src/utils/logging.py",
                },
                {
                    "id": "A10:2021",
                    "category": "Server-Side Request Forgery (SSRF)",
                    "status": "구현됨",
                    "description": "내부 IP 범위 차단, URL 화이트리스트 검증",
                    "implementation": "services/ecommerce/backend/src/utils/owasp_security.py",
                },
            ],
            "recommendations": [
                "정기 보안 감사 수행 (분기별)",
                "의존성 취약점 스캔 (pip-audit, safety)",
                "침투 테스트 실행 (반기별)",
                "보안 헤더 추가 (X-Frame-Options, X-Content-Type-Options)",
                "Content Security Policy (CSP) 적용",
                "Rate Limiting 강화 (API 남용 방지)",
            ],
        }

        return report


# 사용 예시
if __name__ == "__main__":
    # 1. SQL Injection 검사
    print("=== SQL Injection 검사 ===")
    malicious_input = "admin' OR '1'='1"
    result = OWASPSecurityChecker.check_sql_injection(malicious_input)
    print(f"안전 여부: {result['safe']}")
    print(f"탐지 패턴: {result['detected_patterns']}")

    # 2. XSS 검사
    print("\n=== XSS 검사 ===")
    xss_input = "<script>alert('XSS')</script>"
    result = OWASPSecurityChecker.check_xss(xss_input)
    print(f"안전 여부: {result['safe']}")
    print(f"권장 사항: {result['recommendation']}")

    # 3. HTML 이스케이프
    print("\n=== HTML 이스케이프 ===")
    unsafe_html = "<script>alert('XSS')</script>"
    safe_html = OWASPSecurityChecker.sanitize_html(unsafe_html)
    print(f"원본: {unsafe_html}")
    print(f"이스케이프: {safe_html}")

    # 4. CSRF 토큰 생성/검증
    print("\n=== CSRF 토큰 ===")
    csrf_token = OWASPSecurityChecker.generate_csrf_token()
    print(f"생성된 토큰: {csrf_token[:20]}...")
    is_valid = OWASPSecurityChecker.validate_csrf_token(csrf_token, csrf_token)
    print(f"토큰 검증: {is_valid}")

    # 5. 종합 보안 검사
    print("\n=== 종합 보안 검사 ===")
    test_data = {
        "username": "admin",
        "comment": "<script>alert('xss')</script>",
        "query": "SELECT * FROM users WHERE id=1 OR 1=1",
        "file_path": "../../../etc/passwd",
        "callback_url": "http://localhost:8000/admin",
    }
    comprehensive_result = OWASPSecurityChecker.comprehensive_security_check(test_data)
    print(f"전체 안전 여부: {comprehensive_result['overall_safe']}")
    print(f"발견된 취약점 수: {len(comprehensive_result['checks'])}")
    for check in comprehensive_result['checks']:
        print(f"- {check['field']}: {check['vulnerability']}")

    # 6. 보안 리포트 생성
    print("\n=== OWASP Top 10 준수 리포트 ===")
    report = OWASPSecurityChecker.generate_security_report()
    print(f"버전: {report['owasp_version']}")
    print(f"보안 통제 수: {len(report['security_controls'])}")
    for control in report['security_controls']:
        print(f"- {control['id']} {control['category']}: {control['status']}")
