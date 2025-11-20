/**
 * Behavior Tracking Hook
 *
 * T039: 행동 패턴 분석 통합 - React Hook
 *
 * Usage:
 * ```tsx
 * import { useBehaviorTracking } from '../hooks/useBehaviorTracking';
 *
 * function CheckoutPage() {
 *   const { submitBehaviorPattern } = useBehaviorTracking('/checkout');
 *
 *   const handleSubmit = async () => {
 *     const result = await submitBehaviorPattern();
 *     if (result && result.bot_score > 90) {
 *       alert('비정상적인 접근이 감지되었습니다.');
 *       return;
 *     }
 *     // 주문 진행...
 *   };
 * }
 * ```
 */

import { useEffect, useRef } from 'react';
import behaviorTracker from '../utils/behaviorTracking';

interface BehaviorAnalysisResult {
  session_id: string;
  bot_score: number;
  risk_level: string;
  requires_additional_auth: boolean;
  mouse_analysis: {
    avg_speed: number;
    avg_acceleration: number;
    straight_line_ratio: number;
    pause_count: number;
  };
  keyboard_analysis: {
    avg_typing_speed: number;
    avg_key_hold_time: number;
    backspace_ratio: number;
  };
  clickstream_analysis: {
    total_clicks: number;
    avg_time_between_clicks: number;
    unique_pages: number;
  };
  risk_factors: string[];
}

export function useBehaviorTracking(pagePath: string) {
  const isTrackingRef = useRef(false);

  useEffect(() => {
    // 추적 시작
    if (!isTrackingRef.current) {
      behaviorTracker.startTracking();
      behaviorTracker.trackPageChange(pagePath);
      isTrackingRef.current = true;
    }

    // 컴포넌트 언마운트 시 추적 중지
    return () => {
      if (isTrackingRef.current) {
        behaviorTracker.stopTracking();
        isTrackingRef.current = false;
      }
    };
  }, [pagePath]);

  /**
   * 행동 패턴 데이터 수집 및 FDS API로 전송
   *
   * @param userId 로그인한 사용자 ID (선택사항)
   * @returns 분석 결과 또는 null (실패 시)
   */
  const submitBehaviorPattern = async (
    userId?: string
  ): Promise<BehaviorAnalysisResult | null> => {
    try {
      const behaviorPattern = behaviorTracker.getBehaviorPattern();

      console.log('[Behavior Tracking] 수집 데이터:', {
        mouseMovements: behaviorPattern.mouseMovements.length,
        keyboardEvents: behaviorPattern.keyboardEvents.length,
        clickstream: behaviorPattern.clickstream.length,
        collectDuration: behaviorPattern.collectDuration,
      });

      // FDS API로 행동 패턴 데이터 전송
      const response = await fetch('http://localhost:8001/v1/fds/behavior-pattern', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: behaviorPattern.sessionId,
          user_id: userId || null,
          mouse_movements: behaviorPattern.mouseMovements,
          keyboard_events: behaviorPattern.keyboardEvents,
          clickstream: behaviorPattern.clickstream,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result: BehaviorAnalysisResult = await response.json();

      console.log('[Behavior Analysis] 봇 점수:', result.bot_score);
      console.log('[Behavior Analysis] 위험 수준:', result.risk_level);
      console.log('[Behavior Analysis] 위험 요인:', result.risk_factors);

      if (result.requires_additional_auth) {
        console.log('[Behavior Analysis] 추가 인증이 필요합니다.');
      }

      return result;
    } catch (error) {
      console.error('[Behavior Analysis] 분석 실패:', error);
      // Fail-Open: 분석 실패 시에도 계속 진행
      return null;
    }
  };

  /**
   * 현재 수집된 행동 패턴 데이터 반환
   */
  const getBehaviorPattern = () => {
    return behaviorTracker.getBehaviorPattern();
  };

  /**
   * 페이지 변경 추적
   */
  const trackPageChange = (newPage: string) => {
    behaviorTracker.trackPageChange(newPage);
  };

  return {
    submitBehaviorPattern,
    getBehaviorPattern,
    trackPageChange,
  };
}
