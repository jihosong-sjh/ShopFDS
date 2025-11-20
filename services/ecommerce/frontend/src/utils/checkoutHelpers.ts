/**
 * Checkout Helper Functions
 *
 * 체크아웃 페이지에서 사용되는 헬퍼 함수들
 */

import { Address } from "../hooks/useAddresses";

/**
 * 기본 배송지 찾기
 */
export const getDefaultAddress = (addresses: Address[]): Address | null => {
  return addresses.find((addr) => addr.is_default) || addresses[0] || null;
};

/**
 * 배송지를 체크아웃 폼 데이터로 변환
 */
export const addressToCheckoutData = (address: Address | null) => {
  if (!address) {
    return {
      recipient_name: "",
      phone: "",
      zipcode: "",
      address: "",
      address_detail: "",
    };
  }

  return {
    recipient_name: address.recipient_name,
    phone: address.phone,
    zipcode: address.zipcode,
    address: address.address,
    address_detail: address.address_detail || "",
  };
};
