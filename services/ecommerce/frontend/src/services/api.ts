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
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // 인증 실패 시 로그아웃
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
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
  }) => {
    const response = await apiClient.post<{
      order: Order;
      fds_result: any;
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
    list: (params?: any) => ['products', 'list', params] as const,
    detail: (id: string) => ['products', 'detail', id] as const,
    categories: ['products', 'categories'] as const,
    featured: ['products', 'featured'] as const,
  },
  cart: {
    current: ['cart'] as const,
  },
  orders: {
    all: ['orders'] as const,
    list: (params?: any) => ['orders', 'list', params] as const,
    detail: (id: string) => ['orders', 'detail', id] as const,
  },
};
