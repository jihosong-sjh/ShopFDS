#!/usr/bin/env python3
"""
Phase 4 통합 테스트 실행 스크립트

사용자 스토리 2 - 의심 거래 시 단계적 인증 통합 검증

실행 방법:
    python tests/run_phase4_integration_tests.py

또는 pytest로 직접 실행:
    pytest services/fds/tests/integration/test_medium_risk_scenario.py -v
    pytest services/ecommerce/backend/tests/integration/test_otp_success_scenario.py -v
    pytest services/ecommerce/backend/tests/integration/test_otp_failure_scenario.py -v
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime


def print_banner(text: str):
    """배너 출력"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def run_test_suite(test_path: str, description: str) -> bool:
    """
    테스트 스위트 실행

    Args:
        test_path: 테스트 파일 경로
        description: 테스트 설명

    Returns:
        bool: 테스트 성공 여부
    """
    print_banner(f"T{description.split('T')[1].split(':')[0]}: {description.split(': ')[1]}")

    try:
        # pytest 실행
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                test_path,
                "-v",
                "-s",
                "--tb=short",
                "--color=yes",
            ],
            capture_output=True,
            text=True,
        )

        # 결과 출력
        print(result.stdout)
        if result.stderr:
            print(result.stderr)

        # 성공 여부 판단
        if result.returncode == 0:
            print(f"\n✅ {description} - 통과\n")
            return True
        else:
            print(f"\n❌ {description} - 실패\n")
            return False

    except Exception as e:
        print(f"\n❌ 테스트 실행 중 에러 발생: {str(e)}\n")
        return False


def main():
    """메인 함수"""
    print_banner("Phase 4: 사용자 스토리 2 - 의심 거래 시 단계적 인증")
    print(f"테스트 시작 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 프로젝트 루트 디렉토리
    project_root = Path(__file__).parent.parent

    # 테스트 스위트 목록
    test_suites = [
        {
            "path": str(
                project_root
                / "services/fds/tests/integration/test_medium_risk_scenario.py"
            ),
            "description": "T064: FDS에서 중간 위험도 거래 시나리오 검증 (위험 점수 40-70점)",
        },
        {
            "path": str(
                project_root
                / "services/ecommerce/backend/tests/integration/test_otp_success_scenario.py"
            ),
            "description": "T065: 추가 인증 성공 시나리오 검증 (거래 승인)",
        },
        {
            "path": str(
                project_root
                / "services/ecommerce/backend/tests/integration/test_otp_failure_scenario.py"
            ),
            "description": "T066: 추가 인증 3회 실패 시나리오 검증 (거래 차단)",
        },
    ]

    # 결과 추적
    results = []

    # 각 테스트 스위트 실행
    for suite in test_suites:
        success = run_test_suite(suite["path"], suite["description"])
        results.append(
            {
                "description": suite["description"],
                "success": success,
            }
        )

    # 최종 결과 요약
    print_banner("통합 테스트 결과 요약")

    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed

    print(f"총 테스트 스위트: {len(results)}개")
    print(f"✅ 통과: {passed}개")
    print(f"❌ 실패: {failed}개\n")

    # 상세 결과
    for i, result in enumerate(results, 1):
        status = "✅ 통과" if result["success"] else "❌ 실패"
        print(f"{i}. {result['description']}: {status}")

    print(f"\n테스트 종료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 모든 테스트가 통과했는지 확인
    if failed == 0:
        print("\n" + "🎉" * 40)
        print("\n  Phase 4 통합 검증 완료!")
        print("  사용자 스토리 2 - 의심 거래 시 단계적 인증이 정상 작동합니다.\n")
        print("🎉" * 40 + "\n")
        print("\n✅ 체크포인트 달성:")
        print("  - 사용자 스토리 1과 2가 모두 독립적으로 작동")
        print("  - 정상 거래는 그대로 진행")
        print("  - 의심 거래는 추가 인증을 거침")
        print("  - OTP 검증 성공 시 거래 완료")
        print("  - OTP 3회 실패 시 거래 차단\n")
        return 0
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다. 위 로그를 확인해주세요.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
