import { test, expect } from '@playwright/test';

/**
 * 관리자 대시보드 E2E 테스트
 */
test.describe('관리자 대시보드', () => {
  // 관리자 로그인
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3001/login');
    await page.fill('input[name="email"]', 'admin@shopfds.com');
    await page.fill('input[name="password"]', 'AdminPassword123!');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('http://localhost:3001/dashboard');
  });

  test('대시보드 메인 화면 접근', async ({ page }) => {
    // 주요 위젯 확인
    await expect(page.locator('[data-testid="sales-widget"]')).toBeVisible();
    await expect(page.locator('[data-testid="orders-widget"]')).toBeVisible();
    await expect(page.locator('[data-testid="fds-alerts-widget"]')).toBeVisible();
    await expect(page.locator('[data-testid="users-widget"]')).toBeVisible();

    // 실시간 차트 확인
    await expect(page.locator('[data-testid="realtime-transactions-chart"]')).toBeVisible();
    await expect(page.locator('[data-testid="risk-distribution-chart"]')).toBeVisible();
  });

  test('FDS 알림 관리', async ({ page }) => {
    // FDS 알림 페이지로 이동
    await page.click('[data-testid="nav-fds-alerts"]');
    await expect(page).toHaveURL('http://localhost:3001/fds/alerts');

    // 알림 목록 확인
    await expect(page.locator('[data-testid="alerts-table"]')).toBeVisible();

    // High Risk 알림 필터링
    await page.selectOption('[data-testid="risk-filter"]', 'high');

    // 첫 번째 알림 상세 보기
    await page.click('[data-testid="alert-row"]').first();

    // 알림 상세 모달 확인
    await expect(page.locator('[data-testid="alert-detail-modal"]')).toBeVisible();
    await expect(page.locator('text=거래 상세 정보')).toBeVisible();
    await expect(page.locator('text=위험 요인')).toBeVisible();

    // 검토 결과 입력
    await page.selectOption('[data-testid="review-decision"]', 'fraud');
    await page.fill('[data-testid="review-notes"]', '카드 도용 의심 거래로 확인됨');
    await page.click('[data-testid="submit-review"]');

    // 검토 완료 확인
    await expect(page.locator('text=검토가 완료되었습니다')).toBeVisible();
  });

  test('탐지 룰 관리', async ({ page }) => {
    // 룰 관리 페이지로 이동
    await page.click('[data-testid="nav-rules"]');
    await expect(page).toHaveURL('http://localhost:3001/fds/rules');

    // 새 룰 생성
    await page.click('[data-testid="create-rule"]');

    // 룰 정보 입력
    await page.fill('[data-testid="rule-name"]', '야간 대량 구매 차단');
    await page.fill('[data-testid="rule-description"]', '새벽 시간대 고액 대량 구매 차단');

    // 조건 설정
    await page.selectOption('[data-testid="condition-field"]', 'transaction_time');
    await page.selectOption('[data-testid="condition-operator"]', 'between');
    await page.fill('[data-testid="condition-value-1"]', '00:00');
    await page.fill('[data-testid="condition-value-2"]', '06:00');

    // AND 조건 추가
    await page.click('[data-testid="add-condition"]');
    await page.selectOption('[data-testid="condition-field-2"]', 'amount');
    await page.selectOption('[data-testid="condition-operator-2"]', 'greater_than');
    await page.fill('[data-testid="condition-value-2"]', '1000000');

    // 액션 설정
    await page.selectOption('[data-testid="rule-action"]', 'block');
    await page.fill('[data-testid="risk-score-adjustment"]', '+50');

    // 룰 저장
    await page.click('[data-testid="save-rule"]');

    // 저장 확인
    await expect(page.locator('text=룰이 생성되었습니다')).toBeVisible();
    await expect(page.locator('text=야간 대량 구매 차단')).toBeVisible();

    // 룰 활성화/비활성화 토글
    const ruleRow = page.locator('[data-testid="rule-row"]').filter({ hasText: '야간 대량 구매 차단' });
    await ruleRow.locator('[data-testid="rule-toggle"]').click();
    await expect(page.locator('text=룰이 비활성화되었습니다')).toBeVisible();
  });

  test('A/B 테스트 설정', async ({ page }) => {
    // A/B 테스트 페이지로 이동
    await page.click('[data-testid="nav-ab-tests"]');
    await expect(page).toHaveURL('http://localhost:3001/fds/ab-tests');

    // 새 A/B 테스트 생성
    await page.click('[data-testid="create-ab-test"]');

    // 테스트 정보 입력
    await page.fill('[data-testid="test-name"]', 'ML 모델 v2.0 성능 테스트');
    await page.fill('[data-testid="test-description"]', '새로운 LightGBM 모델과 기존 모델 비교');

    // 그룹 설정
    await page.fill('[data-testid="group-a-name"]', '기존 모델 (v1.5)');
    await page.fill('[data-testid="group-b-name"]', '신규 모델 (v2.0)');
    await page.fill('[data-testid="traffic-split"]', '50'); // 50:50 분할

    // 성공 지표 설정
    await page.check('[data-testid="metric-precision"]');
    await page.check('[data-testid="metric-recall"]');
    await page.check('[data-testid="metric-evaluation-time"]');

    // 테스트 기간 설정
    await page.fill('[data-testid="test-duration"]', '7'); // 7일

    // 테스트 시작
    await page.click('[data-testid="start-test"]');

    // 시작 확인
    await expect(page.locator('text=A/B 테스트가 시작되었습니다')).toBeVisible();

    // 실시간 결과 확인
    await page.click('[data-testid="view-results"]');
    await expect(page.locator('[data-testid="ab-test-results-chart"]')).toBeVisible();
    await expect(page.locator('text=그룹 A')).toBeVisible();
    await expect(page.locator('text=그룹 B')).toBeVisible();
  });

  test('주문 관리', async ({ page }) => {
    // 주문 관리 페이지로 이동
    await page.click('[data-testid="nav-orders"]');
    await expect(page).toHaveURL('http://localhost:3001/orders');

    // 주문 목록 확인
    await expect(page.locator('[data-testid="orders-table"]')).toBeVisible();

    // 상태별 필터링
    await page.selectOption('[data-testid="status-filter"]', 'pending');

    // 첫 번째 주문 상세 보기
    const firstOrder = page.locator('[data-testid="order-row"]').first();
    await firstOrder.click();

    // 주문 상세 정보 확인
    await expect(page.locator('[data-testid="order-detail-modal"]')).toBeVisible();
    await expect(page.locator('text=주문 정보')).toBeVisible();
    await expect(page.locator('text=배송 정보')).toBeVisible();
    await expect(page.locator('text=결제 정보')).toBeVisible();
    await expect(page.locator('text=FDS 평가 결과')).toBeVisible();

    // 주문 상태 변경
    await page.selectOption('[data-testid="order-status-select"]', 'processing');
    await page.click('[data-testid="update-status"]');

    // 상태 변경 확인
    await expect(page.locator('text=주문 상태가 변경되었습니다')).toBeVisible();
  });

  test('사용자 관리', async ({ page }) => {
    // 사용자 관리 페이지로 이동
    await page.click('[data-testid="nav-users"]');
    await expect(page).toHaveURL('http://localhost:3001/users');

    // 사용자 검색
    await page.fill('[data-testid="user-search"]', 'test@example.com');
    await page.press('[data-testid="user-search"]', 'Enter');

    // 검색 결과 확인
    const userRow = page.locator('[data-testid="user-row"]').filter({ hasText: 'test@example.com' });
    await expect(userRow).toBeVisible();

    // 사용자 상세 보기
    await userRow.click();

    // 사용자 정보 확인
    await expect(page.locator('[data-testid="user-detail-modal"]')).toBeVisible();
    await expect(page.locator('text=거래 이력')).toBeVisible();
    await expect(page.locator('text=FDS 점수 이력')).toBeVisible();

    // 사용자 상태 변경
    await page.selectOption('[data-testid="user-status-select"]', 'suspended');
    await page.fill('[data-testid="status-reason"]', 'FDS 다중 차단 이력');
    await page.click('[data-testid="update-user-status"]');

    // 변경 확인
    await expect(page.locator('text=사용자 상태가 변경되었습니다')).toBeVisible();
  });

  test('보고서 생성', async ({ page }) => {
    // 보고서 페이지로 이동
    await page.click('[data-testid="nav-reports"]');
    await expect(page).toHaveURL('http://localhost:3001/reports');

    // 일일 FDS 성과 보고서 생성
    await page.selectOption('[data-testid="report-type"]', 'fds_daily');
    await page.fill('[data-testid="report-date"]', '2025-11-17');
    await page.click('[data-testid="generate-report"]');

    // 보고서 생성 중
    await expect(page.locator('text=보고서를 생성하고 있습니다...')).toBeVisible();

    // 보고서 완료 (최대 10초 대기)
    await expect(page.locator('[data-testid="report-ready"]')).toBeVisible({ timeout: 10000 });

    // 보고서 미리보기
    await page.click('[data-testid="preview-report"]');
    await expect(page.locator('[data-testid="report-preview"]')).toBeVisible();

    // 주요 지표 확인
    await expect(page.locator('text=총 거래 수')).toBeVisible();
    await expect(page.locator('text=차단된 거래')).toBeVisible();
    await expect(page.locator('text=정탐률')).toBeVisible();
    await expect(page.locator('text=평균 평가 시간')).toBeVisible();

    // PDF 다운로드
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('[data-testid="download-pdf"]')
    ]);

    // 다운로드 확인
    expect(download.suggestedFilename()).toContain('FDS_Report');
  });
});