/**
 * ErrorBoundary Component
 * React Error Boundary 패턴 구현
 */

import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("[ErrorBoundary] Caught error:", error, errorInfo);

    this.setState({
      error,
      errorInfo,
    });

    // 에러 리포팅 (Sentry 등)
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900 px-4"
          role="alert"
          aria-live="assertive"
        >
          <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 dark:bg-red-900 rounded-full mb-4">
              <svg
                className="w-6 h-6 text-red-600 dark:text-red-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>

            <h2 className="text-xl font-bold text-center text-gray-900 dark:text-white mb-2">
              앗! 오류가 발생했습니다
            </h2>

            <p className="text-center text-gray-600 dark:text-gray-400 mb-4">
              일시적인 문제가 발생했습니다. 페이지를 새로고침하거나 다시
              시도해주세요.
            </p>

            {/* 개발 환경: 에러 상세 정보 표시 */}
            {process.env.NODE_ENV === "development" &&
              this.state.error &&
              this.state.errorInfo && (
                <details className="mb-4 p-3 bg-gray-100 dark:bg-gray-700 rounded text-sm">
                  <summary className="cursor-pointer font-semibold text-gray-700 dark:text-gray-300">
                    에러 상세 정보 (개발 전용)
                  </summary>
                  <div className="mt-2 text-red-600 dark:text-red-400 overflow-auto max-h-40">
                    <p className="font-semibold">{this.state.error.toString()}</p>
                    <pre className="text-xs mt-2 whitespace-pre-wrap">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </div>
                </details>
              )}

            <div className="flex gap-3">
              <button
                onClick={this.handleReset}
                className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
              >
                다시 시도
              </button>
              <button
                onClick={() => (window.location.href = "/")}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
              >
                홈으로 이동
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * useErrorBoundary Hook
 * 함수형 컴포넌트에서 에러를 ErrorBoundary로 전파
 */
export const useErrorBoundary = () => {
  const [, setState] = React.useState();

  return React.useCallback((error: Error) => {
    setState(() => {
      throw error;
    });
  }, []);
};
