/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_WS_URL: string
  readonly VITE_ML_SERVICE_URL: string
  readonly VITE_ADMIN_API_URL: string
  readonly VITE_FDS_API_URL: string
  readonly VITE_ECOMMERCE_API_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
