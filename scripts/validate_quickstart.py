#!/usr/bin/env python3
"""
ShopFDS Quickstart Validation Script
T144: quickstart.md 가이드 전체 실행 검증

이 스크립트는 quickstart.md에 명시된 모든 요구사항과 절차를 자동으로 검증합니다.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class QuickstartValidator:
    """quickstart.md 가이드 검증 클래스"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = []
        self.start_time = None
        self.end_time = None

    def log(self, message: str, level: str = "INFO"):
        """로그 출력"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        self.results.append({
            "timestamp": timestamp,
            "level": level,
            "message": message
        })

    def check_command(self, command: str, expected_output: str = None) -> bool:
        """명령어 실행 및 확인"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self.log(f"[OK] 명령어 성공: {command}", "SUCCESS")
                if expected_output and expected_output not in result.stdout:
                    self.log(f"  경고: 예상 출력을 찾을 수 없음 - {expected_output}", "WARNING")
                return True
            else:
                self.log(f"[FAIL] 명령어 실패: {command}", "ERROR")
                self.log(f"  에러: {result.stderr}", "ERROR")
                return False

        except subprocess.TimeoutExpired:
            self.log(f"[FAIL] 명령어 타임아웃: {command}", "ERROR")
            return False
        except Exception as e:
            self.log(f"[FAIL] 명령어 실행 오류: {command} - {str(e)}", "ERROR")
            return False

    def check_file_exists(self, file_path: str) -> bool:
        """파일 존재 확인"""
        path = self.project_root / file_path
        if path.exists():
            self.log(f"[OK] 파일 존재: {file_path}", "SUCCESS")
            return True
        else:
            self.log(f"[FAIL] 파일 없음: {file_path}", "ERROR")
            return False

    def check_port(self, port: int, service_name: str) -> bool:
        """포트 사용 확인"""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()

        if result == 0:
            self.log(f"[OK] 포트 {port} 사용 중 ({service_name})", "SUCCESS")
            return True
        else:
            self.log(f"[FAIL] 포트 {port} 사용하지 않음 ({service_name})", "ERROR")
            return False

    def check_api_health(self, url: str, service_name: str) -> bool:
        """API 헬스체크"""
        try:
            import urllib.request
            import urllib.error

            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status in [200, 404]:  # 404는 엔드포인트가 없어도 서버는 응답
                    self.log(f"[OK] API 응답 정상: {service_name} ({url})", "SUCCESS")
                    return True
                else:
                    self.log(f"[FAIL] API 응답 비정상: {service_name} - 상태 {response.status}", "ERROR")
                    return False
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            self.log(f"[FAIL] API 접근 실패: {service_name} ({url}) - {str(e)}", "ERROR")
            return False
        except Exception as e:
            self.log(f"[FAIL] API 접근 실패: {service_name} ({url}) - {str(e)}", "ERROR")
            return False

    def validate_prerequisites(self) -> Dict[str, bool]:
        """1. 사전 요구사항 검증"""
        self.log("=" * 60)
        self.log("1. 사전 요구사항 검증 시작")
        self.log("=" * 60)

        results = {}

        # Python 버전 확인
        results["python"] = self.check_command(
            "python --version",
            "Python 3.11"
        )

        # Node.js 버전 확인
        results["nodejs"] = self.check_command(
            "node --version",
            "v18"
        )

        # PostgreSQL 확인
        results["postgresql"] = self.check_command(
            "psql --version",
            "psql"
        )

        # Redis 확인
        results["redis"] = self.check_command(
            "redis-cli --version",
            "redis"
        )

        # Docker 확인
        results["docker"] = self.check_command(
            "docker --version",
            "Docker version"
        )

        # Docker Compose 확인
        results["docker_compose"] = self.check_command(
            "docker-compose --version",
            "Docker Compose"
        )

        return results

    def validate_project_structure(self) -> Dict[str, bool]:
        """2. 프로젝트 구조 검증"""
        self.log("=" * 60)
        self.log("2. 프로젝트 구조 검증 시작")
        self.log("=" * 60)

        results = {}

        # 주요 디렉토리 확인
        directories = [
            "services/ecommerce/backend",
            "services/ecommerce/frontend",
            "services/fds",
            "services/ml-service",
            "services/admin-dashboard",
            "infrastructure/docker",
            "infrastructure/k8s",
            "infrastructure/nginx",
            "specs/001-ecommerce-fds-platform"
        ]

        for directory in directories:
            results[directory] = self.check_file_exists(directory)

        # 주요 파일 확인
        files = [
            "docker-compose.yml",
            "services/ecommerce/backend/requirements.txt",
            "services/ecommerce/frontend/package.json",
            "services/fds/requirements.txt",
            "infrastructure/nginx/nginx.conf",
            "specs/001-ecommerce-fds-platform/spec.md"
        ]

        for file in files:
            results[file] = self.check_file_exists(file)

        return results

    def validate_database_setup(self) -> Dict[str, bool]:
        """3. 데이터베이스 설정 검증"""
        self.log("=" * 60)
        self.log("3. 데이터베이스 설정 검증 시작")
        self.log("=" * 60)

        results = {}

        # PostgreSQL 연결 테스트
        results["postgres_connection"] = self.check_command(
            'docker exec shopfds_postgres psql -U postgres -c "SELECT version();" 2>/dev/null',
            "PostgreSQL"
        )

        # 데이터베이스 존재 확인
        if results["postgres_connection"]:
            results["ecommerce_db"] = self.check_command(
                'docker exec shopfds_postgres psql -U postgres -c "\\l" 2>/dev/null | grep ecommerce_db',
                "ecommerce_db"
            )

            results["fds_db"] = self.check_command(
                'docker exec shopfds_postgres psql -U postgres -c "\\l" 2>/dev/null | grep fds_db',
                "fds_db"
            )

        # Redis 연결 테스트
        results["redis_connection"] = self.check_command(
            'docker exec shopfds_redis redis-cli ping 2>/dev/null',
            "PONG"
        )

        return results

    def validate_services(self) -> Dict[str, bool]:
        """4. 서비스 실행 검증"""
        self.log("=" * 60)
        self.log("4. 서비스 실행 검증 시작")
        self.log("=" * 60)

        results = {}

        # 포트 확인
        services_ports = [
            (8000, "ecommerce-backend"),
            (8001, "fds"),
            (8002, "ml-service"),
            (8003, "admin-dashboard"),
            (3000, "ecommerce-frontend"),
            (3001, "admin-frontend"),
            (80, "nginx"),
            (5432, "postgresql"),
            (6379, "redis")
        ]

        for port, service in services_ports:
            results[f"{service}_port"] = self.check_port(port, service)

        # API 헬스체크
        api_endpoints = [
            ("http://localhost:8000/health", "ecommerce-backend"),
            ("http://localhost:8001/health", "fds"),
            ("http://localhost:8002/health", "ml-service"),
            ("http://localhost:8003/health", "admin-dashboard"),
            ("http://localhost:3000", "ecommerce-frontend"),
            ("http://localhost:3001", "admin-frontend"),
            ("http://localhost/api/v1/health", "nginx-gateway")
        ]

        for url, service in api_endpoints:
            results[f"{service}_health"] = self.check_api_health(url, service)

        return results

    def validate_api_tests(self) -> Dict[str, bool]:
        """5. API 테스트 검증"""
        self.log("=" * 60)
        self.log("5. API 테스트 검증 시작")
        self.log("=" * 60)

        results = {}

        # 테스트 실행 - 각 서비스
        test_commands = [
            ("cd services/ecommerce/backend && python -m pytest tests/unit -v --tb=short",
             "ecommerce_unit_tests"),
            ("cd services/fds && python -m pytest tests/unit -v --tb=short",
             "fds_unit_tests"),
            ("cd services/ml-service && python -m pytest tests/unit -v --tb=short",
             "ml_unit_tests"),
            ("cd services/admin-dashboard/backend && python -m pytest tests/unit -v --tb=short",
             "admin_unit_tests")
        ]

        for command, test_name in test_commands:
            results[test_name] = self.check_command(command)

        return results

    def validate_development_workflow(self) -> Dict[str, bool]:
        """6. 개발 워크플로우 검증"""
        self.log("=" * 60)
        self.log("6. 개발 워크플로우 검증 시작")
        self.log("=" * 60)

        results = {}

        # 코드 스타일 검사
        style_commands = [
            ("cd services/ecommerce/backend && black --check src/",
             "ecommerce_black_check"),
            ("cd services/ecommerce/backend && ruff check src/",
             "ecommerce_ruff_check"),
            ("cd services/fds && black --check src/",
             "fds_black_check"),
            ("cd services/fds && ruff check src/",
             "fds_ruff_check")
        ]

        for command, check_name in style_commands:
            results[check_name] = self.check_command(command)

        # Git hooks 확인
        results["pre_commit_hook"] = self.check_file_exists(".git/hooks/pre-commit")

        return results

    def generate_report(self):
        """검증 결과 리포트 생성"""
        self.log("=" * 60)
        self.log("검증 결과 요약")
        self.log("=" * 60)

        # 결과 집계
        total_checks = len(self.results)
        success_count = sum(1 for r in self.results if r["level"] == "SUCCESS")
        error_count = sum(1 for r in self.results if r["level"] == "ERROR")
        warning_count = sum(1 for r in self.results if r["level"] == "WARNING")

        # 성공률 계산
        success_rate = (success_count / total_checks * 100) if total_checks > 0 else 0

        # 실행 시간 계산
        execution_time = (self.end_time - self.start_time).total_seconds()

        # 리포트 출력
        self.log(f"총 검사 항목: {total_checks}")
        self.log(f"성공: {success_count} ({success_rate:.1f}%)")
        self.log(f"실패: {error_count}")
        self.log(f"경고: {warning_count}")
        self.log(f"실행 시간: {execution_time:.2f}초")

        # 상세 리포트 파일 생성
        report = {
            "execution_time": execution_time,
            "total_checks": total_checks,
            "success_count": success_count,
            "error_count": error_count,
            "warning_count": warning_count,
            "success_rate": success_rate,
            "details": self.results
        }

        report_path = self.project_root / "validation_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.log(f"상세 리포트 저장: {report_path}")

        # 검증 성공 여부 반환
        return error_count == 0

    def run(self):
        """전체 검증 실행"""
        self.start_time = datetime.now()

        self.log("=" * 60)
        self.log("ShopFDS Quickstart 가이드 검증 시작")
        self.log("=" * 60)

        all_results = {}

        # 1. 사전 요구사항 검증
        all_results["prerequisites"] = self.validate_prerequisites()

        # 2. 프로젝트 구조 검증
        all_results["project_structure"] = self.validate_project_structure()

        # 3. 데이터베이스 설정 검증
        all_results["database"] = self.validate_database_setup()

        # 4. 서비스 실행 검증
        all_results["services"] = self.validate_services()

        # 5. API 테스트 검증
        all_results["api_tests"] = self.validate_api_tests()

        # 6. 개발 워크플로우 검증
        all_results["workflow"] = self.validate_development_workflow()

        self.end_time = datetime.now()

        # 리포트 생성
        success = self.generate_report()

        if success:
            self.log("[SUCCESS] Quickstart 가이드 검증 완료 - 모든 검사 통과!", "SUCCESS")
        else:
            self.log("[ERROR] Quickstart 가이드 검증 실패 - 일부 검사 실패", "ERROR")

        return success


def main():
    """메인 함수"""
    validator = QuickstartValidator()
    success = validator.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()