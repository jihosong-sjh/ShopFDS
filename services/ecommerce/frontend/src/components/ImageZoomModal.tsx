import React, { useState, useEffect, useRef } from 'react';
import LazyImage from './LazyImage';

interface ImageZoomModalProps {
  images: string[];
  initialIndex: number;
  alt: string;
  isOpen: boolean;
  onClose: () => void;
}

/**
 * ImageZoomModal 컴포넌트
 *
 * 이미지를 2배 확대하여 전체 화면으로 보여주는 모달입니다.
 * 좌우 화살표로 이미지를 전환할 수 있습니다.
 *
 * @param images - 이미지 URL 배열
 * @param initialIndex - 초기 표시할 이미지 인덱스
 * @param alt - 이미지 대체 텍스트
 * @param isOpen - 모달 열림 상태
 * @param onClose - 모달 닫기 콜백
 */
const ImageZoomModal: React.FC<ImageZoomModalProps> = ({
  images,
  initialIndex,
  alt,
  isOpen,
  onClose,
}) => {
  const [currentIndex, setCurrentIndex] = useState<number>(initialIndex);
  const [scale, setScale] = useState<number>(1);
  const [position, setPosition] = useState<{ x: number; y: number }>({
    x: 0,
    y: 0,
  });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({
    x: 0,
    y: 0,
  });
  const imageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setCurrentIndex(initialIndex);
  }, [initialIndex]);

  useEffect(() => {
    if (!isOpen) {
      // 모달이 닫힐 때 상태 초기화
      setScale(1);
      setPosition({ x: 0, y: 0 });
      setIsDragging(false);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowLeft') {
        handlePrevious();
      } else if (e.key === 'ArrowRight') {
        handleNext();
      } else if (e.key === '+' || e.key === '=') {
        handleZoomIn();
      } else if (e.key === '-' || e.key === '_') {
        handleZoomOut();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, currentIndex, scale]);

  if (!isOpen) return null;

  const handlePrevious = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : images.length - 1));
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev < images.length - 1 ? prev + 1 : 0));
    setScale(1);
    setPosition({ x: 0, y: 0 });
  };

  const handleZoomIn = () => {
    setScale((prev) => Math.min(prev + 0.5, 4));
  };

  const handleZoomOut = () => {
    setScale((prev) => Math.max(prev - 0.5, 1));
    if (scale <= 1.5) {
      setPosition({ x: 0, y: 0 });
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (scale > 1) {
      setIsDragging(true);
      setDragStart({
        x: e.clientX - position.x,
        y: e.clientY - position.y,
      });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging && scale > 1) {
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black bg-opacity-95 flex items-center justify-center"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-label="이미지 확대 보기"
    >
      {/* 닫기 버튼 */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 text-white hover:text-gray-300 transition-colors z-10"
        aria-label="닫기"
      >
        <svg
          className="w-8 h-8"
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

      {/* 이미지 카운터 */}
      <div className="absolute top-4 left-4 text-white text-lg z-10">
        {currentIndex + 1} / {images.length}
      </div>

      {/* 줌 컨트롤 */}
      <div className="absolute bottom-4 right-4 flex gap-2 z-10">
        <button
          onClick={handleZoomOut}
          disabled={scale <= 1}
          className="bg-white bg-opacity-80 hover:bg-opacity-100 disabled:bg-opacity-40 disabled:cursor-not-allowed rounded-lg p-2 transition-all duration-200"
          aria-label="축소"
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
              d="M20 12H4"
            />
          </svg>
        </button>
        <div className="bg-white bg-opacity-80 rounded-lg px-4 py-2 flex items-center">
          <span className="text-gray-700 font-medium">
            {Math.round(scale * 100)}%
          </span>
        </div>
        <button
          onClick={handleZoomIn}
          disabled={scale >= 4}
          className="bg-white bg-opacity-80 hover:bg-opacity-100 disabled:bg-opacity-40 disabled:cursor-not-allowed rounded-lg p-2 transition-all duration-200"
          aria-label="확대"
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
              d="M12 4v16m8-8H4"
            />
          </svg>
        </button>
      </div>

      {/* 이전 버튼 */}
      {images.length > 1 && (
        <button
          onClick={handlePrevious}
          className="absolute left-4 top-1/2 -translate-y-1/2 bg-white bg-opacity-80 hover:bg-opacity-100 rounded-full p-3 shadow-lg transition-all duration-200 z-10"
          aria-label="이전 이미지"
        >
          <svg
            className="w-8 h-8 text-gray-700"
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
      )}

      {/* 메인 이미지 */}
      <div
        ref={imageRef}
        className={`max-w-full max-h-full ${
          scale > 1 ? 'cursor-move' : 'cursor-zoom-in'
        } ${isDragging ? 'cursor-grabbing' : ''}`}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={(e) => {
          e.stopPropagation();
          if (scale === 1) handleZoomIn();
        }}
      >
        <div
          style={{
            transform: `scale(${scale}) translate(${position.x / scale}px, ${
              position.y / scale
            }px)`,
            transition: isDragging ? 'none' : 'transform 0.2s ease-out',
          }}
        >
          <LazyImage
            src={images[currentIndex]}
            alt={`${alt} - 이미지 ${currentIndex + 1}`}
            className="max-w-screen-lg max-h-screen select-none pointer-events-none"
          />
        </div>
      </div>

      {/* 다음 버튼 */}
      {images.length > 1 && (
        <button
          onClick={handleNext}
          className="absolute right-4 top-1/2 -translate-y-1/2 bg-white bg-opacity-80 hover:bg-opacity-100 rounded-full p-3 shadow-lg transition-all duration-200 z-10"
          aria-label="다음 이미지"
        >
          <svg
            className="w-8 h-8 text-gray-700"
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
      )}

      {/* 키보드 단축키 안내 */}
      <div className="absolute bottom-4 left-4 text-white text-sm opacity-70 z-10">
        <div>ESC: 닫기</div>
        <div>←/→: 이미지 전환</div>
        <div>+/-: 확대/축소</div>
      </div>
    </div>
  );
};

export default ImageZoomModal;
