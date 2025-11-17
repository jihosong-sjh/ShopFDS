import { test, expect } from '@playwright/test';

/**
 * 상품 탐색 플로우 E2E 테스트
 */
test.describe('상품 탐색', () => {
  test('상품 목록 페이지 접속', async ({ page }) => {
    await page.goto('/products');

    // 상품 목록 로딩 확인
    await expect(page.locator('[data-testid="product-grid"]')).toBeVisible();

    // 상품 카드가 최소 1개 이상 표시되는지 확인
    const productCards = page.locator('[data-testid="product-card"]');
    await expect(productCards).toHaveCount(await productCards.count());
    expect(await productCards.count()).toBeGreaterThan(0);

    // 필터 및 정렬 옵션 확인
    await expect(page.locator('[data-testid="category-filter"]')).toBeVisible();
    await expect(page.locator('[data-testid="price-filter"]')).toBeVisible();
    await expect(page.locator('[data-testid="sort-dropdown"]')).toBeVisible();
  });

  test('카테고리별 필터링', async ({ page }) => {
    await page.goto('/products');

    // 전자제품 카테고리 선택
    await page.click('[data-testid="category-electronics"]');

    // URL 파라미터 확인
    await expect(page).toHaveURL(/category=electronics/);

    // 필터링된 결과 확인
    const productCards = page.locator('[data-testid="product-card"]');
    const firstProduct = productCards.first();
    await expect(firstProduct.locator('[data-testid="product-category"]')).toContainText('전자제품');
  });

  test('가격 범위 필터링', async ({ page }) => {
    await page.goto('/products');

    // 가격 범위 설정 (10만원 ~ 50만원)
    await page.fill('[data-testid="price-min"]', '100000');
    await page.fill('[data-testid="price-max"]', '500000');
    await page.click('[data-testid="apply-price-filter"]');

    // 필터 적용 확인
    await expect(page).toHaveURL(/price_min=100000/);
    await expect(page).toHaveURL(/price_max=500000/);

    // 첫 번째 상품의 가격이 범위 내인지 확인
    const firstPrice = await page.locator('[data-testid="product-price"]').first().textContent();
    const priceValue = parseInt(firstPrice?.replace(/[^0-9]/g, '') || '0');
    expect(priceValue).toBeGreaterThanOrEqual(100000);
    expect(priceValue).toBeLessThanOrEqual(500000);
  });

  test('상품 정렬 기능', async ({ page }) => {
    await page.goto('/products');

    // 가격 낮은 순 정렬
    await page.selectOption('[data-testid="sort-dropdown"]', 'price_asc');

    // URL 파라미터 확인
    await expect(page).toHaveURL(/sort=price_asc/);

    // 가격 순서 확인 (첫 두 상품)
    const prices = await page.locator('[data-testid="product-price"]').evaluateAll(
      elements => elements.slice(0, 2).map(el => parseInt(el.textContent?.replace(/[^0-9]/g, '') || '0'))
    );
    expect(prices[0]).toBeLessThanOrEqual(prices[1]);

    // 가격 높은 순 정렬
    await page.selectOption('[data-testid="sort-dropdown"]', 'price_desc');
    await expect(page).toHaveURL(/sort=price_desc/);

    const pricesDesc = await page.locator('[data-testid="product-price"]').evaluateAll(
      elements => elements.slice(0, 2).map(el => parseInt(el.textContent?.replace(/[^0-9]/g, '') || '0'))
    );
    expect(pricesDesc[0]).toBeGreaterThanOrEqual(pricesDesc[1]);
  });

  test('상품 상세 페이지 이동', async ({ page }) => {
    await page.goto('/products');

    // 첫 번째 상품 클릭
    const firstProduct = page.locator('[data-testid="product-card"]').first();
    const productName = await firstProduct.locator('[data-testid="product-name"]').textContent();
    await firstProduct.click();

    // 상세 페이지로 이동 확인
    await expect(page).toHaveURL(/\/products\/\d+/);

    // 상품 정보 표시 확인
    await expect(page.locator('h1')).toContainText(productName || '');
    await expect(page.locator('[data-testid="product-description"]')).toBeVisible();
    await expect(page.locator('[data-testid="product-price-detail"]')).toBeVisible();
    await expect(page.locator('[data-testid="add-to-cart-button"]')).toBeVisible();
  });

  test('상품 검색 기능', async ({ page }) => {
    await page.goto('/');

    // 검색어 입력
    await page.fill('[data-testid="search-input"]', '노트북');
    await page.press('[data-testid="search-input"]', 'Enter');

    // 검색 결과 페이지로 이동
    await expect(page).toHaveURL(/search\?q=노트북/);

    // 검색 결과 확인
    await expect(page.locator('text=검색 결과: 노트북')).toBeVisible();

    // 검색 결과에 검색어가 포함된 상품이 있는지 확인
    const searchResults = page.locator('[data-testid="product-card"]');
    const count = await searchResults.count();

    if (count > 0) {
      const firstResult = searchResults.first();
      const productText = await firstResult.textContent();
      expect(productText?.toLowerCase()).toContain('노트북');
    }
  });

  test('페이지네이션', async ({ page }) => {
    await page.goto('/products');

    // 페이지네이션 컨트롤 확인
    await expect(page.locator('[data-testid="pagination"]')).toBeVisible();

    // 2페이지로 이동
    await page.click('[data-testid="page-2"]');
    await expect(page).toHaveURL(/page=2/);

    // 이전/다음 버튼 테스트
    await page.click('[data-testid="next-page"]');
    await expect(page).toHaveURL(/page=3/);

    await page.click('[data-testid="prev-page"]');
    await expect(page).toHaveURL(/page=2/);
  });
});