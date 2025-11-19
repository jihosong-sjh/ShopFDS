/**
 * ThemeToggle Component
 * 다크 모드 전환 버튼 (접근성 지원)
 */

import { useThemeStore } from "../stores/themeStore";

export const ThemeToggle = () => {
  const { theme, resolvedTheme, setTheme } = useThemeStore();

  const handleToggle = () => {
    const newTheme = resolvedTheme === "light" ? "dark" : "light";
    setTheme(newTheme);
  };

  return (
    <button
      onClick={handleToggle}
      className="relative p-2 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
      aria-label={
        resolvedTheme === "light"
          ? "다크 모드로 전환"
          : "라이트 모드로 전환"
      }
      title={
        resolvedTheme === "light"
          ? "다크 모드로 전환"
          : "라이트 모드로 전환"
      }
    >
      {resolvedTheme === "light" ? (
        <svg
          className="w-5 h-5 text-gray-800"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
          />
        </svg>
      ) : (
        <svg
          className="w-5 h-5 text-yellow-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
          />
        </svg>
      )}
    </button>
  );
};

/**
 * ThemeToggleWithOptions Component
 * 다크 모드 드롭다운 선택 (Light / Dark / System)
 */
export const ThemeToggleWithOptions = () => {
  const { theme, setTheme } = useThemeStore();

  return (
    <div className="relative inline-block text-left">
      <select
        value={theme}
        onChange={(e) => setTheme(e.target.value as "light" | "dark" | "system")}
        className="block w-full px-4 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        aria-label="테마 선택"
      >
        <option value="light">라이트 모드</option>
        <option value="dark">다크 모드</option>
        <option value="system">시스템 설정</option>
      </select>
    </div>
  );
};
