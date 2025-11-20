/**
 * RecentlyViewed Utility Functions
 *
 * Separate utility functions for recently viewed products
 */

const STORAGE_KEY = 'recently-viewed';
const MAX_ITEMS = 10;

export interface RecentlyViewedItem {
  product_id: string;
  viewed_at: number;
}

/**
 * Load recently viewed from LocalStorage
 */
export function loadRecentlyViewed(): RecentlyViewedItem[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    return JSON.parse(stored);
  } catch {
    return [];
  }
}

/**
 * Save recently viewed to LocalStorage
 */
export function saveRecentlyViewed(items: RecentlyViewedItem[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch (error) {
    console.error('[RecentlyViewed] Failed to save:', error);
  }
}

/**
 * Add product to recently viewed
 */
export function addToRecentlyViewed(productId: string, syncBackend: boolean = false): void {
  const items = loadRecentlyViewed();

  // Remove duplicate if exists
  const filtered = items.filter((item) => item.product_id !== productId);

  // Add to beginning
  const updated = [{ product_id: productId, viewed_at: Date.now() }, ...filtered];

  // Keep only MAX_ITEMS
  const limited = updated.slice(0, MAX_ITEMS);

  saveRecentlyViewed(limited);

  // Sync with backend (optional)
  if (syncBackend) {
    // Dynamic import to avoid circular dependency
    import('../services/api').then((api) => {
      api.default.post('/v1/recommendations/recently-viewed', { product_id: productId }).catch(() => {
        // Silently fail - LocalStorage is primary
      });
    });
  }
}
