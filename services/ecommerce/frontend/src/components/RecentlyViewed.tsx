/**
 * RecentlyViewed Component
 *
 * Displays recently viewed products.
 * Uses LocalStorage for quick access + backend sync for authenticated users.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import type { Product } from '../hooks/useSearch';

const STORAGE_KEY = 'recently-viewed';
const MAX_ITEMS = 10;

interface RecentlyViewedItem {
  product_id: string;
  viewed_at: number;
}

/**
 * Load recently viewed from LocalStorage
 */
function loadRecentlyViewed(): RecentlyViewedItem[] {
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
function saveRecentlyViewed(items: RecentlyViewedItem[]): void {
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
    api.post('/v1/recommendations/recently-viewed', { product_id: productId }).catch(() => {
      // Silently fail - LocalStorage is primary
    });
  }
}

interface RecentlyViewedProps {
  limit?: number;
  className?: string;
}

export function RecentlyViewed({ limit = 10, className = '' }: RecentlyViewedProps) {
  const navigate = useNavigate();
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadProducts() {
      try {
        // Get product IDs from LocalStorage
        const items = loadRecentlyViewed().slice(0, limit);

        if (items.length === 0) {
          setIsLoading(false);
          return;
        }

        // Fetch product details from API
        const productIds = items.map((item) => item.product_id);
        const response = await api.get('/v1/products', {
          params: { ids: productIds.join(',') },
        });

        // Sort by viewed_at order
        const productsMap = new Map(
          response.data.products.map((p: Product) => [p.id, p])
        );
        const sorted = items
          .map((item) => productsMap.get(item.product_id))
          .filter((p): p is Product => p !== undefined);

        setProducts(sorted);
      } catch (error) {
        console.error('[RecentlyViewed] Failed to load products:', error);
      } finally {
        setIsLoading(false);
      }
    }

    loadProducts();
  }, [limit]);

  if (isLoading) {
    return (
      <div className={`py-4 ${className}`}>
        <div className="animate-pulse flex gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="w-48 h-64 bg-gray-200 rounded-lg"></div>
          ))}
        </div>
      </div>
    );
  }

  if (products.length === 0) {
    return null; // Don't show section if no products
  }

  return (
    <section className={`py-8 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">최근 본 상품</h2>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {products.map((product) => (
          <div
            key={product.id}
            className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
            onClick={() => {
              addToRecentlyViewed(product.id, true);
              navigate(`/products/${product.id}`);
            }}
          >
            {/* Product Image */}
            <div className="aspect-w-1 aspect-h-1 bg-gray-100">
              <img
                src={product.images[0] || '/placeholder.png'}
                alt={product.name}
                className="w-full h-40 object-cover"
              />
            </div>

            {/* Product Info */}
            <div className="p-3">
              <div className="text-xs text-gray-500 mb-1">{product.brand}</div>
              <h3 className="text-sm font-medium text-gray-900 mb-2 line-clamp-2">
                {product.name}
              </h3>
              <div className="text-base font-bold text-gray-900">
                {product.discounted_price
                  ? product.discounted_price.toLocaleString()
                  : product.price.toLocaleString()}
                원
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default RecentlyViewed;
