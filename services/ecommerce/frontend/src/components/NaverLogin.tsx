/**
 * NaverLogin Component
 *
 * Naver OAuth 로그인 버튼 컴포넌트
 */

import React from 'react';

interface NaverLoginProps {
  onSuccess?: (response: any) => void;
  onError?: (error: any) => void;
}

const NaverLogin: React.FC<NaverLoginProps> = ({ onSuccess, onError }) => {
  const handleNaverLogin = () => {
    // Naver OAuth 로그인 URL로 리다이렉트
    const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const naverLoginUrl = `${backendUrl}/v1/auth/oauth/naver`;

    // 현재 URL을 세션 스토리지에 저장 (콜백 후 돌아올 URL)
    sessionStorage.setItem('oauth_redirect_url', window.location.href);

    // Naver OAuth 페이지로 이동
    window.location.href = naverLoginUrl;
  };

  return (
    <button
      onClick={handleNaverLogin}
      className="flex items-center justify-center w-full px-4 py-2 rounded-lg shadow-sm bg-green-500 hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
      data-testid="naver-login-button"
      aria-label="Naver로 로그인"
    >
      {/* Naver 로고 텍스트 */}
      <svg
        className="w-5 h-5 mr-2"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M16.273 12.845L7.376 0H0v24h7.726V11.156L16.624 24H24V0h-7.727v12.845z"
          fill="#FFFFFF"
        />
      </svg>
      <span className="text-sm font-medium text-white">Naver로 로그인</span>
    </button>
  );
};

export default NaverLogin;
