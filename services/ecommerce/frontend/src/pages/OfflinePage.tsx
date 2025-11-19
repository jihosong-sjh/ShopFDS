import { useEffect, useState } from 'react';
import { usePWA } from '../hooks/usePWA';

/**
 * 오프라인 폴백 페이지
 *
 * - 네트워크 연결이 끊겼을 때 표시
 * - 최근 본 상품 10개 표시 (캐시에서)
 * - 온라인 복구 시 자동으로 새로고침
 */
interface RecentlyViewedProduct {
  product_id: string;
  viewed_at: number;
  name?: string;
}

export function OfflinePage() {
  const { isOnline } = usePWA();
  const [recentlyViewed, setRecentlyViewed] = useState<RecentlyViewedProduct[]>([]);

  // 최근 본 상품 로드 (LocalStorage에서)
  useEffect(() => {
    const loadRecentlyViewed = () => {
      try {
        const stored = localStorage.getItem('recently-viewed');
        if (stored) {
          const items = JSON.parse(stored);
          setRecentlyViewed(items.slice(0, 10)); // 최대 10개
        }
      } catch (error) {
        console.error('[Offline] Error loading recently viewed:', error);
      }
    };

    loadRecentlyViewed();
  }, []);

  // 온라인 복구 시 새로고침
  useEffect(() => {
    if (isOnline) {
      window.location.reload();
    }
  }, [isOnline]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        {/* 오프라인 아이콘 */}
        <div className="flex justify-center mb-6">
          <div className="w-24 h-24 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center">
            <svg
              className="w-12 h-12 text-gray-400 dark:text-gray-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414"
              />
            </svg>
          </div>
        </div>

        {/* 제목 */}
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white text-center mb-2">
          오프라인 상태
        </h1>

        {/* 설명 */}
        <p className="text-gray-600 dark:text-gray-300 text-center mb-8">
          인터넷 연결이 끊겼습니다. 연결이 복구되면 자동으로 업데이트됩니다.
        </p>

        {/* 상태 표시 */}
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-8">
          <div className="flex items-center">
            <svg
              className="w-5 h-5 text-yellow-600 dark:text-yellow-500 mr-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <span className="text-sm text-yellow-800 dark:text-yellow-300">
              일부 기능이 제한될 수 있습니다
            </span>
          </div>
        </div>

        {/* 최근 본 상품 */}
        {recentlyViewed.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              최근 본 상품 (오프라인 지원)
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
              {recentlyViewed.map((product, index) => (
                <div
                  key={index}
                  className="bg-gray-50 dark:bg-gray-700 rounded-lg p-2 cursor-not-allowed opacity-75"
                >
                  <div className="aspect-square bg-gray-200 dark:bg-gray-600 rounded-md mb-2 flex items-center justify-center">
                    <svg
                      className="w-8 h-8 text-gray-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                      />
                    </svg>
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-300 truncate">
                    {product.name || '상품'}
                  </p>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-4 text-center">
              온라인 상태에서 더 많은 상품을 확인하세요
            </p>
          </div>
        )}

        {/* 도움말 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
            연결 문제 해결 방법
          </h3>
          <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
            <li className="flex items-start">
              <span className="inline-block w-5 h-5 bg-blue-100 dark:bg-blue-900 rounded-full text-blue-600 dark:text-blue-400 text-center mr-2 flex-shrink-0 text-xs leading-5">
                1
              </span>
              <span>Wi-Fi 또는 모바일 데이터가 켜져 있는지 확인하세요</span>
            </li>
            <li className="flex items-start">
              <span className="inline-block w-5 h-5 bg-blue-100 dark:bg-blue-900 rounded-full text-blue-600 dark:text-blue-400 text-center mr-2 flex-shrink-0 text-xs leading-5">
                2
              </span>
              <span>비행기 모드가 꺼져 있는지 확인하세요</span>
            </li>
            <li className="flex items-start">
              <span className="inline-block w-5 h-5 bg-blue-100 dark:bg-blue-900 rounded-full text-blue-600 dark:text-blue-400 text-center mr-2 flex-shrink-0 text-xs leading-5">
                3
              </span>
              <span>라우터를 재시작하거나 다른 네트워크에 연결해 보세요</span>
            </li>
          </ul>
        </div>

        {/* 재시도 버튼 */}
        <div className="mt-6 flex justify-center">
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-lg transition-colors shadow-md"
          >
            다시 시도
          </button>
        </div>
      </div>

      {/* 연결 상태 모니터링 */}
      <div className="fixed bottom-4 right-4">
        <div className="flex items-center bg-white dark:bg-gray-800 rounded-full shadow-lg px-4 py-2">
          <div className="w-2 h-2 bg-red-500 rounded-full mr-2 animate-pulse" />
          <span className="text-sm text-gray-600 dark:text-gray-300">오프라인</span>
        </div>
      </div>
    </div>
  );
}
