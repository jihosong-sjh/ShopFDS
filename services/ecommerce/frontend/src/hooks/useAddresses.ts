/**
 * useAddresses Hook
 *
 * 배송지 관리 Hook (React Query)
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export interface Address {
  id: string;
  address_name: string;
  recipient_name: string;
  phone: string;
  zipcode: string;
  address: string;
  address_detail?: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateAddressRequest {
  address_name: string;
  recipient_name: string;
  phone: string;
  zipcode: string;
  address: string;
  address_detail?: string;
  is_default: boolean;
}

export interface UpdateAddressRequest extends CreateAddressRequest {}

/**
 * 배송지 목록 조회 Hook
 */
export const useAddresses = () => {
  return useQuery<Address[]>({
    queryKey: ["addresses"],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/v1/addresses`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
      return response.data.addresses;
    },
  });
};

/**
 * 배송지 추가 Hook
 */
export const useCreateAddress = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateAddressRequest) => {
      const response = await axios.post(`${API_BASE_URL}/v1/addresses`, data, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["addresses"] });
    },
  });
};

/**
 * 배송지 수정 Hook
 */
export const useUpdateAddress = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: UpdateAddressRequest;
    }) => {
      const response = await axios.put(
        `${API_BASE_URL}/v1/addresses/${id}`,
        data,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["addresses"] });
    },
  });
};

/**
 * 배송지 삭제 Hook
 */
export const useDeleteAddress = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await axios.delete(`${API_BASE_URL}/v1/addresses/${id}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["addresses"] });
    },
  });
};

/**
 * 기본 배송지 설정 Hook
 */
export const useSetDefaultAddress = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await axios.post(
        `${API_BASE_URL}/v1/addresses/${id}/set-default`,
        {},
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["addresses"] });
    },
  });
};
