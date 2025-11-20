/// <reference types="vite/client" />
/// <reference lib="webworker" />

declare module 'virtual:pwa-register/react' {
  export interface RegisterSWOptions {
    immediate?: boolean;
    onNeedRefresh?: () => void;
    onOfflineReady?: () => void;
    onRegistered?: (registration: ServiceWorkerRegistration | undefined) => void;
    onRegisterError?: (error: unknown) => void;
  }

  export function useRegisterSW(options?: RegisterSWOptions): {
    needRefresh: [boolean, (value: boolean) => void];
    offlineReady: [boolean, (value: boolean) => void];
    updateServiceWorker: (reloadPage?: boolean) => Promise<void>;
  };
}

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_VAPID_PUBLIC_KEY: string;
  readonly VITE_SENTRY_DSN: string;
  readonly VITE_ENABLE_PWA: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
