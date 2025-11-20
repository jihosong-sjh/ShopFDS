# 빠른 시작 가이드: 프론트엔드 UX 고도화

**Feature**: 004-frontend-ux-enhancement
**작성일**: 2025-11-19
**대상**: 개발자
**소요 시간**: 약 30분

## 개요

이 가이드는 프론트엔드 UX 고도화 기능을 로컬 환경에서 개발하고 테스트하기 위한 설정 방법을 안내합니다.

**구현할 기능**:
1. 검색 및 자동완성
2. 리뷰 시스템 (별점, 텍스트, 사진)
3. 위시리스트
4. 배송지 관리
5. 쿠폰 시스템
6. OAuth 소셜 로그인 (Google, Kakao, Naver)
7. PWA (Progressive Web App)

---

## 사전 요구사항

### 필수 소프트웨어

- **Node.js**: 18.x 이상
- **Python**: 3.11 이상
- **PostgreSQL**: 15 이상
- **Redis**: 7 이상

### 확인 방법

```bash
node --version   # v18.0.0 이상
python --version # Python 3.11.0 이상
psql --version   # PostgreSQL 15.0 이상
redis-cli --version  # Redis 7.0.0 이상
```

---

## 1. 프로젝트 클론 및 브랜치 전환

```bash
# 1. 저장소 클론 (이미 있으면 생략)
git clone https://github.com/your-org/ShopFDS.git
cd ShopFDS

# 2. 기능 브랜치로 전환
git checkout 004-frontend-ux-enhancement

# 3. 최신 변경사항 가져오기
git pull origin 004-frontend-ux-enhancement
```

---

## 2. 백엔드 설정 (FastAPI)

### 2.1 데이터베이스 마이그레이션

```bash
# 1. 백엔드 디렉토리로 이동
cd services/ecommerce/backend

# 2. 가상환경 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경 변수 설정
cp .env.example .env

# .env 파일 편집 (PostgreSQL, Redis 연결 정보)
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/shopfds
# REDIS_URL=redis://localhost:6379/0

# 5. Alembic 마이그레이션 실행
alembic upgrade head

# 6. 확인: 새 테이블 생성되었는지 확인
psql -U user -d shopfds -c "\dt"
# reviews, review_votes, wishlist_items, addresses, coupons, user_coupons,
# oauth_accounts, push_subscriptions 테이블 확인
```

### 2.2 초기 데이터 시드

```bash
# 샘플 데이터 로드 (상품, 카테고리, 쿠폰)
python scripts/seed_data.py
```

**seed_data.py 예시**:
```python
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from src.db import async_session
from src.models import Coupon, DiscountType
from datetime import datetime, timedelta

async def seed_coupons():
    async with async_session() as session:
        coupons = [
            Coupon(
                coupon_code="WELCOME2025",
                coupon_name="신규 회원 환영 쿠폰",
                discount_type=DiscountType.PERCENT,
                discount_value=10,
                max_discount_amount=10000,
                min_purchase_amount=50000,
                valid_from=datetime.now(),
                valid_until=datetime.now() + timedelta(days=365),
                is_active=True
            ),
            Coupon(
                coupon_code="SPRING5000",
                coupon_name="봄맞이 5천원 할인",
                discount_type=DiscountType.FIXED,
                discount_value=5000,
                min_purchase_amount=30000,
                valid_from=datetime.now(),
                valid_until=datetime.now() + timedelta(days=90),
                is_active=True
            )
        ]
        session.add_all(coupons)
        await session.commit()

if __name__ == "__main__":
    asyncio.run(seed_coupons())
```

### 2.3 OAuth 클라이언트 ID 설정

**Google OAuth**:
1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. "API 및 서비스" → "사용자 인증 정보" → "OAuth 2.0 클라이언트 ID" 생성
4. 승인된 리디렉션 URI 추가: `http://localhost:8000/v1/auth/oauth/google/callback`
5. 클라이언트 ID와 시크릿을 `.env`에 추가

```bash
# .env
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

**Kakao OAuth**:
1. [Kakao Developers](https://developers.kakao.com/) 접속
2. 애플리케이션 생성
3. "플랫폼" → "Web" 추가, 도메인: `http://localhost:8000`
4. "Redirect URI": `http://localhost:8000/v1/auth/oauth/kakao/callback`
5. REST API 키를 `.env`에 추가

```bash
# .env
KAKAO_CLIENT_ID=your_kakao_rest_api_key
```

**Naver OAuth**:
1. [Naver Developers](https://developers.naver.com/) 접속
2. 애플리케이션 등록
3. "서비스 URL": `http://localhost:8000`
4. "Callback URL": `http://localhost:8000/v1/auth/oauth/naver/callback`
5. 클라이언트 ID와 시크릿을 `.env`에 추가

```bash
# .env
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
```

### 2.4 백엔드 서버 실행

```bash
# services/ecommerce/backend에서
uvicorn src.main:app --reload --port 8000
```

**확인**:
- Swagger UI: http://localhost:8000/docs
- 새 엔드포인트 확인: `/v1/search/autocomplete`, `/v1/reviews`, `/v1/wishlist` 등

---

## 3. 프론트엔드 설정 (React + Vite)

### 3.1 의존성 설치

```bash
# 1. 프론트엔드 디렉토리로 이동
cd services/ecommerce/frontend

# 2. 의존성 설치
npm install

# 3. 추가 라이브러리 설치 (신규 기능용)
npm install @tanstack/react-query zustand react-router-dom
npm install lodash.debounce react-lazyload react-dropzone
npm install vite-plugin-pwa workbox-precaching workbox-routing workbox-strategies
npm install @react-oauth/google
```

### 3.2 환경 변수 설정

```bash
# .env.local 파일 생성
cat > .env.local << EOF
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=your_google_client_id
VITE_KAKAO_CLIENT_ID=your_kakao_client_id
EOF
```

### 3.3 Vite PWA 플러그인 설정

**vite.config.ts**:
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /^http:\/\/localhost:8000\/v1\//,
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
});
```

### 3.4 React Query 설정

**src/main.tsx**:
```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import App from './App';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5분
      cacheTime: 10 * 60 * 1000, // 10분
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </React.StrictMode>
);
```

### 3.5 프론트엔드 개발 서버 실행

```bash
# services/ecommerce/frontend에서
npm run dev
```

**확인**:
- 브라우저: http://localhost:3000
- React Query Devtools: 하단 오른쪽 아이콘 클릭

---

## 4. 기능별 개발 가이드

### 4.1 검색 자동완성 구현

**useSearch Hook** (`src/hooks/useSearch.ts`):
```typescript
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import debounce from 'lodash.debounce';
import { searchApi } from '../services/api';

export const useSearch = () => {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');

  useEffect(() => {
    const handler = debounce(() => setDebouncedQuery(query), 300);
    handler();
    return () => handler.cancel();
  }, [query]);

  const { data, isLoading } = useQuery({
    queryKey: ['search', 'autocomplete', debouncedQuery],
    queryFn: () => searchApi.autocomplete(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
  });

  return { query, setQuery, suggestions: data?.suggestions || [], isLoading };
};
```

**SearchBar 컴포넌트** (`src/components/SearchBar.tsx`):
```typescript
import { useState } from 'react';
import { useSearch } from '../hooks/useSearch';

export const SearchBar = () => {
  const { query, setQuery, suggestions, isLoading } = useSearch();
  const [showSuggestions, setShowSuggestions] = useState(false);

  return (
    <div className="relative">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => setShowSuggestions(true)}
        onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
        placeholder="검색어를 입력하세요"
        className="w-full px-4 py-2 border rounded"
      />

      {showSuggestions && suggestions.length > 0 && (
        <div className="absolute z-10 w-full mt-1 bg-white border rounded shadow-lg">
          {suggestions.map((item, index) => (
            <div
              key={index}
              className="px-4 py-2 hover:bg-gray-100 cursor-pointer"
            >
              {item.type === 'product' ? (
                <div className="flex items-center gap-2">
                  <img src={item.image_url} className="w-10 h-10" alt="" />
                  <span>{item.text}</span>
                </div>
              ) : (
                <span className="text-gray-600">{item.text}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

### 4.2 리뷰 작성 구현

**ReviewForm 컴포넌트** (`src/components/ReviewForm.tsx`):
```typescript
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useDropzone } from 'react-dropzone';
import { reviewApi } from '../services/api';

export const ReviewForm = ({ productId, orderId }) => {
  const [rating, setRating] = useState(0);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [photos, setPhotos] = useState<File[]>([]);
  const queryClient = useQueryClient();

  const { getRootProps, getInputProps } = useDropzone({
    onDrop: (acceptedFiles) => {
      setPhotos((prev) => [...prev, ...acceptedFiles].slice(0, 3));
    },
    accept: { 'image/*': ['.jpeg', '.jpg', '.png', '.webp'] },
    maxFiles: 3,
  });

  const createReviewMutation = useMutation({
    mutationFn: reviewApi.createReview,
    onSuccess: () => {
      queryClient.invalidateQueries(['reviews', productId]);
      alert('리뷰가 작성되었습니다');
    },
  });

  const handleSubmit = async (e) => {
    e.preventDefault();

    // 1. 사진 업로드 (S3/R2)
    const imageUrls = await Promise.all(
      photos.map((file) => uploadImage(file))
    );

    // 2. 리뷰 생성
    createReviewMutation.mutate({
      product_id: productId,
      order_id: orderId,
      rating,
      title,
      content,
      images: imageUrls,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* 별점 */}
      <div>
        <label>별점</label>
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((star) => (
            <button
              key={star}
              type="button"
              onClick={() => setRating(star)}
              className={`text-2xl ${star <= rating ? 'text-yellow-400' : 'text-gray-300'}`}
            >
              ★
            </button>
          ))}
        </div>
      </div>

      {/* 제목 */}
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="제목 (선택사항)"
        className="w-full px-4 py-2 border rounded"
      />

      {/* 내용 */}
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="리뷰 내용 (최소 10자)"
        className="w-full px-4 py-2 border rounded"
        rows={5}
        required
        minLength={10}
      />

      {/* 사진 업로드 */}
      <div {...getRootProps()} className="border-2 border-dashed p-4 text-center cursor-pointer">
        <input {...getInputProps()} />
        <p>사진을 드래그하거나 클릭하여 업로드 (최대 3장)</p>
      </div>

      {photos.length > 0 && (
        <div className="flex gap-2">
          {photos.map((file, index) => (
            <img
              key={index}
              src={URL.createObjectURL(file)}
              alt=""
              className="w-20 h-20 object-cover"
            />
          ))}
        </div>
      )}

      <button type="submit" className="w-full bg-blue-500 text-white py-2 rounded">
        리뷰 작성
      </button>
    </form>
  );
};
```

### 4.3 위시리스트 구현

**useWishlist Hook** (`src/hooks/useWishlist.ts`):
```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { wishlistApi } from '../services/api';

export const useWishlist = () => {
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ['wishlist'],
    queryFn: wishlistApi.getWishlist,
  });

  const addMutation = useMutation({
    mutationFn: wishlistApi.addToWishlist,
    onSuccess: () => {
      queryClient.invalidateQueries(['wishlist']);
    },
  });

  const removeMutation = useMutation({
    mutationFn: wishlistApi.removeFromWishlist,
    onSuccess: () => {
      queryClient.invalidateQueries(['wishlist']);
    },
  });

  return {
    items: data?.items || [],
    addToWishlist: addMutation.mutate,
    removeFromWishlist: removeMutation.mutate,
  };
};
```

### 4.4 OAuth 로그인 구현

**GoogleLogin 컴포넌트** (`src/components/GoogleLogin.tsx`):
```typescript
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';

export const GoogleLoginButton = () => {
  const handleSuccess = async (credentialResponse) => {
    const { credential } = credentialResponse; // JWT token

    // 백엔드로 토큰 전송
    const response = await fetch('/v1/auth/oauth/google/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: credential }),
    });

    const { access_token, user } = await response.json();

    // JWT 저장
    localStorage.setItem('access_token', access_token);

    // 사용자 정보 Zustand 스토어에 저장
    useUserStore.setState({ user });
  };

  return (
    <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
      <GoogleLogin onSuccess={handleSuccess} onError={() => alert('로그인 실패')} />
    </GoogleOAuthProvider>
  );
};
```

---

## 5. 테스트

### 5.1 백엔드 테스트

```bash
cd services/ecommerce/backend

# 유닛 테스트
pytest tests/unit -v

# 통합 테스트
pytest tests/integration -v

# 특정 테스트만 실행
pytest tests/integration/test_reviews.py -v
```

### 5.2 프론트엔드 테스트

```bash
cd services/ecommerce/frontend

# 유닛 테스트 (Vitest)
npm test

# E2E 테스트 (Playwright)
npx playwright test
```

---

## 6. 일반적인 문제 해결

### 문제 1: Alembic 마이그레이션 실패

**증상**: `alembic upgrade head` 실행 시 오류

**해결**:
```bash
# 1. 현재 마이그레이션 버전 확인
alembic current

# 2. 마이그레이션 히스토리 확인
alembic history

# 3. 특정 버전으로 롤백 후 재시도
alembic downgrade -1
alembic upgrade head
```

### 문제 2: OAuth 리다이렉트 오류

**증상**: "Redirect URI mismatch" 오류

**해결**:
1. OAuth 제공자 콘솔에서 Redirect URI 확인
2. 정확히 `http://localhost:8000/v1/auth/oauth/{provider}/callback` 등록
3. `https://` vs `http://` 프로토콜 확인

### 문제 3: CORS 오류

**증상**: 프론트엔드에서 API 호출 시 CORS 오류

**해결**:
```python
# backend/src/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 문제 4: Redis 연결 실패

**증상**: "Connection refused" 오류

**해결**:
```bash
# Windows: Redis 서버 시작
redis-server

# Linux/Mac:
sudo service redis-server start

# Docker:
docker run -d -p 6379:6379 redis:7-alpine
```

---

## 7. 다음 단계

빠른 시작 가이드 완료. Phase 2로 진행:
1. **구현 계획**: tasks.md 작성 (`/speckit.tasks` 명령)
2. **개발 시작**: User Story별 구현
3. **테스트 작성**: 통합 테스트 및 E2E 테스트

---

## 추가 자료

- **API 문서**: http://localhost:8000/docs (Swagger UI)
- **React Query Devtools**: http://localhost:3000 (개발 모드)
- **데이터 모델**: `specs/004-frontend-ux-enhancement/data-model.md`
- **API 계약**: `specs/004-frontend-ux-enhancement/contracts/api-endpoints.md`
- **리서치**: `specs/004-frontend-ux-enhancement/research.md`

도움이 필요하면 팀에 문의하세요!
