import { test, expect } from '@playwright/test';

/**
 * 사용자 로그인 플로우 E2E 테스트
 */
test.describe('사용자 로그인', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('정상 로그인 성공', async ({ page }) => {
    // 로그인 폼 작성
    await page.fill('input[name="email"]', 'testuser@example.com');
    await page.fill('input[name="password"]', 'TestPassword123!');

    // 로그인 버튼 클릭
    await page.click('button[type="submit"]');

    // 로그인 성공 확인
    await expect(page).toHaveURL('/');
    await expect(page.locator('text=testuser@example.com')).toBeVisible();
    await expect(page.locator('text=로그아웃')).toBeVisible();

    // 장바구니 아이콘 표시 확인
    await expect(page.locator('[data-testid="cart-icon"]')).toBeVisible();
  });

  test('잘못된 비밀번호로 로그인 실패', async ({ page }) => {
    await page.fill('input[name="email"]', 'testuser@example.com');
    await page.fill('input[name="password"]', 'WrongPassword123!');
    await page.click('button[type="submit"]');

    // 에러 메시지 확인
    await expect(page.locator('text=이메일 또는 비밀번호가 일치하지 않습니다')).toBeVisible();
    await expect(page).toHaveURL('/login');
  });

  test('존재하지 않는 이메일로 로그인 실패', async ({ page }) => {
    await page.fill('input[name="email"]', 'nonexistent@example.com');
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.click('button[type="submit"]');

    await expect(page.locator('text=이메일 또는 비밀번호가 일치하지 않습니다')).toBeVisible();
  });

  test('로그아웃 기능', async ({ page }) => {
    // 먼저 로그인
    await page.fill('input[name="email"]', 'testuser@example.com');
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL('/');

    // 로그아웃
    await page.click('text=로그아웃');

    // 로그아웃 확인
    await expect(page).toHaveURL('/');
    await expect(page.locator('text=로그인')).toBeVisible();
    await expect(page.locator('text=회원가입')).toBeVisible();
    await expect(page.locator('text=testuser@example.com')).not.toBeVisible();
  });

  test('리멤버미 기능', async ({ page, context }) => {
    // 리멤버미 체크하고 로그인
    await page.fill('input[name="email"]', 'testuser@example.com');
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.check('input[name="rememberMe"]');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL('/');

    // 쿠키 확인
    const cookies = await context.cookies();
    const authCookie = cookies.find(c => c.name === 'auth_token');
    expect(authCookie).toBeDefined();
    expect(authCookie?.expires).toBeGreaterThan(Date.now() / 1000 + 7 * 24 * 60 * 60); // 7일 이상
  });
});