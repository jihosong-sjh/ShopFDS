import { test, expect } from '@playwright/test';

/**
 * 사용자 회원가입 플로우 E2E 테스트
 */
test.describe('사용자 회원가입', () => {
  test('신규 사용자 회원가입 성공', async ({ page }) => {
    // 홈페이지 접속
    await page.goto('/');

    // 회원가입 페이지로 이동
    await page.click('text=회원가입');
    await expect(page).toHaveURL('/register');

    // 회원가입 폼 작성
    const timestamp = Date.now();
    const email = `testuser${timestamp}@example.com`;

    await page.fill('input[name="email"]', email);
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.fill('input[name="confirmPassword"]', 'TestPassword123!');
    await page.fill('input[name="name"]', '테스트 사용자');
    await page.fill('input[name="phone"]', '010-1234-5678');

    // 이용약관 동의
    await page.check('input[name="termsAgree"]');
    await page.check('input[name="privacyAgree"]');

    // 회원가입 버튼 클릭
    await page.click('button[type="submit"]');

    // 회원가입 성공 확인
    await expect(page).toHaveURL('/register/success');
    await expect(page.locator('text=회원가입이 완료되었습니다')).toBeVisible();

    // 로그인 페이지로 이동
    await page.click('text=로그인하러 가기');
    await expect(page).toHaveURL('/login');
  });

  test('중복 이메일 검증', async ({ page }) => {
    await page.goto('/register');

    // 이미 존재하는 이메일 입력
    await page.fill('input[name="email"]', 'existing@example.com');
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.fill('input[name="confirmPassword"]', 'TestPassword123!');
    await page.fill('input[name="name"]', '중복 테스트');
    await page.fill('input[name="phone"]', '010-9999-9999');

    await page.check('input[name="termsAgree"]');
    await page.check('input[name="privacyAgree"]');

    await page.click('button[type="submit"]');

    // 에러 메시지 확인
    await expect(page.locator('text=이미 사용 중인 이메일입니다')).toBeVisible();
  });

  test('비밀번호 유효성 검증', async ({ page }) => {
    await page.goto('/register');

    const timestamp = Date.now();
    const email = `testuser${timestamp}@example.com`;

    await page.fill('input[name="email"]', email);

    // 약한 비밀번호 입력
    await page.fill('input[name="password"]', '123456');
    await page.fill('input[name="confirmPassword"]', '123456');

    // 비밀번호 강도 메시지 확인
    await expect(page.locator('text=비밀번호는 8자 이상, 대소문자, 숫자, 특수문자를 포함해야 합니다')).toBeVisible();

    // 비밀번호 불일치 테스트
    await page.fill('input[name="password"]', 'TestPassword123!');
    await page.fill('input[name="confirmPassword"]', 'DifferentPassword123!');

    await page.click('button[type="submit"]');

    await expect(page.locator('text=비밀번호가 일치하지 않습니다')).toBeVisible();
  });
});