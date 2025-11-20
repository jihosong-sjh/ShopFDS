/**
 * Theme Store (Zustand)
 * 다크 모드 상태 관리 및 시스템 설정 감지
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark" | "system";

interface ThemeState {
  theme: Theme;
  resolvedTheme: "light" | "dark"; // 실제 적용되는 테마
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

// 시스템 다크 모드 감지
const getSystemTheme = (): "light" | "dark" => {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
};

// 테마 적용 (HTML root element)
const applyTheme = (theme: "light" | "dark") => {
  const root = document.documentElement;
  if (theme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
};

// 실제 테마 계산
const resolveTheme = (theme: Theme): "light" | "dark" => {
  if (theme === "system") {
    return getSystemTheme();
  }
  return theme;
};

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "system",
      resolvedTheme: getSystemTheme(),

      setTheme: (theme: Theme) => {
        const resolved = resolveTheme(theme);
        applyTheme(resolved);
        set({ theme, resolvedTheme: resolved });
      },

      toggleTheme: () => {
        const current = get().resolvedTheme;
        const newTheme = current === "light" ? "dark" : "light";
        applyTheme(newTheme);
        set({ theme: newTheme, resolvedTheme: newTheme });
      },
    }),
    {
      name: "theme-storage",
      // 초기화 시 테마 적용
      onRehydrateStorage: () => (state) => {
        if (state) {
          const resolved = resolveTheme(state.theme);
          applyTheme(resolved);
          state.resolvedTheme = resolved;
        }
      },
    }
  )
);

// 시스템 테마 변경 감지 리스너
if (typeof window !== "undefined") {
  const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  mediaQuery.addEventListener("change", (e) => {
    const store = useThemeStore.getState();
    if (store.theme === "system") {
      const resolved = e.matches ? "dark" : "light";
      applyTheme(resolved);
      useThemeStore.setState({ resolvedTheme: resolved });
    }
  });
}
