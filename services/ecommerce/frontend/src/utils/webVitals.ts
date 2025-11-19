/**
 * Web Vitals Measurement and Reporting
 * Google Core Web Vitals (CLS, FID, LCP, FCP, TTFB) 측정
 */

import { onCLS, onFID, onFCP, onLCP, onTTFB, Metric } from "web-vitals";

interface WebVitalsReport {
  name: string;
  value: number;
  rating: "good" | "needs-improvement" | "poor";
  delta: number;
  id: string;
  navigationType: string;
}

/**
 * 성능 지표 임계값 (Google 기준)
 */
const THRESHOLDS = {
  CLS: { good: 0.1, poor: 0.25 }, // Cumulative Layout Shift
  FID: { good: 100, poor: 300 }, // First Input Delay (ms)
  LCP: { good: 2500, poor: 4000 }, // Largest Contentful Paint (ms)
  FCP: { good: 1800, poor: 3000 }, // First Contentful Paint (ms)
  TTFB: { good: 800, poor: 1800 }, // Time to First Byte (ms)
};

/**
 * 성능 등급 계산
 */
function getRating(
  name: string,
  value: number
): "good" | "needs-improvement" | "poor" {
  const threshold = THRESHOLDS[name as keyof typeof THRESHOLDS];
  if (!threshold) return "good";

  if (value <= threshold.good) return "good";
  if (value <= threshold.poor) return "needs-improvement";
  return "poor";
}

/**
 * 지표를 콘솔에 출력
 */
function logMetric(metric: Metric) {
  const rating = getRating(metric.name, metric.value);

  const emoji = {
    good: "[OK]",
    "needs-improvement": "[WARNING]",
    poor: "[FAIL]",
  }[rating];

  console.log(
    `${emoji} ${metric.name}: ${metric.value.toFixed(2)}${
      metric.name === "CLS" ? "" : "ms"
    } (${rating})`
  );
}

/**
 * 지표를 서버로 전송 (분석용)
 */
function sendMetricToAnalytics(metric: WebVitalsReport) {
  // Google Analytics 4 이벤트 전송
  if (typeof gtag !== "undefined") {
    gtag("event", metric.name, {
      event_category: "Web Vitals",
      value: Math.round(metric.value),
      event_label: metric.id,
      non_interaction: true,
      metric_rating: metric.rating,
    });
  }

  // 자체 분석 서버로 전송 (선택사항)
  const analyticsEndpoint = import.meta.env.VITE_ANALYTICS_ENDPOINT;
  if (analyticsEndpoint) {
    navigator.sendBeacon(
      analyticsEndpoint,
      JSON.stringify({
        ...metric,
        url: window.location.href,
        userAgent: navigator.userAgent,
        timestamp: new Date().toISOString(),
      })
    );
  }
}

/**
 * Web Vitals 측정 시작
 */
export function reportWebVitals(
  onPerfEntry?: (metric: WebVitalsReport) => void
) {
  if (!onPerfEntry && typeof window === "undefined") {
    return;
  }

  const handleMetric = (metric: Metric) => {
    const report: WebVitalsReport = {
      name: metric.name,
      value: metric.value,
      rating: getRating(metric.name, metric.value),
      delta: metric.delta,
      id: metric.id,
      navigationType: metric.navigationType,
    };

    // 콘솔 출력
    logMetric(metric);

    // 분석 서버로 전송
    sendMetricToAnalytics(report);

    // 커스텀 핸들러 호출
    if (onPerfEntry) {
      onPerfEntry(report);
    }
  };

  // Core Web Vitals 측정
  onCLS(handleMetric);
  onFID(handleMetric);
  onLCP(handleMetric);

  // 추가 지표
  onFCP(handleMetric);
  onTTFB(handleMetric);
}

/**
 * 성능 요약 리포트 생성
 */
export function generatePerformanceSummary(): {
  metrics: Record<string, number>;
  overallRating: "good" | "needs-improvement" | "poor";
} {
  const metrics: Record<string, number> = {};

  // PerformanceObserver로 수집된 지표 가져오기
  if (typeof window !== "undefined" && window.performance) {
    const navigation = performance.getEntriesByType(
      "navigation"
    )[0] as PerformanceNavigationTiming;
    const paint = performance.getEntriesByType("paint");

    if (navigation) {
      metrics.TTFB = navigation.responseStart - navigation.requestStart;
      metrics.domContentLoaded =
        navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart;
      metrics.loadComplete = navigation.loadEventEnd - navigation.loadEventStart;
    }

    paint.forEach((entry) => {
      if (entry.name === "first-contentful-paint") {
        metrics.FCP = entry.startTime;
      }
    });
  }

  // 전체 등급 계산 (최악 등급 사용)
  const ratings = Object.entries(metrics).map(([name, value]) =>
    getRating(name, value)
  );
  const overallRating = ratings.includes("poor")
    ? "poor"
    : ratings.includes("needs-improvement")
    ? "needs-improvement"
    : "good";

  return { metrics, overallRating };
}

/**
 * 커스텀 성능 마크 추가
 */
export function markPerformance(name: string) {
  if (typeof window !== "undefined" && window.performance) {
    performance.mark(name);
  }
}

/**
 * 커스텀 성능 측정
 */
export function measurePerformance(
  name: string,
  startMark: string,
  endMark: string
): number | null {
  if (typeof window !== "undefined" && window.performance) {
    try {
      performance.measure(name, startMark, endMark);
      const measure = performance.getEntriesByName(name, "measure")[0];
      return measure?.duration || null;
    } catch (e) {
      console.error(`[Performance] Failed to measure ${name}:`, e);
      return null;
    }
  }
  return null;
}

/**
 * React Component 렌더링 시간 측정 Hook
 */
export function usePerformanceMark(componentName: string) {
  React.useEffect(() => {
    const mountMark = `${componentName}-mount`;
    markPerformance(mountMark);

    return () => {
      const unmountMark = `${componentName}-unmount`;
      markPerformance(unmountMark);

      const duration = measurePerformance(
        `${componentName}-lifetime`,
        mountMark,
        unmountMark
      );

      if (duration !== null) {
        console.log(`[Performance] ${componentName} lifetime: ${duration.toFixed(2)}ms`);
      }
    };
  }, [componentName]);
}

/**
 * Long Task 감지 (50ms 이상 blocking 작업)
 */
export function observeLongTasks(
  callback: (duration: number, startTime: number) => void
) {
  if (
    typeof window !== "undefined" &&
    "PerformanceObserver" in window &&
    PerformanceObserver.supportedEntryTypes?.includes("longtask")
  ) {
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        callback(entry.duration, entry.startTime);
        console.warn(
          `[Performance] Long Task detected: ${entry.duration.toFixed(2)}ms at ${entry.startTime.toFixed(2)}ms`
        );
      }
    });

    observer.observe({ entryTypes: ["longtask"] });

    return () => observer.disconnect();
  }

  return () => {};
}

/**
 * 리소스 로딩 시간 분석
 */
export function analyzeResourceTimings() {
  if (typeof window !== "undefined" && window.performance) {
    const resources = performance.getEntriesByType(
      "resource"
    ) as PerformanceResourceTiming[];

    const slowResources = resources
      .filter((r) => r.duration > 1000) // 1초 이상
      .sort((a, b) => b.duration - a.duration)
      .slice(0, 10);

    console.group("[Performance] Slow Resources (>1s)");
    slowResources.forEach((resource) => {
      console.log(
        `${resource.name}: ${resource.duration.toFixed(2)}ms (${resource.initiatorType})`
      );
    });
    console.groupEnd();

    return slowResources;
  }

  return [];
}

// React import (타입만)
import React from "react";

// gtag 타입 선언
declare global {
  function gtag(...args: any[]): void;
}
