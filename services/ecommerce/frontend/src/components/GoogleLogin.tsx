/**
 * GoogleLogin Component
 *
 * Google OAuth 로그인 버튼 컴포넌트
 */

import React from 'react';

interface GoogleLoginProps {
  onSuccess?: (response: unknown) => void;
  onError?: (error: unknown) => void;
}

const GoogleLogin: React.FC<GoogleLoginProps> = () => {
  const handleGoogleLogin = () => {
    // Google OAuth 로그인 URL로 리다이렉트
    const backendUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const googleLoginUrl = `${backendUrl}/v1/auth/oauth/google`;

    // 현재 URL을 세션 스토리지에 저장 (콜백 후 돌아올 URL)
    sessionStorage.setItem('oauth_redirect_url', window.location.href);

    // Google OAuth 페이지로 이동
    window.location.href = googleLoginUrl;
  };

  return (
    <button
      onClick={handleGoogleLogin}
      className="flex items-center justify-center w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
      data-testid="google-login-button"
      aria-label="Google로 로그인"
    >
      {/* Google 로고 SVG */}
      <svg
        className="w-5 h-5 mr-2"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          fill="#4285F4"
        />
        <path
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          fill="#34A853"
        />
        <path
          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
          fill="#FBBC05"
        />
        <path
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
          fill="#EA4335"
        />
      </svg>
      <span className="text-sm font-medium text-gray-700">Google로 로그인</span>
    </button>
  );
};

export default GoogleLogin;
