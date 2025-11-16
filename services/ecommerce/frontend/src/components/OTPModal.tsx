/**
 * 추가 인증 모달 컴포넌트 (OTP 입력 화면)
 *
 * T062: 의심 거래 시 추가 인증을 요구하는 모달
 *
 * 기능:
 * - OTP 6자리 입력 UI
 * - OTP 재전송 기능
 * - 실패 횟수 표시 (최대 3회)
 * - 타이머 표시 (5분)
 */

import React, { useState, useEffect, useRef } from 'react';

interface OTPModalProps {
  isOpen: boolean;
  onClose: () => void;
  onVerify: (otp: string) => Promise<void>;
  onResend: () => Promise<void>;
  phoneNumber: string;
  remainingAttempts: number;
}

export const OTPModal: React.FC<OTPModalProps> = ({
  isOpen,
  onClose,
  onVerify,
  onResend,
  phoneNumber,
  remainingAttempts,
}) => {
  const [otp, setOtp] = useState<string[]>(['', '', '', '', '', '']);
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState('');
  const [timeLeft, setTimeLeft] = useState(300); // 5분 = 300초
  const [canResend, setCanResend] = useState(false);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // 타이머 카운트다운
  useEffect(() => {
    if (!isOpen || timeLeft === 0) return;

    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          setCanResend(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isOpen, timeLeft]);

  // 모달이 열릴 때 상태 초기화 및 첫 번째 입력칸에 포커스
  useEffect(() => {
    if (isOpen) {
      setOtp(['', '', '', '', '', '']);
      setError('');
      setTimeLeft(300);
      setCanResend(false);
      setTimeout(() => {
        inputRefs.current[0]?.focus();
      }, 100);
    }
  }, [isOpen]);

  const handleChange = (index: number, value: string) => {
    // 숫자만 입력 가능
    if (value && !/^\d$/.test(value)) return;

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);
    setError('');

    // 값을 입력하면 다음 칸으로 자동 이동
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // 6자리가 모두 입력되면 자동으로 검증
    if (value && index === 5 && newOtp.every((digit) => digit !== '')) {
      handleVerify(newOtp.join(''));
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    // Backspace를 누르면 이전 칸으로 이동
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }

    // 왼쪽 화살표
    if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }

    // 오른쪽 화살표
    if (e.key === 'ArrowRight' && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Enter 키로 검증
    if (e.key === 'Enter' && otp.every((digit) => digit !== '')) {
      handleVerify(otp.join(''));
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text');
    const digits = pastedData.replace(/\D/g, '').slice(0, 6).split('');

    if (digits.length === 6) {
      setOtp(digits);
      setError('');
      inputRefs.current[5]?.focus();
      // 붙여넣기 후 자동 검증
      setTimeout(() => handleVerify(digits.join('')), 100);
    }
  };

  const handleVerify = async (otpCode: string) => {
    if (otpCode.length !== 6) {
      setError('6자리 인증번호를 입력해주세요.');
      return;
    }

    setIsVerifying(true);
    setError('');

    try {
      await onVerify(otpCode);
      // 성공 시 모달은 상위 컴포넌트에서 닫힘
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || '인증번호가 올바르지 않습니다.');
      setOtp(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } finally {
      setIsVerifying(false);
    }
  };

  const handleResend = async () => {
    if (!canResend) return;

    try {
      await onResend();
      setTimeLeft(300);
      setCanResend(false);
      setOtp(['', '', '', '', '', '']);
      setError('');
      inputRefs.current[0]?.focus();
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || '인증번호 재전송에 실패했습니다.');
    }
  };

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const maskedPhoneNumber = phoneNumber.replace(/(\d{3})-(\d{4})-(\d{4})/, '$1-****-$3');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* 헤더 */}
        <div className="px-6 py-4 border-b">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900">추가 인증</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
              aria-label="닫기"
            >
              <svg
                className="w-6 h-6"
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
        </div>

        {/* 본문 */}
        <div className="px-6 py-6">
          {/* 안내 메시지 */}
          <div className="mb-6">
            <div className="flex items-center justify-center mb-4">
              <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-indigo-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                  />
                </svg>
              </div>
            </div>
            <p className="text-center text-gray-700 mb-2">
              보안을 위해 추가 인증이 필요합니다.
            </p>
            <p className="text-center text-sm text-gray-600">
              {maskedPhoneNumber}로 전송된<br />
              6자리 인증번호를 입력해주세요.
            </p>
          </div>

          {/* OTP 입력 칸 */}
          <div className="flex justify-center gap-2 mb-4">
            {otp.map((digit, index) => (
              <input
                key={index}
                ref={(el) => (inputRefs.current[index] = el)}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                onPaste={index === 0 ? handlePaste : undefined}
                className={`w-12 h-14 text-center text-2xl font-bold border-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${
                  error ? 'border-red-500' : 'border-gray-300'
                }`}
                disabled={isVerifying}
              />
            ))}
          </div>

          {/* 타이머 */}
          <div className="text-center mb-4">
            <span className={`text-sm font-medium ${timeLeft <= 60 ? 'text-red-600' : 'text-gray-600'}`}>
              남은 시간: {formatTime(timeLeft)}
            </span>
          </div>

          {/* 에러 메시지 */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800 text-center">{error}</p>
            </div>
          )}

          {/* 남은 시도 횟수 */}
          <div className="text-center mb-4">
            <p className="text-sm text-gray-600">
              남은 시도 횟수: <span className={`font-bold ${remainingAttempts <= 1 ? 'text-red-600' : 'text-indigo-600'}`}>
                {remainingAttempts}회
              </span>
            </p>
          </div>

          {/* 재전송 버튼 */}
          <div className="text-center">
            <button
              onClick={handleResend}
              disabled={!canResend}
              className={`text-sm font-medium ${
                canResend
                  ? 'text-indigo-600 hover:text-indigo-700'
                  : 'text-gray-400 cursor-not-allowed'
              }`}
            >
              {canResend ? '인증번호 재전송' : `재전송 가능 (${formatTime(timeLeft)})`}
            </button>
          </div>

          {/* 검증 버튼 (선택적으로 사용, 자동 검증이 기본) */}
          {otp.every((digit) => digit !== '') && !isVerifying && (
            <button
              onClick={() => handleVerify(otp.join(''))}
              className="w-full mt-4 px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              인증 확인
            </button>
          )}

          {isVerifying && (
            <div className="flex items-center justify-center mt-4">
              <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
              <span className="ml-2 text-gray-600">인증 중...</span>
            </div>
          )}
        </div>

        {/* 푸터 안내 */}
        <div className="px-6 py-4 bg-gray-50 border-t rounded-b-lg">
          <p className="text-xs text-gray-600 text-center">
            인증번호가 오지 않으면 스팸 메시지함을 확인해주세요.<br />
            3회 실패 시 거래가 자동으로 차단됩니다.
          </p>
        </div>
      </div>
    </div>
  );
};
