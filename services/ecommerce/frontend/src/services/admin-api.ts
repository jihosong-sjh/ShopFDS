/**
 * 관리자 API 레이어 (T091-T095)
 *
 * 관리자 전용 API 엔드포인트 통신을 관리합니다.
 */

import { apiClient, Product, Order, User } from './api';

// 관리자 API
export const adminApi = {
  // 상품 관리 (T091)
  createProduct: async (data: {
    name: string;
    description?: string;
    price: number;
    stock_quantity: number;
    category: string;
    image_url?: string;
  }) => {
    const response = await apiClient.post<Product>('/v1/admin/products', data);
    return response.data;
  },

  updateProduct: async (
    productId: string,
    data: {
      name?: string;
      description?: string;
      price?: number;
      category?: string;
      image_url?: string;
      status?: string;
    }
  ) => {
    const response = await apiClient.put<Product>(`/v1/admin/products/${productId}`, data);
    return response.data;
  },

  deleteProduct: async (productId: string) => {
    await apiClient.delete(`/v1/admin/products/${productId}`);
  },

  // 재고 관리 (T092)
  updateStock: async (
    productId: string,
    data: {
      stock_quantity: number;
      operation?: 'set' | 'increment' | 'decrement';
    }
  ) => {
    const response = await apiClient.patch<Product>(`/v1/admin/products/${productId}/stock`, data);
    return response.data;
  },

  // 주문 관리 (T093)
  getAllOrders: async (params?: {
    status?: string;
    user_id?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }) => {
    const response = await apiClient.get<{
      orders: Order[];
      total_count: number;
      page: number;
      page_size: number;
    }>('/v1/admin/orders', { params });
    return response.data;
  },

  getOrderDetail: async (orderId: string) => {
    const response = await apiClient.get<Order>(`/v1/admin/orders/${orderId}`);
    return response.data;
  },

  updateOrderStatus: async (orderId: string, data: { status: string; admin_notes?: string }) => {
    const response = await apiClient.patch<Order>(`/v1/admin/orders/${orderId}/status`, data);
    return response.data;
  },

  // 회원 관리 (T094)
  getAllUsers: async (params?: {
    status?: string;
    role?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }) => {
    const response = await apiClient.get<{
      users: User[];
      total_count: number;
      page: number;
      page_size: number;
    }>('/v1/admin/users', { params });
    return response.data;
  },

  getUserDetail: async (userId: string) => {
    const response = await apiClient.get<User>(`/v1/admin/users/${userId}`);
    return response.data;
  },

  updateUserStatus: async (userId: string, data: { status: string; admin_notes?: string }) => {
    const response = await apiClient.patch<User>(`/v1/admin/users/${userId}/status`, data);
    return response.data;
  },

  // 매출 대시보드 (T095)
  getSalesStats: async (params?: {
    start_date?: string;
    end_date?: string;
    group_by?: 'day' | 'week' | 'month';
  }) => {
    const response = await apiClient.get<{
      total_sales: number;
      total_orders: number;
      average_order_value: number;
      sales_by_period: Array<{
        period: string;
        sales: number;
        orders: number;
      }>;
      top_products: Array<{
        product_id: string;
        product_name: string;
        total_sold: number;
        revenue: number;
      }>;
      top_categories: Array<{
        category: string;
        total_sold: number;
        revenue: number;
      }>;
    }>('/v1/admin/dashboard/sales', { params });
    return response.data;
  },
};

// React Query 키 팩토리 (관리자용)
export const adminQueryKeys = {
  products: {
    all: ['admin', 'products'] as const,
    detail: (id: string) => ['admin', 'products', id] as const,
  },
  orders: {
    all: ['admin', 'orders'] as const,
    list: (params?: Record<string, unknown>) => ['admin', 'orders', 'list', params] as const,
    detail: (id: string) => ['admin', 'orders', id] as const,
  },
  users: {
    all: ['admin', 'users'] as const,
    list: (params?: Record<string, unknown>) => ['admin', 'users', 'list', params] as const,
    detail: (id: string) => ['admin', 'users', id] as const,
  },
  sales: {
    stats: (params?: Record<string, unknown>) => ['admin', 'sales', 'stats', params] as const,
  },
};
