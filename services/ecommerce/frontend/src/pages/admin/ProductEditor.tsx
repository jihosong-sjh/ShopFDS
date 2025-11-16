/**
 * 상품 등록/수정 페이지
 *
 * T091: 상품 등록/수정 페이지 구현
 */

import React, { useState, useEffect } from 'react';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { adminApi, adminQueryKeys } from '../../services/admin-api';
import { productsApi, queryKeys as publicQueryKeys } from '../../services/api';

export const ProductEditor: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const isEditMode = !!id;

  // 폼 상태
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    price: 0,
    stock_quantity: 0,
    category: '',
    image_url: '',
    status: 'active',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  // 수정 모드일 경우 기존 상품 데이터 로드
  const { data: product, isLoading: isLoadingProduct } = useQuery({
    queryKey: adminQueryKeys.products.detail(id || ''),
    queryFn: () => productsApi.getProduct(id!),
    enabled: isEditMode,
  });

  useEffect(() => {
    if (product && isEditMode) {
      setFormData({
        name: product.name,
        description: product.description || '',
        price: product.price,
        stock_quantity: product.stock_quantity,
        category: product.category,
        image_url: product.image_url || '',
        status: product.status,
      });
    }
  }, [product, isEditMode]);

  // 상품 생성 뮤테이션
  const createProductMutation = useMutation({
    mutationFn: adminApi.createProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.products.all });
      queryClient.invalidateQueries({ queryKey: publicQueryKeys.products.all });
      alert('상품이 성공적으로 등록되었습니다.');
      navigate('/admin/products');
    },
    onError: (error) => {
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      alert(`상품 등록 실패: ${err.response?.data?.detail || err.message}`);
    },
  });

  // 상품 수정 뮤테이션
  const updateProductMutation = useMutation({
    mutationFn: ({ productId, data }: { productId: string; data: Record<string, unknown> }) =>
      adminApi.updateProduct(productId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.products.all });
      queryClient.invalidateQueries({ queryKey: publicQueryKeys.products.all });
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.products.detail(id!) });
      alert('상품이 성공적으로 수정되었습니다.');
      navigate('/admin/products');
    },
    onError: (error) => {
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      alert(`상품 수정 실패: ${err.response?.data?.detail || err.message}`);
    },
  });

  // 상품 삭제 뮤테이션
  const deleteProductMutation = useMutation({
    mutationFn: adminApi.deleteProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminQueryKeys.products.all });
      queryClient.invalidateQueries({ queryKey: publicQueryKeys.products.all });
      alert('상품이 성공적으로 삭제되었습니다.');
      navigate('/admin/products');
    },
    onError: (error) => {
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      alert(`상품 삭제 실패: ${err.response?.data?.detail || err.message}`);
    },
  });

  // 유효성 검증
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = '상품명은 필수입니다.';
    }

    if (formData.price <= 0) {
      newErrors.price = '가격은 0보다 커야 합니다.';
    }

    if (formData.stock_quantity < 0) {
      newErrors.stock_quantity = '재고 수량은 0 이상이어야 합니다.';
    }

    if (!formData.category.trim()) {
      newErrors.category = '카테고리는 필수입니다.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // 폼 제출 핸들러
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    if (isEditMode) {
      updateProductMutation.mutate({
        productId: id!,
        data: formData,
      });
    } else {
      createProductMutation.mutate(formData);
    }
  };

  // 삭제 핸들러
  const handleDelete = () => {
    if (window.confirm('정말로 이 상품을 삭제하시겠습니까?')) {
      deleteProductMutation.mutate(id!);
    }
  };

  // 입력 변경 핸들러
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'price' || name === 'stock_quantity' ? Number(value) : value,
    }));
    // 에러 클리어
    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  if (isEditMode && isLoadingProduct) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-lg">로딩 중...</div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6 flex justify-between items-center">
        <h1 className="text-3xl font-bold">{isEditMode ? '상품 수정' : '상품 등록'}</h1>
        <button
          onClick={() => navigate('/admin/products')}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
        >
          목록으로
        </button>
      </div>

      <form onSubmit={handleSubmit} className="bg-white shadow-md rounded-lg p-6 space-y-6">
        {/* 상품명 */}
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
            상품명 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            className={`w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              errors.name ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-indigo-500'
            }`}
            placeholder="예: 삼성 갤럭시 S23"
          />
          {errors.name && <p className="mt-1 text-sm text-red-500">{errors.name}</p>}
        </div>

        {/* 설명 */}
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
            상품 설명
          </label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            rows={4}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="상품에 대한 상세 설명을 입력하세요."
          />
        </div>

        {/* 가격 */}
        <div>
          <label htmlFor="price" className="block text-sm font-medium text-gray-700 mb-2">
            가격 (원) <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            id="price"
            name="price"
            value={formData.price}
            onChange={handleChange}
            min="0"
            step="100"
            className={`w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              errors.price ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-indigo-500'
            }`}
            placeholder="예: 1200000"
          />
          {errors.price && <p className="mt-1 text-sm text-red-500">{errors.price}</p>}
        </div>

        {/* 재고 수량 */}
        <div>
          <label htmlFor="stock_quantity" className="block text-sm font-medium text-gray-700 mb-2">
            재고 수량 <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            id="stock_quantity"
            name="stock_quantity"
            value={formData.stock_quantity}
            onChange={handleChange}
            min="0"
            className={`w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              errors.stock_quantity
                ? 'border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:ring-indigo-500'
            }`}
            placeholder="예: 50"
          />
          {errors.stock_quantity && <p className="mt-1 text-sm text-red-500">{errors.stock_quantity}</p>}
        </div>

        {/* 카테고리 */}
        <div>
          <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-2">
            카테고리 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="category"
            name="category"
            value={formData.category}
            onChange={handleChange}
            className={`w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              errors.category ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-indigo-500'
            }`}
            placeholder="예: 전자제품"
          />
          {errors.category && <p className="mt-1 text-sm text-red-500">{errors.category}</p>}
        </div>

        {/* 이미지 URL */}
        <div>
          <label htmlFor="image_url" className="block text-sm font-medium text-gray-700 mb-2">
            이미지 URL
          </label>
          <input
            type="url"
            id="image_url"
            name="image_url"
            value={formData.image_url}
            onChange={handleChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="https://example.com/image.jpg"
          />
        </div>

        {/* 상태 (수정 모드에서만) */}
        {isEditMode && (
          <div>
            <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-2">
              상태
            </label>
            <select
              id="status"
              name="status"
              value={formData.status}
              onChange={handleChange}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="active">활성</option>
              <option value="inactive">비활성</option>
              <option value="discontinued">단종</option>
            </select>
          </div>
        )}

        {/* 버튼 그룹 */}
        <div className="flex justify-between items-center pt-4 border-t">
          <div>
            {isEditMode && (
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleteProductMutation.isPending}
                className="px-6 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                {deleteProductMutation.isPending ? '삭제 중...' : '삭제'}
              </button>
            )}
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => navigate('/admin/products')}
              className="px-6 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={createProductMutation.isPending || updateProductMutation.isPending}
              className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
            >
              {createProductMutation.isPending || updateProductMutation.isPending
                ? '저장 중...'
                : isEditMode
                ? '수정'
                : '등록'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};
