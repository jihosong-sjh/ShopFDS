/**
 * KakaoLogin Component
 *
 * Kakao OAuth 로그인 버튼 컴포넌트
 */

import React from 'react';

interface KakaoLoginProps {
  onSuccess?: (response: any) => void;
  onError?: (error: any) => void;
}

const KakaoLogin: React.FC<KakaoLoginProps> = ({ onSuccess, onError }) => {
  const handleKakaoLogin = () => {
    // Kakao OAuth 로그인 URL로 리다이렉트
    const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const kakaoLoginUrl = `${backendUrl}/v1/auth/oauth/kakao`;

    // 현재 URL을 세션 스토리지에 저장 (콜백 후 돌아올 URL)
    sessionStorage.setItem('oauth_redirect_url', window.location.href);

    // Kakao OAuth 페이지로 이동
    window.location.href = kakaoLoginUrl;
  };

  return (
    <button
      onClick={handleKakaoLogin}
      className="flex items-center justify-center w-full px-4 py-2 rounded-lg shadow-sm bg-yellow-400 hover:bg-yellow-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 transition-colors"
      data-testid="kakao-login-button"
      aria-label="Kakao로 로그인"
    >
      {/* Kakao 로고 SVG */}
      <svg
        className="w-5 h-5 mr-2"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M12 3C6.48 3 2 6.48 2 10.8c0 2.7 1.74 5.07 4.38 6.45-.18.66-.72 2.58-.84 2.97-.15.51.18.51.39.36.15-.12 2.46-1.68 3.54-2.43.84.12 1.71.18 2.61.18 5.52 0 10-3.48 10-7.8C22 6.48 17.52 3 12 3z"
          fill="#3C1E1E"
        />
      </svg>
      <span className="text-sm font-medium text-gray-900">Kakao로 로그인</span>
    </button>
  );
};

export default KakaoLogin;
