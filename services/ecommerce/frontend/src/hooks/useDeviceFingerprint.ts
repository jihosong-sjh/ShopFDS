/**
 * Device Fingerprinting Hook
 *
 * Automatically collects and submits device fingerprint on mount
 */

import { useEffect, useState } from 'react';
import { generateDeviceFingerprint, calculateDeviceId } from '../utils/deviceFingerprint';
import axios from 'axios';

const FDS_API_URL = import.meta.env.VITE_FDS_API_URL || 'http://localhost:8001';

interface DeviceFingerprintResult {
  deviceId: string | null;
  isBlacklisted: boolean;
  isLoading: boolean;
  error: string | null;
}

export function useDeviceFingerprint(): DeviceFingerprintResult {
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [isBlacklisted, setIsBlacklisted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function collectFingerprint() {
      try {
        // 로컬 스토리지에서 이전 device_id 확인
        const cachedDeviceId = localStorage.getItem('device_id');
        if (cachedDeviceId) {
          setDeviceId(cachedDeviceId);
          setIsLoading(false);
          return;
        }

        // 디바이스 핑거프린트 생성
        const fingerprint = await generateDeviceFingerprint();
        await calculateDeviceId(fingerprint);

        if (!mounted) return;

        // FDS 서비스에 핑거프린트 전송
        const response = await axios.post(`${FDS_API_URL}/v1/fds/device-fingerprint/collect`, {
          canvas_hash: fingerprint.canvasHash,
          webgl_hash: fingerprint.webglHash,
          audio_hash: fingerprint.audioHash,
          cpu_cores: fingerprint.cpuCores,
          memory_size: fingerprint.memorySize,
          screen_resolution: fingerprint.screenResolution,
          timezone: fingerprint.timezone,
          language: fingerprint.language,
          user_agent: fingerprint.userAgent,
        });

        if (!mounted) return;

        const { device_id, blacklisted, is_new } = response.data;

        // 디바이스 ID를 로컬 스토리지에 저장
        localStorage.setItem('device_id', device_id);
        setDeviceId(device_id);
        setIsBlacklisted(blacklisted);

        // 신규 디바이스 또는 블랙리스트 상태 로깅
        if (is_new) {
          console.log('[Device Fingerprint] New device registered:', device_id);
        }

        if (blacklisted) {
          console.warn('[Device Fingerprint] Device is blacklisted:', device_id);
          // 블랙리스트 알림 (옵션)
          // alert('보안 사유로 접속이 제한되었습니다. 고객센터에 문의하세요.');
        }
      } catch (err: any) {
        console.error('[Device Fingerprint] Error collecting fingerprint:', err);
        setError(err.message || 'Failed to collect device fingerprint');
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    collectFingerprint();

    return () => {
      mounted = false;
    };
  }, []);

  return { deviceId, isBlacklisted, isLoading, error };
}
