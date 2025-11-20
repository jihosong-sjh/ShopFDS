"""
Behavior Analysis Engine

마우스 움직임, 키보드 타이핑, 클릭스트림 분석으로 봇 탐지
"""

from typing import Dict, List, Any
import statistics


class BehaviorAnalysisEngine:
    """행동 패턴 분석 엔진 - 봇 탐지"""

    # 봇 탐지 임계값
    MOUSE_LOW_CURVATURE_THRESHOLD = 0.1  # 곡률 < 0.1 = 직선 움직임 (봇)
    MOUSE_HIGH_SPEED_THRESHOLD = 5000  # pixels/sec (비정상 빠른 속도)
    KEYBOARD_FAST_TYPING_THRESHOLD = 50  # ms (너무 빠른 타이핑)
    KEYBOARD_BACKSPACE_RATIO_THRESHOLD = 0.3  # 백스페이스 30% 이상 (사람)
    CLICKSTREAM_SHORT_DURATION_THRESHOLD = 500  # ms (페이지 체류 시간 < 0.5초)
    CLICKSTREAM_LONG_DURATION_THRESHOLD = 300000  # ms (페이지 체류 시간 > 5분)

    def __init__(self):
        pass

    def analyze(
        self,
        mouse_movements: List[Dict[str, Any]],
        keyboard_events: List[Dict[str, Any]],
        clickstream: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        행동 패턴 종합 분석

        Args:
            mouse_movements: 마우스 움직임 데이터
            keyboard_events: 키보드 이벤트 데이터
            clickstream: 클릭스트림 데이터

        Returns:
            분석 결과 및 봇 점수
        """
        # 각 분석 수행
        mouse_analysis = self.analyze_mouse_movements(mouse_movements)
        keyboard_analysis = self.analyze_keyboard_typing(keyboard_events)
        clickstream_analysis = self.analyze_clickstream(clickstream)

        # 봇 확률 점수 계산
        bot_score = self.calculate_bot_score(
            mouse_analysis, keyboard_analysis, clickstream_analysis
        )

        return {
            "bot_score": bot_score,
            "mouse_analysis": mouse_analysis,
            "keyboard_analysis": keyboard_analysis,
            "clickstream_analysis": clickstream_analysis,
            "risk_factors": self._extract_risk_factors(
                bot_score, mouse_analysis, keyboard_analysis, clickstream_analysis
            ),
        }

    def analyze_mouse_movements(
        self, mouse_movements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        마우스 움직임 분석 (속도, 가속도, 곡률)

        Args:
            mouse_movements: 마우스 움직임 데이터
                [{"timestamp": int, "x": int, "y": int, "speed": float,
                  "acceleration": float, "curvature": float}]

        Returns:
            분석 결과
        """
        if not mouse_movements:
            return {
                "avg_speed": 0,
                "avg_acceleration": 0,
                "avg_curvature": 0,
                "low_curvature_ratio": 1.0,  # 데이터 없음 = 의심
                "high_speed_ratio": 0,
                "is_bot_like": True,
                "total_movements": 0,
            }

        speeds = [m["speed"] for m in mouse_movements if "speed" in m]
        accelerations = [
            m["acceleration"] for m in mouse_movements if "acceleration" in m
        ]
        curvatures = [m["curvature"] for m in mouse_movements if "curvature" in m]

        # 통계 계산
        avg_speed = statistics.mean(speeds) if speeds else 0
        avg_acceleration = statistics.mean(accelerations) if accelerations else 0
        avg_curvature = statistics.mean(curvatures) if curvatures else 0

        # 낮은 곡률 비율 (직선 움직임 = 봇)
        low_curvature_count = sum(
            1 for c in curvatures if c < self.MOUSE_LOW_CURVATURE_THRESHOLD
        )
        low_curvature_ratio = (
            low_curvature_count / len(curvatures) if curvatures else 1.0
        )

        # 높은 속도 비율 (비정상 빠른 속도 = 봇)
        high_speed_count = sum(1 for s in speeds if s > self.MOUSE_HIGH_SPEED_THRESHOLD)
        high_speed_ratio = high_speed_count / len(speeds) if speeds else 0

        # 봇과 유사한 패턴 판별
        is_bot_like = (
            low_curvature_ratio > 0.7  # 70% 이상 직선 움직임
            or high_speed_ratio > 0.5  # 50% 이상 비정상 속도
            or len(mouse_movements) < 10  # 마우스 움직임 너무 적음
        )

        return {
            "avg_speed": round(avg_speed, 2),
            "avg_acceleration": round(avg_acceleration, 2),
            "avg_curvature": round(avg_curvature, 4),
            "low_curvature_ratio": round(low_curvature_ratio, 2),
            "high_speed_ratio": round(high_speed_ratio, 2),
            "is_bot_like": is_bot_like,
            "total_movements": len(mouse_movements),
        }

    def analyze_keyboard_typing(
        self, keyboard_events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        키보드 타이핑 패턴 분석 (입력 속도, 백스페이스 빈도)

        Args:
            keyboard_events: 키보드 이벤트 데이터
                [{"timestamp": int, "key": str, "duration": int}]

        Returns:
            분석 결과
        """
        if not keyboard_events:
            return {
                "avg_typing_speed": 0,
                "backspace_ratio": 0,
                "fast_typing_ratio": 0,
                "is_bot_like": False,  # 타이핑 없음은 정상 (마우스만 사용)
                "total_keystrokes": 0,
            }

        durations = [e["duration"] for e in keyboard_events if "duration" in e]
        avg_duration = statistics.mean(durations) if durations else 0

        # 백스페이스 빈도 (사람은 실수로 백스페이스 자주 누름)
        backspace_count = sum(
            1 for e in keyboard_events if e.get("key") in ["Backspace", "Delete"]
        )
        backspace_ratio = (
            backspace_count / len(keyboard_events) if keyboard_events else 0
        )

        # 빠른 타이핑 비율 (봇은 일정한 빠른 속도)
        fast_typing_count = sum(
            1 for d in durations if d < self.KEYBOARD_FAST_TYPING_THRESHOLD
        )
        fast_typing_ratio = fast_typing_count / len(durations) if durations else 0

        # 타이핑 속도 변동 (표준편차 작음 = 일정한 속도 = 봇)
        typing_speed_stddev = statistics.stdev(durations) if len(durations) > 1 else 0

        # 봇과 유사한 패턴 판별
        is_bot_like = (
            fast_typing_ratio > 0.8  # 80% 이상 매우 빠른 타이핑
            and backspace_ratio < 0.05  # 백스페이스 거의 없음 (완벽한 타이핑)
            and typing_speed_stddev < 10  # 타이핑 속도 변동 거의 없음
        )

        return {
            "avg_typing_speed": round(avg_duration, 2),
            "backspace_ratio": round(backspace_ratio, 2),
            "fast_typing_ratio": round(fast_typing_ratio, 2),
            "typing_speed_stddev": round(typing_speed_stddev, 2),
            "is_bot_like": is_bot_like,
            "total_keystrokes": len(keyboard_events),
        }

    def analyze_clickstream(self, clickstream: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        클릭스트림 분석 (페이지 체류 시간 이상치 탐지)

        Args:
            clickstream: 클릭스트림 데이터
                [{"page": str, "timestamp": int, "duration": int}]

        Returns:
            분석 결과
        """
        if not clickstream:
            return {
                "avg_page_duration": 0,
                "short_duration_ratio": 0,
                "long_duration_ratio": 0,
                "is_bot_like": False,
                "total_pages": 0,
            }

        durations = [c["duration"] for c in clickstream if "duration" in c]
        avg_duration = statistics.mean(durations) if durations else 0

        # 짧은 체류 시간 비율 (봇은 빠르게 페이지 전환)
        short_duration_count = sum(
            1 for d in durations if d < self.CLICKSTREAM_SHORT_DURATION_THRESHOLD
        )
        short_duration_ratio = short_duration_count / len(durations) if durations else 0

        # 긴 체류 시간 비율 (봇이 멈춤)
        long_duration_count = sum(
            1 for d in durations if d > self.CLICKSTREAM_LONG_DURATION_THRESHOLD
        )
        long_duration_ratio = long_duration_count / len(durations) if durations else 0

        # 페이지 체류 시간 변동 (표준편차 작음 = 일정한 패턴 = 봇)
        duration_stddev = statistics.stdev(durations) if len(durations) > 1 else 0

        # 봇과 유사한 패턴 판별
        is_bot_like = (
            short_duration_ratio > 0.7  # 70% 이상 매우 짧은 체류
            or duration_stddev < 500  # 체류 시간 변동 거의 없음
            or avg_duration < 1000  # 평균 체류 시간 < 1초
        )

        return {
            "avg_page_duration": round(avg_duration, 2),
            "short_duration_ratio": round(short_duration_ratio, 2),
            "long_duration_ratio": round(long_duration_ratio, 2),
            "duration_stddev": round(duration_stddev, 2),
            "is_bot_like": is_bot_like,
            "total_pages": len(clickstream),
        }

    def calculate_bot_score(
        self,
        mouse_analysis: Dict[str, Any],
        keyboard_analysis: Dict[str, Any],
        clickstream_analysis: Dict[str, Any],
    ) -> int:
        """
        봇 확률 점수 계산 (0-100)

        Args:
            mouse_analysis: 마우스 분석 결과
            keyboard_analysis: 키보드 분석 결과
            clickstream_analysis: 클릭스트림 분석 결과

        Returns:
            봇 점수 (0 = 정상 사용자, 100 = 확실한 봇)
        """
        score = 0

        # 마우스 분석 점수 (가중치: 50%)
        if mouse_analysis["is_bot_like"]:
            score += 50
        else:
            # 곡률 기반 점수 (곡률 낮을수록 봇)
            curvature_score = max(
                0, 25 - mouse_analysis["avg_curvature"] * 100
            )  # 곡률 < 0.25 = 봇
            score += curvature_score

            # 속도 기반 점수
            if mouse_analysis["high_speed_ratio"] > 0.3:
                score += 15

            # 움직임 부족 점수
            if mouse_analysis["total_movements"] < 50:
                score += 10

        # 키보드 분석 점수 (가중치: 25%)
        if keyboard_analysis["is_bot_like"]:
            score += 25
        else:
            # 백스페이스 부족 점수 (사람은 백스페이스 자주 사용)
            if keyboard_analysis["backspace_ratio"] < 0.05:
                score += 10

            # 빠른 타이핑 점수
            if keyboard_analysis["fast_typing_ratio"] > 0.6:
                score += 10

        # 클릭스트림 분석 점수 (가중치: 25%)
        if clickstream_analysis["is_bot_like"]:
            score += 25
        else:
            # 짧은 체류 시간 점수
            if clickstream_analysis["short_duration_ratio"] > 0.5:
                score += 15

            # 체류 시간 변동 부족 점수
            if clickstream_analysis["duration_stddev"] < 1000:
                score += 10

        # 0-100 범위로 제한
        return min(100, max(0, int(score)))

    def _extract_risk_factors(
        self,
        bot_score: int,
        mouse_analysis: Dict[str, Any],
        keyboard_analysis: Dict[str, Any],
        clickstream_analysis: Dict[str, Any],
    ) -> List[str]:
        """
        위험 요인 추출

        Args:
            bot_score: 봇 점수
            mouse_analysis: 마우스 분석 결과
            keyboard_analysis: 키보드 분석 결과
            clickstream_analysis: 클릭스트림 분석 결과

        Returns:
            위험 요인 리스트
        """
        risk_factors = []

        if bot_score < 30:
            risk_factors.append("정상 사용자 패턴")
            return risk_factors

        # 마우스 관련 위험 요인
        if mouse_analysis["is_bot_like"]:
            risk_factors.append("봇과 유사한 마우스 패턴 감지")

        if mouse_analysis["low_curvature_ratio"] > 0.7:
            risk_factors.append(
                f"직선 움직임 비율 높음 ({mouse_analysis['low_curvature_ratio']:.0%})"
            )

        if mouse_analysis["avg_curvature"] < self.MOUSE_LOW_CURVATURE_THRESHOLD:
            risk_factors.append(f"평균 곡률 낮음 ({mouse_analysis['avg_curvature']:.4f})")

        if mouse_analysis["total_movements"] < 50:
            risk_factors.append(f"마우스 움직임 부족 ({mouse_analysis['total_movements']}회)")

        # 키보드 관련 위험 요인
        if keyboard_analysis["is_bot_like"]:
            risk_factors.append("봇과 유사한 타이핑 패턴 감지")

        if keyboard_analysis["backspace_ratio"] < 0.05:
            risk_factors.append(
                f"백스페이스 사용 거의 없음 ({keyboard_analysis['backspace_ratio']:.0%})"
            )

        if keyboard_analysis["fast_typing_ratio"] > 0.8:
            risk_factors.append(
                f"비정상 빠른 타이핑 ({keyboard_analysis['fast_typing_ratio']:.0%})"
            )

        # 클릭스트림 관련 위험 요인
        if clickstream_analysis["is_bot_like"]:
            risk_factors.append("봇과 유사한 페이지 탐색 패턴 감지")

        if clickstream_analysis["short_duration_ratio"] > 0.7:
            risk_factors.append(
                f"짧은 페이지 체류 시간 ({clickstream_analysis['short_duration_ratio']:.0%})"
            )

        if clickstream_analysis["avg_page_duration"] < 1000:
            risk_factors.append(
                f"평균 페이지 체류 시간 < 1초 ({clickstream_analysis['avg_page_duration']:.0f}ms)"
            )

        return risk_factors
