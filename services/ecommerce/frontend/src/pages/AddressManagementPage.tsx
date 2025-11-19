/**
 * AddressManagementPage
 *
 * 배송지 관리 페이지 (목록, CRUD)
 */

import React, { useState } from "react";
import {
  useAddresses,
  useCreateAddress,
  useUpdateAddress,
  useDeleteAddress,
  useSetDefaultAddress,
  Address,
  CreateAddressRequest,
} from "../hooks/useAddresses";
import { AddressCard } from "../components/AddressCard";
import { AddressForm } from "../components/AddressForm";

export const AddressManagementPage: React.FC = () => {
  const { data: addresses, isLoading, error } = useAddresses();
  const createAddress = useCreateAddress();
  const updateAddress = useUpdateAddress();
  const deleteAddress = useDeleteAddress();
  const setDefaultAddress = useSetDefaultAddress();

  const [showForm, setShowForm] = useState(false);
  const [editingAddress, setEditingAddress] = useState<Address | null>(null);

  // 배송지 추가
  const handleCreate = (data: CreateAddressRequest) => {
    createAddress.mutate(data, {
      onSuccess: () => {
        setShowForm(false);
        alert("배송지가 추가되었습니다.");
      },
      onError: (error: any) => {
        alert(
          error.response?.data?.detail ||
            "배송지 추가에 실패했습니다."
        );
      },
    });
  };

  // 배송지 수정
  const handleUpdate = (data: CreateAddressRequest) => {
    if (!editingAddress) return;

    updateAddress.mutate(
      { id: editingAddress.id, data },
      {
        onSuccess: () => {
          setEditingAddress(null);
          setShowForm(false);
          alert("배송지가 수정되었습니다.");
        },
        onError: (error: any) => {
          alert(
            error.response?.data?.detail ||
              "배송지 수정에 실패했습니다."
          );
        },
      }
    );
  };

  // 배송지 삭제
  const handleDelete = (id: string) => {
    if (!confirm("정말 삭제하시겠습니까?")) return;

    deleteAddress.mutate(id, {
      onSuccess: () => {
        alert("배송지가 삭제되었습니다.");
      },
      onError: (error: any) => {
        alert(
          error.response?.data?.detail ||
            "배송지 삭제에 실패했습니다."
        );
      },
    });
  };

  // 기본 배송지 설정
  const handleSetDefault = (id: string) => {
    setDefaultAddress.mutate(id, {
      onSuccess: () => {
        alert("기본 배송지로 설정되었습니다.");
      },
      onError: (error: any) => {
        alert(
          error.response?.data?.detail ||
            "기본 배송지 설정에 실패했습니다."
        );
      },
    });
  };

  // 수정 버튼 클릭
  const handleEdit = (address: Address) => {
    setEditingAddress(address);
    setShowForm(true);
  };

  // 폼 닫기
  const handleCancel = () => {
    setShowForm(false);
    setEditingAddress(null);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-gray-600">로딩 중...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-red-600">
          배송지를 불러오는 중 오류가 발생했습니다.
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* 헤더 */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">배송지 관리</h1>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            배송지 추가
          </button>
        )}
      </div>

      {/* 배송지 추가/수정 폼 */}
      {showForm && (
        <div className="mb-6 p-6 bg-white border rounded-lg shadow-sm">
          <h2 className="text-lg font-semibold mb-4">
            {editingAddress ? "배송지 수정" : "새 배송지 추가"}
          </h2>
          <AddressForm
            address={editingAddress}
            onSubmit={editingAddress ? handleUpdate : handleCreate}
            onCancel={handleCancel}
            isLoading={createAddress.isPending || updateAddress.isPending}
          />
        </div>
      )}

      {/* 배송지 목록 */}
      <div className="space-y-4">
        {addresses && addresses.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            등록된 배송지가 없습니다.
            <br />
            배송지를 추가해주세요.
          </div>
        ) : (
          addresses?.map((address) => (
            <AddressCard
              key={address.id}
              address={address}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onSetDefault={handleSetDefault}
            />
          ))
        )}
      </div>
    </div>
  );
};
