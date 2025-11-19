/**
 * API 통신 레이어 (React Query)
 *
 * 백엔드 API와의 모든 통신을 관리합니다.
 */

import axios, { AxiosError } from 'axios';

// API 기본 설정
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// 요청 인터셉터: JWT 토큰 자동 추가
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 응답 인터셉터: 에러 처리
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;

    // 401 에러: 토큰 갱신 시도
    if (error.response?.status === 401 && originalRequest && !originalRequest.headers['X-Retry']) {
      const refreshToken = localStorage.getItem('refresh_token');

      if (refreshToken) {
        try {
          // 토큰 갱신 요청
          const response = await axios.post(`${API_BASE_URL}/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token: newRefreshToken } = response.data;

          // 새 토큰 저장
          localStorage.setItem('access_token', access_token);
          if (newRefreshToken) {
            localStorage.setItem('refresh_token', newRefreshToken);
          }

          // 원래 요청 재시도
          originalRequest.headers['Authorization'] = `Bearer ${access_token}`;
          originalRequest.headers['X-Retry'] = 'true';

          return apiClient(originalRequest);
        } catch (refreshError) {
          // 토큰 갱신 실패 시 로그아웃
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      } else {
        // 리프레시 토큰이 없으면 로그아웃
        localStorage.removeItem('access_token');
        window.location.href = '/login';
      }
    }

    // 네트워크 에러 처리
    if (!error.response) {
      console.error('[NETWORK ERROR] Unable to reach server');
    }

    return Promise.reject(error);
  }
);

// 타입 정의

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  created_at?: string;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Product {
  id: string;
  name: string;
  description?: string;
  price: number;
  stock_quantity: number;
  category: string;
  image_url?: string;
  status: string;
  is_available: boolean;
}

export interface CartItem {
  cart_item_id: string;
  product_id: string;
  product_name: string;
  unit_price: number;
  quantity: number;
  subtotal: number;
  image_url?: string;
  is_available: boolean;
}

export interface Cart {
  cart_id: string;
  total_amount: number;
  total_items: number;
  items: CartItem[];
}

export interface OrderItem {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
}

export interface Order {
  id: string;
  order_number: string;
  status: string;
  total_amount: number;
  shipping_name: string;
  shipping_address: string;
  shipping_phone: string;
  created_at: string;
  items?: OrderItem[];
}

// FDS 평가 결과 (T062-T063)
export interface FDSResult {
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high';
  requires_verification: boolean;
  verification_method?: 'otp' | 'biometric';
  transaction_id?: string;
}

// API 함수들

// 인증 API
export const authApi = {
  register: async (data: { email: string; password: string; name: string }) => {
    const response = await apiClient.post<AuthResponse>('/v1/auth/register', data);
    return response.data;
  },

  login: async (data: { email: string; password: string }) => {
    const response = await apiClient.post<AuthResponse>('/v1/auth/login', data);
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await apiClient.get<User>('/v1/auth/me');
    return response.data;
  },

  // OTP 인증 관련 API (T062-T063)
  requestOtp: async (data: { phone_number: string }) => {
    const response = await apiClient.post<{
      message: string;
      otp_token: string;
      expires_at: string;
    }>('/v1/auth/request-otp', data);
    return response.data;
  },

  verifyOtp: async (data: { otp_token: string; otp_code: string }) => {
    const response = await apiClient.post<{
      verified: boolean;
      message: string;
    }>('/v1/auth/verify-otp', data);
    return response.data;
  },
};

// 상품 API
export const productsApi = {
  getProducts: async (params?: {
    category?: string;
    search?: string;
    min_price?: number;
    max_price?: number;
    page?: number;
    page_size?: number;
  }) => {
    const response = await apiClient.get<{
      products: Product[];
      total_count: number;
      page: number;
      page_size: number;
    }>('/v1/products', { params });
    return response.data;
  },

  getProduct: async (productId: string) => {
    const response = await apiClient.get<Product>(`/v1/products/${productId}`);
    return response.data;
  },

  searchProducts: async (query: string) => {
    const response = await apiClient.get<Product[]>('/v1/products/search', {
      params: { q: query },
    });
    return response.data;
  },

  getCategories: async () => {
    const response = await apiClient.get<string[]>('/v1/products/categories');
    return response.data;
  },

  getFeaturedProducts: async () => {
    const response = await apiClient.get<Product[]>('/v1/products/featured');
    return response.data;
  },
};

// 장바구니 API
export const cartApi = {
  getCart: async () => {
    const response = await apiClient.get<Cart>('/v1/cart');
    return response.data;
  },

  addToCart: async (data: { product_id: string; quantity: number }) => {
    const response = await apiClient.post('/v1/cart/items', data);
    return response.data;
  },

  updateCartItem: async (cartItemId: string, quantity: number) => {
    const response = await apiClient.put(`/v1/cart/items/${cartItemId}`, { quantity });
    return response.data;
  },

  removeCartItem: async (cartItemId: string) => {
    await apiClient.delete(`/v1/cart/items/${cartItemId}`);
  },

  clearCart: async () => {
    await apiClient.delete('/v1/cart');
  },
};

// 주문 API
export const ordersApi = {
  createOrder: async (data: {
    shipping_name: string;
    shipping_address: string;
    shipping_phone: string;
    payment_info: {
      card_number: string;
      card_expiry: string;
      card_cvv: string;
    };
    otp_token?: string; // 추가 인증이 필요한 경우 (T063)
  }) => {
    const response = await apiClient.post<{
      order?: Order;
      fds_result: FDSResult;
      message?: string;
    }>('/v1/orders', data);
    return response.data;
  },

  getOrders: async (params?: { status_filter?: string; page?: number; page_size?: number }) => {
    const response = await apiClient.get<Order[]>('/v1/orders', { params });
    return response.data;
  },

  getOrder: async (orderId: string) => {
    const response = await apiClient.get<Order>(`/v1/orders/${orderId}`);
    return response.data;
  },

  cancelOrder: async (orderId: string) => {
    const response = await apiClient.post(`/v1/orders/${orderId}/cancel`);
    return response.data;
  },

  trackOrder: async (orderId: string) => {
    const response = await apiClient.get(`/v1/orders/${orderId}/tracking`);
    return response.data;
  },
};

// React Query 키 팩토리
export const queryKeys = {
  auth: {
    currentUser: ['auth', 'current-user'] as const,
  },
  products: {
    all: ['products'] as const,
    list: (params?: Record<string, unknown>) => ['products', 'list', params] as const,
    detail: (id: string) => ['products', 'detail', id] as const,
    categories: ['products', 'categories'] as const,
    featured: ['products', 'featured'] as const,
  },
  cart: {
    current: ['cart'] as const,
  },
  orders: {
    all: ['orders'] as const,
    list: (params?: Record<string, unknown>) => ['orders', 'list', params] as const,
    detail: (id: string) => ['orders', 'detail', id] as const,
  },
};

// API 에러 처리 유틸리티
export interface ApiError {
  message: string;
  status?: number;
  code?: string;
  details?: unknown;
}

export const handleApiError = (error: unknown): ApiError => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string; message?: string }>;
    return {
      message: axiosError.response?.data?.detail || axiosError.response?.data?.message || axiosError.message,
      status: axiosError.response?.status,
      code: axiosError.code,
      details: axiosError.response?.data,
    };
  }

  if (error instanceof Error) {
    return {
      message: error.message,
    };
  }

  return {
    message: 'An unknown error occurred',
  };
};

// 파일 업로드 유틸리티
export const uploadFile = async (file: File, endpoint: string): Promise<{ url: string }> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<{ url: string }>(endpoint, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

// 여러 파일 업로드 유틸리티
export const uploadFiles = async (files: File[], endpoint: string): Promise<{ urls: string[] }> => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await apiClient.post<{ urls: string[] }>(endpoint, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};
