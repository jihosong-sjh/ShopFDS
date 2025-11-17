#!/usr/bin/env python3
"""
ShopFDS 최종 검증 통합 스크립트
T144-T146의 모든 검증을 순차적으로 실행합니다.
"""

import os
import sys
import subprocess
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


class FinalValidator:
    """최종 검증 통합 실행 클래스"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.scripts_dir = self.project_root / "scripts"
        self.e2e_dir = self.project_root / "tests" / "e2e"
        self.results = {}
        self.start_time = None
        self.end_time = None

    def log(self, message: str, level: str = "INFO"):
        """로그 출력"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def run_command(self, command: str, cwd: Path = None) -> Tuple[bool, str]:
        """명령어 실행"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5분 타임아웃
            )

            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr

        except subprocess.TimeoutExpired:
            return False, "Command timed out after 5 minutes"
        except Exception as e:
            return False, str(e)

    def validate_prerequisites(self) -> bool:
        """사전 요구사항 확인"""
        self.log("=" * 60)
        self.log("사전 요구사항 확인")
        self.log("=" * 60)

        requirements = [
            ("Docker", "docker --version"),
            ("Docker Compose", "docker-compose --version"),
            ("Python", "python --version"),
            ("Node.js", "node --version"),
            ("npm", "npm --version"),
        ]

        all_passed = True

        for name, command in requirements:
            success, output = self.run_command(command)
            if success:
                self.log(f"[OK] {name}: {output.strip()[:50]}", "SUCCESS")
            else:
                self.log(f"[FAIL] {name}: 설치되지 않음", "ERROR")
                all_passed = False

        return all_passed

    def start_services(self) -> bool:
        """Docker Compose로 서비스 시작"""
        self.log("=" * 60)
        self.log("서비스 시작")
        self.log("=" * 60)

        # Docker Compose 실행
        self.log("Docker Compose로 서비스 시작 중...")
        success, output = self.run_command("docker-compose up -d")

        if not success:
            self.log(f"Docker Compose 실행 실패: {output}", "ERROR")
            return False

        self.log("서비스 시작 완료", "SUCCESS")

        # 서비스 준비 대기
        self.log("서비스가 준비될 때까지 대기 중... (30초)")
        import time
        time.sleep(30)

        # 헬스체크
        health_checks = [
            ("PostgreSQL", "docker exec shopfds_postgres pg_isready -U postgres"),
            ("Redis", "docker exec shopfds_redis redis-cli ping"),
            ("Ecommerce Backend", "curl -s http://localhost:8000/health"),
            ("FDS Service", "curl -s http://localhost:8001/health"),
        ]

        all_healthy = True

        for service, command in health_checks:
            success, output = self.run_command(command)
            if success:
                self.log(f"[OK] {service}: 정상", "SUCCESS")
            else:
                self.log(f"[FAIL] {service}: 응답 없음", "ERROR")
                all_healthy = False

        return all_healthy

    async def run_t144_quickstart_validation(self) -> Dict:
        """T144: quickstart.md 가이드 검증"""
        self.log("=" * 60)
        self.log("T144: quickstart.md 가이드 검증")
        self.log("=" * 60)

        script_path = self.scripts_dir / "validate_quickstart.py"

        if not script_path.exists():
            self.log(f"검증 스크립트를 찾을 수 없습니다: {script_path}", "ERROR")
            return {"success": False, "message": "Script not found"}

        # 스크립트 실행
        self.log("quickstart.md 검증 스크립트 실행 중...")
        success, output = self.run_command(f"python {script_path}")

        # 결과 파싱
        report_path = self.project_root / "validation_report.json"
        if report_path.exists():
            with open(report_path, "r", encoding="utf-8") as f:
                report = json.load(f)

            self.log(f"검증 완료: 성공률 {report.get('success_rate', 0):.1f}%")

            return {
                "success": report.get("error_count", 1) == 0,
                "total_checks": report.get("total_checks", 0),
                "success_count": report.get("success_count", 0),
                "error_count": report.get("error_count", 0),
                "success_rate": report.get("success_rate", 0)
            }
        else:
            return {"success": success, "output": output}

    async def run_t145_e2e_tests(self) -> Dict:
        """T145: E2E 테스트 실행"""
        self.log("=" * 60)
        self.log("T145: E2E 테스트 (Playwright)")
        self.log("=" * 60)

        # Playwright 설치 확인
        self.log("Playwright 설치 확인 중...")
        success, _ = self.run_command("npm list @playwright/test", cwd=self.e2e_dir)

        if not success:
            self.log("Playwright 설치 중...")
            success, output = self.run_command("npm install", cwd=self.e2e_dir)
            if not success:
                self.log(f"npm install 실패: {output}", "ERROR")
                return {"success": False, "message": "npm install failed"}

            # Playwright 브라우저 설치
            success, output = self.run_command("npx playwright install", cwd=self.e2e_dir)
            if not success:
                self.log(f"Playwright 브라우저 설치 실패: {output}", "ERROR")
                return {"success": False, "message": "Playwright install failed"}

        # E2E 테스트 실행
        self.log("E2E 테스트 실행 중...")
        success, output = self.run_command(
            "npx playwright test --reporter=json",
            cwd=self.e2e_dir
        )

        # 결과 파싱
        results_path = self.e2e_dir / "test-results" / "results.json"
        if results_path.exists():
            with open(results_path, "r", encoding="utf-8") as f:
                results = json.load(f)

            total_tests = len(results.get("tests", []))
            passed_tests = sum(1 for t in results.get("tests", []) if t.get("status") == "passed")
            failed_tests = sum(1 for t in results.get("tests", []) if t.get("status") == "failed")

            self.log(f"E2E 테스트 완료: {passed_tests}/{total_tests} 통과")

            return {
                "success": failed_tests == 0,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests
            }
        else:
            # JSON 리포터가 없는 경우 출력에서 파싱
            passed = "passed" in output.lower()
            return {
                "success": passed and success,
                "output": output
            }

    async def run_t146_performance_benchmark(self) -> Dict:
        """T146: 성능 벤치마크 실행"""
        self.log("=" * 60)
        self.log("T146: 성능 목표 검증 (FDS 100ms, API 200ms, 1000 TPS)")
        self.log("=" * 60)

        script_path = self.scripts_dir / "performance_benchmark.py"

        if not script_path.exists():
            self.log(f"성능 벤치마크 스크립트를 찾을 수 없습니다: {script_path}", "ERROR")
            return {"success": False, "message": "Script not found"}

        # 스크립트 실행
        self.log("성능 벤치마크 실행 중... (약 2-3분 소요)")
        success, output = self.run_command(f"python {script_path}")

        # 결과 파싱
        report_path = self.project_root / "performance_report.json"
        if report_path.exists():
            with open(report_path, "r", encoding="utf-8") as f:
                report = json.load(f)

            # 성능 목표 달성 여부 확인
            fds_passed = all(r.get("target_met", False) for r in report.get("fds", []))
            api_passed = all(r.get("target_met", False) for r in report.get("ecommerce", []))
            throughput_passed = report.get("throughput", {}).get("target_met", False)

            all_passed = fds_passed and api_passed and throughput_passed

            self.log(f"FDS 목표 달성: {'[OK]' if fds_passed else '[FAIL]'}")
            self.log(f"API 목표 달성: {'[OK]' if api_passed else '[FAIL]'}")
            self.log(f"처리량 목표 달성: {'[OK]' if throughput_passed else '[FAIL]'}")

            return {
                "success": all_passed,
                "fds_passed": fds_passed,
                "api_passed": api_passed,
                "throughput_passed": throughput_passed,
                "actual_tps": report.get("throughput", {}).get("actual_tps", 0)
            }
        else:
            return {"success": success, "output": output}

    def generate_final_report(self):
        """최종 검증 리포트 생성"""
        self.log("=" * 60)
        self.log("최종 검증 결과 요약")
        self.log("=" * 60)

        all_passed = True

        # T144 결과
        t144 = self.results.get("t144", {})
        if t144.get("success"):
            self.log("[SUCCESS] T144: quickstart.md 가이드 검증 - 통과", "SUCCESS")
            self.log(f"   - 검사 항목: {t144.get('total_checks', 0)}개")
            self.log(f"   - 성공률: {t144.get('success_rate', 0):.1f}%")
        else:
            self.log("[ERROR] T144: quickstart.md 가이드 검증 - 실패", "ERROR")
            all_passed = False

        # T145 결과
        t145 = self.results.get("t145", {})
        if t145.get("success"):
            self.log("[SUCCESS] T145: E2E 테스트 - 통과", "SUCCESS")
            self.log(f"   - 총 테스트: {t145.get('total_tests', 0)}개")
            self.log(f"   - 통과: {t145.get('passed_tests', 0)}개")
        else:
            self.log("[ERROR] T145: E2E 테스트 - 실패", "ERROR")
            self.log(f"   - 실패: {t145.get('failed_tests', 0)}개")
            all_passed = False

        # T146 결과
        t146 = self.results.get("t146", {})
        if t146.get("success"):
            self.log("[SUCCESS] T146: 성능 목표 검증 - 통과", "SUCCESS")
            self.log(f"   - FDS 100ms 이내: {'[OK]' if t146.get('fds_passed') else '[FAIL]'}")
            self.log(f"   - API 200ms 이내: {'[OK]' if t146.get('api_passed') else '[FAIL]'}")
            self.log(f"   - 1000 TPS 달성: {'[OK]' if t146.get('throughput_passed') else '[FAIL]'}")
            self.log(f"   - 실제 TPS: {t146.get('actual_tps', 0):.1f}")
        else:
            self.log("[ERROR] T146: 성능 목표 검증 - 실패", "ERROR")
            all_passed = False

        # 실행 시간
        execution_time = (self.end_time - self.start_time).total_seconds()
        self.log(f"\n총 실행 시간: {execution_time:.2f}초")

        # 최종 판정
        self.log("\n" + "=" * 60)
        if all_passed:
            self.log("[COMPLETE] ShopFDS 플랫폼 최종 검증 완료!", "SUCCESS")
            self.log("   모든 검증 항목을 통과했습니다.")
            self.log("   프로덕션 배포 준비가 완료되었습니다.")
        else:
            self.log("[WARNING] ShopFDS 플랫폼 최종 검증 미완료", "WARNING")
            self.log("   일부 검증 항목이 실패했습니다.")
            self.log("   문제를 해결한 후 재검증이 필요합니다.")

        # 최종 리포트 저장
        final_report = {
            "timestamp": datetime.now().isoformat(),
            "execution_time": execution_time,
            "all_passed": all_passed,
            "results": self.results
        }

        report_path = self.project_root / "final_validation_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)

        self.log(f"\n최종 검증 리포트 저장: {report_path}")

        return all_passed

    async def run(self):
        """최종 검증 실행"""
        self.start_time = datetime.now()

        self.log("=" * 60)
        self.log("ShopFDS 최종 검증 시작")
        self.log(f"시작 시간: {self.start_time}")
        self.log("=" * 60)

        # 1. 사전 요구사항 확인
        if not self.validate_prerequisites():
            self.log("사전 요구사항이 충족되지 않았습니다.", "ERROR")
            return False

        # 2. 서비스 시작
        if not self.start_services():
            self.log("서비스 시작에 실패했습니다.", "ERROR")
            return False

        # 3. T144 실행
        self.log("\n[1/3] T144 실행 중...")
        self.results["t144"] = await self.run_t144_quickstart_validation()

        # 4. T145 실행
        self.log("\n[2/3] T145 실행 중...")
        self.results["t145"] = await self.run_t145_e2e_tests()

        # 5. T146 실행
        self.log("\n[3/3] T146 실행 중...")
        self.results["t146"] = await self.run_t146_performance_benchmark()

        self.end_time = datetime.now()

        # 6. 최종 리포트 생성
        return self.generate_final_report()

    def cleanup(self):
        """정리 작업"""
        self.log("\n정리 작업 중...")
        # Docker Compose 중지 (선택적)
        # self.run_command("docker-compose down")
        self.log("정리 완료")


async def main():
    """메인 함수"""
    validator = FinalValidator()

    try:
        success = await validator.run()
        return 0 if success else 1

    except KeyboardInterrupt:
        validator.log("\n검증 중단됨", "WARNING")
        return 1

    except Exception as e:
        validator.log(f"예상치 못한 오류: {str(e)}", "ERROR")
        return 1

    finally:
        validator.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)