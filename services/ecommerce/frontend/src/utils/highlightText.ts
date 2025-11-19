/**
 * Text Highlighting Utility
 *
 * Highlights search query in text by wrapping matched substrings with <mark> tags.
 * Supports case-insensitive matching and multiple occurrences.
 */

export interface HighlightedTextPart {
  text: string;
  highlighted: boolean;
}

/**
 * Split text into parts with highlighted search query
 *
 * @param text - Original text to search in
 * @param query - Search query to highlight
 * @returns Array of text parts with highlight flag
 *
 * @example
 * highlightText("iPhone 15 Pro Max", "iPhone")
 * // Returns: [
 * //   { text: "iPhone", highlighted: true },
 * //   { text: " 15 Pro Max", highlighted: false }
 * // ]
 */
export function highlightText(text: string, query: string): HighlightedTextPart[] {
  if (!query || !text) {
    return [{ text, highlighted: false }];
  }

  // Escape special regex characters in query
  const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

  // Create case-insensitive regex
  const regex = new RegExp(`(${escapedQuery})`, 'gi');

  // Split text by query matches
  const parts = text.split(regex);

  // Map parts to highlighted segments
  return parts
    .filter((part) => part.length > 0) // Remove empty strings
    .map((part) => ({
      text: part,
      highlighted: regex.test(part), // Check if part matches query
    }));
}

/**
 * Render highlighted text as HTML string
 *
 * @param text - Original text
 * @param query - Search query to highlight
 * @param highlightClass - CSS class for highlighted text (default: "highlight")
 * @returns HTML string with <mark> tags
 *
 * @example
 * highlightTextHTML("Galaxy S24 Ultra", "Galaxy", "bg-yellow-200")
 * // Returns: '<mark class="bg-yellow-200">Galaxy</mark> S24 Ultra'
 */
export function highlightTextHTML(
  text: string,
  query: string,
  highlightClass: string = 'highlight'
): string {
  const parts = highlightText(text, query);

  return parts
    .map((part) =>
      part.highlighted
        ? `<mark class="${highlightClass}">${part.text}</mark>`
        : part.text
    )
    .join('');
}

/**
 * Render highlighted text as React elements
 *
 * @param text - Original text
 * @param query - Search query to highlight
 * @param highlightClassName - CSS class for highlighted text
 * @returns Array of React element props
 *
 * @example
 * const parts = highlightTextReact("MacBook Pro 14", "Pro");
 * return (
 *   <span>
 *     {parts.map((part, i) =>
 *       part.highlighted ? (
 *         <mark key={i} className="bg-yellow-200">{part.text}</mark>
 *       ) : (
 *         <span key={i}>{part.text}</span>
 *       )
 *     )}
 *   </span>
 * );
 */
export function highlightTextReact(text: string, query: string): HighlightedTextPart[] {
  return highlightText(text, query);
}

/**
 * Check if text contains query (case-insensitive)
 *
 * @param text - Text to search in
 * @param query - Query to search for
 * @returns true if text contains query
 */
export function containsQuery(text: string, query: string): boolean {
  if (!query || !text) return false;
  return text.toLowerCase().includes(query.toLowerCase());
}

/**
 * Get first highlighted snippet from text
 *
 * Extracts a snippet around the first occurrence of the query.
 * Useful for showing search result previews.
 *
 * @param text - Full text
 * @param query - Search query
 * @param maxLength - Maximum snippet length (default: 150)
 * @returns Snippet with highlighted query
 *
 * @example
 * getHighlightedSnippet(
 *   "This is a very long product description with iPhone mentioned here...",
 *   "iPhone",
 *   50
 * )
 * // Returns: "...description with iPhone mentioned..."
 */
export function getHighlightedSnippet(
  text: string,
  query: string,
  maxLength: number = 150
): string {
  if (!query || !text) return text.substring(0, maxLength);

  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  const index = lowerText.indexOf(lowerQuery);

  if (index === -1) {
    // Query not found, return beginning
    return text.substring(0, maxLength) + (text.length > maxLength ? '...' : '');
  }

  // Calculate snippet bounds
  const halfLength = Math.floor(maxLength / 2);
  let start = Math.max(0, index - halfLength);
  let end = Math.min(text.length, index + query.length + halfLength);

  // Adjust if snippet is too short
  if (end - start < maxLength) {
    if (start === 0) {
      end = Math.min(text.length, maxLength);
    } else {
      start = Math.max(0, end - maxLength);
    }
  }

  // Add ellipsis if needed
  const prefix = start > 0 ? '...' : '';
  const suffix = end < text.length ? '...' : '';

  return prefix + text.substring(start, end) + suffix;
}

export default {
  highlightText,
  highlightTextHTML,
  highlightTextReact,
  containsQuery,
  getHighlightedSnippet,
};
