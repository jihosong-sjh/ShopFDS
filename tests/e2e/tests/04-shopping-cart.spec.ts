import { test, expect } from '@playwright/test';

/**
 * 장바구니 기능 E2E 테스트
 */
test.describe('장바구니 기능', () => {
  // 테스트 전 로그인
  test.beforeEach(async ({ page }) => {
    // 로그인
    await page.goto('/login');
    await page.fill('input[name="email"]', 'testuser@example.com');
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/');
  });

  test('상품을 장바구니에 추가', async ({ page }) => {
    // 상품 목록으로 이동
    await page.goto('/products');

    // 첫 번째 상품 선택
    const firstProduct = page.locator('[data-testid="product-card"]').first();
    const productName = await firstProduct.locator('[data-testid="product-name"]').textContent();
    await firstProduct.click();

    // 상품 상세 페이지에서 장바구니 추가
    await page.fill('[data-testid="quantity-input"]', '2');
    await page.click('[data-testid="add-to-cart-button"]');

    // 성공 메시지 확인
    await expect(page.locator('text=장바구니에 추가되었습니다')).toBeVisible();

    // 장바구니 아이콘의 수량 업데이트 확인
    await expect(page.locator('[data-testid="cart-count"]')).toContainText('2');

    // 장바구니 페이지로 이동
    await page.click('[data-testid="cart-icon"]');
    await expect(page).toHaveURL('/cart');

    // 추가한 상품 확인
    await expect(page.locator(`text=${productName}`)).toBeVisible();
    await expect(page.locator('[data-testid="cart-item-quantity"]').first()).toHaveValue('2');
  });

  test('장바구니에서 수량 변경', async ({ page }) => {
    // 장바구니에 상품 추가 (준비)
    await page.goto('/products');
    await page.locator('[data-testid="product-card"]').first().click();
    await page.click('[data-testid="add-to-cart-button"]');

    // 장바구니로 이동
    await page.goto('/cart');

    // 수량 증가
    const quantityInput = page.locator('[data-testid="cart-item-quantity"]').first();
    await quantityInput.fill('3');
    await page.click('[data-testid="update-quantity"]');

    // 업데이트 확인
    await expect(page.locator('text=장바구니가 업데이트되었습니다')).toBeVisible();
    await expect(quantityInput).toHaveValue('3');

    // 총 금액 업데이트 확인
    const totalPrice = await page.locator('[data-testid="cart-total"]').textContent();
    expect(totalPrice).toBeTruthy();
  });

  test('장바구니에서 상품 제거', async ({ page }) => {
    // 장바구니에 상품 추가
    await page.goto('/products');
    await page.locator('[data-testid="product-card"]').first().click();
    await page.click('[data-testid="add-to-cart-button"]');

    // 장바구니로 이동
    await page.goto('/cart');

    // 상품 개수 확인
    const itemCount = await page.locator('[data-testid="cart-item"]').count();
    expect(itemCount).toBeGreaterThan(0);

    // 첫 번째 상품 제거
    await page.click('[data-testid="remove-item"]');

    // 확인 다이얼로그에서 확인
    await page.click('text=제거');

    // 제거 확인
    await expect(page.locator('text=상품이 제거되었습니다')).toBeVisible();

    // 장바구니가 비었는지 또는 상품 수가 감소했는지 확인
    const newItemCount = await page.locator('[data-testid="cart-item"]').count();
    expect(newItemCount).toBe(itemCount - 1);
  });

  test('장바구니 비우기', async ({ page }) => {
    // 여러 상품 추가
    await page.goto('/products');

    for (let i = 0; i < 3; i++) {
      await page.locator('[data-testid="product-card"]').nth(i).click();
      await page.click('[data-testid="add-to-cart-button"]');
      await page.goto('/products');
    }

    // 장바구니로 이동
    await page.goto('/cart');

    // 장바구니 비우기
    await page.click('[data-testid="clear-cart"]');
    await page.click('text=확인'); // 확인 다이얼로그

    // 빈 장바구니 메시지 확인
    await expect(page.locator('text=장바구니가 비어있습니다')).toBeVisible();
    await expect(page.locator('[data-testid="cart-item"]')).toHaveCount(0);
  });

  test('장바구니 저장 및 복원', async ({ page, context }) => {
    // 장바구니에 상품 추가
    await page.goto('/products');
    await page.locator('[data-testid="product-card"]').first().click();
    await page.click('[data-testid="add-to-cart-button"]');

    // 로그아웃
    await page.click('text=로그아웃');

    // 다시 로그인
    await page.goto('/login');
    await page.fill('input[name="email"]', 'testuser@example.com');
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.click('button[type="submit"]');

    // 장바구니 확인
    await page.goto('/cart');

    // 이전에 추가한 상품이 있는지 확인
    await expect(page.locator('[data-testid="cart-item"]')).toHaveCount(1);
  });

  test('재고 부족 상품 처리', async ({ page }) => {
    // 재고가 제한된 상품 페이지로 이동 (예: product ID 999)
    await page.goto('/products/999');

    // 재고보다 많은 수량 입력
    await page.fill('[data-testid="quantity-input"]', '1000');
    await page.click('[data-testid="add-to-cart-button"]');

    // 에러 메시지 확인
    await expect(page.locator('text=재고가 부족합니다')).toBeVisible();
  });
});