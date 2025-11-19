/**
 * SearchPage Component
 *
 * Displays search results with:
 * - Product grid
 * - Filters (price, brand, stock)
 * - Sorting options
 * - Pagination
 * - URL query parameter synchronization
 */

import React, { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useProductSearch, SearchFilters as FilterValues } from '../hooks/useSearch';
import SearchFilters from '../components/SearchFilters';
import { highlightTextReact } from '../utils/highlightText';

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Parse URL parameters
  const query = searchParams.get('q') || '';
  const category = searchParams.get('category') || undefined;
  const brand = searchParams.get('brand') || undefined;
  const minPrice = searchParams.get('min_price')
    ? parseInt(searchParams.get('min_price')!, 10)
    : undefined;
  const maxPrice = searchParams.get('max_price')
    ? parseInt(searchParams.get('max_price')!, 10)
    : undefined;
  const inStock = searchParams.get('in_stock') === 'true';
  const sort = (searchParams.get('sort') as FilterValues['sort']) || 'popular';
  const page = parseInt(searchParams.get('page') || '1', 10);

  // Build filters from URL
  const filters: FilterValues = {
    category,
    brand,
    min_price: minPrice,
    max_price: maxPrice,
    in_stock: inStock || undefined,
    sort,
    page,
    limit: 20,
  };

  // Fetch search results
  const { products, totalCount, totalPages, isLoading, error } = useProductSearch(
    query,
    filters
  );

  // Handle filter changes
  const handleFilterApply = (newFilters: Partial<FilterValues>) => {
    const params = new URLSearchParams(searchParams);

    // Update filters
    if (newFilters.minPrice !== undefined) {
      params.set('min_price', newFilters.minPrice.toString());
    } else {
      params.delete('min_price');
    }

    if (newFilters.maxPrice !== undefined) {
      params.set('max_price', newFilters.maxPrice.toString());
    } else {
      params.delete('max_price');
    }

    if (newFilters.brand) {
      params.set('brand', newFilters.brand);
    } else {
      params.delete('brand');
    }

    if (newFilters.inStock) {
      params.set('in_stock', 'true');
    } else {
      params.delete('in_stock');
    }

    // Reset to page 1 when filters change
    params.set('page', '1');

    setSearchParams(params);
  };

  // Handle clear filters
  const handleClearFilters = () => {
    const params = new URLSearchParams();
    params.set('q', query);
    if (sort !== 'popular') {
      params.set('sort', sort);
    }
    setSearchParams(params);
  };

  // Handle sort change
  const handleSortChange = (newSort: string) => {
    const params = new URLSearchParams(searchParams);
    params.set('sort', newSort);
    params.set('page', '1'); // Reset to page 1
    setSearchParams(params);
  };

  // Handle page change
  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams);
    params.set('page', newPage.toString());
    setSearchParams(params);

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Redirect to home if no query
  useEffect(() => {
    if (!query) {
      navigate('/');
    }
  }, [query, navigate]);

  if (!query) {
    return null;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">
          Search Results for "{query}"
        </h1>
        <p className="text-gray-600">
          {totalCount.toLocaleString()}개의 상품을 찾았습니다
        </p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar - Filters */}
        <aside className="w-64 flex-shrink-0">
          <SearchFilters
            initialFilters={{
              minPrice,
              maxPrice,
              brand,
              inStock,
            }}
            onApply={handleFilterApply}
            onClear={handleClearFilters}
            brands={['Apple', 'Samsung', 'LG', 'Sony']} // TODO: Fetch from API
          />
        </aside>

        {/* Main Content */}
        <main className="flex-1">
          {/* Sort Dropdown */}
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm text-gray-600">
              {(page - 1) * 20 + 1} - {Math.min(page * 20, totalCount)} / {totalCount}개
            </div>
            <div className="flex items-center gap-2">
              <label htmlFor="sort" className="text-sm text-gray-700">
                정렬:
              </label>
              <select
                id="sort"
                value={sort}
                onChange={(e) => handleSortChange(e.target.value)}
                data-testid="sort-dropdown"
                className="px-3 py-1 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="popular">인기순</option>
                <option value="price_asc">가격 낮은순</option>
                <option value="price_desc">가격 높은순</option>
                <option value="newest">최신순</option>
                <option value="rating">평점순</option>
              </select>
            </div>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">검색 중...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
              검색 중 오류가 발생했습니다. 다시 시도해주세요.
            </div>
          )}

          {/* No Results */}
          {!isLoading && !error && products.length === 0 && (
            <div
              data-testid="no-results"
              className="text-center py-12 bg-gray-50 rounded-lg"
            >
              <svg
                className="mx-auto h-12 w-12 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <p className="mt-4 text-lg text-gray-600">No products found</p>
              <p className="text-sm text-gray-500">
                다른 검색어로 시도하거나 필터를 조정해보세요
              </p>
            </div>
          )}

          {/* Product Grid */}
          {!isLoading && !error && products.length > 0 && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {products.map((product) => {
                  const highlightedName = highlightTextReact(product.name, query);

                  return (
                    <div
                      key={product.id}
                      data-testid="product-card"
                      className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
                      onClick={() => navigate(`/products/${product.id}`)}
                    >
                      {/* Product Image */}
                      <div className="aspect-w-1 aspect-h-1 bg-gray-100">
                        <img
                          src={product.images[0] || '/placeholder.png'}
                          alt={product.name}
                          data-testid="product-image"
                          className="w-full h-48 object-cover"
                        />
                      </div>

                      {/* Product Info */}
                      <div className="p-4">
                        {/* Brand */}
                        <div
                          data-testid="product-brand"
                          className="text-xs text-gray-500 mb-1"
                        >
                          {product.brand}
                        </div>

                        {/* Name with Highlight */}
                        <h3
                          data-testid="product-name"
                          className="text-sm font-medium text-gray-900 mb-2 line-clamp-2"
                        >
                          {highlightedName.map((part, i) =>
                            part.highlighted ? (
                              <mark
                                key={i}
                                data-testid="highlighted-query"
                                className="bg-yellow-200"
                              >
                                {part.text}
                              </mark>
                            ) : (
                              <span key={i}>{part.text}</span>
                            )
                          )}
                        </h3>

                        {/* Price */}
                        <div data-testid="product-price" className="mb-2">
                          {product.discounted_price ? (
                            <>
                              <span className="text-lg font-bold text-gray-900">
                                {product.discounted_price.toLocaleString()}원
                              </span>
                              <span className="ml-2 text-sm text-gray-500 line-through">
                                {product.price.toLocaleString()}원
                              </span>
                            </>
                          ) : (
                            <span className="text-lg font-bold text-gray-900">
                              {product.price.toLocaleString()}원
                            </span>
                          )}
                        </div>

                        {/* Rating & Stock */}
                        <div className="flex items-center justify-between text-xs">
                          <div
                            data-testid="product-rating"
                            className="flex items-center gap-1"
                          >
                            <svg
                              className="w-4 h-4 text-yellow-400"
                              fill="currentColor"
                              viewBox="0 0 20 20"
                            >
                              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                            </svg>
                            <span>{product.rating.toFixed(1)}</span>
                            <span className="text-gray-400">
                              ({product.review_count})
                            </span>
                          </div>
                          {product.in_stock ? (
                            <span
                              data-testid="stock-badge"
                              className="text-green-600 font-medium"
                            >
                              In Stock
                            </span>
                          ) : (
                            <span className="text-red-600 font-medium">
                              품절
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="mt-8 flex items-center justify-center gap-2">
                  {/* Previous Button */}
                  <button
                    onClick={() => handlePageChange(page - 1)}
                    disabled={page === 1}
                    data-testid="pagination-previous"
                    className="px-4 py-2 border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                  >
                    이전
                  </button>

                  {/* Page Numbers */}
                  {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                    const pageNum = i + 1;
                    return (
                      <button
                        key={pageNum}
                        onClick={() => handlePageChange(pageNum)}
                        data-testid={`pagination-page-${pageNum}`}
                        className={`px-4 py-2 border rounded-md ${
                          page === pageNum
                            ? 'bg-blue-600 text-white border-blue-600'
                            : 'border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}

                  {/* Next Button */}
                  <button
                    onClick={() => handlePageChange(page + 1)}
                    disabled={page === totalPages}
                    data-testid="pagination-next"
                    className="px-4 py-2 border border-gray-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                  >
                    다음
                  </button>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default SearchPage;
