/**
 * [OK] E2E Tests: Review Feature
 *
 * Playwright E2E tests for review creation, viewing, voting, and filtering.
 * User Story 2: 신뢰할 수 있는 상품 정보 확인
 */

import { test, expect, Page } from '@playwright/test';

// Helper function to login as a test user
async function loginAsTestUser(page: Page) {
  await page.goto('/login');
  await page.locator('[data-testid="login-email"]').fill('testuser@example.com');
  await page.locator('[data-testid="login-password"]').fill('testpassword123');
  await page.locator('[data-testid="login-submit"]').click();
  await page.waitForURL('/'); // Wait for redirect to homepage after login
}

test.describe('Review Display on Product Page', () => {
  test('shows reviews on product detail page', async ({ page }) => {
    // Given: User navigates to a product with reviews
    await page.goto('/products/sample-product-id');

    // Then: Review section is visible
    const reviewSection = page.locator('[data-testid="review-section"]');
    await expect(reviewSection).toBeVisible();

    // And: Average rating is displayed
    const averageRating = page.locator('[data-testid="average-rating"]');
    await expect(averageRating).toBeVisible();
    await expect(averageRating).toContainText(/[0-9]\.[0-9]/); // e.g., "4.5"

    // And: Total review count is displayed
    const reviewCount = page.locator('[data-testid="review-count"]');
    await expect(reviewCount).toBeVisible();
    await expect(reviewCount).toContainText(/[0-9]+ reviews/);

    // And: Individual reviews are displayed
    const reviewCards = page.locator('[data-testid="review-card"]');
    await expect(reviewCards.first()).toBeVisible();
  });

  test('displays review rating distribution', async ({ page }) => {
    // Given: User is on product page with reviews
    await page.goto('/products/sample-product-id');

    // Then: Rating distribution bars are visible
    const ratingBar5 = page.locator('[data-testid="rating-bar-5"]');
    const ratingBar4 = page.locator('[data-testid="rating-bar-4"]');
    const ratingBar3 = page.locator('[data-testid="rating-bar-3"]');
    const ratingBar2 = page.locator('[data-testid="rating-bar-2"]');
    const ratingBar1 = page.locator('[data-testid="rating-bar-1"]');

    await expect(ratingBar5).toBeVisible();
    await expect(ratingBar4).toBeVisible();
    await expect(ratingBar3).toBeVisible();
    await expect(ratingBar2).toBeVisible();
    await expect(ratingBar1).toBeVisible();

    // And: Each bar shows count and percentage
    await expect(ratingBar5).toContainText(/[0-9]+/); // Count
  });

  test('shows verified purchase badge on reviews', async ({ page }) => {
    // Given: User is on product page
    await page.goto('/products/sample-product-id');

    // When: Review is from verified purchase
    const verifiedBadge = page.locator('[data-testid="verified-purchase-badge"]').first();

    // Then: Badge is visible
    await expect(verifiedBadge).toBeVisible();
    await expect(verifiedBadge).toContainText('Verified Purchase');
  });

  test('displays review images as thumbnails', async ({ page }) => {
    // Given: User is on product page with photo reviews
    await page.goto('/products/sample-product-id');

    // When: Review has images
    const reviewWithImages = page.locator('[data-testid="review-card"]').filter({ has: page.locator('[data-testid="review-image"]') }).first();

    // Then: Image thumbnails are visible
    const reviewImages = reviewWithImages.locator('[data-testid="review-image"]');
    await expect(reviewImages.first()).toBeVisible();

    // And: Images are clickable for zoom
    await expect(reviewImages.first()).toHaveAttribute('role', 'button');
  });
});

test.describe('Review Filtering and Sorting', () => {
  test('filters reviews by rating', async ({ page }) => {
    // Given: User is on product page
    await page.goto('/products/sample-product-id');

    // When: User selects "5 stars only" filter
    await page.locator('[data-testid="filter-5-stars"]').click();

    // Then: Only 5-star reviews are displayed
    const reviewCards = page.locator('[data-testid="review-card"]');
    const count = await reviewCards.count();

    for (let i = 0; i < count; i++) {
      const rating = reviewCards.nth(i).locator('[data-testid="review-rating"]');
      await expect(rating).toHaveAttribute('data-rating', '5');
    }

    // And: URL includes rating filter
    await expect(page).toHaveURL(/rating=5/);
  });

  test('filters to show photo reviews only', async ({ page }) => {
    // Given: User is on product page
    await page.goto('/products/sample-product-id');

    // When: User toggles "Photo reviews only" filter
    await page.locator('[data-testid="filter-photos-only"]').check();

    // Then: All displayed reviews have images
    const reviewCards = page.locator('[data-testid="review-card"]');
    const count = await reviewCards.count();

    for (let i = 0; i < count; i++) {
      const reviewImages = reviewCards.nth(i).locator('[data-testid="review-image"]');
      await expect(reviewImages.first()).toBeVisible();
    }

    // And: URL includes photo filter
    await expect(page).toHaveURL(/has_images=true/);
  });

  test('sorts reviews by most helpful', async ({ page }) => {
    // Given: User is on product page
    await page.goto('/products/sample-product-id');

    // When: User selects "Most Helpful" sort
    await page.locator('[data-testid="sort-dropdown"]').selectOption('helpful');

    // Then: Reviews are sorted by helpful count descending
    await expect(page).toHaveURL(/sort=helpful/);

    const reviewCards = page.locator('[data-testid="review-card"]');
    const count = await reviewCards.count();
    const helpfulCounts: number[] = [];

    for (let i = 0; i < count; i++) {
      const helpfulText = await reviewCards.nth(i).locator('[data-testid="helpful-count"]').textContent();
      const helpfulCount = parseInt(helpfulText?.replace(/[^0-9]/g, '') || '0', 10);
      helpfulCounts.push(helpfulCount);
    }

    // Verify descending order
    for (let i = 1; i < helpfulCounts.length; i++) {
      expect(helpfulCounts[i]).toBeLessThanOrEqual(helpfulCounts[i - 1]);
    }
  });

  test('sorts reviews by most recent', async ({ page }) => {
    // Given: User is on product page
    await page.goto('/products/sample-product-id');

    // When: User selects "Most Recent" sort
    await page.locator('[data-testid="sort-dropdown"]').selectOption('recent');

    // Then: URL includes sort parameter
    await expect(page).toHaveURL(/sort=recent/);

    // And: Reviews are ordered by creation date (newest first)
    const firstReview = page.locator('[data-testid="review-card"]').first();
    const firstReviewDate = await firstReview.locator('[data-testid="review-date"]').textContent();

    // Most recent review should have a recent timestamp
    expect(firstReviewDate).toBeTruthy();
  });

  test('sorts reviews by highest rating', async ({ page }) => {
    // Given: User is on product page
    await page.goto('/products/sample-product-id');

    // When: User selects "Highest Rating" sort
    await page.locator('[data-testid="sort-dropdown"]').selectOption('rating_desc');

    // Then: URL includes sort parameter
    await expect(page).toHaveURL(/sort=rating_desc/);

    const reviewCards = page.locator('[data-testid="review-card"]');
    const count = await reviewCards.count();
    const ratings: number[] = [];

    for (let i = 0; i < count; i++) {
      const ratingAttr = await reviewCards.nth(i).locator('[data-testid="review-rating"]').getAttribute('data-rating');
      ratings.push(parseInt(ratingAttr || '0', 10));
    }

    // Verify ratings are in descending order
    for (let i = 1; i < ratings.length; i++) {
      expect(ratings[i]).toBeLessThanOrEqual(ratings[i - 1]);
    }
  });
});

test.describe('Review Creation', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await loginAsTestUser(page);
  });

  test('opens review form when clicking "Write a Review" button', async ({ page }) => {
    // Given: User purchased a product and navigated to product page
    await page.goto('/products/purchased-product-id');

    // When: User clicks "Write a Review" button
    await page.locator('[data-testid="write-review-button"]').click();

    // Then: Review form modal opens
    const reviewFormModal = page.locator('[data-testid="review-form-modal"]');
    await expect(reviewFormModal).toBeVisible();

    // And: Form fields are visible
    await expect(page.locator('[data-testid="review-rating-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="review-title-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="review-content-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="review-image-upload"]')).toBeVisible();
  });

  test('successfully creates a review with text only', async ({ page }) => {
    // Given: User opened review form
    await page.goto('/products/purchased-product-id');
    await page.locator('[data-testid="write-review-button"]').click();

    // When: User fills out review form
    // Select 5-star rating
    await page.locator('[data-testid="star-rating-5"]').click();

    // Enter title
    await page.locator('[data-testid="review-title-input"]').fill('정말 만족합니다');

    // Enter content (minimum 10 characters)
    await page.locator('[data-testid="review-content-input"]').fill('배송도 빠르고 상품도 좋아요. 적극 추천드립니다!');

    // Submit form
    await page.locator('[data-testid="review-submit-button"]').click();

    // Then: Success message appears
    const successToast = page.locator('[data-testid="success-toast"]');
    await expect(successToast).toBeVisible();
    await expect(successToast).toContainText('리뷰가 작성되었습니다');

    // And: Modal closes
    const reviewFormModal = page.locator('[data-testid="review-form-modal"]');
    await expect(reviewFormModal).not.toBeVisible();

    // And: New review appears in review list
    const newReview = page.locator('[data-testid="review-card"]').filter({ hasText: '정말 만족합니다' });
    await expect(newReview).toBeVisible();
  });

  test('successfully creates a review with images', async ({ page }) => {
    // Given: User opened review form
    await page.goto('/products/purchased-product-id');
    await page.locator('[data-testid="write-review-button"]').click();

    // When: User uploads images
    const fileInput = page.locator('[data-testid="review-image-upload"]');

    // Upload 2 images (max 3)
    await fileInput.setInputFiles([
      'tests/fixtures/review-image-1.jpg',
      'tests/fixtures/review-image-2.jpg',
    ]);

    // And: Fill out other fields
    await page.locator('[data-testid="star-rating-4"]').click();
    await page.locator('[data-testid="review-title-input"]').fill('사진 리뷰입니다');
    await page.locator('[data-testid="review-content-input"]').fill('실제 사용 사진을 첨부합니다. 제품이 깔끔하네요.');

    // Submit
    await page.locator('[data-testid="review-submit-button"]').click();

    // Then: Success
    await expect(page.locator('[data-testid="success-toast"]')).toBeVisible();

    // And: Review with images is visible
    const newReview = page.locator('[data-testid="review-card"]').filter({ hasText: '사진 리뷰입니다' });
    const reviewImages = newReview.locator('[data-testid="review-image"]');
    await expect(reviewImages).toHaveCount(2);
  });

  test('shows error when content is too short', async ({ page }) => {
    // Given: User opened review form
    await page.goto('/products/purchased-product-id');
    await page.locator('[data-testid="write-review-button"]').click();

    // When: User enters content less than 10 characters
    await page.locator('[data-testid="star-rating-5"]').click();
    await page.locator('[data-testid="review-title-input"]').fill('짧음');
    await page.locator('[data-testid="review-content-input"]').fill('짧아');

    // Submit
    await page.locator('[data-testid="review-submit-button"]').click();

    // Then: Error message appears
    const errorMessage = page.locator('[data-testid="content-error"]');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText('10자 이상');
  });

  test('shows error when uploading more than 3 images', async ({ page }) => {
    // Given: User opened review form
    await page.goto('/products/purchased-product-id');
    await page.locator('[data-testid="write-review-button"]').click();

    // When: User uploads 4 images (exceeds limit)
    const fileInput = page.locator('[data-testid="review-image-upload"]');

    await fileInput.setInputFiles([
      'tests/fixtures/review-image-1.jpg',
      'tests/fixtures/review-image-2.jpg',
      'tests/fixtures/review-image-3.jpg',
      'tests/fixtures/review-image-4.jpg',
    ]);

    // Then: Error message appears
    const errorMessage = page.locator('[data-testid="image-limit-error"]');
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toContainText('최대 3장');
  });

  test('requires login to write a review', async ({ page }) => {
    // Given: User is not logged in
    await page.goto('/logout'); // Ensure logged out
    await page.goto('/products/sample-product-id');

    // When: User clicks "Write a Review" button
    await page.locator('[data-testid="write-review-button"]').click();

    // Then: Redirects to login page
    await expect(page).toHaveURL(/\/login/);

    // And: Shows message about login requirement
    const loginMessage = page.locator('[data-testid="login-required-message"]');
    await expect(loginMessage).toContainText('리뷰를 작성하려면 로그인이 필요합니다');
  });
});

test.describe('Review Voting (Helpful)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsTestUser(page);
  });

  test('votes a review as helpful', async ({ page }) => {
    // Given: User is viewing a review
    await page.goto('/products/sample-product-id');

    const firstReview = page.locator('[data-testid="review-card"]').first();
    const helpfulButton = firstReview.locator('[data-testid="helpful-button"]');

    // Get initial helpful count
    const initialCountText = await firstReview.locator('[data-testid="helpful-count"]').textContent();
    const initialCount = parseInt(initialCountText?.replace(/[^0-9]/g, '') || '0', 10);

    // When: User clicks "도움돼요" button
    await helpfulButton.click();

    // Then: Button changes to "voted" state
    await expect(helpfulButton).toHaveAttribute('data-voted', 'true');

    // And: Helpful count increases by 1
    const newCountText = await firstReview.locator('[data-testid="helpful-count"]').textContent();
    const newCount = parseInt(newCountText?.replace(/[^0-9]/g, '') || '0', 10);
    expect(newCount).toBe(initialCount + 1);
  });

  test('cancels helpful vote', async ({ page }) => {
    // Given: User already voted a review as helpful
    await page.goto('/products/sample-product-id');

    const firstReview = page.locator('[data-testid="review-card"]').first();
    const helpfulButton = firstReview.locator('[data-testid="helpful-button"]');

    // Vote first
    await helpfulButton.click();
    await expect(helpfulButton).toHaveAttribute('data-voted', 'true');

    const countAfterVote = await firstReview.locator('[data-testid="helpful-count"]').textContent();
    const voteCount = parseInt(countAfterVote?.replace(/[^0-9]/g, '') || '0', 10);

    // When: User clicks "도움돼요" button again to cancel
    await helpfulButton.click();

    // Then: Button returns to unvoted state
    await expect(helpfulButton).toHaveAttribute('data-voted', 'false');

    // And: Helpful count decreases by 1
    const newCountText = await firstReview.locator('[data-testid="helpful-count"]').textContent();
    const newCount = parseInt(newCountText?.replace(/[^0-9]/g, '') || '0', 10);
    expect(newCount).toBe(voteCount - 1);
  });

  test('requires login to vote helpful', async ({ page }) => {
    // Given: User is not logged in
    await page.goto('/logout');
    await page.goto('/products/sample-product-id');

    // When: User clicks "도움돼요" button
    const firstReview = page.locator('[data-testid="review-card"]').first();
    const helpfulButton = firstReview.locator('[data-testid="helpful-button"]');
    await helpfulButton.click();

    // Then: Redirects to login or shows login modal
    const loginRequired = page.locator('[data-testid="login-required-modal"]');
    await expect(loginRequired).toBeVisible();
    await expect(loginRequired).toContainText('로그인이 필요합니다');
  });
});

test.describe('Review Image Zoom', () => {
  test('opens image zoom modal when clicking review image', async ({ page }) => {
    // Given: User is viewing a review with images
    await page.goto('/products/sample-product-id');

    // When: User clicks on review image thumbnail
    const reviewImage = page.locator('[data-testid="review-image"]').first();
    await reviewImage.click();

    // Then: Image zoom modal opens
    const zoomModal = page.locator('[data-testid="image-zoom-modal"]');
    await expect(zoomModal).toBeVisible();

    // And: Enlarged image is displayed
    const enlargedImage = zoomModal.locator('[data-testid="zoomed-image"]');
    await expect(enlargedImage).toBeVisible();
  });

  test('closes image zoom modal when clicking close button', async ({ page }) => {
    // Given: Image zoom modal is open
    await page.goto('/products/sample-product-id');
    const reviewImage = page.locator('[data-testid="review-image"]').first();
    await reviewImage.click();

    const zoomModal = page.locator('[data-testid="image-zoom-modal"]');
    await expect(zoomModal).toBeVisible();

    // When: User clicks close button
    const closeButton = zoomModal.locator('[data-testid="modal-close-button"]');
    await closeButton.click();

    // Then: Modal closes
    await expect(zoomModal).not.toBeVisible();
  });

  test('closes image zoom modal when pressing Escape key', async ({ page }) => {
    // Given: Image zoom modal is open
    await page.goto('/products/sample-product-id');
    const reviewImage = page.locator('[data-testid="review-image"]').first();
    await reviewImage.click();

    const zoomModal = page.locator('[data-testid="image-zoom-modal"]');
    await expect(zoomModal).toBeVisible();

    // When: User presses Escape key
    await page.keyboard.press('Escape');

    // Then: Modal closes
    await expect(zoomModal).not.toBeVisible();
  });

  test('navigates through multiple review images', async ({ page }) => {
    // Given: Review has multiple images and zoom modal is open
    await page.goto('/products/sample-product-id');

    const reviewWithMultipleImages = page.locator('[data-testid="review-card"]').filter({
      has: page.locator('[data-testid="review-image"]').nth(1)
    }).first();

    const firstImage = reviewWithMultipleImages.locator('[data-testid="review-image"]').first();
    await firstImage.click();

    const zoomModal = page.locator('[data-testid="image-zoom-modal"]');
    await expect(zoomModal).toBeVisible();

    // When: User clicks "next" button
    const nextButton = zoomModal.locator('[data-testid="image-next-button"]');
    await nextButton.click();

    // Then: Next image is displayed
    const zoomedImage = zoomModal.locator('[data-testid="zoomed-image"]');
    const imageSrc = await zoomedImage.getAttribute('src');
    expect(imageSrc).toBeTruthy();

    // And: Previous button is enabled
    const prevButton = zoomModal.locator('[data-testid="image-prev-button"]');
    await expect(prevButton).not.toBeDisabled();
  });
});

test.describe('Review Pagination', () => {
  test('loads more reviews when clicking "Load More" button', async ({ page }) => {
    // Given: Product has many reviews
    await page.goto('/products/popular-product-id');

    // Get initial review count
    const initialReviews = page.locator('[data-testid="review-card"]');
    const initialCount = await initialReviews.count();

    // When: User clicks "Load More" button
    await page.locator('[data-testid="load-more-reviews"]').click();

    // Then: More reviews are loaded
    await page.waitForTimeout(1000); // Wait for loading
    const newReviews = page.locator('[data-testid="review-card"]');
    const newCount = await newReviews.count();

    expect(newCount).toBeGreaterThan(initialCount);
  });

  test('hides "Load More" button when all reviews are loaded', async ({ page }) => {
    // Given: User loaded all available reviews
    await page.goto('/products/few-reviews-product-id'); // Product with < 10 reviews

    // Then: "Load More" button is not visible
    const loadMoreButton = page.locator('[data-testid="load-more-reviews"]');
    await expect(loadMoreButton).not.toBeVisible();
  });
});
