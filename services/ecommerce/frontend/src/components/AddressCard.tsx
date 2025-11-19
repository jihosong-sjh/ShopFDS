/**
 * AddressCard Component
 *
 * 배송지 카드 (기본 배송지 뱃지, 수정/삭제 버튼)
 */

import React from "react";
import { Address } from "../hooks/useAddresses";

interface AddressCardProps {
  address: Address;
  onEdit: (address: Address) => void;
  onDelete: (id: string) => void;
  onSetDefault: (id: string) => void;
}

export const AddressCard: React.FC<AddressCardProps> = ({
  address,
  onEdit,
  onDelete,
  onSetDefault,
}) => {
  return (
    <div className="border rounded-lg p-4 hover:shadow-md transition-shadow">
      {/* 헤더: 이름 + 기본 배송지 뱃지 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-lg">{address.address_name}</h3>
          {address.is_default && (
            <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">
              기본 배송지
            </span>
          )}
        </div>

        {/* 액션 버튼 */}
        <div className="flex gap-2">
          <button
            onClick={() => onEdit(address)}
            className="px-3 py-1 text-sm text-gray-700 hover:text-gray-900 border border-gray-300 rounded hover:bg-gray-50"
          >
            수정
          </button>
          <button
            onClick={() => onDelete(address.id)}
            className="px-3 py-1 text-sm text-red-600 hover:text-red-800 border border-red-300 rounded hover:bg-red-50"
          >
            삭제
          </button>
        </div>
      </div>

      {/* 수령인 정보 */}
      <div className="space-y-1 text-sm text-gray-700">
        <p className="font-medium">{address.recipient_name}</p>
        <p>{address.phone}</p>
        <p className="text-gray-600">
          ({address.zipcode}) {address.address}
        </p>
        {address.address_detail && (
          <p className="text-gray-600">{address.address_detail}</p>
        )}
      </div>

      {/* 기본 배송지 설정 버튼 */}
      {!address.is_default && (
        <button
          onClick={() => onSetDefault(address.id)}
          className="mt-4 w-full py-2 text-sm text-blue-600 border border-blue-300 rounded hover:bg-blue-50"
        >
          기본 배송지로 설정
        </button>
      )}
    </div>
  );
};
