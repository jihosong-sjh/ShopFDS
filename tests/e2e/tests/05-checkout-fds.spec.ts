import { test, expect } from '@playwright/test';

/**
 * 결제 및 FDS 검증 E2E 테스트
 */
test.describe('결제 및 FDS 검증', () => {
  // 테스트 전 로그인 및 장바구니 준비
  test.beforeEach(async ({ page }) => {
    // 로그인
    await page.goto('/login');
    await page.fill('input[name="email"]', 'testuser@example.com');
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.click('button[type="submit"]');

    // 장바구니에 상품 추가
    await page.goto('/products');
    await page.locator('[data-testid="product-card"]').first().click();
    await page.click('[data-testid="add-to-cart-button"]');
  });

  test('정상 거래 - Low Risk 결제 성공', async ({ page }) => {
    // 장바구니에서 결제 진행
    await page.goto('/cart');
    await page.click('[data-testid="proceed-to-checkout"]');

    // 배송 정보 입력
    await page.fill('[data-testid="shipping-name"]', '홍길동');
    await page.fill('[data-testid="shipping-address"]', '서울특별시 강남구 테헤란로 123');
    await page.fill('[data-testid="shipping-phone"]', '010-1234-5678');
    await page.fill('[data-testid="shipping-zipcode"]', '06234');

    // 결제 수단 선택
    await page.click('[data-testid="payment-method-card"]');

    // 카드 정보 입력 (테스트용 카드 번호)
    await page.fill('[data-testid="card-number"]', '4111111111111111'); // Visa 테스트 카드
    await page.fill('[data-testid="card-expiry"]', '12/25');
    await page.fill('[data-testid="card-cvv"]', '123');
    await page.fill('[data-testid="card-holder"]', '홍길동');

    // 주문 확인
    await page.click('[data-testid="place-order"]');

    // FDS 평가 진행 중 표시
    await expect(page.locator('text=거래 보안 검증 중...')).toBeVisible();

    // Low Risk - 바로 성공
    await expect(page).toHaveURL('/order/success', { timeout: 10000 });
    await expect(page.locator('text=주문이 완료되었습니다')).toBeVisible();

    // 주문 번호 확인
    const orderNumber = await page.locator('[data-testid="order-number"]').textContent();
    expect(orderNumber).toBeTruthy();
  });

  test('Medium Risk - OTP 인증 필요', async ({ page }) => {
    // 높은 금액 상품 추가 (Medium Risk 트리거)
    await page.goto('/products?category=electronics');
    await page.locator('[data-testid="product-card"]').first().click();
    await page.fill('[data-testid="quantity-input"]', '5'); // 대량 구매
    await page.click('[data-testid="add-to-cart-button"]');

    // 결제 진행
    await page.goto('/cart');
    await page.click('[data-testid="proceed-to-checkout"]');

    // 배송 정보 입력
    await page.fill('[data-testid="shipping-name"]', '김철수');
    await page.fill('[data-testid="shipping-address"]', '부산광역시 해운대구 해운대로 999');
    await page.fill('[data-testid="shipping-phone"]', '010-9999-9999');
    await page.fill('[data-testid="shipping-zipcode"]', '48000');

    // 카드 정보 입력
    await page.click('[data-testid="payment-method-card"]');
    await page.fill('[data-testid="card-number"]', '5555555555554444'); // Mastercard 테스트
    await page.fill('[data-testid="card-expiry"]', '06/26');
    await page.fill('[data-testid="card-cvv"]', '456');
    await page.fill('[data-testid="card-holder"]', '김철수');

    // 주문 확인
    await page.click('[data-testid="place-order"]');

    // FDS 평가 - Medium Risk 감지
    await expect(page.locator('text=추가 인증이 필요합니다')).toBeVisible({ timeout: 10000 });

    // OTP 입력 화면 표시
    await expect(page.locator('[data-testid="otp-modal"]')).toBeVisible();
    await expect(page.locator('text=휴대폰으로 인증번호를 전송했습니다')).toBeVisible();

    // OTP 입력 (테스트용 OTP)
    await page.fill('[data-testid="otp-input"]', '123456');
    await page.click('[data-testid="verify-otp"]');

    // OTP 검증 성공 후 주문 완료
    await expect(page).toHaveURL('/order/success', { timeout: 10000 });
    await expect(page.locator('text=주문이 완료되었습니다')).toBeVisible();
  });

  test('High Risk - 거래 차단', async ({ page }) => {
    // 의심스러운 거래 패턴 생성
    // 1. VPN/프록시 IP 시뮬레이션 (헤더 설정)
    await page.setExtraHTTPHeaders({
      'X-Forwarded-For': '192.0.2.1', // 의심스러운 IP
      'X-Real-IP': '192.0.2.1'
    });

    // 2. 대량 주문 시도
    await page.goto('/products?category=electronics');

    // 여러 고가 상품 추가
    for (let i = 0; i < 3; i++) {
      await page.locator('[data-testid="product-card"]').nth(i).click();
      await page.fill('[data-testid="quantity-input"]', '10');
      await page.click('[data-testid="add-to-cart-button"]');
      await page.goto('/products?category=electronics');
    }

    // 결제 진행
    await page.goto('/cart');
    await page.click('[data-testid="proceed-to-checkout"]');

    // 배송 정보 입력 (의심스러운 패턴)
    await page.fill('[data-testid="shipping-name"]', 'XXX');
    await page.fill('[data-testid="shipping-address"]', '123 Unknown St');
    await page.fill('[data-testid="shipping-phone"]', '000-0000-0000');
    await page.fill('[data-testid="shipping-zipcode"]', '00000');

    // 카드 정보 입력
    await page.click('[data-testid="payment-method-card"]');
    await page.fill('[data-testid="card-number"]', '4000000000000002'); // 거절될 카드
    await page.fill('[data-testid="card-expiry"]', '01/24');
    await page.fill('[data-testid="card-cvv"]', '999');
    await page.fill('[data-testid="card-holder"]', 'STOLEN CARD');

    // 주문 시도
    await page.click('[data-testid="place-order"]');

    // FDS 평가 - High Risk 감지
    await expect(page.locator('text=거래가 차단되었습니다')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="transaction-blocked-modal"]')).toBeVisible();

    // 차단 사유 확인
    await expect(page.locator('text=보안상의 이유로 거래를 진행할 수 없습니다')).toBeVisible();
    await expect(page.locator('text=고객센터에 문의해주세요')).toBeVisible();

    // 주문 실패 확인
    await page.click('[data-testid="close-modal"]');
    await expect(page).toHaveURL('/cart'); // 장바구니로 돌아감
  });

  test('FDS 평가 시간 측정', async ({ page }) => {
    await page.goto('/cart');
    await page.click('[data-testid="proceed-to-checkout"]');

    // 배송 정보 입력
    await page.fill('[data-testid="shipping-name"]', '정상고객');
    await page.fill('[data-testid="shipping-address"]', '서울특별시 종로구 세종대로 100');
    await page.fill('[data-testid="shipping-phone"]', '010-5555-5555');
    await page.fill('[data-testid="shipping-zipcode"]', '03172');

    // 카드 정보 입력
    await page.click('[data-testid="payment-method-card"]');
    await page.fill('[data-testid="card-number"]', '4111111111111111');
    await page.fill('[data-testid="card-expiry"]', '12/25');
    await page.fill('[data-testid="card-cvv"]', '123');
    await page.fill('[data-testid="card-holder"]', '정상고객');

    // 주문 시작 시간 기록
    const startTime = Date.now();

    // 주문 확인
    await page.click('[data-testid="place-order"]');

    // FDS 평가 완료 대기
    await page.waitForURL(/order\/(success|failed|otp)/, { timeout: 5000 });

    // 평가 시간 계산
    const evaluationTime = Date.now() - startTime;

    // FDS 평가가 100ms 이내에 완료되어야 함
    expect(evaluationTime).toBeLessThan(1000); // 네트워크 지연 포함 1초 이내

    // 개발자 콘솔에서 실제 FDS 평가 시간 확인 (있는 경우)
    const fdsTime = await page.locator('[data-testid="fds-evaluation-time"]').textContent();
    if (fdsTime) {
      const actualTime = parseInt(fdsTime);
      expect(actualTime).toBeLessThan(100); // 실제 FDS 평가는 100ms 이내
    }
  });

  test('결제 실패 후 재시도', async ({ page }) => {
    await page.goto('/cart');
    await page.click('[data-testid="proceed-to-checkout"]');

    // 배송 정보 입력
    await page.fill('[data-testid="shipping-name"]', '재시도고객');
    await page.fill('[data-testid="shipping-address"]', '서울특별시 강남구 역삼동 123');
    await page.fill('[data-testid="shipping-phone"]', '010-7777-7777');
    await page.fill('[data-testid="shipping-zipcode"]', '06234');

    // 첫 번째 시도 - 잘못된 카드 정보
    await page.click('[data-testid="payment-method-card"]');
    await page.fill('[data-testid="card-number"]', '4000000000000002'); // 거절될 카드
    await page.fill('[data-testid="card-expiry"]', '01/24');
    await page.fill('[data-testid="card-cvv"]', '999');
    await page.fill('[data-testid="card-holder"]', '재시도고객');

    await page.click('[data-testid="place-order"]');

    // 결제 실패
    await expect(page.locator('text=결제에 실패했습니다')).toBeVisible({ timeout: 10000 });

    // 다시 시도
    await page.click('[data-testid="retry-payment"]');

    // 올바른 카드 정보 입력
    await page.fill('[data-testid="card-number"]', '4111111111111111');
    await page.fill('[data-testid="card-expiry"]', '12/25');
    await page.fill('[data-testid="card-cvv"]', '123');

    await page.click('[data-testid="place-order"]');

    // 두 번째 시도 성공
    await expect(page).toHaveURL('/order/success', { timeout: 10000 });
    await expect(page.locator('text=주문이 완료되었습니다')).toBeVisible();
  });
});