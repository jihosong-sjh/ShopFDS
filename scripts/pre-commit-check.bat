@echo off
REM 커밋 전 빠른 CI 체크 스크립트 (Windows)
REM 사용법: scripts\pre-commit-check.bat

echo ========================================
echo   Pre-Commit CI Check
echo ========================================

set ALL_PASSED=1

REM Python 서비스 목록
set SERVICES=ecommerce/backend fds ml-service admin-dashboard/backend

for %%S in (%SERVICES%) do (
  if not exist "services\%%S\src" (
    echo [SKIP] services/%%S (no src/ directory)
  ) else (
    echo.
    echo ^>^>^> Checking services/%%S
    cd services\%%S

    REM 1. Black 포맷팅 적용
    echo   [1/4] Applying Black formatting...
    black src\ --quiet

    REM 2. Ruff 자동 수정
    echo   [2/4] Running Ruff auto-fix...
    ruff check src\ --fix --quiet 2>nul

    REM 3. Black 검증
    echo   [3/4] Verifying Black formatting...
    black --check src\ --quiet
    if errorlevel 1 (
      echo   [FAIL] Black formatting check failed!
      set ALL_PASSED=0
    ) else (
      echo   [OK] Black formatting passed
    )

    REM 4. Ruff 검증
    echo   [4/4] Verifying Ruff linting...
    ruff check src\ --quiet
    if errorlevel 1 (
      echo   [FAIL] Ruff linting check failed!
      echo   Run 'ruff check src\' for details
      set ALL_PASSED=0
    ) else (
      echo   [OK] Ruff linting passed
    )

    cd ..\..
  )
)

echo.
echo ========================================
if %ALL_PASSED%==1 (
  echo   [SUCCESS] All checks passed!
  echo   You can safely commit now.
  exit /b 0
) else (
  echo   [FAIL] Some checks failed.
  echo   Please fix the issues above.
  exit /b 1
)
