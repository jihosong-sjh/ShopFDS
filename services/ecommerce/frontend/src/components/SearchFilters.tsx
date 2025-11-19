/**
 * SearchFilters Component
 *
 * Provides filters for search results:
 * - Price range (min/max)
 * - Brand selection
 * - In-stock only checkbox
 */

import React, { useState, useEffect } from 'react';

export interface FilterValues {
  minPrice?: number;
  maxPrice?: number;
  brand?: string;
  inStock?: boolean;
}

interface SearchFiltersProps {
  initialFilters?: FilterValues;
  onApply: (filters: FilterValues) => void;
  onClear: () => void;
  brands?: string[]; // Available brands for dropdown
  className?: string;
}

export function SearchFilters({
  initialFilters = {},
  onApply,
  onClear,
  brands = [],
  className = '',
}: SearchFiltersProps) {
  const [minPrice, setMinPrice] = useState<string>(
    initialFilters.minPrice?.toString() || ''
  );
  const [maxPrice, setMaxPrice] = useState<string>(
    initialFilters.maxPrice?.toString() || ''
  );
  const [brand, setBrand] = useState<string>(initialFilters.brand || '');
  const [inStock, setInStock] = useState<boolean>(initialFilters.inStock || false);

  // Sync with initial filters when they change
  useEffect(() => {
    setMinPrice(initialFilters.minPrice?.toString() || '');
    setMaxPrice(initialFilters.maxPrice?.toString() || '');
    setBrand(initialFilters.brand || '');
    setInStock(initialFilters.inStock || false);
  }, [initialFilters]);

  // Handle apply filters
  const handleApply = () => {
    const filters: FilterValues = {};

    if (minPrice) {
      filters.minPrice = parseInt(minPrice, 10);
    }

    if (maxPrice) {
      filters.maxPrice = parseInt(maxPrice, 10);
    }

    if (brand) {
      filters.brand = brand;
    }

    if (inStock) {
      filters.inStock = true;
    }

    onApply(filters);
  };

  // Handle clear filters
  const handleClear = () => {
    setMinPrice('');
    setMaxPrice('');
    setBrand('');
    setInStock(false);
    onClear();
  };

  // Check if any filter is applied
  const hasActiveFilters = minPrice || maxPrice || brand || inStock;

  return (
    <div className={`bg-white p-4 rounded-lg border border-gray-200 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">필터</h3>
        {hasActiveFilters && (
          <button
            onClick={handleClear}
            data-testid="filter-clear-button"
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            초기화
          </button>
        )}
      </div>

      <div className="space-y-4">
        {/* Price Range */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            가격 범위
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={minPrice}
              onChange={(e) => setMinPrice(e.target.value)}
              placeholder="최소"
              min="0"
              data-testid="filter-min-price"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-gray-500">~</span>
            <input
              type="number"
              value={maxPrice}
              onChange={(e) => setMaxPrice(e.target.value)}
              placeholder="최대"
              min="0"
              data-testid="filter-max-price"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Brand Filter */}
        {brands.length > 0 && (
          <div>
            <label
              htmlFor="brand-filter"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              브랜드
            </label>
            <select
              id="brand-filter"
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              data-testid="filter-brand"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">전체 브랜드</option>
              {brands.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* In-Stock Only */}
        <div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={inStock}
              onChange={(e) => setInStock(e.target.checked)}
              data-testid="filter-in-stock-checkbox"
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">재고 있는 상품만</span>
          </label>
        </div>

        {/* Apply Button */}
        <button
          onClick={handleApply}
          data-testid="filter-apply-button"
          className="w-full py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          필터 적용
        </button>
      </div>

      {/* Active Filters Summary */}
      {hasActiveFilters && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="text-xs text-gray-500 mb-2">적용된 필터:</div>
          <div className="flex flex-wrap gap-2">
            {minPrice && (
              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                최소 {parseInt(minPrice).toLocaleString()}원
              </span>
            )}
            {maxPrice && (
              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                최대 {parseInt(maxPrice).toLocaleString()}원
              </span>
            )}
            {brand && (
              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                {brand}
              </span>
            )}
            {inStock && (
              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                재고 있음
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default SearchFilters;
