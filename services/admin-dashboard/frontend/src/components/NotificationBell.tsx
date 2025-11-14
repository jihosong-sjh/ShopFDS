/**
 * 실시간 알림 컴포넌트
 *
 * WebSocket 기반 실시간 알림 시스템입니다.
 * 고위험 거래가 탐지되면 즉시 보안팀에 알립니다.
 */

import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

interface Notification {
  id: string;
  type: "high_risk_transaction" | "system_alert" | "review_assigned";
  title: string;
  message: string;
  transaction_id?: string;
  timestamp: string;
  read: boolean;
}

const NotificationBell = () => {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // WebSocket 연결 URL (환경 변수에서 가져오거나 기본값 사용)
  const WS_URL =
    import.meta.env.VITE_WS_URL || "ws://localhost:8002/ws/notifications";

  // WebSocket 연결 초기화
  useEffect(() => {
    // NOTE: 실제 WebSocket 서버가 구현되기 전까지는 모의 알림을 사용합니다.
    // 실제 구현 시 아래 주석을 해제하고 connectWebSocket()를 호출하세요.

    // connectWebSocket();

    // 모의 알림 생성 (개발/테스트용)
    const mockNotifications: Notification[] = [
      {
        id: "1",
        type: "high_risk_transaction",
        title: "고위험 거래 탐지",
        message: "IP 주소 203.0.113.42에서 고위험 거래가 탐지되었습니다.",
        transaction_id: "00000000-0000-0000-0000-000000000001",
        timestamp: new Date().toISOString(),
        read: false,
      },
      {
        id: "2",
        type: "system_alert",
        title: "시스템 성능 경고",
        message: "FDS 평가 시간이 150ms로 증가했습니다.",
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        read: false,
      },
    ];

    setNotifications(mockNotifications);
    setUnreadCount(mockNotifications.filter((n) => !n.read).length);

    // 컴포넌트 언마운트 시 WebSocket 연결 종료
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // WebSocket 연결 함수
  const connectWebSocket = () => {
    try {
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log("WebSocket 연결 성공");
      };

      ws.onmessage = (event) => {
        try {
          const notification: Notification = JSON.parse(event.data);
          notification.read = false;

          setNotifications((prev) => [notification, ...prev]);
          setUnreadCount((prev) => prev + 1);

          // 브라우저 알림 (권한이 있는 경우)
          if (Notification.permission === "granted") {
            new Notification(notification.title, {
              body: notification.message,
              icon: "/notification-icon.png",
            });
          }
        } catch (error) {
          console.error("알림 파싱 오류:", error);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket 오류:", error);
      };

      ws.onclose = () => {
        console.log("WebSocket 연결 종료. 5초 후 재연결 시도...");
        // 5초 후 재연결 시도
        setTimeout(() => {
          connectWebSocket();
        }, 5000);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error("WebSocket 연결 실패:", error);
    }
  };

  // 브라우저 알림 권한 요청
  const requestNotificationPermission = async () => {
    if ("Notification" in window && Notification.permission === "default") {
      await Notification.requestPermission();
    }
  };

  useEffect(() => {
    requestNotificationPermission();
  }, []);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // 알림 읽음 처리
  const markAsRead = (notificationId: string) => {
    setNotifications((prev) =>
      prev.map((n) =>
        n.id === notificationId ? { ...n, read: true } : n
      )
    );
    setUnreadCount((prev) => Math.max(0, prev - 1));
  };

  // 모든 알림 읽음 처리
  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    setUnreadCount(0);
  };

  // 알림 클릭 핸들러
  const handleNotificationClick = (notification: Notification) => {
    markAsRead(notification.id);

    // 거래 관련 알림이면 상세 페이지로 이동
    if (notification.transaction_id) {
      navigate(`/transactions/${notification.transaction_id}`);
      setIsOpen(false);
    }
  };

  // 알림 타입별 아이콘
  const getNotificationIcon = (type: string) => {
    switch (type) {
      case "high_risk_transaction":
        return (
          <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
            <svg
              className="w-6 h-6 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
        );
      case "system_alert":
        return (
          <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center">
            <svg
              className="w-6 h-6 text-amber-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
        );
      case "review_assigned":
        return (
          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
            <svg
              className="w-6 h-6 text-blue-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
        );
      default:
        return (
          <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
            <svg
              className="w-6 h-6 text-gray-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
              />
            </svg>
          </div>
        );
    }
  };

  // 상대 시간 표시
  const getRelativeTime = (timestamp: string) => {
    const now = new Date();
    const past = new Date(timestamp);
    const diffMs = now.getTime() - past.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "방금 전";
    if (diffMins < 60) return `${diffMins}분 전`;
    if (diffHours < 24) return `${diffHours}시간 전`;
    return `${diffDays}일 전`;
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* 알림 벨 버튼 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg"
      >
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white transform translate-x-1/2 -translate-y-1/2 bg-red-600 rounded-full">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* 알림 드롭다운 */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
          {/* 헤더 */}
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">알림</h3>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                모두 읽음
              </button>
            )}
          </div>

          {/* 알림 목록 */}
          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-gray-500">
                <svg
                  className="mx-auto h-12 w-12 text-gray-400 mb-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
                  />
                </svg>
                <p>새로운 알림이 없습니다</p>
              </div>
            ) : (
              notifications.map((notification) => (
                <div
                  key={notification.id}
                  onClick={() => handleNotificationClick(notification)}
                  className={`px-4 py-3 border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors ${
                    !notification.read ? "bg-blue-50" : ""
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {getNotificationIcon(notification.type)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <p className="text-sm font-medium text-gray-900">
                          {notification.title}
                        </p>
                        {!notification.read && (
                          <span className="w-2 h-2 bg-blue-600 rounded-full"></span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mb-1">
                        {notification.message}
                      </p>
                      <p className="text-xs text-gray-500">
                        {getRelativeTime(notification.timestamp)}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* 푸터 */}
          {notifications.length > 0 && (
            <div className="px-4 py-3 border-t border-gray-200 text-center">
              <button
                onClick={() => {
                  navigate("/notifications");
                  setIsOpen(false);
                }}
                className="text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                모든 알림 보기
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
