"""
카나리 배포 (Canary Deployment) 로직

기능:
- 트래픽의 일부만 새로운 모델로 라우팅
- 점진적 트래픽 증가 (10% → 25% → 50% → 100%)
- 실시간 성능 모니터링 및 자동 롤백
- A/B 테스트와 통합 가능
"""

import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.models.ml_model import MLModel, DeploymentStatus


class CanaryDeployment:
    """카나리 배포 관리자"""

    def __init__(self, db_session: AsyncSession):
        """
        Args:
            db_session: 데이터베이스 세션
        """
        self.db_session = db_session
        # 카나리 배포 상태 (메모리 캐시)
        self._canary_config: Optional[Dict[str, Any]] = None

    async def start_canary_deployment(
        self,
        canary_model_id: UUID,
        initial_traffic_percentage: int = 10,
        success_threshold: float = 0.95,
        monitoring_window_minutes: int = 60,
    ) -> Dict[str, Any]:
        """
        카나리 배포 시작

        Args:
            canary_model_id: 새로운 모델 ID (카나리)
            initial_traffic_percentage: 초기 트래픽 비율 (기본값: 10%)
            success_threshold: 성공률 임계값 (기본값: 95%)
            monitoring_window_minutes: 모니터링 시간 (기본값: 60분)

        Returns:
            Dict[str, Any]: 카나리 배포 설정 정보
        """
        # 카나리 모델 조회
        canary_model = await self._get_model(canary_model_id)
        if canary_model.deployment_status != DeploymentStatus.STAGING:
            raise ValueError("카나리 모델은 STAGING 상태여야 합니다")

        # 현재 프로덕션 모델 조회
        production_model = await self._get_production_model(canary_model.model_type)
        if not production_model:
            raise ValueError("프로덕션 모델이 없습니다")

        # 카나리 배포 설정
        self._canary_config = {
            "canary_model_id": str(canary_model_id),
            "production_model_id": str(production_model.id),
            "traffic_percentage": initial_traffic_percentage,
            "success_threshold": success_threshold,
            "monitoring_window_minutes": monitoring_window_minutes,
            "start_time": datetime.utcnow().isoformat(),
            "status": "active",
            "canary_requests": 0,
            "canary_successes": 0,
            "production_requests": 0,
            "production_successes": 0,
        }

        return {
            "message": f"카나리 배포 시작: {initial_traffic_percentage}% 트래픽",
            "canary_model": {
                "id": str(canary_model.id),
                "name": canary_model.name,
                "version": canary_model.version,
            },
            "production_model": {
                "id": str(production_model.id),
                "name": production_model.name,
                "version": production_model.version,
            },
            "config": self._canary_config,
        }

    async def route_traffic(
        self, transaction_id: str
    ) -> Tuple[str, MLModel]:
        """
        트래픽을 카나리 또는 프로덕션 모델로 라우팅

        Args:
            transaction_id: 거래 ID (해시 기반 일관된 라우팅)

        Returns:
            Tuple[모델 타입 ("canary" 또는 "production"), MLModel 객체]
        """
        if not self._canary_config or self._canary_config["status"] != "active":
            # 카나리 배포가 없으면 프로덕션 모델 사용
            production_model = await self._get_production_model()
            return "production", production_model

        # 거래 ID 해시 기반 트래픽 분할 (일관된 라우팅)
        hash_value = int(hashlib.sha256(transaction_id.encode()).hexdigest(), 16)
        traffic_percentage = self._canary_config["traffic_percentage"]
        is_canary = (hash_value % 100) < traffic_percentage

        if is_canary:
            # 카나리 모델 사용
            canary_model = await self._get_model(UUID(self._canary_config["canary_model_id"]))
            return "canary", canary_model
        else:
            # 프로덕션 모델 사용
            production_model = await self._get_model(
                UUID(self._canary_config["production_model_id"])
            )
            return "production", production_model

    async def record_result(
        self,
        model_type: str,
        success: bool,
    ) -> None:
        """
        모델 평가 결과 기록

        Args:
            model_type: 모델 타입 ("canary" 또는 "production")
            success: 평가 성공 여부
        """
        if not self._canary_config:
            return

        if model_type == "canary":
            self._canary_config["canary_requests"] += 1
            if success:
                self._canary_config["canary_successes"] += 1
        elif model_type == "production":
            self._canary_config["production_requests"] += 1
            if success:
                self._canary_config["production_successes"] += 1

    async def get_canary_status(self) -> Dict[str, Any]:
        """
        카나리 배포 상태 조회

        Returns:
            Dict[str, Any]: 카나리 배포 상태 및 통계
        """
        if not self._canary_config:
            return {"status": "inactive", "message": "카나리 배포가 없습니다"}

        # 성공률 계산
        canary_success_rate = (
            self._canary_config["canary_successes"] / self._canary_config["canary_requests"]
            if self._canary_config["canary_requests"] > 0
            else 0.0
        )
        production_success_rate = (
            self._canary_config["production_successes"]
            / self._canary_config["production_requests"]
            if self._canary_config["production_requests"] > 0
            else 0.0
        )

        # 모니터링 시간 경과 확인
        start_time = datetime.fromisoformat(self._canary_config["start_time"])
        elapsed_minutes = (datetime.utcnow() - start_time).total_seconds() / 60

        return {
            "status": self._canary_config["status"],
            "traffic_percentage": self._canary_config["traffic_percentage"],
            "elapsed_minutes": round(elapsed_minutes, 2),
            "monitoring_window_minutes": self._canary_config["monitoring_window_minutes"],
            "canary": {
                "requests": self._canary_config["canary_requests"],
                "successes": self._canary_config["canary_successes"],
                "success_rate": round(canary_success_rate, 4),
            },
            "production": {
                "requests": self._canary_config["production_requests"],
                "successes": self._canary_config["production_successes"],
                "success_rate": round(production_success_rate, 4),
            },
            "recommendation": self._generate_recommendation(
                canary_success_rate,
                production_success_rate,
                elapsed_minutes,
            ),
        }

    async def increase_traffic(
        self, new_percentage: int
    ) -> Dict[str, Any]:
        """
        카나리 트래픽 비율 증가

        Args:
            new_percentage: 새로운 트래픽 비율 (0-100)

        Returns:
            Dict[str, Any]: 업데이트된 카나리 상태
        """
        if not self._canary_config:
            raise ValueError("카나리 배포가 활성화되어 있지 않습니다")

        if new_percentage < 0 or new_percentage > 100:
            raise ValueError("트래픽 비율은 0-100 사이여야 합니다")

        old_percentage = self._canary_config["traffic_percentage"]
        self._canary_config["traffic_percentage"] = new_percentage

        # 통계 초기화 (새로운 비율로 모니터링 재시작)
        self._canary_config["canary_requests"] = 0
        self._canary_config["canary_successes"] = 0
        self._canary_config["production_requests"] = 0
        self._canary_config["production_successes"] = 0
        self._canary_config["start_time"] = datetime.utcnow().isoformat()

        return {
            "message": f"트래픽 비율 증가: {old_percentage}% → {new_percentage}%",
            "config": self._canary_config,
        }

    async def complete_canary_deployment(self) -> Dict[str, Any]:
        """
        카나리 배포 완료 (카나리 모델을 프로덕션으로 승격)

        Returns:
            Dict[str, Any]: 완료 결과
        """
        if not self._canary_config:
            raise ValueError("카나리 배포가 활성화되어 있지 않습니다")

        canary_model_id = UUID(self._canary_config["canary_model_id"])
        production_model_id = UUID(self._canary_config["production_model_id"])

        # 기존 프로덕션 모델을 은퇴 상태로 변경
        await self.db_session.execute(
            select(MLModel)
            .where(MLModel.id == production_model_id)
            .with_for_update()
        )
        production_model = await self._get_model(production_model_id)
        production_model.deployment_status = DeploymentStatus.RETIRED

        # 카나리 모델을 프로덕션으로 승격
        canary_model = await self._get_model(canary_model_id)
        canary_model.deployment_status = DeploymentStatus.PRODUCTION
        canary_model.deployed_at = datetime.utcnow()

        await self.db_session.commit()

        # 카나리 설정 초기화
        completed_config = self._canary_config.copy()
        self._canary_config = None

        return {
            "message": "카나리 배포 완료: 새 모델이 프로덕션으로 승격되었습니다",
            "new_production_model": {
                "id": str(canary_model.id),
                "name": canary_model.name,
                "version": canary_model.version,
            },
            "retired_model": {
                "id": str(production_model.id),
                "name": production_model.name,
                "version": production_model.version,
            },
            "final_stats": completed_config,
        }

    async def abort_canary_deployment(self, reason: str) -> Dict[str, Any]:
        """
        카나리 배포 중단 (롤백)

        Args:
            reason: 중단 사유

        Returns:
            Dict[str, Any]: 중단 결과
        """
        if not self._canary_config:
            raise ValueError("카나리 배포가 활성화되어 있지 않습니다")

        # 카나리 설정 저장 후 초기화
        aborted_config = self._canary_config.copy()
        aborted_config["status"] = "aborted"
        aborted_config["abort_reason"] = reason
        aborted_config["abort_time"] = datetime.utcnow().isoformat()

        self._canary_config = None

        return {
            "message": f"카나리 배포 중단: {reason}",
            "final_stats": aborted_config,
        }

    def _generate_recommendation(
        self,
        canary_success_rate: float,
        production_success_rate: float,
        elapsed_minutes: float,
    ) -> str:
        """
        카나리 배포 권장 사항 생성

        Args:
            canary_success_rate: 카나리 성공률
            production_success_rate: 프로덕션 성공률
            elapsed_minutes: 경과 시간 (분)

        Returns:
            str: 권장 사항 메시지
        """
        if not self._canary_config:
            return "카나리 배포가 없습니다"

        monitoring_window = self._canary_config["monitoring_window_minutes"]
        success_threshold = self._canary_config["success_threshold"]
        current_percentage = self._canary_config["traffic_percentage"]

        # 최소 요청 수 확인 (통계적 신뢰도)
        min_requests = 100
        if self._canary_config["canary_requests"] < min_requests:
            return f"통계적 신뢰도를 위해 최소 {min_requests}개의 요청이 필요합니다 (현재: {self._canary_config['canary_requests']}개)"

        # 성공률 비교
        if canary_success_rate < success_threshold:
            return f"카나리 성공률({canary_success_rate:.2%})이 임계값({success_threshold:.2%})보다 낮습니다. 배포 중단을 권장합니다."

        if canary_success_rate < production_success_rate - 0.05:
            return f"카나리 성공률({canary_success_rate:.2%})이 프로덕션({production_success_rate:.2%})보다 낮습니다. 배포 중단을 권장합니다."

        # 모니터링 시간 확인
        if elapsed_minutes < monitoring_window:
            remaining = monitoring_window - elapsed_minutes
            return f"모니터링 시간 부족: {remaining:.0f}분 후 다음 단계 진행 가능"

        # 트래픽 증가 권장
        if current_percentage < 25:
            return "카나리 성능 양호. 트래픽을 25%로 증가시키는 것을 권장합니다."
        elif current_percentage < 50:
            return "카나리 성능 양호. 트래픽을 50%로 증가시키는 것을 권장합니다."
        elif current_percentage < 100:
            return "카나리 성능 양호. 트래픽을 100%로 증가시키고 프로덕션 승격을 권장합니다."
        else:
            return "카나리 배포 완료 가능. 프로덕션으로 승격하세요."

    async def _get_model(self, model_id: UUID) -> MLModel:
        """모델 조회"""
        result = await self.db_session.execute(
            select(MLModel).where(MLModel.id == model_id)
        )
        model = result.scalars().first()
        if not model:
            raise ValueError(f"모델을 찾을 수 없습니다: {model_id}")
        return model

    async def _get_production_model(
        self, model_type: Optional[str] = None
    ) -> Optional[MLModel]:
        """프로덕션 모델 조회"""
        query = select(MLModel).where(MLModel.deployment_status == DeploymentStatus.PRODUCTION)
        if model_type:
            query = query.where(MLModel.model_type == model_type)

        result = await self.db_session.execute(query)
        return result.scalars().first()
