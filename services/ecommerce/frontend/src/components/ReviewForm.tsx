import React, { useState } from 'react';

interface ReviewFormProps {
  productId: string;
  orderId?: string;
  onSubmit: (data: ReviewFormData) => Promise<void>;
  onCancel: () => void;
  initialData?: Partial<ReviewFormData>;
}

export interface ReviewFormData {
  product_id: string;
  order_id?: string;
  rating: number;
  title: string;
  content: string;
  images: string[];
}

/**
 * ReviewForm 컴포넌트
 *
 * 리뷰를 작성하거나 수정하는 폼입니다.
 * 별점, 제목, 내용, 사진 업로드(최대 3장) 기능을 제공합니다.
 *
 * @param productId - 상품 ID
 * @param orderId - 주문 ID (선택사항, 구매 확정 고객인 경우)
 * @param onSubmit - 리뷰 제출 콜백
 * @param onCancel - 취소 콜백
 * @param initialData - 초기 데이터 (수정 모드)
 */
const ReviewForm: React.FC<ReviewFormProps> = ({
  productId,
  orderId,
  onSubmit,
  onCancel,
  initialData,
}) => {
  const [rating, setRating] = useState<number>(initialData?.rating || 0);
  const [hoveredRating, setHoveredRating] = useState<number>(0);
  const [title, setTitle] = useState<string>(initialData?.title || '');
  const [content, setContent] = useState<string>(initialData?.content || '');
  const [images, setImages] = useState<string[]>(initialData?.images || []);
  const [uploading, setUploading] = useState<boolean>(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (rating === 0) {
      newErrors.rating = '별점을 선택해주세요';
    }

    if (!title.trim()) {
      newErrors.title = '제목을 입력해주세요';
    } else if (title.length > 50) {
      newErrors.title = '제목은 50자 이하로 입력해주세요';
    }

    if (!content.trim()) {
      newErrors.content = '내용을 입력해주세요';
    } else if (content.length < 10) {
      newErrors.content = '내용은 10자 이상 입력해주세요';
    } else if (content.length > 1000) {
      newErrors.content = '내용은 1000자 이하로 입력해주세요';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      await onSubmit({
        product_id: productId,
        order_id: orderId,
        rating,
        title: title.trim(),
        content: content.trim(),
        images,
      });
    } catch (error) {
      console.error('리뷰 제출 실패:', error);
      setErrors({
        submit: '리뷰 제출에 실패했습니다. 다시 시도해주세요.',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    // 최대 3장 제한
    const remainingSlots = 3 - images.length;
    if (remainingSlots <= 0) {
      setErrors({ ...errors, images: '최대 3장까지 업로드할 수 있습니다' });
      return;
    }

    const filesToUpload = Array.from(files).slice(0, remainingSlots);

    setUploading(true);
    setErrors({ ...errors, images: '' });

    try {
      // 실제 구현에서는 API를 통해 이미지를 업로드해야 합니다
      // 여기서는 임시로 FileReader를 사용하여 base64로 변환합니다
      const uploadedImages: string[] = [];

      for (const file of filesToUpload) {
        // 파일 크기 체크 (5MB 제한)
        if (file.size > 5 * 1024 * 1024) {
          setErrors({ ...errors, images: '이미지는 5MB 이하만 업로드 가능합니다' });
          continue;
        }

        // 이미지 파일 타입 체크
        if (!file.type.startsWith('image/')) {
          setErrors({ ...errors, images: '이미지 파일만 업로드 가능합니다' });
          continue;
        }

        // FileReader를 사용하여 base64로 변환 (실제로는 API로 업로드)
        const reader = new FileReader();
        const imageUrl = await new Promise<string>((resolve, reject) => {
          reader.onload = () => resolve(reader.result as string);
          reader.onerror = reject;
          reader.readAsDataURL(file);
        });

        uploadedImages.push(imageUrl);
      }

      setImages([...images, ...uploadedImages]);
    } catch (error) {
      console.error('이미지 업로드 실패:', error);
      setErrors({ ...errors, images: '이미지 업로드에 실패했습니다' });
    } finally {
      setUploading(false);
    }
  };

  const handleRemoveImage = (index: number) => {
    setImages(images.filter((_, i) => i !== index));
  };

  const renderStars = () => {
    return (
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => setRating(star)}
            onMouseEnter={() => setHoveredRating(star)}
            onMouseLeave={() => setHoveredRating(0)}
            className="focus:outline-none focus:ring-2 focus:ring-yellow-400 rounded"
            aria-label={`${star}점`}
          >
            <svg
              className={`w-10 h-10 transition-colors ${
                star <= (hoveredRating || rating)
                  ? 'text-yellow-400 fill-current'
                  : 'text-gray-300'
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1}
                d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
              />
            </svg>
          </button>
        ))}
        <span className="ml-2 text-gray-600 self-center">
          {rating > 0 ? `${rating}점` : '별점을 선택하세요'}
        </span>
      </div>
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* 별점 선택 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          별점 <span className="text-red-500">*</span>
        </label>
        {renderStars()}
        {errors.rating && (
          <p className="mt-1 text-sm text-red-600">{errors.rating}</p>
        )}
      </div>

      {/* 제목 */}
      <div>
        <label
          htmlFor="review-title"
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          제목 <span className="text-red-500">*</span>
        </label>
        <input
          id="review-title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={50}
          placeholder="리뷰 제목을 입력하세요"
          className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
            errors.title
              ? 'border-red-500 focus:ring-red-500'
              : 'border-gray-300 focus:ring-blue-500'
          }`}
        />
        <div className="mt-1 flex justify-between">
          {errors.title && (
            <p className="text-sm text-red-600">{errors.title}</p>
          )}
          <p className="text-sm text-gray-500 ml-auto">{title.length}/50</p>
        </div>
      </div>

      {/* 내용 */}
      <div>
        <label
          htmlFor="review-content"
          className="block text-sm font-medium text-gray-700 mb-2"
        >
          내용 <span className="text-red-500">*</span>
        </label>
        <textarea
          id="review-content"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          maxLength={1000}
          rows={6}
          placeholder="상품에 대한 솔직한 리뷰를 작성해주세요 (최소 10자)"
          className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 resize-none ${
            errors.content
              ? 'border-red-500 focus:ring-red-500'
              : 'border-gray-300 focus:ring-blue-500'
          }`}
        />
        <div className="mt-1 flex justify-between">
          {errors.content && (
            <p className="text-sm text-red-600">{errors.content}</p>
          )}
          <p className="text-sm text-gray-500 ml-auto">{content.length}/1000</p>
        </div>
      </div>

      {/* 사진 업로드 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          사진 첨부 (선택사항, 최대 3장)
        </label>

        <div className="flex gap-4 flex-wrap">
          {/* 업로드된 이미지 미리보기 */}
          {images.map((image, index) => (
            <div key={index} className="relative w-24 h-24 group">
              <img
                src={image}
                alt={`리뷰 이미지 ${index + 1}`}
                className="w-full h-full object-cover rounded-lg"
              />
              <button
                type="button"
                onClick={() => handleRemoveImage(index)}
                className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                aria-label="이미지 삭제"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          ))}

          {/* 업로드 버튼 */}
          {images.length < 3 && (
            <label
              className={`w-24 h-24 border-2 border-dashed border-gray-300 rounded-lg flex flex-col items-center justify-center cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-colors ${
                uploading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {uploading ? (
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
              ) : (
                <>
                  <svg
                    className="w-8 h-8 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 4v16m8-8H4"
                    />
                  </svg>
                  <span className="text-xs text-gray-500 mt-1">사진 추가</span>
                </>
              )}
              <input
                type="file"
                accept="image/*"
                multiple
                onChange={handleImageUpload}
                disabled={uploading}
                className="hidden"
              />
            </label>
          )}
        </div>

        {errors.images && (
          <p className="mt-2 text-sm text-red-600">{errors.images}</p>
        )}
        <p className="mt-2 text-sm text-gray-500">
          JPG, PNG, GIF 형식, 최대 5MB
        </p>
      </div>

      {/* 제출 에러 */}
      {errors.submit && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{errors.submit}</p>
        </div>
      )}

      {/* 버튼 */}
      <div className="flex gap-3 justify-end">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          취소
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isSubmitting ? '제출 중...' : initialData ? '수정하기' : '리뷰 작성'}
        </button>
      </div>
    </form>
  );
};

export default ReviewForm;
