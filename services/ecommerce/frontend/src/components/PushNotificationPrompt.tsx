import { useState, useEffect } from 'react';
import { usePWA } from '../hooks/usePWA';

/**
 * 푸시 알림 권한 요청 컴포넌트
 *
 * - 사용자가 로그인 후 푸시 알림 권한 요청
 * - 주문 상태 변경, 배송 알림 등을 받을 수 있음
 * - 사용자가 거부하면 다시 표시하지 않음
 */
export function PushNotificationPrompt() {
  const {
    notificationPermission,
    isPushSupported,
    requestNotificationPermission,
    subscribeToPush,
  } = usePWA();

  const [isVisible, setIsVisible] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // 권한 요청 표시 여부 확인
  useEffect(() => {
    // 푸시 알림을 지원하지 않으면 표시하지 않음
    if (!isPushSupported) {
      return;
    }

    // 이미 권한이 부여되었거나 거부되었으면 표시하지 않음
    if (notificationPermission !== 'default') {
      return;
    }

    // 사용자가 이전에 닫았는지 확인
    const dismissed = localStorage.getItem('push-notification-dismissed');
    if (dismissed === 'true') {
      return;
    }

    // 로그인 여부 확인 (예: localStorage에서 토큰 확인)
    const token = localStorage.getItem('auth-token');
    if (!token) {
      return;
    }

    // 3초 후에 표시 (페이지 로드 직후 표시하지 않음)
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, 3000);

    return () => clearTimeout(timer);
  }, [isPushSupported, notificationPermission]);

  const handleAllow = async () => {
    setIsLoading(true);

    try {
      const permission = await requestNotificationPermission();

      if (permission === 'granted') {
        // 푸시 알림 구독
        await subscribeToPush();
        setIsVisible(false);

        // 성공 알림 표시
        showSuccessToast();
      } else {
        // 거부됨
        setIsVisible(false);
        localStorage.setItem('push-notification-dismissed', 'true');
      }
    } catch (error) {
      console.error('[Push] Error requesting permission:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDismiss = () => {
    setIsVisible(false);
    localStorage.setItem('push-notification-dismissed', 'true');
  };

  const showSuccessToast = () => {
    // TODO: 토스트 알림 시스템 사용
    console.log('[Push] Notification enabled successfully');
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6 animate-fade-in">
        {/* 아이콘 */}
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
            <svg
              className="w-8 h-8 text-blue-500 dark:text-blue-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
              />
            </svg>
          </div>
        </div>

        {/* 제목 */}
        <h3 className="text-xl font-bold text-gray-900 dark:text-white text-center mb-2">
          알림 받기
        </h3>

        {/* 설명 */}
        <p className="text-gray-600 dark:text-gray-300 text-center mb-6">
          주문 상태 변경, 배송 시작, 할인 쿠폰 등<br />
          중요한 소식을 놓치지 마세요!
        </p>

        {/* 혜택 목록 */}
        <ul className="space-y-3 mb-6">
          <li className="flex items-start">
            <svg
              className="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span className="text-sm text-gray-600 dark:text-gray-300">
              주문 상태 실시간 업데이트
            </span>
          </li>
          <li className="flex items-start">
            <svg
              className="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span className="text-sm text-gray-600 dark:text-gray-300">
              배송 시작 및 도착 알림
            </span>
          </li>
          <li className="flex items-start">
            <svg
              className="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span className="text-sm text-gray-600 dark:text-gray-300">
              위시리스트 상품 할인 소식
            </span>
          </li>
          <li className="flex items-start">
            <svg
              className="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span className="text-sm text-gray-600 dark:text-gray-300">
              특별 쿠폰 및 프로모션
            </span>
          </li>
        </ul>

        {/* 버튼 */}
        <div className="flex flex-col space-y-2">
          <button
            onClick={handleAllow}
            disabled={isLoading}
            className="w-full px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-lg transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <span className="flex items-center justify-center">
                <svg
                  className="animate-spin h-5 w-5 mr-2"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                처리 중...
              </span>
            ) : (
              '알림 받기'
            )}
          </button>
          <button
            onClick={handleDismiss}
            disabled={isLoading}
            className="w-full px-6 py-3 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            나중에
          </button>
        </div>

        {/* 개인정보 안내 */}
        <p className="text-xs text-gray-500 dark:text-gray-400 text-center mt-4">
          언제든지 설정에서 알림을 끄실 수 있습니다
        </p>
      </div>
    </div>
  );
}
