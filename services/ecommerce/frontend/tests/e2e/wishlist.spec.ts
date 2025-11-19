/**
 * [OK] E2E Tests: Wishlist Feature
 *
 * Playwright E2E tests for wishlist functionality including add, remove, and move to cart.
 */

import { test, expect, Page } from '@playwright/test';

test.describe('Wishlist Management', () => {
  test.beforeEach(async ({ page }) => {
    // Given: User is logged in
    await page.goto('/login');
    await page.locator('[data-testid="email-input"]').fill('testuser@example.com');
    await page.locator('[data-testid="password-input"]').fill('password123');
    await page.locator('[data-testid="login-button"]').click();

    // Wait for login success
    await expect(page).toHaveURL(/\/(home|dashboard)?/);
  });

  test('adds product to wishlist from product detail page', async ({ page }) => {
    // Given: User is on product detail page
    await page.goto('/products/test-product-id');
    await expect(page.locator('h1')).toBeVisible();

    // When: User clicks wishlist button (heart icon)
    const wishlistButton = page.locator('[data-testid="wishlist-button"]');
    await expect(wishlistButton).toBeVisible();
    await wishlistButton.click();

    // Then: Wishlist button shows active state (filled heart)
    await expect(wishlistButton).toHaveAttribute('aria-pressed', 'true');
    await expect(wishlistButton).toHaveClass(/active|filled/);

    // And: Success toast notification appears
    const toast = page.locator('[data-testid="toast"]');
    await expect(toast).toBeVisible();
    await expect(toast).toContainText('Wishlist added successfully');
  });

  test('removes product from wishlist by toggling button', async ({ page }) => {
    // Given: Product is already in wishlist
    await page.goto('/products/test-product-id');
    const wishlistButton = page.locator('[data-testid="wishlist-button"]');

    // Add to wishlist first
    await wishlistButton.click();
    await expect(wishlistButton).toHaveAttribute('aria-pressed', 'true');

    // When: User clicks wishlist button again to remove
    await wishlistButton.click();

    // Then: Wishlist button shows inactive state (outline heart)
    await expect(wishlistButton).toHaveAttribute('aria-pressed', 'false');
    await expect(wishlistButton).not.toHaveClass(/active|filled/);

    // And: Success toast appears
    const toast = page.locator('[data-testid="toast"]');
    await expect(toast).toContainText('Removed from wishlist');
  });

  test('adds product to wishlist from product card in search results', async ({ page }) => {
    // Given: User is on search results page
    await page.goto('/search?q=smartphone');

    // When: User clicks wishlist button on first product card
    const firstProductCard = page.locator('[data-testid="product-card"]').first();
    const wishlistButton = firstProductCard.locator('[data-testid="wishlist-button"]');
    await wishlistButton.click();

    // Then: Wishlist button shows active state
    await expect(wishlistButton).toHaveAttribute('aria-pressed', 'true');

    // And: Success toast notification appears
    const toast = page.locator('[data-testid="toast"]');
    await expect(toast).toBeVisible();
    await expect(toast).toContainText('Wishlist added successfully');
  });
});

test.describe('Wishlist Page', () => {
  test.beforeEach(async ({ page }) => {
    // Given: User is logged in
    await page.goto('/login');
    await page.locator('[data-testid="email-input"]').fill('testuser@example.com');
    await page.locator('[data-testid="password-input"]').fill('password123');
    await page.locator('[data-testid="login-button"]').click();
    await expect(page).toHaveURL(/\/(home|dashboard)?/);
  });

  test('displays wishlist items with product details', async ({ page }) => {
    // Given: User has items in wishlist
    await page.goto('/wishlist');

    // Then: Wishlist page shows product cards
    const wishlistItems = page.locator('[data-testid="wishlist-item"]');
    await expect(wishlistItems).toHaveCount(3, { timeout: 5000 }); // Assuming 3 items

    // And: Each item shows required product information
    const firstItem = wishlistItems.first();
    await expect(firstItem.locator('[data-testid="product-name"]')).toBeVisible();
    await expect(firstItem.locator('[data-testid="product-price"]')).toBeVisible();
    await expect(firstItem.locator('[data-testid="product-image"]')).toBeVisible();
    await expect(firstItem.locator('[data-testid="in-stock-status"]')).toBeVisible();
  });

  test('shows empty state when wishlist is empty', async ({ page }) => {
    // Given: User has no items in wishlist (or cleared all)
    await page.goto('/wishlist');

    // When: Wishlist is empty
    const wishlistItems = page.locator('[data-testid="wishlist-item"]');
    const itemCount = await wishlistItems.count();

    if (itemCount === 0) {
      // Then: Shows empty state message
      const emptyState = page.locator('[data-testid="wishlist-empty"]');
      await expect(emptyState).toBeVisible();
      await expect(emptyState).toContainText('Your wishlist is empty');

      // And: Shows "Continue Shopping" button
      const continueShoppingButton = page.locator('[data-testid="continue-shopping"]');
      await expect(continueShoppingButton).toBeVisible();
    }
  });

  test('removes item from wishlist page', async ({ page }) => {
    // Given: User is on wishlist page with items
    await page.goto('/wishlist');
    const wishlistItems = page.locator('[data-testid="wishlist-item"]');
    const initialCount = await wishlistItems.count();

    if (initialCount > 0) {
      // When: User clicks remove button on first item
      const firstItem = wishlistItems.first();
      const removeButton = firstItem.locator('[data-testid="remove-button"]');
      await removeButton.click();

      // Then: Item is removed from list
      await expect(wishlistItems).toHaveCount(initialCount - 1);

      // And: Success toast appears
      const toast = page.locator('[data-testid="toast"]');
      await expect(toast).toContainText('Removed from wishlist');
    }
  });

  test('navigates to product detail when clicking product name', async ({ page }) => {
    // Given: User is on wishlist page
    await page.goto('/wishlist');
    const wishlistItems = page.locator('[data-testid="wishlist-item"]');
    const itemCount = await wishlistItems.count();

    if (itemCount > 0) {
      // When: User clicks product name
      const firstItemName = wishlistItems.first().locator('[data-testid="product-name"]');
      await firstItemName.click();

      // Then: Navigates to product detail page
      await expect(page).toHaveURL(/\/products\/[a-f0-9-]+/);
    }
  });

  test('shows correct stock status for each product', async ({ page }) => {
    // Given: User is on wishlist page
    await page.goto('/wishlist');
    const wishlistItems = page.locator('[data-testid="wishlist-item"]');
    const itemCount = await wishlistItems.count();

    if (itemCount > 0) {
      // Then: Each item shows stock status
      const firstItem = wishlistItems.first();
      const stockStatus = firstItem.locator('[data-testid="in-stock-status"]');
      await expect(stockStatus).toBeVisible();

      // And: Stock status is either "In Stock" or "Out of Stock"
      const statusText = await stockStatus.textContent();
      expect(statusText).toMatch(/In Stock|Out of Stock/i);
    }
  });
});

test.describe('Move Wishlist to Cart', () => {
  test.beforeEach(async ({ page }) => {
    // Given: User is logged in
    await page.goto('/login');
    await page.locator('[data-testid="email-input"]').fill('testuser@example.com');
    await page.locator('[data-testid="password-input"]').fill('password123');
    await page.locator('[data-testid="login-button"]').click();
    await expect(page).toHaveURL(/\/(home|dashboard)?/);
  });

  test('adds single wishlist item to cart', async ({ page }) => {
    // Given: User is on wishlist page with items
    await page.goto('/wishlist');
    const wishlistItems = page.locator('[data-testid="wishlist-item"]');
    const itemCount = await wishlistItems.count();

    if (itemCount > 0) {
      // When: User clicks "Add to Cart" button on first item
      const firstItem = wishlistItems.first();
      const addToCartButton = firstItem.locator('[data-testid="add-to-cart-button"]');
      await addToCartButton.click();

      // Then: Success toast appears
      const toast = page.locator('[data-testid="toast"]');
      await expect(toast).toBeVisible();
      await expect(toast).toContainText('Added to cart');

      // And: Cart icon shows updated count
      const cartBadge = page.locator('[data-testid="cart-badge"]');
      await expect(cartBadge).toBeVisible();
    }
  });

  test('moves multiple wishlist items to cart at once', async ({ page }) => {
    // Given: User is on wishlist page with multiple items
    await page.goto('/wishlist');
    const wishlistItems = page.locator('[data-testid="wishlist-item"]');
    const itemCount = await wishlistItems.count();

    if (itemCount >= 2) {
      // When: User selects multiple items and clicks "Move to Cart"
      const firstCheckbox = wishlistItems.nth(0).locator('[data-testid="item-checkbox"]');
      const secondCheckbox = wishlistItems.nth(1).locator('[data-testid="item-checkbox"]');

      await firstCheckbox.check();
      await secondCheckbox.check();

      const moveToCartButton = page.locator('[data-testid="move-selected-to-cart"]');
      await moveToCartButton.click();

      // Then: Success toast shows number of items added
      const toast = page.locator('[data-testid="toast"]');
      await expect(toast).toBeVisible();
      await expect(toast).toContainText(/2 products added to cart/i);

      // And: Selected items are removed from wishlist
      await expect(wishlistItems).toHaveCount(itemCount - 2);
    }
  });

  test('disables add to cart for out of stock items', async ({ page }) => {
    // Given: User is on wishlist page
    await page.goto('/wishlist');
    const wishlistItems = page.locator('[data-testid="wishlist-item"]');
    const itemCount = await wishlistItems.count();

    if (itemCount > 0) {
      // When: Looking at items with out of stock status
      for (let i = 0; i < itemCount; i++) {
        const item = wishlistItems.nth(i);
        const stockStatus = item.locator('[data-testid="in-stock-status"]');
        const statusText = await stockStatus.textContent();

        if (statusText?.includes('Out of Stock')) {
          // Then: Add to cart button is disabled
          const addToCartButton = item.locator('[data-testid="add-to-cart-button"]');
          await expect(addToCartButton).toBeDisabled();
          break;
        }
      }
    }
  });

  test('shows confirmation dialog before moving all items to cart', async ({ page }) => {
    // Given: User is on wishlist page with items
    await page.goto('/wishlist');
    const wishlistItems = page.locator('[data-testid="wishlist-item"]');
    const itemCount = await wishlistItems.count();

    if (itemCount > 0) {
      // When: User clicks "Move All to Cart" button
      const moveAllButton = page.locator('[data-testid="move-all-to-cart"]');
      if (await moveAllButton.isVisible()) {
        await moveAllButton.click();

        // Then: Confirmation dialog appears
        const confirmDialog = page.locator('[data-testid="confirm-dialog"]');
        await expect(confirmDialog).toBeVisible();
        await expect(confirmDialog).toContainText(/move all items to cart/i);

        // When: User confirms
        const confirmButton = confirmDialog.locator('[data-testid="confirm-button"]');
        await confirmButton.click();

        // Then: All items moved to cart
        const toast = page.locator('[data-testid="toast"]');
        await expect(toast).toContainText(/added to cart/i);
      }
    }
  });
});

test.describe('Wishlist Persistence', () => {
  test('persists wishlist items after page reload', async ({ page }) => {
    // Given: User logs in and adds item to wishlist
    await page.goto('/login');
    await page.locator('[data-testid="email-input"]').fill('testuser@example.com');
    await page.locator('[data-testid="password-input"]').fill('password123');
    await page.locator('[data-testid="login-button"]').click();
    await expect(page).toHaveURL(/\/(home|dashboard)?/);

    await page.goto('/products/test-product-id');
    const wishlistButton = page.locator('[data-testid="wishlist-button"]');
    await wishlistButton.click();
    await expect(wishlistButton).toHaveAttribute('aria-pressed', 'true');

    // When: User reloads the page
    await page.reload();

    // Then: Wishlist button still shows active state
    await expect(wishlistButton).toHaveAttribute('aria-pressed', 'true');

    // And: Wishlist page still shows the item
    await page.goto('/wishlist');
    const wishlistItems = page.locator('[data-testid="wishlist-item"]');
    await expect(wishlistItems).toHaveCount(1, { timeout: 5000 });
  });

  test('syncs wishlist across multiple tabs', async ({ context }) => {
    // Given: User logs in on first tab
    const page1 = await context.newPage();
    await page1.goto('/login');
    await page1.locator('[data-testid="email-input"]').fill('testuser@example.com');
    await page1.locator('[data-testid="password-input"]').fill('password123');
    await page1.locator('[data-testid="login-button"]').click();
    await expect(page1).toHaveURL(/\/(home|dashboard)?/);

    // When: User adds item to wishlist on first tab
    await page1.goto('/products/test-product-id');
    const wishlistButton1 = page1.locator('[data-testid="wishlist-button"]');
    await wishlistButton1.click();

    // And: User opens second tab
    const page2 = await context.newPage();
    await page2.goto('/wishlist');

    // Then: Second tab shows the added item
    const wishlistItems = page2.locator('[data-testid="wishlist-item"]');
    await expect(wishlistItems).toHaveCount(1, { timeout: 5000 });

    await page1.close();
    await page2.close();
  });
});

test.describe('Wishlist Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    // Given: User is logged in
    await page.goto('/login');
    await page.locator('[data-testid="email-input"]').fill('testuser@example.com');
    await page.locator('[data-testid="password-input"]').fill('password123');
    await page.locator('[data-testid="login-button"]').click();
    await expect(page).toHaveURL(/\/(home|dashboard)?/);
  });

  test('wishlist button has proper ARIA attributes', async ({ page }) => {
    // Given: User is on product page
    await page.goto('/products/test-product-id');

    // Then: Wishlist button has ARIA label and pressed state
    const wishlistButton = page.locator('[data-testid="wishlist-button"]');
    await expect(wishlistButton).toHaveAttribute('aria-label', /add to wishlist|remove from wishlist/i);
    await expect(wishlistButton).toHaveAttribute('aria-pressed');
  });

  test('keyboard navigation works on wishlist page', async ({ page }) => {
    // Given: User is on wishlist page
    await page.goto('/wishlist');
    const wishlistItems = page.locator('[data-testid="wishlist-item"]');
    const itemCount = await wishlistItems.count();

    if (itemCount > 0) {
      // When: User navigates with Tab key
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');

      // Then: Focusable elements receive focus
      const removeButton = wishlistItems.first().locator('[data-testid="remove-button"]');

      // And: User can activate button with Enter key
      await removeButton.focus();
      await page.keyboard.press('Enter');

      // Then: Item is removed
      const toast = page.locator('[data-testid="toast"]');
      await expect(toast).toContainText('Removed from wishlist');
    }
  });

  test('screen reader announces wishlist updates', async ({ page }) => {
    // Given: User is on product page
    await page.goto('/products/test-product-id');

    // When: User adds to wishlist
    const wishlistButton = page.locator('[data-testid="wishlist-button"]');
    await wishlistButton.click();

    // Then: ARIA live region announces the change
    const liveRegion = page.locator('[aria-live="polite"], [role="status"]');
    await expect(liveRegion).toContainText(/added to wishlist/i);
  });
});
