/**
 * SearchBar Component
 *
 * Search bar with autocomplete dropdown showing:
 * - Product suggestions (with images)
 * - Brand suggestions
 * - Category suggestions
 * - Recent search history
 */

import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAutocomplete } from '../hooks/useSearch';
import { useSearchHistory } from '../hooks/useSearchHistory';
import { highlightTextReact } from '../utils/highlightText';

interface SearchBarProps {
  placeholder?: string;
  className?: string;
  autoFocus?: boolean;
  onSearch?: (query: string) => void;
}

export function SearchBar({
  placeholder = '상품, 브랜드, 카테고리 검색',
  className = '',
  autoFocus = false,
  onSearch,
}: SearchBarProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Hooks
  const { suggestions, isLoading } = useAutocomplete(query);
  const { history, addSearch, getRecentSearches } = useSearchHistory();

  // Handle search submission
  const handleSubmit = (searchQuery: string) => {
    if (!searchQuery.trim()) return;

    // Add to history
    addSearch(searchQuery, true); // true = sync with backend

    // Close dropdown
    setShowDropdown(false);

    // Navigate to search page
    navigate(`/search?q=${encodeURIComponent(searchQuery)}`);

    // Optional callback
    if (onSearch) {
      onSearch(searchQuery);
    }
  };

  // Handle form submit
  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSubmit(query);
  };

  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    setShowDropdown(value.length >= 2 || value.length === 0);
  };

  // Handle input focus
  const handleFocus = () => {
    setShowDropdown(true);
  };

  // Handle suggestion click
  const handleSuggestionClick = (suggestionQuery: string) => {
    setQuery(suggestionQuery);
    handleSubmit(suggestionQuery);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowDropdown(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Recent searches (show when input is empty)
  const recentSearches = getRecentSearches(5);
  const showRecentSearches = query.length === 0 && recentSearches.length > 0;

  return (
    <div className={`relative ${className}`}>
      <form onSubmit={handleFormSubmit} className="relative">
        {/* Search Input */}
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleInputChange}
          onFocus={handleFocus}
          placeholder={placeholder}
          autoFocus={autoFocus}
          data-testid="search-input"
          className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />

        {/* Search Icon */}
        <button
          type="submit"
          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
          aria-label="Search"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </button>
      </form>

      {/* Autocomplete Dropdown */}
      {showDropdown && (
        <div
          ref={dropdownRef}
          data-testid="autocomplete-dropdown"
          className="absolute z-50 w-full mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-96 overflow-y-auto"
        >
          {/* Loading State */}
          {isLoading && query.length >= 2 && (
            <div className="px-4 py-3 text-sm text-gray-500">
              검색 중...
            </div>
          )}

          {/* Recent Searches */}
          {showRecentSearches && (
            <div className="py-2">
              <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase">
                최근 검색어
              </div>
              {recentSearches.map((item, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(item.query)}
                  data-testid="recent-search-item"
                  className="w-full px-4 py-2 text-left hover:bg-gray-50 flex items-center gap-2"
                >
                  <svg
                    className="w-4 h-4 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <span className="text-sm">{item.query}</span>
                </button>
              ))}
            </div>
          )}

          {/* Autocomplete Suggestions */}
          {!isLoading && query.length >= 2 && suggestions.length > 0 && (
            <div className="py-2">
              {suggestions.map((suggestion, index) => {
                const highlighted = highlightTextReact(suggestion.text, query);

                return (
                  <button
                    key={index}
                    onClick={() => handleSuggestionClick(suggestion.text)}
                    data-testid={`autocomplete-${suggestion.type}`}
                    className="w-full px-4 py-2 text-left hover:bg-gray-50 flex items-center gap-3"
                  >
                    {/* Product Image */}
                    {suggestion.type === 'product' && suggestion.image_url && (
                      <img
                        src={suggestion.image_url}
                        alt={suggestion.text}
                        className="w-10 h-10 object-cover rounded"
                      />
                    )}

                    {/* Icon for Brand/Category */}
                    {suggestion.type === 'brand' && (
                      <div className="w-10 h-10 flex items-center justify-center bg-gray-100 rounded">
                        <svg
                          className="w-5 h-5 text-gray-400"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                          />
                        </svg>
                      </div>
                    )}

                    {suggestion.type === 'category' && (
                      <div className="w-10 h-10 flex items-center justify-center bg-gray-100 rounded">
                        <svg
                          className="w-5 h-5 text-gray-400"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
                          />
                        </svg>
                      </div>
                    )}

                    {/* Highlighted Text */}
                    <div className="flex-1">
                      <div className="text-sm">
                        {highlighted.map((part, i) =>
                          part.highlighted ? (
                            <mark
                              key={i}
                              data-testid="autocomplete-highlight"
                              className="bg-yellow-200 font-bold"
                            >
                              {part.text}
                            </mark>
                          ) : (
                            <span key={i}>{part.text}</span>
                          )
                        )}
                      </div>
                      {suggestion.type !== 'product' && (
                        <div className="text-xs text-gray-500 capitalize">
                          {suggestion.type === 'brand' ? '브랜드' : '카테고리'}
                        </div>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {/* No Results */}
          {!isLoading &&
            query.length >= 2 &&
            suggestions.length === 0 &&
            !showRecentSearches && (
              <div className="px-4 py-3 text-sm text-gray-500">
                검색 결과가 없습니다.
              </div>
            )}
        </div>
      )}
    </div>
  );
}

export default SearchBar;
