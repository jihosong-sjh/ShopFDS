# 기술 리서치: 이커머스 프론트엔드 고도화

**Feature**: 004-frontend-ux-enhancement
**작성일**: 2025-11-19
**상태**: 완료

## 개요

이커머스 프론트엔드 고급 UX 기능 구현을 위한 기술 스택, 라이브러리, 아키텍처 패턴을 조사하고 결정한 내용을 정리합니다.

**주요 조사 영역**:
1. 상품 검색 및 자동완성 (Autocomplete, Fuzzy Matching)
2. 이미지 최적화 및 레이지 로딩
3. 리뷰 시스템 (별점, 텍스트, 사진 업로드)
4. OAuth 소셜 로그인 (Google, Kakao, Naver)
5. Progressive Web App (PWA)
6. 성능 최적화 (코드 스플리팅, 가상 스크롤)
7. 접근성 (WCAG AA 준수)
8. 다크 모드
9. 결제 게이트웨이 (Toss Payments, Kakao Pay)

---

## 1. 상품 검색 및 자동완성

### 결정사항: Debounced 검색 + PostgreSQL Trigram 유사도

**채택 이유**:
- 프론트엔드에서 300ms 디바운싱으로 불필요한 API 호출 방지
- PostgreSQL `pg_trgm` 확장으로 퍼지 매칭 (오타 교정)
- 2글자 이상 입력 시 상품명, 브랜드, 카테고리 통합 자동완성 제공
- 최근 검색어는 LocalStorage에 저장 (최대 10개)

**구현 예시**:
```typescript
// 프론트엔드: 디바운싱 Hook
const useSearch = () => {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);

  const { data } = useQuery({
    queryKey: ['search', 'autocomplete', debouncedQuery],
    queryFn: () => searchApi.autocomplete(debouncedQuery),
    enabled: debouncedQuery.length >= 2
  });

  return { query, setQuery, suggestions: data };
};

// 백엔드: PostgreSQL Trigram
SELECT name, similarity(name, 'search_term') as score
FROM products
WHERE similarity(name, 'search_term') > 0.3
ORDER BY score DESC LIMIT 10;
```

**검토한 대안**:
- **Elasticsearch**: 전문 검색 엔진 → 기각 (규모 대비 과도, 인프라 복잡도)
- **Algolia**: 관리형 검색 서비스 → 기각 (비용, 벤더 종속)
- **클라이언트 사이드 필터링**: → 기각 (대량 데이터 성능 문제)

**사용 라이브러리**: `lodash.debounce`, `fuse.js` (선택)

**성능 목표**:
- 자동완성 응답: < 300ms
- 검색 결과 페이지 로드: < 2s
- 검색어 하이라이트: `mark.js` 또는 커스텀 React Hook

---

## 2. 이미지 최적화 및 레이지 로딩

### 결정사항: 네이티브 Lazy Loading + Intersection Observer

**채택 이유**:
- `loading="lazy"` 속성으로 모던 브라우저 네이티브 지원 (Chrome 77+, Firefox 75+)
- Intersection Observer API로 구형 브라우저 폴백 및 세밀한 제어
- Image CDN (Cloudflare Images)으로 자동 WebP 변환 및 리사이징
- 뷰포트 진입 50px 전에 미리 로드 (rootMargin)

**구현 예시**:
```typescript
const LazyImage = ({ src, alt, width, height }) => {
  const imgRef = useRef<HTMLImageElement>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsLoaded(true);
          observer.disconnect();
        }
      },
      { rootMargin: '50px' }
    );

    if (imgRef.current) observer.observe(imgRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <img
      ref={imgRef}
      src={isLoaded ? src : undefined}
      alt={alt}
      loading="lazy"
      width={width}
      height={height}
      className={isLoaded ? '' : 'skeleton-loader'}
    />
  );
};
```

**검토한 대안**:
- **react-lazyload**: → 기각 (네이티브 API로 충분)
- **BlurHash/LQIP**: → 연기 (P3 우선순위, 복잡도 대비 UX 개선 미미)
- **Next.js Image**: → 기각 (Vite 사용 중)

**성능 목표**:
- 뷰포트 진입 후 0.5초 이내 로드
- LCP (Largest Contentful Paint) < 2.5s

---

## 3. 리뷰 시스템

### 결정사항: PostgreSQL 저장 + S3/R2 이미지 업로드

**채택 이유**:
- `reviews` 테이블에 별점(1-5), 텍스트, 이미지 URL 배열 저장
- `review_votes` 테이블로 "도움돼요" 중복 투표 방지
- 사진 최대 3장, 객체 스토리지 (S3/Cloudflare R2)에 업로드
- `is_verified_purchase` 플래그로 구매 확정 고객만 리뷰 작성

**데이터베이스 스키마**:
```sql
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    product_id UUID NOT NULL REFERENCES products(id),
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title VARCHAR(200),
    content TEXT NOT NULL,
    images JSONB DEFAULT '[]',
    helpful_count INT DEFAULT 0,
    is_verified_purchase BOOLEAN DEFAULT FALSE,
    is_flagged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, product_id)
);

CREATE TABLE review_votes (
    review_id UUID REFERENCES reviews(id),
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (review_id, user_id)
);

CREATE INDEX idx_reviews_product ON reviews(product_id, created_at DESC);
CREATE INDEX idx_reviews_rating ON reviews(product_id, rating DESC);
```

**검토한 대안**:
- **MongoDB**: → 기각 (PostgreSQL로 충분)
- **별도 마이크로서비스**: → 기각 (현재 규모에 과도)
- **서드파티 서비스 (Yotpo)**: → 기각 (비용, 커스터마이징 제한)

**성능 목표**:
- 리뷰 목록 로드: < 1s
- 페이지네이션: 10개/페이지
- 이미지 업로드: 최대 5MB, 1200px 폭으로 리사이징

---

## 4. OAuth 소셜 로그인

### 결정사항: PKCE를 사용한 OAuth 2.0 (Google, Kakao, Naver)

**채택 이유**:
- 표준 OAuth 2.0 Authorization Code Flow with PKCE (보안 강화)
- 백엔드에서 토큰 교환 및 사용자 프로필 저장
- 이메일 기반 자동 회원가입
- 세션 관리용 JWT 발급

**제공자별 정보**:

| 제공자 | Authorization URL | Token URL | User Info |
|--------|-------------------|-----------|-----------|
| Google | `https://accounts.google.com/o/oauth2/v2/auth` | `https://oauth2.googleapis.com/token` | `https://www.googleapis.com/oauth2/v3/userinfo` |
| Kakao | `https://kauth.kakao.com/oauth/authorize` | `https://kauth.kakao.com/oauth/token` | `https://kapi.kakao.com/v2/user/me` |
| Naver | `https://nid.naver.com/oauth2.0/authorize` | `https://nid.naver.com/oauth2.0/token` | `https://openapi.naver.com/v1/nid/me` |

**백엔드 구현 (FastAPI + Authlib)**:
```python
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()
oauth.register(
    name='google',
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@router.get('/auth/oauth/google')
async def google_login(request: Request):
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get('/auth/oauth/google/callback')
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token['userinfo']
    # 사용자 생성 또는 업데이트, JWT 발급
```

**검토한 대안**:
- **Firebase Auth**: → 기각 (비용, 벤더 종속)
- **Passport.js**: → 기각 (FastAPI 사용, Node.js 아님)

**보안 고려사항**:
- PKCE (SPA/모바일 필수)
- State 파라미터 (CSRF 방지)
- Nonce (Replay attack 방지)
- 토큰 암호화 저장

---

## 5. Progressive Web App (PWA)

### 결정사항: Workbox + Vite PWA Plugin

**채택 이유**:
- `vite-plugin-pwa`로 Workbox 자동 통합
- Service Worker 캐싱 전략: Cache First (정적 에셋), Network First (API)
- Manifest.json으로 홈 화면 추가, Standalone 모드 지원
- Firebase Cloud Messaging (FCM)으로 푸시 알림 (P3 우선순위)

**Vite 설정**:
```typescript
// vite.config.ts
import { VitePWA } from 'vite-plugin-pwa';

export default {
  plugins: [
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\.shopfds\.com\/v1\/products/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: { maxEntries: 50, maxAgeSeconds: 300 },
            },
          },
        ],
      },
      manifest: {
        name: 'ShopFDS',
        short_name: 'ShopFDS',
        theme_color: '#3b82f6',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
    }),
  ],
};
```

**설치 프롬프트**:
```typescript
const usePWA = () => {
  const [installPrompt, setInstallPrompt] = useState<any>(null);
  const [isInstalled, setIsInstalled] = useState(false);

  useEffect(() => {
    if (window.matchMedia('(display-mode: standalone)').matches) {
      setIsInstalled(true);
    }

    const handler = (e: Event) => {
      e.preventDefault();
      setInstallPrompt(e);
    };
    window.addEventListener('beforeinstallprompt', handler);

    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const install = async () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    const { outcome } = await installPrompt.userChoice;
    if (outcome === 'accepted') {
      setIsInstalled(true);
    }
  };

  return { install, canInstall: !!installPrompt, isInstalled };
};
```

**검토한 대안**:
- **수동 Service Worker**: → 기각 (Workbox가 검증됨)

---

## 6. 성능 최적화

### 결정사항: 코드 스플리팅 + 가상 스크롤 + React Query 캐싱

**채택 이유**:
- React.lazy + Suspense로 라우트별 코드 스플리팅 (초기 번들 감소)
- `react-window`로 긴 상품 목록 가상 스크롤링
- React Query로 API 응답 캐싱 (staleTime 5분)
- `web-vitals` 라이브러리로 FCP, LCP, CLS 등 측정

**코드 스플리팅**:
```typescript
import { lazy, Suspense } from 'react';

const ProductList = lazy(() => import('./pages/ProductList'));
const ProductDetail = lazy(() => import('./pages/ProductDetail'));
const Checkout = lazy(() => import('./pages/Checkout'));

function App() {
  return (
    <Suspense fallback={<SkeletonLoader />}>
      <Routes>
        <Route path="/products" element={<ProductList />} />
        <Route path="/products/:id" element={<ProductDetail />} />
        <Route path="/checkout" element={<Checkout />} />
      </Routes>
    </Suspense>
  );
}
```

**가상 스크롤**:
```typescript
import { FixedSizeList } from 'react-window';

const VirtualProductList = ({ products }) => {
  const Row = ({ index, style }) => (
    <div style={style}>
      <ProductCard product={products[index]} />
    </div>
  );

  return (
    <FixedSizeList
      height={800}
      itemCount={products.length}
      itemSize={200}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  );
};
```

**검토한 대안**:
- **SSR (Next.js)**: → 연기 (Vite SPA로 시작, v2에서 고려)
- **React Server Components**: → 기각 (아직 실험적)

**성능 목표**:
- FCP < 1.5s
- LCP < 2.5s
- CLS < 0.1

---

## 7. 접근성 (WCAG AA)

### 결정사항: 시맨틱 HTML + ARIA + 키보드 네비게이션

**채택 이유**:
- WCAG AA 색상 대비 기준 (일반 텍스트 4.5:1, 큰 텍스트 3:1)
- `<button>`, `<nav>`, `<main>` 시맨틱 HTML로 스크린 리더 지원
- `role`, `aria-label`, `aria-describedby` 속성 사용
- Tab, Enter, Esc 키보드 네비게이션 전체 지원

**Modal 예시**:
```typescript
const Modal = ({ isOpen, onClose, children }) => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;

    const firstInput = modalRef.current?.querySelector('button, input, select');
    if (firstInput) (firstInput as HTMLElement).focus();

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEscape);

    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      ref={modalRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <h2 id="modal-title">제목</h2>
      {children}
      <button onClick={onClose} aria-label="모달 닫기">닫기</button>
    </div>
  );
};
```

**검토한 대안**:
- **Radix UI, Headless UI**: → 연기 (P2, 복잡한 컴포넌트에 고려)

**사용 도구**:
- `eslint-plugin-jsx-a11y` (린팅)
- `@axe-core/react` (런타임 테스트)
- Lighthouse (자동 감사)

---

## 8. 다크 모드

### 결정사항: Tailwind CSS `dark:` 변형 + LocalStorage

**채택 이유**:
- Tailwind CSS `darkMode: 'class'` 설정으로 `dark:` 클래스 활성화
- `prefers-color-scheme` 미디어 쿼리로 시스템 환경설정 감지
- Zustand persist 미들웨어로 LocalStorage 동기화
- light, dark, system 3가지 모드 지원

**구현**:
```typescript
import create from 'zustand';
import { persist } from 'zustand/middleware';

type Theme = 'light' | 'dark' | 'system';

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set) => ({
      theme: 'system',
      setTheme: (theme) => set({ theme })
    }),
    { name: 'theme-storage' }
  )
);

// <html> 요소에 적용
const applyTheme = (theme: Theme) => {
  const root = document.documentElement;
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const isDark = theme === 'dark' || (theme === 'system' && systemPrefersDark);

  if (isDark) {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }
};
```

**Tailwind 설정**:
```javascript
// tailwind.config.js
module.exports = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: {
          light: '#FFFFFF',
          dark: '#1F2937'
        },
        text: {
          light: '#1F2937',
          dark: '#F9FAFB'
        }
      }
    }
  }
};
```

---

## 9. 결제 게이트웨이

### 결정사항: Toss Payments + Kakao Pay

**채택 이유**:
- **Toss Payments**: 한국 시장 점유율 40%, 간편결제 선두
- **Kakao Pay**: Kakao 생태계 통합 (메신저 1위)
- 신용카드, 계좌이체, 모바일 결제 지원
- PG 수수료: 신용카드 3.5%, 계좌이체 2.5%

**Toss Payments**:
```typescript
const requestPayment = async (orderId: string, amount: number) => {
  const tossPayments = await window.TossPayments(CLIENT_KEY);

  await tossPayments.requestPayment('CARD', {
    amount,
    orderId,
    orderName: '상품명',
    successUrl: `${window.location.origin}/checkout/success`,
    failUrl: `${window.location.origin}/checkout/fail`,
    customerEmail: user.email,
    customerName: user.name
  });
};
```

**Kakao Pay**:
```typescript
const requestKakaoPay = async (orderId: string, amount: number) => {
  const response = await fetch('/v1/payments/kakao/ready', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cid: 'TC0ONETIME',
      partner_order_id: orderId,
      partner_user_id: user.id,
      item_name: '상품명',
      quantity: 1,
      total_amount: amount,
      tax_free_amount: 0,
      approval_url: `${window.location.origin}/checkout/success`,
      cancel_url: `${window.location.origin}/checkout/cancel`,
      fail_url: `${window.location.origin}/checkout/fail`
    })
  });

  const { next_redirect_pc_url } = await response.json();
  window.location.href = next_redirect_pc_url;
};
```

**검토한 대안**:
- **PortOne (IamPort)**: → 기각 (높은 수수료)
- **Stripe**: → 기각 (한국 결제 수단 지원 부족)
- **PayPal**: → 기각 (한국 사용률 < 5%)

**보안 고려사항**:
- PCI-DSS 준수 (원시 카드 번호 절대 저장 금지)
- 토큰화 사용
- 웹훅 서버 사이드 검증
- HTTPS 강제

---

## 결정사항 요약

| 기능 | 결정사항 | 주요 라이브러리/도구 |
|------|----------|---------------------|
| 검색 | Debounced 검색 + PostgreSQL trigram | lodash.debounce, pg_trgm |
| 이미지 | 네이티브 Lazy Loading + Intersection Observer | 없음 (네이티브 API) |
| 리뷰 | PostgreSQL + S3/R2 | React Query, React-Dropzone |
| OAuth | OAuth 2.0 with PKCE | Authlib (Python) |
| PWA | Workbox + Manifest | vite-plugin-pwa |
| 성능 | 코드 스플리팅 + 가상 스크롤 | react-window, React Query |
| 접근성 | WCAG AA + 시맨틱 HTML + ARIA | eslint-plugin-jsx-a11y |
| 다크 모드 | Tailwind CSS + LocalStorage | Zustand persist |
| 결제 | Toss Payments + Kakao Pay | Toss Payments SDK |

---

## 다음 단계

Phase 1로 진행:
1. **데이터 모델**: 리뷰, 위시리스트, 배송지, 쿠폰 스키마 정의
2. **API 계약**: 모든 신규 기능용 REST 엔드포인트 명세
3. **빠른 시작 가이드**: 로컬 개발 환경 설정 문서

Technical Context의 모든 "NEEDS CLARIFICATION" 항목이 해결되었습니다.
