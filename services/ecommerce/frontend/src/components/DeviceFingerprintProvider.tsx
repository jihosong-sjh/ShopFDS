/**
 * Device Fingerprint Provider
 *
 * Automatically collects device fingerprint when the app loads
 */

import React from 'react';
import { useDeviceFingerprint } from '../hooks/useDeviceFingerprint';

export const DeviceFingerprintProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const { deviceId, isBlacklisted, isLoading } = useDeviceFingerprint();

  // 블랙리스트된 디바이스 경고 표시 (옵션)
  if (isBlacklisted && deviceId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-8 text-center">
          <div className="text-6xl mb-4">[BLOCKED]</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            Access Blocked
          </h1>
          <p className="text-gray-600 mb-6">
            Security reasons. Please contact customer support.
          </p>
          <p className="text-sm text-gray-400">
            Device ID: {deviceId}
          </p>
        </div>
      </div>
    );
  }

  // 로딩 중에는 자식 컴포넌트 렌더링 (백그라운드에서 수집)
  return <>{children}</>;
};
