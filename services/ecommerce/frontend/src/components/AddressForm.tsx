/**
 * AddressForm Component
 *
 * 배송지 추가/수정 폼
 */

import React, { useState, useEffect } from "react";
import { Address, CreateAddressRequest } from "../hooks/useAddresses";

interface AddressFormProps {
  address?: Address | null;
  onSubmit: (data: CreateAddressRequest) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export const AddressForm: React.FC<AddressFormProps> = ({
  address,
  onSubmit,
  onCancel,
  isLoading = false,
}) => {
  const [formData, setFormData] = useState<CreateAddressRequest>({
    address_name: "",
    recipient_name: "",
    phone: "",
    zipcode: "",
    address: "",
    address_detail: "",
    is_default: false,
  });

  // 수정 모드일 때 기존 데이터 로드
  useEffect(() => {
    if (address) {
      setFormData({
        address_name: address.address_name,
        recipient_name: address.recipient_name,
        phone: address.phone,
        zipcode: address.zipcode,
        address: address.address,
        address_detail: address.address_detail || "",
        is_default: address.is_default,
      });
    }
  }, [address]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;
    const checked = (e.target as HTMLInputElement).checked;

    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* 배송지 이름 */}
      <div>
        <label htmlFor="address_name" className="block text-sm font-medium text-gray-700 mb-1">
          배송지 이름
        </label>
        <input
          type="text"
          id="address_name"
          name="address_name"
          value={formData.address_name}
          onChange={handleChange}
          required
          maxLength={100}
          placeholder="예: 집, 회사"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* 수령인 이름 */}
      <div>
        <label htmlFor="recipient_name" className="block text-sm font-medium text-gray-700 mb-1">
          수령인
        </label>
        <input
          type="text"
          id="recipient_name"
          name="recipient_name"
          value={formData.recipient_name}
          onChange={handleChange}
          required
          maxLength={100}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* 전화번호 */}
      <div>
        <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-1">
          전화번호
        </label>
        <input
          type="tel"
          id="phone"
          name="phone"
          value={formData.phone}
          onChange={handleChange}
          required
          placeholder="010-1234-5678"
          pattern="^0\d{1,2}-\d{3,4}-\d{4}$"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">형식: 010-1234-5678</p>
      </div>

      {/* 우편번호 */}
      <div>
        <label htmlFor="zipcode" className="block text-sm font-medium text-gray-700 mb-1">
          우편번호
        </label>
        <input
          type="text"
          id="zipcode"
          name="zipcode"
          value={formData.zipcode}
          onChange={handleChange}
          required
          maxLength={10}
          placeholder="06234"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* 기본 주소 */}
      <div>
        <label htmlFor="address" className="block text-sm font-medium text-gray-700 mb-1">
          주소
        </label>
        <input
          type="text"
          id="address"
          name="address"
          value={formData.address}
          onChange={handleChange}
          required
          maxLength={500}
          placeholder="서울특별시 강남구 테헤란로 123"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* 상세 주소 */}
      <div>
        <label htmlFor="address_detail" className="block text-sm font-medium text-gray-700 mb-1">
          상세 주소 (선택)
        </label>
        <input
          type="text"
          id="address_detail"
          name="address_detail"
          value={formData.address_detail}
          onChange={handleChange}
          maxLength={500}
          placeholder="456동 789호"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* 기본 배송지 설정 */}
      <div className="flex items-center">
        <input
          type="checkbox"
          id="is_default"
          name="is_default"
          checked={formData.is_default}
          onChange={handleChange}
          className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
        />
        <label htmlFor="is_default" className="ml-2 text-sm text-gray-700">
          기본 배송지로 설정
        </label>
      </div>

      {/* 버튼 */}
      <div className="flex gap-3 pt-4">
        <button
          type="submit"
          disabled={isLoading}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
        >
          {isLoading ? "저장 중..." : address ? "수정" : "추가"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={isLoading}
          className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:bg-gray-100"
        >
          취소
        </button>
      </div>
    </form>
  );
};
