/**
 * Accessibility Utilities
 * WCAG AA 접근성 지원 유틸리티
 */

/**
 * 키보드 이벤트 핸들러 (Enter, Space 키 처리)
 * @param handler 실행할 함수
 * @returns KeyboardEvent 핸들러
 */
export const handleKeyPress = (handler: () => void) => {
  return (event: React.KeyboardEvent) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handler();
    }
  };
};

/**
 * ESC 키 핸들러 (모달 닫기 등)
 * @param handler 실행할 함수
 * @returns KeyboardEvent 핸들러
 */
export const handleEscapeKey = (handler: () => void) => {
  return (event: React.KeyboardEvent) => {
    if (event.key === "Escape") {
      handler();
    }
  };
};

/**
 * 포커스 트랩 (모달 내부 포커스 유지)
 * @param containerRef 컨테이너 ref
 */
export const useFocusTrap = (containerRef: React.RefObject<HTMLElement>) => {
  React.useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const focusableElements = container.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;

      if (e.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    container.addEventListener("keydown", handleTab);
    firstElement?.focus();

    return () => {
      container.removeEventListener("keydown", handleTab);
    };
  }, [containerRef]);
};

/**
 * ARIA 라이브 리전 알림 (스크린 리더)
 * @param message 알림 메시지
 * @param politeness "polite" | "assertive"
 */
export const announceToScreenReader = (
  message: string,
  politeness: "polite" | "assertive" = "polite"
) => {
  const liveRegion = document.createElement("div");
  liveRegion.setAttribute("role", "status");
  liveRegion.setAttribute("aria-live", politeness);
  liveRegion.setAttribute("aria-atomic", "true");
  liveRegion.className = "sr-only"; // Tailwind: screen reader only
  liveRegion.textContent = message;

  document.body.appendChild(liveRegion);

  setTimeout(() => {
    document.body.removeChild(liveRegion);
  }, 1000);
};

/**
 * 색상 대비 검증 (WCAG AA: 4.5:1)
 * @param foreground 전경색 (hex)
 * @param background 배경색 (hex)
 * @returns 대비 비율
 */
export const getContrastRatio = (
  foreground: string,
  background: string
): number => {
  const getLuminance = (hex: string): number => {
    const rgb = parseInt(hex.slice(1), 16);
    const r = ((rgb >> 16) & 0xff) / 255;
    const g = ((rgb >> 8) & 0xff) / 255;
    const b = (rgb & 0xff) / 255;

    const [rs, gs, bs] = [r, g, b].map((c) =>
      c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
    );

    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
  };

  const l1 = getLuminance(foreground);
  const l2 = getLuminance(background);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);

  return (lighter + 0.05) / (darker + 0.05);
};

/**
 * 스크롤 가능 영역 키보드 네비게이션
 * @param containerRef 스크롤 컨테이너 ref
 */
export const useKeyboardScroll = (
  containerRef: React.RefObject<HTMLElement>
) => {
  React.useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const scrollAmount = 40;

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          container.scrollTop += scrollAmount;
          break;
        case "ArrowUp":
          e.preventDefault();
          container.scrollTop -= scrollAmount;
          break;
        case "PageDown":
          e.preventDefault();
          container.scrollTop += container.clientHeight;
          break;
        case "PageUp":
          e.preventDefault();
          container.scrollTop -= container.clientHeight;
          break;
        case "Home":
          e.preventDefault();
          container.scrollTop = 0;
          break;
        case "End":
          e.preventDefault();
          container.scrollTop = container.scrollHeight;
          break;
      }
    };

    container.addEventListener("keydown", handleKeyDown);
    return () => {
      container.removeEventListener("keydown", handleKeyDown);
    };
  }, [containerRef]);
};

/**
 * 접근성 체크리스트 (개발자 도구)
 */
export const checkAccessibility = () => {
  const issues: string[] = [];

  // 이미지 alt 속성 검사
  const images = document.querySelectorAll("img");
  images.forEach((img, index) => {
    if (!img.alt) {
      issues.push(`Image ${index + 1}: Missing alt attribute`);
    }
  });

  // 버튼 aria-label 검사 (아이콘 버튼)
  const buttons = document.querySelectorAll("button");
  buttons.forEach((btn, index) => {
    if (!btn.textContent?.trim() && !btn.getAttribute("aria-label")) {
      issues.push(`Button ${index + 1}: Missing aria-label or text content`);
    }
  });

  // 링크 텍스트 검사
  const links = document.querySelectorAll("a");
  links.forEach((link, index) => {
    if (!link.textContent?.trim() && !link.getAttribute("aria-label")) {
      issues.push(`Link ${index + 1}: Missing text or aria-label`);
    }
  });

  if (issues.length > 0) {
    console.warn("[Accessibility Issues]", issues);
  } else {
    console.log("[Accessibility] No issues found");
  }

  return issues;
};

// React import (타입만)
import React from "react";
