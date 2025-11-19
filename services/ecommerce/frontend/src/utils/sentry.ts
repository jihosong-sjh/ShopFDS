/**
 * Sentry Error Tracking Setup
 * 프로덕션 에러 추적 및 성능 모니터링
 */

import * as Sentry from "@sentry/react";
import { BrowserTracing } from "@sentry/tracing";

/**
 * Sentry 초기화
 */
export function initSentry() {
  const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN;
  const ENVIRONMENT = import.meta.env.VITE_ENVIRONMENT || "development";

  if (!SENTRY_DSN || ENVIRONMENT === "development") {
    console.log("[Sentry] Skipped in development mode");
    return;
  }

  Sentry.init({
    dsn: SENTRY_DSN,
    environment: ENVIRONMENT,
    integrations: [
      new BrowserTracing(),
      new Sentry.Replay({
        maskAllText: true, // 민감 정보 마스킹
        blockAllMedia: true,
      }),
    ],

    // 성능 모니터링
    tracesSampleRate: ENVIRONMENT === "production" ? 0.1 : 1.0, // 프로덕션 10%, 개발 100%

    // 세션 리플레이
    replaysSessionSampleRate: 0.1, // 세션의 10%
    replaysOnErrorSampleRate: 1.0, // 에러 발생 시 100%

    // 민감 정보 필터링
    beforeSend(event, hint) {
      // 로컬스토리지 정보 제거
      if (event.breadcrumbs) {
        event.breadcrumbs = event.breadcrumbs.filter(
          (breadcrumb) => breadcrumb.category !== "localstorage"
        );
      }

      // 쿠키 정보 제거
      if (event.request?.cookies) {
        delete event.request.cookies;
      }

      // URL에서 민감 정보 제거 (토큰, API 키 등)
      if (event.request?.url) {
        event.request.url = event.request.url.replace(
          /([?&])(token|api_key|secret)=[^&]*/gi,
          "$1$2=***"
        );
      }

      return event;
    },

    // 무시할 에러 패턴
    ignoreErrors: [
      "ResizeObserver loop limit exceeded",
      "Non-Error promise rejection captured",
      "Network request failed",
      "Failed to fetch",
    ],

    // 디버그 옵션
    debug: ENVIRONMENT !== "production",
  });

  // 사용자 정보 설정
  const user = JSON.parse(localStorage.getItem("user") || "{}");
  if (user.id) {
    Sentry.setUser({
      id: user.id,
      email: user.email,
    });
  }

  console.log(`[Sentry] Initialized in ${ENVIRONMENT} mode`);
}

/**
 * 수동 에러 리포팅
 */
export function captureError(
  error: Error,
  context?: Record<string, any>
) {
  Sentry.captureException(error, {
    contexts: context,
  });
}

/**
 * 커스텀 이벤트 추적
 */
export function captureMessage(
  message: string,
  level: Sentry.SeverityLevel = "info"
) {
  Sentry.captureMessage(message, level);
}

/**
 * 성능 추적
 */
export function startTransaction(name: string, op: string) {
  return Sentry.startTransaction({
    name,
    op,
  });
}
