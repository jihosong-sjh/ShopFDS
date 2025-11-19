import { useState, useEffect } from 'react';
import { usePWA } from '../hooks/usePWA';

/**
 * PWA 설치 프롬프트 컴포넌트
 *
 * - "홈 화면에 추가" 배너 표시
 * - 사용자가 닫으면 7일 동안 표시하지 않음
 * - iOS 사용자를 위한 별도 안내
 */
export function PWAInstallPrompt() {
  const { isInstallable, isInstalled, promptInstall } = usePWA();
  const [isDismissed, setIsDismissed] = useState(false);
  const [showIOSInstructions, setShowIOSInstructions] = useState(false);

  // handleDismiss 함수를 먼저 정의
  const handleDismiss = () => {
    setIsDismissed(true);
    const dismissUntil = new Date();
    dismissUntil.setDate(dismissUntil.getDate() + 7); // 7일 동안 표시하지 않음
    localStorage.setItem('pwa-install-dismissed-until', dismissUntil.toISOString());
  };

  // 배너 표시 여부 확인
  useEffect(() => {
    const dismissedUntil = localStorage.getItem('pwa-install-dismissed-until');
    if (dismissedUntil) {
      const dismissedDate = new Date(dismissedUntil);
      if (dismissedDate > new Date()) {
        setIsDismissed(true);
      } else {
        localStorage.removeItem('pwa-install-dismissed-until');
      }
    }
  }, []);

  // iOS 감지
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as { MSStream?: unknown }).MSStream;

  // 이미 설치되었거나 닫혔으면 표시하지 않음
  if (isInstalled || isDismissed) {
    return null;
  }

  // iOS이고 설치 가능하지 않으면 iOS 안내 표시
  if (isIOS && !isInstallable) {
    return showIOSInstructions ? (
      <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-800 shadow-lg border-t border-gray-200 dark:border-gray-700 z-50">
        <div className="max-w-4xl mx-auto p-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                홈 화면에 ShopFDS 추가하기
              </h3>
              <ol className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
                <li className="flex items-start">
                  <span className="inline-block w-6 h-6 rounded-full bg-blue-500 text-white text-center mr-2 flex-shrink-0">
                    1
                  </span>
                  <span>
                    Safari 하단의 공유 버튼
                    <svg
                      className="inline w-4 h-4 mx-1"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path d="M16 5l-1.42 1.42-1.59-1.59V16h-1.98V4.83L9.42 6.42 8 5l4-4 4 4zm4 5v11c0 1.1-.9 2-2 2H6c-1.11 0-2-.9-2-2V10c0-1.11.89-2 2-2h3v2H6v11h12V10h-3V8h3c1.1 0 2 .89 2 2z" />
                    </svg>
                    을 탭하세요
                  </span>
                </li>
                <li className="flex items-start">
                  <span className="inline-block w-6 h-6 rounded-full bg-blue-500 text-white text-center mr-2 flex-shrink-0">
                    2
                  </span>
                  <span>"홈 화면에 추가"를 선택하세요</span>
                </li>
                <li className="flex items-start">
                  <span className="inline-block w-6 h-6 rounded-full bg-blue-500 text-white text-center mr-2 flex-shrink-0">
                    3
                  </span>
                  <span>"추가"를 탭하세요</span>
                </li>
              </ol>
            </div>
            <button
              onClick={() => {
                setShowIOSInstructions(false);
                handleDismiss();
              }}
              className="ml-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              aria-label="닫기"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    ) : (
      <div className="fixed bottom-0 left-0 right-0 bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg z-50">
        <div className="max-w-4xl mx-auto p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3 flex-1">
              <div className="w-12 h-12 bg-white rounded-lg flex items-center justify-center flex-shrink-0">
                <svg
                  className="w-8 h-8 text-blue-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                  />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-lg">ShopFDS 앱 설치하기</h3>
                <p className="text-sm text-blue-100">
                  홈 화면에서 빠르게 접속하세요
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setShowIOSInstructions(true)}
                className="px-4 py-2 bg-white text-blue-600 rounded-lg font-semibold hover:bg-blue-50 transition-colors"
              >
                설치하기
              </button>
              <button
                onClick={handleDismiss}
                className="px-4 py-2 text-white hover:bg-blue-700 rounded-lg transition-colors"
              >
                나중에
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Android/Desktop - beforeinstallprompt 이벤트 사용
  if (!isInstallable) {
    return null;
  }

  const handleInstall = async () => {
    await promptInstall();
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg z-50 animate-slide-up">
      <div className="max-w-4xl mx-auto p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 flex-1">
            <div className="w-12 h-12 bg-white rounded-lg flex items-center justify-center flex-shrink-0">
              <svg
                className="w-8 h-8 text-blue-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-lg">ShopFDS 앱 설치하기</h3>
              <p className="text-sm text-blue-100">
                오프라인에서도 사용 가능하고, 더 빠른 앱 경험을 누리세요
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleInstall}
              className="px-6 py-2 bg-white text-blue-600 rounded-lg font-semibold hover:bg-blue-50 transition-colors shadow-md"
            >
              설치하기
            </button>
            <button
              onClick={handleDismiss}
              className="px-4 py-2 text-white hover:bg-blue-700 rounded-lg transition-colors"
            >
              나중에
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
