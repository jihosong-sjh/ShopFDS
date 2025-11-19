import React, { useState } from 'react';
import LazyImage from './LazyImage';

interface ImageGalleryProps {
  images: string[];
  alt: string;
  onImageClick?: (index: number) => void;
}

/**
 * ImageGallery 컴포넌트
 *
 * 상품 이미지를 썸네일 목록과 메인 이미지로 표시합니다.
 * 썸네일을 클릭하면 메인 이미지가 전환됩니다.
 *
 * @param images - 이미지 URL 배열
 * @param alt - 이미지 대체 텍스트
 * @param onImageClick - 메인 이미지 클릭 시 호출될 콜백 (확대 보기용)
 */
const ImageGallery: React.FC<ImageGalleryProps> = ({
  images,
  alt,
  onImageClick,
}) => {
  const [selectedIndex, setSelectedIndex] = useState<number>(0);

  if (!images || images.length === 0) {
    return (
      <div className="w-full bg-gray-100 rounded-lg flex items-center justify-center h-96">
        <span className="text-gray-400 text-lg">이미지 없음</span>
      </div>
    );
  }

  const handleThumbnailClick = (index: number) => {
    setSelectedIndex(index);
  };

  const handleMainImageClick = () => {
    if (onImageClick) {
      onImageClick(selectedIndex);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, index: number) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setSelectedIndex(index);
    }
  };

  const handlePrevious = () => {
    setSelectedIndex((prev) => (prev > 0 ? prev - 1 : images.length - 1));
  };

  const handleNext = () => {
    setSelectedIndex((prev) => (prev < images.length - 1 ? prev + 1 : 0));
  };

  return (
    <div className="flex flex-col gap-4">
      {/* 메인 이미지 */}
      <div className="relative w-full aspect-square bg-gray-100 rounded-lg overflow-hidden group">
        <LazyImage
          src={images[selectedIndex]}
          alt={`${alt} - 이미지 ${selectedIndex + 1}`}
          className="w-full h-full object-contain cursor-pointer"
          onClick={handleMainImageClick}
        />

        {/* 확대 보기 힌트 */}
        {onImageClick && (
          <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-all duration-200 flex items-center justify-center pointer-events-none">
            <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-white px-4 py-2 rounded-lg shadow-lg">
              <span className="text-sm text-gray-700">클릭하여 확대</span>
            </div>
          </div>
        )}

        {/* 이전/다음 버튼 (이미지가 2개 이상일 때만 표시) */}
        {images.length > 1 && (
          <>
            <button
              onClick={handlePrevious}
              className="absolute left-2 top-1/2 -translate-y-1/2 bg-white bg-opacity-80 hover:bg-opacity-100 rounded-full p-2 shadow-lg transition-all duration-200 opacity-0 group-hover:opacity-100"
              aria-label="이전 이미지"
            >
              <svg
                className="w-6 h-6 text-gray-700"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            </button>
            <button
              onClick={handleNext}
              className="absolute right-2 top-1/2 -translate-y-1/2 bg-white bg-opacity-80 hover:bg-opacity-100 rounded-full p-2 shadow-lg transition-all duration-200 opacity-0 group-hover:opacity-100"
              aria-label="다음 이미지"
            >
              <svg
                className="w-6 h-6 text-gray-700"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          </>
        )}

        {/* 이미지 인디케이터 */}
        {images.length > 1 && (
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
            {images.map((_, index) => (
              <div
                key={index}
                className={`w-2 h-2 rounded-full transition-all duration-200 ${
                  index === selectedIndex
                    ? 'bg-white w-6'
                    : 'bg-white bg-opacity-50'
                }`}
              />
            ))}
          </div>
        )}
      </div>

      {/* 썸네일 목록 */}
      {images.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-2">
          {images.map((image, index) => (
            <button
              key={index}
              onClick={() => handleThumbnailClick(index)}
              onKeyDown={(e) => handleKeyDown(e, index)}
              className={`flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden border-2 transition-all duration-200 ${
                index === selectedIndex
                  ? 'border-blue-500 ring-2 ring-blue-200'
                  : 'border-gray-200 hover:border-gray-400'
              }`}
              aria-label={`썸네일 ${index + 1}`}
              aria-pressed={index === selectedIndex}
            >
              <LazyImage
                src={image}
                alt={`${alt} - 썸네일 ${index + 1}`}
                className="w-full h-full object-cover"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default ImageGallery;
