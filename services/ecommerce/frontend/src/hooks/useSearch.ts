/**
 * useSearch Hook
 *
 * Provides search functionality with autocomplete, debouncing, and React Query.
 * Handles search queries, autocomplete suggestions, and product search results.
 */

import { useQuery } from '@tanstack/react-query';
import { useState, useEffect, useCallback } from 'react';
import debounce from 'lodash.debounce';
import api from '../services/api';

// Types
export interface AutocompleteSuggestion {
  type: 'product' | 'brand' | 'category';
  text: string;
  product_id?: string;
  image_url?: string;
}

export interface AutocompleteResponse {
  suggestions: AutocompleteSuggestion[];
}

export interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  discounted_price?: number;
  images: string[];
  brand: string;
  category: string;
  stock: number;
  in_stock: boolean;
  rating: number;
  review_count: number;
}

export interface SearchFilters {
  category?: string;
  brand?: string;
  min_price?: number;
  max_price?: number;
  in_stock?: boolean;
  sort?: 'popular' | 'price_asc' | 'price_desc' | 'newest' | 'rating';
  page?: number;
  limit?: number;
}

export interface ProductSearchResponse {
  products: Product[];
  total_count: number;
  page: number;
  total_pages: number;
  filters_applied: SearchFilters & { query: string };
}

/**
 * useAutocomplete Hook
 *
 * Provides autocomplete suggestions with debouncing.
 */
export function useAutocomplete(query: string, limit: number = 10) {
  const [debouncedQuery, setDebouncedQuery] = useState(query);

  // Debounce search query (300ms delay)
  useEffect(() => {
    const debounceFn = debounce((value: string) => {
      setDebouncedQuery(value);
    }, 300);

    debounceFn(query);

    return () => {
      debounceFn.cancel();
    };
  }, [query]);

  // Fetch autocomplete suggestions
  const { data, isLoading, error } = useQuery<AutocompleteResponse>({
    queryKey: ['autocomplete', debouncedQuery, limit],
    queryFn: async () => {
      const response = await api.get('/v1/search/autocomplete', {
        params: { q: debouncedQuery, limit },
      });
      return response.data;
    },
    enabled: debouncedQuery.length >= 2, // Only fetch if query >= 2 characters
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return {
    suggestions: data?.suggestions || [],
    isLoading,
    error,
  };
}

/**
 * useProductSearch Hook
 *
 * Provides product search with filters, sorting, and pagination.
 */
export function useProductSearch(query: string, filters: SearchFilters = {}) {
  const {
    category,
    brand,
    min_price,
    max_price,
    in_stock,
    sort = 'popular',
    page = 1,
    limit = 20,
  } = filters;

  // Fetch product search results
  const { data, isLoading, error, refetch } = useQuery<ProductSearchResponse>({
    queryKey: ['productSearch', query, category, brand, min_price, max_price, in_stock, sort, page, limit],
    queryFn: async () => {
      const response = await api.get('/v1/search/products', {
        params: {
          q: query,
          category,
          brand,
          min_price,
          max_price,
          in_stock,
          sort,
          page,
          limit,
        },
      });
      return response.data;
    },
    enabled: query.length >= 1, // Only fetch if query exists
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  return {
    products: data?.products || [],
    totalCount: data?.total_count || 0,
    page: data?.page || 1,
    totalPages: data?.total_pages || 0,
    filtersApplied: data?.filters_applied,
    isLoading,
    error,
    refetch,
  };
}

/**
 * useSearch Hook (Combined)
 *
 * Main search hook that combines autocomplete and product search.
 */
export function useSearch() {
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<SearchFilters>({});
  const [showAutocomplete, setShowAutocomplete] = useState(false);

  // Autocomplete
  const autocomplete = useAutocomplete(query);

  // Product search (only when submitted)
  const [searchQuery, setSearchQuery] = useState('');
  const productSearch = useProductSearch(searchQuery, filters);

  // Handle search submission
  const handleSearch = useCallback((newQuery: string) => {
    setSearchQuery(newQuery);
    setShowAutocomplete(false);
  }, []);

  // Handle filter changes
  const handleFilterChange = useCallback((newFilters: SearchFilters) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  }, []);

  // Clear filters
  const clearFilters = useCallback(() => {
    setFilters({});
  }, []);

  return {
    // Query state
    query,
    setQuery,
    searchQuery,
    handleSearch,

    // Autocomplete
    autocomplete: {
      ...autocomplete,
      show: showAutocomplete,
      setShow: setShowAutocomplete,
    },

    // Product search
    productSearch,

    // Filters
    filters,
    handleFilterChange,
    clearFilters,
  };
}

export default useSearch;
