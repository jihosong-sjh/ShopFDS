/**
 * useSearchHistory Hook
 *
 * Manages recent search queries in LocalStorage.
 * Stores up to 10 recent searches with timestamps.
 */

import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

const STORAGE_KEY = 'search-history';
const MAX_HISTORY_ITEMS = 10;

export interface SearchHistoryItem {
  query: string;
  timestamp: number; // Unix timestamp in milliseconds
}

/**
 * Load search history from LocalStorage
 */
function loadSearchHistory(): SearchHistoryItem[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];

    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) return [];

    // Validate structure
    return parsed.filter(
      (item) =>
        typeof item === 'object' &&
        typeof item.query === 'string' &&
        typeof item.timestamp === 'number'
    );
  } catch (error) {
    console.error('[useSearchHistory] Failed to load search history:', error);
    return [];
  }
}

/**
 * Save search history to LocalStorage
 */
function saveSearchHistory(history: SearchHistoryItem[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  } catch (error) {
    console.error('[useSearchHistory] Failed to save search history:', error);
  }
}

/**
 * useSearchHistory Hook
 *
 * Provides methods to manage recent search queries.
 */
export function useSearchHistory() {
  const [history, setHistory] = useState<SearchHistoryItem[]>([]);

  // Load history on mount
  useEffect(() => {
    const loaded = loadSearchHistory();
    setHistory(loaded);
  }, []);

  /**
   * Add search query to history
   *
   * - Removes duplicate if exists
   * - Adds new query to the beginning
   * - Keeps only MAX_HISTORY_ITEMS most recent items
   * - Optionally syncs with backend (authenticated users)
   */
  const addSearch = useCallback(
    async (query: string, syncBackend: boolean = false) => {
      if (!query || query.trim().length === 0) return;

      const trimmedQuery = query.trim();
      const timestamp = Date.now();

      setHistory((prev) => {
        // Remove duplicate if exists (case-insensitive)
        const filtered = prev.filter(
          (item) => item.query.toLowerCase() !== trimmedQuery.toLowerCase()
        );

        // Add new search at the beginning
        const updated = [{ query: trimmedQuery, timestamp }, ...filtered];

        // Keep only MAX_HISTORY_ITEMS
        const limited = updated.slice(0, MAX_HISTORY_ITEMS);

        // Save to LocalStorage
        saveSearchHistory(limited);

        return limited;
      });

      // Optionally sync with backend (for authenticated users)
      if (syncBackend) {
        try {
          await api.post('/v1/search/history', { query: trimmedQuery });
        } catch (error) {
          // Silently fail - LocalStorage is primary storage
          console.debug('[useSearchHistory] Backend sync failed (non-critical):', error);
        }
      }
    },
    []
  );

  /**
   * Remove specific search query from history
   */
  const removeSearch = useCallback((query: string) => {
    setHistory((prev) => {
      const filtered = prev.filter(
        (item) => item.query.toLowerCase() !== query.toLowerCase()
      );
      saveSearchHistory(filtered);
      return filtered;
    });
  }, []);

  /**
   * Clear all search history
   */
  const clearHistory = useCallback(() => {
    setHistory([]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  /**
   * Get recent searches (most recent first)
   */
  const getRecentSearches = useCallback(
    (limit: number = MAX_HISTORY_ITEMS): SearchHistoryItem[] => {
      return history.slice(0, limit);
    },
    [history]
  );

  /**
   * Check if query exists in history
   */
  const hasSearch = useCallback(
    (query: string): boolean => {
      return history.some(
        (item) => item.query.toLowerCase() === query.toLowerCase()
      );
    },
    [history]
  );

  return {
    history,
    addSearch,
    removeSearch,
    clearHistory,
    getRecentSearches,
    hasSearch,
  };
}

export default useSearchHistory;
