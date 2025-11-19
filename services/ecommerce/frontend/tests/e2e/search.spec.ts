/**
 * [OK] E2E Tests: Search Feature
 *
 * Playwright E2E tests for search autocomplete, filtering, and sorting.
 */

import { test, expect, Page } from '@playwright/test';

test.describe('Search Autocomplete', () => {
  test('shows autocomplete suggestions while typing', async ({ page }) => {
    // Given: User is on homepage
    await page.goto('/');

    // When: User types in search bar
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.fill('iPhone');

    // Then: Autocomplete dropdown appears
    const autocompleteDropdown = page.locator('[data-testid="autocomplete-dropdown"]');
    await expect(autocompleteDropdown).toBeVisible();

    // And: Contains product suggestions
    const productSuggestions = page.locator('[data-testid="autocomplete-product"]');
    await expect(productSuggestions).toHaveCount(3, { timeout: 5000 });
  });

  test('navigates to product detail when clicking autocomplete suggestion', async ({ page }) => {
    // Given: User typed "iPhone" and autocomplete appeared
    await page.goto('/');
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.fill('iPhone');

    // When: User clicks first product suggestion
    const firstSuggestion = page.locator('[data-testid="autocomplete-product"]').first();
    await firstSuggestion.click();

    // Then: Navigates to product detail page
    await expect(page).toHaveURL(/\/products\/[a-f0-9-]+/);
    await expect(page.locator('h1')).toContainText('iPhone');
  });

  test('closes autocomplete when clicking outside', async ({ page }) => {
    // Given: Autocomplete is visible
    await page.goto('/');
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.fill('Galaxy');
    const autocompleteDropdown = page.locator('[data-testid="autocomplete-dropdown"]');
    await expect(autocompleteDropdown).toBeVisible();

    // When: User clicks outside search area
    await page.locator('body').click({ position: { x: 100, y: 100 } });

    // Then: Autocomplete closes
    await expect(autocompleteDropdown).not.toBeVisible();
  });

  test('highlights search query in autocomplete suggestions', async ({ page }) => {
    // Given: User typed "Sam" in search
    await page.goto('/');
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.fill('Sam');

    // When: Autocomplete appears
    const autocompleteDropdown = page.locator('[data-testid="autocomplete-dropdown"]');
    await expect(autocompleteDropdown).toBeVisible();

    // Then: Query "Sam" is highlighted in suggestions
    const highlightedText = page.locator('[data-testid="autocomplete-highlight"]').first();
    await expect(highlightedText).toHaveText('Sam');
    await expect(highlightedText).toHaveCSS('font-weight', '700'); // Bold
  });
});

test.describe('Search Results Page', () => {
  test('displays search results for query', async ({ page }) => {
    // Given: User navigated to search page
    await page.goto('/search?q=smartphone');

    // Then: Page displays search results
    await expect(page.locator('h1')).toContainText('Search Results for "smartphone"');

    // And: Product cards are visible
    const productCards = page.locator('[data-testid="product-card"]');
    await expect(productCards).toHaveCount(10, { timeout: 5000 }); // Default page size: 10

    // And: Each product card has required info
    const firstCard = productCards.first();
    await expect(firstCard.locator('[data-testid="product-name"]')).toBeVisible();
    await expect(firstCard.locator('[data-testid="product-price"]')).toBeVisible();
    await expect(firstCard.locator('[data-testid="product-image"]')).toBeVisible();
  });

  test('shows "no results" message for unmatched query', async ({ page }) => {
    // When: User searches for non-existent product
    await page.goto('/search?q=nonexistentproduct12345');

    // Then: Shows "no results" message
    await expect(page.locator('[data-testid="no-results"]')).toBeVisible();
    await expect(page.locator('[data-testid="no-results"]')).toContainText('No products found');
  });

  test('updates URL when submitting search from search bar', async ({ page }) => {
    // Given: User is on homepage
    await page.goto('/');

    // When: User submits search
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.fill('laptop');
    await searchInput.press('Enter');

    // Then: URL updates to search page
    await expect(page).toHaveURL('/search?q=laptop');

    // And: Search results page loads
    await expect(page.locator('h1')).toContainText('Search Results for "laptop"');
  });
});

test.describe('Search Filters', () => {
  test('filters products by price range', async ({ page }) => {
    // Given: User is on search results page
    await page.goto('/search?q=smartphone');

    // When: User sets price range filter (500,000 - 1,000,000)
    await page.locator('[data-testid="filter-min-price"]').fill('500000');
    await page.locator('[data-testid="filter-max-price"]').fill('1000000');
    await page.locator('[data-testid="filter-apply-button"]').click();

    // Then: URL includes price filters
    await expect(page).toHaveURL(/min_price=500000/);
    await expect(page).toHaveURL(/max_price=1000000/);

    // And: All displayed products are within price range
    const productPrices = page.locator('[data-testid="product-price"]');
    const count = await productPrices.count();
    for (let i = 0; i < count; i++) {
      const priceText = await productPrices.nth(i).textContent();
      const price = parseInt(priceText?.replace(/[^0-9]/g, '') || '0', 10);
      expect(price).toBeGreaterThanOrEqual(500000);
      expect(price).toBeLessThanOrEqual(1000000);
    }
  });

  test('filters products by brand', async ({ page }) => {
    // Given: User is on search results page
    await page.goto('/search?q=smartphone');

    // When: User selects "Apple" brand filter
    await page.locator('[data-testid="filter-brand"]').selectOption('Apple');
    await page.locator('[data-testid="filter-apply-button"]').click();

    // Then: URL includes brand filter
    await expect(page).toHaveURL(/brand=Apple/);

    // And: All displayed products are from Apple
    const productBrands = page.locator('[data-testid="product-brand"]');
    const count = await productBrands.count();
    for (let i = 0; i < count; i++) {
      await expect(productBrands.nth(i)).toHaveText('Apple');
    }
  });

  test('filters products to show in-stock only', async ({ page }) => {
    // Given: User is on search results page
    await page.goto('/search?q=phone');

    // When: User enables "in stock only" filter
    await page.locator('[data-testid="filter-in-stock-checkbox"]').check();
    await page.locator('[data-testid="filter-apply-button"]').click();

    // Then: URL includes in_stock filter
    await expect(page).toHaveURL(/in_stock=true/);

    // And: All products show "In Stock" badge
    const stockBadges = page.locator('[data-testid="stock-badge"]');
    const count = await stockBadges.count();
    for (let i = 0; i < count; i++) {
      await expect(stockBadges.nth(i)).toHaveText('In Stock');
    }
  });

  test('clears all filters', async ({ page }) => {
    // Given: User applied multiple filters
    await page.goto('/search?q=smartphone&min_price=500000&max_price=1000000&brand=Apple&in_stock=true');

    // When: User clicks "Clear Filters" button
    await page.locator('[data-testid="filter-clear-button"]').click();

    // Then: URL resets to query only
    await expect(page).toHaveURL('/search?q=smartphone');

    // And: All filter inputs are cleared
    await expect(page.locator('[data-testid="filter-min-price"]')).toHaveValue('');
    await expect(page.locator('[data-testid="filter-max-price"]')).toHaveValue('');
    await expect(page.locator('[data-testid="filter-brand"]')).toHaveValue('');
    await expect(page.locator('[data-testid="filter-in-stock-checkbox"]')).not.toBeChecked();
  });
});

test.describe('Search Sorting', () => {
  test('sorts products by price (low to high)', async ({ page }) => {
    // Given: User is on search results page
    await page.goto('/search?q=phone');

    // When: User selects "Price: Low to High" sort option
    await page.locator('[data-testid="sort-dropdown"]').selectOption('price_asc');

    // Then: URL includes sort parameter
    await expect(page).toHaveURL(/sort=price_asc/);

    // And: Products are sorted by price ascending
    const productPrices = page.locator('[data-testid="product-price"]');
    const count = await productPrices.count();
    const prices: number[] = [];
    for (let i = 0; i < count; i++) {
      const priceText = await productPrices.nth(i).textContent();
      const price = parseInt(priceText?.replace(/[^0-9]/g, '') || '0', 10);
      prices.push(price);
    }

    // Verify prices are in ascending order
    for (let i = 1; i < prices.length; i++) {
      expect(prices[i]).toBeGreaterThanOrEqual(prices[i - 1]);
    }
  });

  test('sorts products by price (high to low)', async ({ page }) => {
    // Given: User is on search results page
    await page.goto('/search?q=phone');

    // When: User selects "Price: High to Low" sort option
    await page.locator('[data-testid="sort-dropdown"]').selectOption('price_desc');

    // Then: URL includes sort parameter
    await expect(page).toHaveURL(/sort=price_desc/);

    // And: Products are sorted by price descending
    const productPrices = page.locator('[data-testid="product-price"]');
    const count = await productPrices.count();
    const prices: number[] = [];
    for (let i = 0; i < count; i++) {
      const priceText = await productPrices.nth(i).textContent();
      const price = parseInt(priceText?.replace(/[^0-9]/g, '') || '0', 10);
      prices.push(price);
    }

    // Verify prices are in descending order
    for (let i = 1; i < prices.length; i++) {
      expect(prices[i]).toBeLessThanOrEqual(prices[i - 1]);
    }
  });

  test('sorts products by rating', async ({ page }) => {
    // Given: User is on search results page
    await page.goto('/search?q=laptop');

    // When: User selects "Rating" sort option
    await page.locator('[data-testid="sort-dropdown"]').selectOption('rating');

    // Then: URL includes sort parameter
    await expect(page).toHaveURL(/sort=rating/);

    // And: Products are sorted by rating descending
    const productRatings = page.locator('[data-testid="product-rating"]');
    const count = await productRatings.count();
    const ratings: number[] = [];
    for (let i = 0; i < count; i++) {
      const ratingText = await productRatings.nth(i).textContent();
      const rating = parseFloat(ratingText || '0');
      ratings.push(rating);
    }

    // Verify ratings are in descending order
    for (let i = 1; i < ratings.length; i++) {
      expect(ratings[i]).toBeLessThanOrEqual(ratings[i - 1]);
    }
  });
});

test.describe('Search Pagination', () => {
  test('navigates to next page', async ({ page }) => {
    // Given: User is on search results page 1
    await page.goto('/search?q=product');

    // When: User clicks "Next" button
    await page.locator('[data-testid="pagination-next"]').click();

    // Then: URL shows page=2
    await expect(page).toHaveURL(/page=2/);

    // And: Page 2 products load
    const productCards = page.locator('[data-testid="product-card"]');
    await expect(productCards.first()).toBeVisible({ timeout: 5000 });
  });

  test('navigates to specific page number', async ({ page }) => {
    // Given: User is on search results page 1
    await page.goto('/search?q=product');

    // When: User clicks page number "3"
    await page.locator('[data-testid="pagination-page-3"]').click();

    // Then: URL shows page=3
    await expect(page).toHaveURL(/page=3/);

    // And: Page 3 products load
    const productCards = page.locator('[data-testid="product-card"]');
    await expect(productCards.first()).toBeVisible({ timeout: 5000 });
  });

  test('disables "Previous" button on first page', async ({ page }) => {
    // Given: User is on page 1
    await page.goto('/search?q=product&page=1');

    // Then: "Previous" button is disabled
    await expect(page.locator('[data-testid="pagination-previous"]')).toBeDisabled();
  });

  test('disables "Next" button on last page', async ({ page }) => {
    // Given: User is on last page
    // (Assuming there are 3 total pages for "product" query)
    await page.goto('/search?q=product&page=3');

    // Then: "Next" button is disabled
    await expect(page.locator('[data-testid="pagination-next"]')).toBeDisabled();
  });
});

test.describe('Search Query Highlighting', () => {
  test('highlights search query in product names', async ({ page }) => {
    // Given: User searched for "Phone"
    await page.goto('/search?q=Phone');

    // Then: Product names highlight "Phone"
    const highlightedText = page.locator('[data-testid="highlighted-query"]').first();
    await expect(highlightedText).toHaveText('Phone');
    await expect(highlightedText).toHaveCSS('background-color', 'rgb(255, 255, 0)'); // Yellow background
  });
});

test.describe('Recent Search History', () => {
  test('saves recent searches to localStorage', async ({ page }) => {
    // Given: User performed multiple searches
    await page.goto('/');

    // Search 1
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.fill('iPhone');
    await searchInput.press('Enter');
    await page.waitForURL('/search?q=iPhone');

    // Search 2
    await page.goto('/');
    await searchInput.fill('Galaxy');
    await searchInput.press('Enter');
    await page.waitForURL('/search?q=Galaxy');

    // When: User clicks on search input again
    await page.goto('/');
    await searchInput.click();

    // Then: Recent searches dropdown appears
    const recentSearches = page.locator('[data-testid="recent-search-item"]');
    await expect(recentSearches).toHaveCount(2);

    // And: Recent searches are in reverse chronological order
    await expect(recentSearches.nth(0)).toHaveText('Galaxy'); // Most recent
    await expect(recentSearches.nth(1)).toHaveText('iPhone');
  });

  test('clicking recent search executes search', async ({ page }) => {
    // Given: User has recent searches
    await page.goto('/');
    const searchInput = page.locator('[data-testid="search-input"]');
    await searchInput.fill('MacBook');
    await searchInput.press('Enter');
    await page.waitForURL('/search?q=MacBook');

    // When: User clicks on search input and selects recent search
    await page.goto('/');
    await searchInput.click();
    const recentSearchItem = page.locator('[data-testid="recent-search-item"]').first();
    await recentSearchItem.click();

    // Then: Search executes for that query
    await expect(page).toHaveURL('/search?q=MacBook');
  });
});
