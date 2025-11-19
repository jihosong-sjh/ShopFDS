import React, { useState, useEffect, useRef } from 'react';

interface LazyImageProps {
  src: string;
  alt: string;
  className?: string;
  placeholderSrc?: string;
  onLoad?: () => void;
  onError?: () => void;
}

/**
 * LazyImage 컴포넌트
 *
 * Intersection Observer API를 사용하여 이미지를 지연 로딩합니다.
 * 뷰포트에 들어올 때만 실제 이미지를 로드하여 성능을 최적화합니다.
 *
 * @param src - 로드할 이미지의 URL
 * @param alt - 이미지 대체 텍스트 (접근성)
 * @param className - 추가 CSS 클래스
 * @param placeholderSrc - 로딩 중 표시할 플레이스홀더 이미지 URL
 * @param onLoad - 이미지 로드 완료 시 호출될 콜백
 * @param onError - 이미지 로드 실패 시 호출될 콜백
 */
const LazyImage: React.FC<LazyImageProps> = ({
  src,
  alt,
  className = '',
  placeholderSrc = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300"%3E%3Crect fill="%23f0f0f0" width="400" height="300"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle"%3ELoading...%3C/text%3E%3C/svg%3E',
  onLoad,
  onError,
}) => {
  const [imageSrc, setImageSrc] = useState<string>(placeholderSrc);
  const [isLoaded, setIsLoaded] = useState<boolean>(false);
  const [hasError, setHasError] = useState<boolean>(false);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    // Intersection Observer가 지원되지 않는 브라우저는 즉시 로드
    if (!('IntersectionObserver' in window)) {
      setImageSrc(src);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            // 뷰포트에 들어오면 실제 이미지 로드
            setImageSrc(src);
            if (imgRef.current) {
              observer.unobserve(imgRef.current);
            }
          }
        });
      },
      {
        // 뷰포트에서 200px 전에 미리 로드 시작
        rootMargin: '200px',
        threshold: 0.01,
      }
    );

    const currentImg = imgRef.current;
    if (currentImg) {
      observer.observe(currentImg);
    }

    return () => {
      if (currentImg) {
        observer.unobserve(currentImg);
      }
    };
  }, [src]);

  const handleLoad = () => {
    setIsLoaded(true);
    if (onLoad) {
      onLoad();
    }
  };

  const handleError = () => {
    setHasError(true);
    // 에러 발생 시 기본 에러 이미지 표시
    setImageSrc(
      'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300"%3E%3Crect fill="%23fee" width="400" height="300"/%3E%3Ctext fill="%23c33" x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle"%3EImage Load Error%3C/text%3E%3C/svg%3E'
    );
    if (onError) {
      onError();
    }
  };

  return (
    <img
      ref={imgRef}
      src={imageSrc}
      alt={alt}
      className={`${className} ${isLoaded ? 'opacity-100' : 'opacity-70'} ${
        hasError ? 'bg-red-50' : ''
      } transition-opacity duration-300`}
      onLoad={handleLoad}
      onError={handleError}
      loading="lazy"
    />
  );
};

export default LazyImage;
