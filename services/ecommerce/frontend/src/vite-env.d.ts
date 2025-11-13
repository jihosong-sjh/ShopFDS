/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  // 추가 환경 변수를 여기에 정의
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
