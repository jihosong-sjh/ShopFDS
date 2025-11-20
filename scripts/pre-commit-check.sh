#!/bin/bash
# 커밋 전 빠른 CI 체크 스크립트
# 사용법: ./scripts/pre-commit-check.sh

set -e  # 에러 발생 시 즉시 중단

echo "========================================"
echo "  Pre-Commit CI Check"
echo "========================================"

# Python 서비스 목록
SERVICES=(
  "services/ecommerce/backend"
  "services/fds"
  "services/ml-service"
  "services/admin-dashboard/backend"
)

# 전체 성공 여부 추적
ALL_PASSED=true

for SERVICE in "${SERVICES[@]}"; do
  if [ ! -d "$SERVICE/src" ]; then
    echo "[SKIP] $SERVICE (no src/ directory)"
    continue
  fi

  echo ""
  echo ">>> Checking $SERVICE"
  cd "$SERVICE"

  # 1. Black 포맷팅 적용
  echo "  [1/4] Applying Black formatting..."
  black src/ --quiet

  # 2. Ruff 자동 수정
  echo "  [2/4] Running Ruff auto-fix..."
  ruff check src/ --fix --quiet || true

  # 3. Black 검증
  echo "  [3/4] Verifying Black formatting..."
  if ! black --check src/ --quiet; then
    echo "  [FAIL] Black formatting check failed!"
    ALL_PASSED=false
  else
    echo "  [OK] Black formatting passed"
  fi

  # 4. Ruff 검증
  echo "  [4/4] Verifying Ruff linting..."
  if ! ruff check src/ --quiet; then
    echo "  [FAIL] Ruff linting check failed!"
    echo "  Run 'ruff check src/' for details"
    ALL_PASSED=false
  else
    echo "  [OK] Ruff linting passed"
  fi

  cd - > /dev/null
done

echo ""
echo "========================================"
if [ "$ALL_PASSED" = true ]; then
  echo "  [SUCCESS] All checks passed!"
  echo "  You can safely commit now."
  exit 0
else
  echo "  [FAIL] Some checks failed."
  echo "  Please fix the issues above."
  exit 1
fi
