/**
 * Behavior Tracking Utility
 *
 * 사용자 행동 패턴 수집 (마우스 움직임, 키보드 입력, 클릭스트림)
 * 봇 탐지를 위한 클라이언트 사이드 데이터 수집
 */

export interface MouseMovement {
  timestamp: number;
  x: number;
  y: number;
  speed: number;
  acceleration: number;
  curvature: number;
}

export interface KeyboardEvent {
  timestamp: number;
  key: string;
  duration: number;
}

export interface ClickstreamEvent {
  page: string;
  timestamp: number;
  duration: number;
}

export interface BehaviorPattern {
  sessionId: string;
  mouseMovements: MouseMovement[];
  keyboardEvents: KeyboardEvent[];
  clickstream: ClickstreamEvent[];
  collectDuration: number;
}

class BehaviorTracker {
  private mouseMovements: MouseMovement[] = [];
  private keyboardEvents: KeyboardEvent[] = [];
  private clickstream: ClickstreamEvent[] = [];
  private sessionId: string;
  private isTracking: boolean = false;
  private startTime: number = 0;
  private lastMousePosition: { x: number; y: number; timestamp: number } | null = null;
  private lastMouseSpeed: number = 0;
  private keydownTimestamps: Map<string, number> = new Map();
  private currentPage: string = "";
  private pageStartTime: number = 0;

  constructor() {
    this.sessionId = this.generateSessionId();
  }

  /**
   * 세션 ID 생성 (UUID v4)
   */
  private generateSessionId(): string {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  /**
   * 행동 패턴 추적 시작
   */
  startTracking(): void {
    if (this.isTracking) {
      return;
    }

    this.isTracking = true;
    this.startTime = Date.now();
    this.currentPage = window.location.pathname;
    this.pageStartTime = Date.now();

    // 마우스 움직임 이벤트 리스너
    document.addEventListener("mousemove", this.handleMouseMove);

    // 키보드 이벤트 리스너
    document.addEventListener("keydown", this.handleKeyDown);
    document.addEventListener("keyup", this.handleKeyUp);

    // 페이지 전환 이벤트 리스너
    window.addEventListener("beforeunload", this.handlePageUnload);
  }

  /**
   * 행동 패턴 추적 중지
   */
  stopTracking(): void {
    if (!this.isTracking) {
      return;
    }

    this.isTracking = false;

    // 이벤트 리스너 제거
    document.removeEventListener("mousemove", this.handleMouseMove);
    document.removeEventListener("keydown", this.handleKeyDown);
    document.removeEventListener("keyup", this.handleKeyUp);
    window.removeEventListener("beforeunload", this.handlePageUnload);

    // 현재 페이지 체류 시간 저장
    if (this.currentPage && this.pageStartTime > 0) {
      this.clickstream.push({
        page: this.currentPage,
        timestamp: this.pageStartTime,
        duration: Date.now() - this.pageStartTime,
      });
    }
  }

  /**
   * 마우스 움직임 이벤트 핸들러
   */
  private handleMouseMove = (event: MouseEvent): void => {
    const currentTime = Date.now();
    const currentX = event.clientX;
    const currentY = event.clientY;

    if (this.lastMousePosition) {
      // 이동 거리 계산
      const deltaX = currentX - this.lastMousePosition.x;
      const deltaY = currentY - this.lastMousePosition.y;
      const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

      // 시간 차이 계산 (초 단위)
      const deltaTime = (currentTime - this.lastMousePosition.timestamp) / 1000;

      if (deltaTime > 0 && distance > 0) {
        // 속도 계산 (pixels per second)
        const speed = distance / deltaTime;

        // 가속도 계산 (pixels per second^2)
        const acceleration = Math.abs(speed - this.lastMouseSpeed) / deltaTime;

        // 곡률 계산 (0 = 직선, 1 = 완전한 곡선)
        // 곡률 = 각도 변화율 / 이동 거리
        const curvature = this.calculateCurvature(
          this.lastMousePosition.x,
          this.lastMousePosition.y,
          currentX,
          currentY,
          deltaX,
          deltaY,
          distance
        );

        this.mouseMovements.push({
          timestamp: currentTime,
          x: currentX,
          y: currentY,
          speed,
          acceleration,
          curvature,
        });

        this.lastMouseSpeed = speed;

        // 메모리 관리: 최근 1000개만 유지
        if (this.mouseMovements.length > 1000) {
          this.mouseMovements = this.mouseMovements.slice(-1000);
        }
      }
    }

    this.lastMousePosition = {
      x: currentX,
      y: currentY,
      timestamp: currentTime,
    };
  };

  /**
   * 곡률 계산
   * 봇은 직선 움직임 (curvature ≈ 0)
   * 사람은 곡선 움직임 (curvature > 0.1)
   */
  private calculateCurvature(
    prevX: number,
    prevY: number,
    currX: number,
    currY: number,
    deltaX: number,
    deltaY: number,
    distance: number
  ): number {
    if (distance < 10) {
      return 0; // 너무 짧은 이동은 무시
    }

    // 이동 방향 각도 계산
    const angle = Math.atan2(deltaY, deltaX);

    // 이전 이동과의 각도 차이 (단순화: 절대값)
    const angleDiff = Math.abs(angle);

    // 곡률 = 각도 변화 / 거리
    const curvature = angleDiff / distance;

    return Math.min(curvature, 1); // 0-1 범위로 제한
  }

  /**
   * 키 다운 이벤트 핸들러
   */
  private handleKeyDown = (event: KeyboardEvent): void => {
    const key = event.key;
    const timestamp = Date.now();

    if (!this.keydownTimestamps.has(key)) {
      this.keydownTimestamps.set(key, timestamp);
    }
  };

  /**
   * 키 업 이벤트 핸들러
   */
  private handleKeyUp = (event: KeyboardEvent): void => {
    const key = event.key;
    const timestamp = Date.now();

    const keydownTime = this.keydownTimestamps.get(key);
    if (keydownTime) {
      const duration = timestamp - keydownTime;

      this.keyboardEvents.push({
        timestamp,
        key: key.length === 1 ? "*" : key, // 실제 문자는 "*"로 마스킹 (보안)
        duration,
      });

      this.keydownTimestamps.delete(key);

      // 메모리 관리: 최근 500개만 유지
      if (this.keyboardEvents.length > 500) {
        this.keyboardEvents = this.keyboardEvents.slice(-500);
      }
    }
  };

  /**
   * 페이지 언로드 이벤트 핸들러
   */
  private handlePageUnload = (): void => {
    if (this.currentPage && this.pageStartTime > 0) {
      this.clickstream.push({
        page: this.currentPage,
        timestamp: this.pageStartTime,
        duration: Date.now() - this.pageStartTime,
      });
    }
  };

  /**
   * 페이지 변경 추적
   */
  trackPageChange(newPage: string): void {
    if (this.currentPage && this.pageStartTime > 0) {
      this.clickstream.push({
        page: this.currentPage,
        timestamp: this.pageStartTime,
        duration: Date.now() - this.pageStartTime,
      });
    }

    this.currentPage = newPage;
    this.pageStartTime = Date.now();
  }

  /**
   * 수집된 행동 패턴 데이터 반환
   */
  getBehaviorPattern(): BehaviorPattern {
    return {
      sessionId: this.sessionId,
      mouseMovements: this.mouseMovements,
      keyboardEvents: this.keyboardEvents,
      clickstream: this.clickstream,
      collectDuration: Date.now() - this.startTime,
    };
  }

  /**
   * 데이터 초기화
   */
  reset(): void {
    this.mouseMovements = [];
    this.keyboardEvents = [];
    this.clickstream = [];
    this.sessionId = this.generateSessionId();
    this.startTime = Date.now();
    this.lastMousePosition = null;
    this.lastMouseSpeed = 0;
    this.keydownTimestamps.clear();
    this.currentPage = "";
    this.pageStartTime = 0;
  }
}

// 싱글톤 인스턴스 생성
const behaviorTracker = new BehaviorTracker();

export default behaviorTracker;
