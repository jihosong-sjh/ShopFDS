/**
 * [OK] E2E Tests: Checkout Process
 *
 * Playwright E2E tests for checkout flow with coupon application and payment.
 */

import { test, expect, Page } from '@playwright/test';

// Helper function to login
async function loginAsTestUser(page: Page) {
  await page.goto('/login');
  await page.locator('[data-testid="email-input"]').fill('test@example.com');
  await page.locator('[data-testid="password-input"]').fill('password123');
  await page.locator('[data-testid="login-button"]').click();
  await expect(page).toHaveURL(/\//, { timeout: 5000 });
}

// Helper function to add product to cart
async function addProductToCart(page: Page) {
  await page.goto('/products');
  const firstProduct = page.locator('[data-testid="product-card"]').first();
  await firstProduct.click();

  // Wait for product detail page
  await expect(page).toHaveURL(/\/products\/[a-f0-9-]+/);

  // Add to cart
  await page.locator('[data-testid="add-to-cart-button"]').click();

  // Wait for success notification
  await expect(page.locator('[data-testid="toast-success"]')).toBeVisible({ timeout: 3000 });
}

test.describe('Checkout Process - Basic Flow', () => {
  test('completes checkout with 3 steps', async ({ page }) => {
    // Given: User is logged in and has items in cart
    await loginAsTestUser(page);
    await addProductToCart(page);

    // When: User navigates to checkout
    await page.goto('/checkout');

    // Then: Step indicator shows 3 steps
    const stepIndicator = page.locator('[data-testid="checkout-steps"]');
    await expect(stepIndicator).toBeVisible();
    await expect(page.locator('[data-testid="step-1"]')).toBeVisible();
    await expect(page.locator('[data-testid="step-2"]')).toBeVisible();
    await expect(page.locator('[data-testid="step-3"]')).toBeVisible();

    // And: Step 1 (shipping info) is active
    await expect(page.locator('[data-testid="step-1"]')).toHaveAttribute('data-active', 'true');
  });

  test('navigates through checkout steps sequentially', async ({ page }) => {
    // Given: User is on checkout page
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    // When: User fills shipping info and clicks next
    await page.locator('[data-testid="shipping-name"]').fill('홍길동');
    await page.locator('[data-testid="shipping-phone"]').fill('010-1234-5678');
    await page.locator('[data-testid="shipping-address"]').fill('서울특별시 강남구');
    await page.locator('[data-testid="shipping-zipcode"]').fill('06000');
    await page.locator('[data-testid="next-button"]').click();

    // Then: Moves to step 2 (payment)
    await expect(page.locator('[data-testid="step-2"]')).toHaveAttribute('data-active', 'true');
    await expect(page.locator('[data-testid="payment-method-selector"]')).toBeVisible();
  });

  test('shows order summary with total amount', async ({ page }) => {
    // Given: User is on checkout page
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    // Then: Order summary is visible
    const orderSummary = page.locator('[data-testid="order-summary"]');
    await expect(orderSummary).toBeVisible();

    // And: Shows subtotal, shipping, and total
    await expect(orderSummary.locator('[data-testid="subtotal"]')).toBeVisible();
    await expect(orderSummary.locator('[data-testid="shipping-cost"]')).toBeVisible();
    await expect(orderSummary.locator('[data-testid="total-amount"]')).toBeVisible();
  });

  test('cannot proceed to next step with incomplete information', async ({ page }) => {
    // Given: User is on checkout page
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    // When: User tries to proceed without filling shipping info
    await page.locator('[data-testid="next-button"]').click();

    // Then: Error message appears
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();

    // And: Still on step 1
    await expect(page.locator('[data-testid="step-1"]')).toHaveAttribute('data-active', 'true');
  });
});

test.describe('Checkout Process - Coupon Application', () => {
  test('applies valid coupon and updates total amount', async ({ page }) => {
    // Given: User is on checkout page
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    // When: User enters valid coupon code
    const couponInput = page.locator('[data-testid="coupon-input"]');
    await couponInput.fill('WELCOME2025');
    await page.locator('[data-testid="apply-coupon-button"]').click();

    // Then: Success message appears
    await expect(page.locator('[data-testid="coupon-success"]')).toBeVisible({ timeout: 3000 });
    await expect(page.locator('[data-testid="coupon-success"]')).toContainText('쿠폰이 적용되었습니다');

    // And: Order summary shows discount
    const orderSummary = page.locator('[data-testid="order-summary"]');
    await expect(orderSummary.locator('[data-testid="discount-amount"]')).toBeVisible();

    // And: Total amount is reduced
    const discountAmount = await orderSummary.locator('[data-testid="discount-amount"]').textContent();
    expect(discountAmount).toMatch(/[0-9,]+/); // Has numeric discount value
  });

  test('shows error for invalid coupon code', async ({ page }) => {
    // Given: User is on checkout page
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    // When: User enters invalid coupon code
    const couponInput = page.locator('[data-testid="coupon-input"]');
    await couponInput.fill('INVALID999');
    await page.locator('[data-testid="apply-coupon-button"]').click();

    // Then: Error message appears
    await expect(page.locator('[data-testid="coupon-error"]')).toBeVisible({ timeout: 3000 });

    // And: No discount is applied
    const orderSummary = page.locator('[data-testid="order-summary"]');
    await expect(orderSummary.locator('[data-testid="discount-amount"]')).not.toBeVisible();
  });

  test('removes applied coupon when user clicks remove button', async ({ page }) => {
    // Given: User has applied a coupon
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    const couponInput = page.locator('[data-testid="coupon-input"]');
    await couponInput.fill('FIXED5000');
    await page.locator('[data-testid="apply-coupon-button"]').click();
    await expect(page.locator('[data-testid="coupon-success"]')).toBeVisible({ timeout: 3000 });

    // When: User clicks remove coupon button
    await page.locator('[data-testid="remove-coupon-button"]').click();

    // Then: Discount is removed
    const orderSummary = page.locator('[data-testid="order-summary"]');
    await expect(orderSummary.locator('[data-testid="discount-amount"]')).not.toBeVisible();

    // And: Coupon input is cleared
    await expect(couponInput).toHaveValue('');
  });

  test('shows error when coupon minimum purchase not met', async ({ page }) => {
    // Given: User has cart total below coupon minimum
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    // When: User tries to apply coupon with minimum purchase requirement
    const couponInput = page.locator('[data-testid="coupon-input"]');
    await couponInput.fill('MIN50K'); // Requires 50,000 won minimum
    await page.locator('[data-testid="apply-coupon-button"]').click();

    // Then: Error message indicates minimum not met
    await expect(page.locator('[data-testid="coupon-error"]')).toBeVisible({ timeout: 3000 });
    await expect(page.locator('[data-testid="coupon-error"]')).toContainText('최소');
  });

  test('displays list of available coupons for user', async ({ page }) => {
    // Given: User is on checkout page
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    // When: User clicks "내 쿠폰 보기" button
    await page.locator('[data-testid="my-coupons-button"]').click();

    // Then: Coupon list modal appears
    const couponModal = page.locator('[data-testid="coupon-list-modal"]');
    await expect(couponModal).toBeVisible({ timeout: 3000 });

    // And: Shows user's available coupons
    const couponItems = page.locator('[data-testid="coupon-item"]');
    await expect(couponItems.first()).toBeVisible();
  });

  test('applies coupon by selecting from available coupons list', async ({ page }) => {
    // Given: User opened available coupons modal
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');
    await page.locator('[data-testid="my-coupons-button"]').click();

    // When: User selects a coupon from the list
    const firstCoupon = page.locator('[data-testid="coupon-item"]').first();
    await firstCoupon.locator('[data-testid="select-coupon-button"]').click();

    // Then: Coupon is applied
    await expect(page.locator('[data-testid="coupon-success"]')).toBeVisible({ timeout: 3000 });

    // And: Modal closes
    await expect(page.locator('[data-testid="coupon-list-modal"]')).not.toBeVisible();
  });
});

test.describe('Checkout Process - Payment Method Selection', () => {
  test('selects credit card payment method', async ({ page }) => {
    // Given: User is on payment step
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    // Fill shipping info
    await page.locator('[data-testid="shipping-name"]').fill('홍길동');
    await page.locator('[data-testid="shipping-phone"]').fill('010-1234-5678');
    await page.locator('[data-testid="shipping-address"]').fill('서울특별시 강남구');
    await page.locator('[data-testid="shipping-zipcode"]').fill('06000');
    await page.locator('[data-testid="next-button"]').click();

    // When: User selects credit card
    await page.locator('[data-testid="payment-method-card"]').click();

    // Then: Credit card is selected
    await expect(page.locator('[data-testid="payment-method-card"]')).toHaveAttribute('data-selected', 'true');

    // And: Credit card input fields appear
    await expect(page.locator('[data-testid="card-number-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="card-expiry-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="card-cvv-input"]')).toBeVisible();
  });

  test('selects Toss Payments method', async ({ page }) => {
    // Given: User is on payment step
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    // Fill shipping info
    await page.locator('[data-testid="shipping-name"]').fill('홍길동');
    await page.locator('[data-testid="shipping-phone"]').fill('010-1234-5678');
    await page.locator('[data-testid="shipping-address"]').fill('서울특별시 강남구');
    await page.locator('[data-testid="shipping-zipcode"]').fill('06000');
    await page.locator('[data-testid="next-button"]').click();

    // When: User selects Toss Payments
    await page.locator('[data-testid="payment-method-toss"]').click();

    // Then: Toss Payments is selected
    await expect(page.locator('[data-testid="payment-method-toss"]')).toHaveAttribute('data-selected', 'true');
  });

  test('selects Kakao Pay method', async ({ page }) => {
    // Given: User is on payment step
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    // Fill shipping info
    await page.locator('[data-testid="shipping-name"]').fill('홍길동');
    await page.locator('[data-testid="shipping-phone"]').fill('010-1234-5678');
    await page.locator('[data-testid="shipping-address"]').fill('서울특별시 강남구');
    await page.locator('[data-testid="shipping-zipcode"]').fill('06000');
    await page.locator('[data-testid="next-button"]').click();

    // When: User selects Kakao Pay
    await page.locator('[data-testid="payment-method-kakao"]').click();

    // Then: Kakao Pay is selected
    await expect(page.locator('[data-testid="payment-method-kakao"]')).toHaveAttribute('data-selected', 'true');
  });

  test('cannot proceed without selecting payment method', async ({ page }) => {
    // Given: User is on payment step but hasn't selected method
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    // Fill shipping info
    await page.locator('[data-testid="shipping-name"]').fill('홍길동');
    await page.locator('[data-testid="shipping-phone"]').fill('010-1234-5678');
    await page.locator('[data-testid="shipping-address"]').fill('서울특별시 강남구');
    await page.locator('[data-testid="shipping-zipcode"]').fill('06000');
    await page.locator('[data-testid="next-button"]').click();

    // When: User tries to proceed without selecting payment method
    await page.locator('[data-testid="next-button"]').click();

    // Then: Error message appears
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-message"]')).toContainText('결제');
  });
});

test.describe('Checkout Process - Order Confirmation', () => {
  test('shows order summary on confirmation step', async ({ page }) => {
    // Given: User completed shipping and payment steps
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    // Fill shipping info
    await page.locator('[data-testid="shipping-name"]').fill('홍길동');
    await page.locator('[data-testid="shipping-phone"]').fill('010-1234-5678');
    await page.locator('[data-testid="shipping-address"]').fill('서울특별시 강남구');
    await page.locator('[data-testid="shipping-zipcode"]').fill('06000');
    await page.locator('[data-testid="next-button"]').click();

    // Select payment method
    await page.locator('[data-testid="payment-method-card"]').click();
    await page.locator('[data-testid="card-number-input"]').fill('1234567890123456');
    await page.locator('[data-testid="card-expiry-input"]').fill('12/25');
    await page.locator('[data-testid="card-cvv-input"]').fill('123');
    await page.locator('[data-testid="next-button"]').click();

    // Then: Step 3 (confirmation) is active
    await expect(page.locator('[data-testid="step-3"]')).toHaveAttribute('data-active', 'true');

    // And: Shows complete order information
    await expect(page.locator('[data-testid="confirm-shipping-info"]')).toBeVisible();
    await expect(page.locator('[data-testid="confirm-payment-method"]')).toBeVisible();
    await expect(page.locator('[data-testid="confirm-order-items"]')).toBeVisible();
    await expect(page.locator('[data-testid="confirm-total-amount"]')).toBeVisible();
  });

  test('completes order and redirects to order complete page', async ({ page }) => {
    // Given: User is on order confirmation step
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    // Fill shipping info
    await page.locator('[data-testid="shipping-name"]').fill('홍길동');
    await page.locator('[data-testid="shipping-phone"]').fill('010-1234-5678');
    await page.locator('[data-testid="shipping-address"]').fill('서울특별시 강남구');
    await page.locator('[data-testid="shipping-zipcode"]').fill('06000');
    await page.locator('[data-testid="next-button"]').click();

    // Select payment method
    await page.locator('[data-testid="payment-method-toss"]').click();
    await page.locator('[data-testid="next-button"]').click();

    // When: User clicks "주문 완료" button
    await page.locator('[data-testid="complete-order-button"]').click();

    // Then: Redirects to order complete page
    await expect(page).toHaveURL(/\/orders\/complete/, { timeout: 10000 });

    // And: Shows order confirmation
    await expect(page.locator('[data-testid="order-complete-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="order-number"]')).toBeVisible();
  });

  test('shows estimated delivery date on order complete page', async ({ page }) => {
    // Given: User completed order
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    // Complete checkout flow
    await page.locator('[data-testid="shipping-name"]').fill('홍길동');
    await page.locator('[data-testid="shipping-phone"]').fill('010-1234-5678');
    await page.locator('[data-testid="shipping-address"]').fill('서울특별시 강남구');
    await page.locator('[data-testid="shipping-zipcode"]').fill('06000');
    await page.locator('[data-testid="next-button"]').click();

    await page.locator('[data-testid="payment-method-toss"]').click();
    await page.locator('[data-testid="next-button"]').click();

    await page.locator('[data-testid="complete-order-button"]').click();

    // Then: Shows estimated delivery date
    await expect(page.locator('[data-testid="estimated-delivery"]')).toBeVisible({ timeout: 5000 });

    // And: Delivery date is in future
    const deliveryText = await page.locator('[data-testid="estimated-delivery"]').textContent();
    expect(deliveryText).toMatch(/[0-9]{4}-[0-9]{2}-[0-9]{2}/); // Date format
  });

  test('can go back to edit information before final confirmation', async ({ page }) => {
    // Given: User is on confirmation step
    await loginAsTestUser(page);
    await addProductToCart(page);
    await page.goto('/checkout');

    // Fill shipping info
    await page.locator('[data-testid="shipping-name"]').fill('홍길동');
    await page.locator('[data-testid="shipping-phone"]').fill('010-1234-5678');
    await page.locator('[data-testid="shipping-address"]').fill('서울특별시 강남구');
    await page.locator('[data-testid="shipping-zipcode"]').fill('06000');
    await page.locator('[data-testid="next-button"]').click();

    await page.locator('[data-testid="payment-method-card"]').click();
    await page.locator('[data-testid="card-number-input"]').fill('1234567890123456');
    await page.locator('[data-testid="card-expiry-input"]').fill('12/25');
    await page.locator('[data-testid="card-cvv-input"]').fill('123');
    await page.locator('[data-testid="next-button"]').click();

    // When: User clicks "배송지 수정" button
    await page.locator('[data-testid="edit-shipping-button"]').click();

    // Then: Goes back to step 1 with form values preserved
    await expect(page.locator('[data-testid="step-1"]')).toHaveAttribute('data-active', 'true');
    await expect(page.locator('[data-testid="shipping-name"]')).toHaveValue('홍길동');
  });
});

test.describe('Checkout Process - Complete E2E Flow', () => {
  test('user completes checkout in under 5 minutes with coupon applied', async ({ page }) => {
    // Given: User is logged in
    await loginAsTestUser(page);

    // When: User adds 3 products to cart
    await page.goto('/products');
    for (let i = 0; i < 3; i++) {
      const product = page.locator('[data-testid="product-card"]').nth(i);
      await product.click();
      await page.locator('[data-testid="add-to-cart-button"]').click();
      await page.goBack();
    }

    // And: Goes to checkout
    await page.goto('/checkout');

    // And: Applies coupon
    await page.locator('[data-testid="coupon-input"]').fill('WELCOME2025');
    await page.locator('[data-testid="apply-coupon-button"]').click();
    await expect(page.locator('[data-testid="coupon-success"]')).toBeVisible({ timeout: 3000 });

    // And: Fills shipping information
    await page.locator('[data-testid="shipping-name"]').fill('김고객');
    await page.locator('[data-testid="shipping-phone"]').fill('010-9876-5432');
    await page.locator('[data-testid="shipping-address"]').fill('부산광역시 해운대구');
    await page.locator('[data-testid="shipping-zipcode"]').fill('48000');
    await page.locator('[data-testid="next-button"]').click();

    // And: Selects payment method
    await page.locator('[data-testid="payment-method-kakao"]').click();
    await page.locator('[data-testid="next-button"]').click();

    // And: Confirms order
    await page.locator('[data-testid="complete-order-button"]').click();

    // Then: Order is completed successfully
    await expect(page).toHaveURL(/\/orders\/complete/, { timeout: 10000 });
    await expect(page.locator('[data-testid="order-complete-message"]')).toContainText('주문이 완료되었습니다');

    // And: Shows order details with discount applied
    await expect(page.locator('[data-testid="order-number"]')).toBeVisible();
    await expect(page.locator('[data-testid="discount-applied"]')).toBeVisible();
    await expect(page.locator('[data-testid="estimated-delivery"]')).toBeVisible();
  });
});
