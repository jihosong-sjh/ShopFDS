import { useState, useEffect, useCallback } from 'react';
import { useRegisterSW } from 'virtual:pwa-register/react';

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed';
    platform: string;
  }>;
  prompt(): Promise<void>;
}

interface PWAState {
  // 설치 관련
  isInstallable: boolean;
  isInstalled: boolean;
  promptInstall: () => Promise<void>;

  // 업데이트 관련
  needRefresh: boolean;
  offlineReady: boolean;
  updateServiceWorker: (reloadPage?: boolean) => Promise<void>;

  // 푸시 알림 관련
  notificationPermission: NotificationPermission;
  isPushSupported: boolean;
  requestNotificationPermission: () => Promise<NotificationPermission>;
  subscribeToPush: () => Promise<PushSubscription | null>;
  unsubscribeFromPush: () => Promise<void>;

  // 온라인/오프라인 상태
  isOnline: boolean;
}

/**
 * PWA 기능을 위한 Hook
 *
 * - 설치 프롬프트 관리
 * - Service Worker 업데이트
 * - 푸시 알림 권한 관리
 * - 온라인/오프라인 상태 감지
 */
export function usePWA(): PWAState {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isInstalled, setIsInstalled] = useState(false);
  const [notificationPermission, setNotificationPermission] = useState<NotificationPermission>(
    'default'
  );
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  // Vite PWA Plugin의 Service Worker 등록 Hook
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    offlineReady: [offlineReady, setOfflineReady],
    updateServiceWorker,
  } = useRegisterSW({
    onRegistered(registration) {
      console.log('[PWA] Service Worker registered:', registration);
    },
    onRegisterError(error) {
      console.error('[PWA] Service Worker registration error:', error);
    },
  });

  // 설치 프롬프트 이벤트 감지
  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  // 설치 상태 감지
  useEffect(() => {
    const checkInstalled = () => {
      const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
      const isIOSStandalone = (window.navigator as any).standalone === true;
      setIsInstalled(isStandalone || isIOSStandalone);
    };

    checkInstalled();

    window.addEventListener('appinstalled', () => {
      setIsInstalled(true);
      setDeferredPrompt(null);
    });
  }, []);

  // 알림 권한 상태 감지
  useEffect(() => {
    if ('Notification' in window) {
      setNotificationPermission(Notification.permission);
    }
  }, []);

  // 온라인/오프라인 상태 감지
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // 설치 프롬프트 표시
  const promptInstall = useCallback(async () => {
    if (!deferredPrompt) {
      console.warn('[PWA] Install prompt not available');
      return;
    }

    try {
      await deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      console.log(`[PWA] User ${outcome} the install prompt`);

      if (outcome === 'accepted') {
        setDeferredPrompt(null);
      }
    } catch (error) {
      console.error('[PWA] Error showing install prompt:', error);
    }
  }, [deferredPrompt]);

  // 알림 권한 요청
  const requestNotificationPermission = useCallback(async (): Promise<NotificationPermission> => {
    if (!('Notification' in window)) {
      console.warn('[PWA] Notifications not supported');
      return 'denied';
    }

    try {
      const permission = await Notification.requestPermission();
      setNotificationPermission(permission);
      return permission;
    } catch (error) {
      console.error('[PWA] Error requesting notification permission:', error);
      return 'denied';
    }
  }, []);

  // 푸시 알림 구독
  const subscribeToPush = useCallback(async (): Promise<PushSubscription | null> => {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      console.warn('[PWA] Push notifications not supported');
      return null;
    }

    try {
      const registration = await navigator.serviceWorker.ready;
      const existingSubscription = await registration.pushManager.getSubscription();

      if (existingSubscription) {
        return existingSubscription;
      }

      // VAPID Public Key (환경 변수에서 가져오기)
      const vapidPublicKey = import.meta.env.VITE_VAPID_PUBLIC_KEY;
      if (!vapidPublicKey) {
        console.error('[PWA] VAPID public key not configured');
        return null;
      }

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
      });

      // 백엔드에 구독 정보 전송
      await fetch('/api/v1/push/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(subscription.toJSON()),
      });

      console.log('[PWA] Push subscription successful');
      return subscription;
    } catch (error) {
      console.error('[PWA] Error subscribing to push:', error);
      return null;
    }
  }, []);

  // 푸시 알림 구독 해지
  const unsubscribeFromPush = useCallback(async (): Promise<void> => {
    if (!('serviceWorker' in navigator)) {
      return;
    }

    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();

      if (subscription) {
        await subscription.unsubscribe();

        // 백엔드에 구독 해지 알림
        await fetch('/api/v1/push/unsubscribe', {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(subscription.toJSON()),
        });

        console.log('[PWA] Push unsubscription successful');
      }
    } catch (error) {
      console.error('[PWA] Error unsubscribing from push:', error);
    }
  }, []);

  return {
    // 설치 관련
    isInstallable: !!deferredPrompt,
    isInstalled,
    promptInstall,

    // 업데이트 관련
    needRefresh,
    offlineReady,
    updateServiceWorker,

    // 푸시 알림 관련
    notificationPermission,
    isPushSupported: 'Notification' in window && 'PushManager' in window,
    requestNotificationPermission,
    subscribeToPush,
    unsubscribeFromPush,

    // 온라인/오프라인 상태
    isOnline,
  };
}

// VAPID Public Key를 Uint8Array로 변환하는 헬퍼 함수
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }

  return outputArray;
}
