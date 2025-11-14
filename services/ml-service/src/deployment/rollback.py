"""
모델 롤백 (Rollback) 로직

기능:
- 프로덕션 모델을 이전 버전으로 롤백
- 롤백 히스토리 관리
- 긴급 롤백 (즉시 실행)
- 예약 롤백 (지정 시간에 실행)
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from src.models.ml_model import MLModel, DeploymentStatus


class RollbackHistory:
    """롤백 히스토리 (메모리 저장)"""

    def __init__(self):
        self.history: List[Dict[str, Any]] = []

    def add_rollback(
        self,
        from_model_id: UUID,
        to_model_id: UUID,
        reason: str,
        rollback_type: str,
        success: bool,
    ) -> None:
        """롤백 기록 추가"""
        self.history.append(
            {
                "from_model_id": str(from_model_id),
                "to_model_id": str(to_model_id),
                "reason": reason,
                "rollback_type": rollback_type,
                "success": success,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """롤백 히스토리 조회 (최신순)"""
        return self.history[-limit:][::-1]


class ModelRollback:
    """모델 롤백 관리자"""

    def __init__(self, db_session: AsyncSession):
        """
        Args:
            db_session: 데이터베이스 세션
        """
        self.db_session = db_session
        self.rollback_history = RollbackHistory()

    async def emergency_rollback(
        self,
        reason: str,
        model_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        긴급 롤백: 현재 프로덕션 모델을 가장 최근 은퇴된 모델로 즉시 롤백

        Args:
            reason: 롤백 사유
            model_type: 모델 타입 (선택, None이면 전체 롤백)

        Returns:
            Dict[str, Any]: 롤백 결과
        """
        # 현재 프로덕션 모델 조회
        current_production = await self._get_production_model(model_type)
        if not current_production:
            raise ValueError("프로덕션 모델이 없습니다")

        # 가장 최근 은퇴된 모델 조회 (이전 프로덕션 모델)
        previous_model = await self._get_previous_production_model(
            current_production.model_type
        )
        if not previous_model:
            raise ValueError("롤백할 이전 모델이 없습니다")

        # 롤백 실행
        try:
            # 현재 프로덕션 모델을 개발 상태로 변경
            current_production.deployment_status = DeploymentStatus.DEVELOPMENT
            current_production.deployed_at = None

            # 이전 모델을 프로덕션으로 복원
            previous_model.deployment_status = DeploymentStatus.PRODUCTION
            previous_model.deployed_at = datetime.utcnow()

            await self.db_session.commit()
            await self.db_session.refresh(current_production)
            await self.db_session.refresh(previous_model)

            # 롤백 히스토리 기록
            self.rollback_history.add_rollback(
                from_model_id=current_production.id,
                to_model_id=previous_model.id,
                reason=reason,
                rollback_type="emergency",
                success=True,
            )

            return {
                "message": "긴급 롤백 성공",
                "reason": reason,
                "rolled_back_from": {
                    "id": str(current_production.id),
                    "name": current_production.name,
                    "version": current_production.version,
                },
                "rolled_back_to": {
                    "id": str(previous_model.id),
                    "name": previous_model.name,
                    "version": previous_model.version,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            await self.db_session.rollback()

            # 롤백 실패 기록
            self.rollback_history.add_rollback(
                from_model_id=current_production.id,
                to_model_id=previous_model.id,
                reason=reason,
                rollback_type="emergency",
                success=False,
            )

            raise ValueError(f"롤백 실패: {str(e)}")

    async def rollback_to_specific_version(
        self,
        target_model_id: UUID,
        reason: str,
    ) -> Dict[str, Any]:
        """
        특정 버전으로 롤백

        Args:
            target_model_id: 롤백할 대상 모델 ID
            reason: 롤백 사유

        Returns:
            Dict[str, Any]: 롤백 결과
        """
        # 대상 모델 조회
        target_model = await self._get_model(target_model_id)
        if not target_model:
            raise ValueError(f"대상 모델을 찾을 수 없습니다: {target_model_id}")

        # 현재 프로덕션 모델 조회
        current_production = await self._get_production_model(target_model.model_type)
        if not current_production:
            raise ValueError("프로덕션 모델이 없습니다")

        if current_production.id == target_model_id:
            raise ValueError("이미 프로덕션 상태인 모델입니다")

        # 롤백 실행
        try:
            # 현재 프로덕션 모델을 은퇴 상태로 변경
            current_production.deployment_status = DeploymentStatus.RETIRED
            current_production.deployed_at = None

            # 대상 모델을 프로덕션으로 승격
            target_model.deployment_status = DeploymentStatus.PRODUCTION
            target_model.deployed_at = datetime.utcnow()

            await self.db_session.commit()
            await self.db_session.refresh(current_production)
            await self.db_session.refresh(target_model)

            # 롤백 히스토리 기록
            self.rollback_history.add_rollback(
                from_model_id=current_production.id,
                to_model_id=target_model.id,
                reason=reason,
                rollback_type="specific_version",
                success=True,
            )

            return {
                "message": "특정 버전으로 롤백 성공",
                "reason": reason,
                "rolled_back_from": {
                    "id": str(current_production.id),
                    "name": current_production.name,
                    "version": current_production.version,
                },
                "rolled_back_to": {
                    "id": str(target_model.id),
                    "name": target_model.name,
                    "version": target_model.version,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            await self.db_session.rollback()

            # 롤백 실패 기록
            self.rollback_history.add_rollback(
                from_model_id=current_production.id,
                to_model_id=target_model.id,
                reason=reason,
                rollback_type="specific_version",
                success=False,
            )

            raise ValueError(f"롤백 실패: {str(e)}")

    async def get_rollback_candidates(
        self,
        model_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        롤백 가능한 모델 목록 조회

        Args:
            model_type: 모델 타입 (선택)
            limit: 조회 개수 (기본값: 5)

        Returns:
            List[Dict[str, Any]]: 롤백 가능한 모델 목록
        """
        # 은퇴된 모델 조회 (최신순)
        query = (
            select(MLModel)
            .where(MLModel.deployment_status == DeploymentStatus.RETIRED)
            .order_by(desc(MLModel.deployed_at))
            .limit(limit)
        )

        if model_type:
            query = query.where(MLModel.model_type == model_type)

        result = await self.db_session.execute(query)
        retired_models = result.scalars().all()

        # 스테이징 모델도 포함
        query = (
            select(MLModel)
            .where(MLModel.deployment_status == DeploymentStatus.STAGING)
            .order_by(desc(MLModel.trained_at))
            .limit(limit)
        )

        if model_type:
            query = query.where(MLModel.model_type == model_type)

        result = await self.db_session.execute(query)
        staging_models = result.scalars().all()

        # 결과 병합
        candidates = []
        for model in retired_models + staging_models:
            candidates.append(
                {
                    "id": str(model.id),
                    "name": model.name,
                    "version": model.version,
                    "model_type": model.model_type,
                    "deployment_status": model.deployment_status.value,
                    "trained_at": model.trained_at.isoformat(),
                    "deployed_at": (
                        model.deployed_at.isoformat() if model.deployed_at else None
                    ),
                    "metrics": {
                        "accuracy": float(model.accuracy) if model.accuracy else None,
                        "precision": float(model.precision) if model.precision else None,
                        "recall": float(model.recall) if model.recall else None,
                        "f1_score": float(model.f1_score) if model.f1_score else None,
                    },
                }
            )

        # 최신순 정렬
        candidates.sort(
            key=lambda x: x["deployed_at"] or x["trained_at"], reverse=True
        )

        return candidates[:limit]

    async def validate_rollback(
        self,
        target_model_id: UUID,
    ) -> Dict[str, Any]:
        """
        롤백 가능 여부 검증

        Args:
            target_model_id: 롤백 대상 모델 ID

        Returns:
            Dict[str, Any]: 검증 결과
        """
        # 대상 모델 조회
        target_model = await self._get_model(target_model_id)
        if not target_model:
            return {
                "valid": False,
                "reason": "대상 모델을 찾을 수 없습니다",
            }

        # 현재 프로덕션 모델 조회
        current_production = await self._get_production_model(target_model.model_type)
        if not current_production:
            return {
                "valid": False,
                "reason": "프로덕션 모델이 없습니다",
            }

        if current_production.id == target_model_id:
            return {
                "valid": False,
                "reason": "이미 프로덕션 상태인 모델입니다",
            }

        # 배포 상태 확인
        if target_model.deployment_status not in [
            DeploymentStatus.RETIRED,
            DeploymentStatus.STAGING,
        ]:
            return {
                "valid": False,
                "reason": f"롤백 불가능한 상태입니다: {target_model.deployment_status.value}",
            }

        # 성능 지표 비교
        performance_comparison = {}
        if target_model.f1_score and current_production.f1_score:
            f1_diff = target_model.f1_score - current_production.f1_score
            performance_comparison["f1_score_diff"] = float(f1_diff)

            if f1_diff < -0.1:
                return {
                    "valid": True,
                    "warning": f"대상 모델의 F1 스코어가 {-f1_diff:.2%} 낮습니다. 롤백 시 성능 저하가 예상됩니다.",
                    "performance_comparison": performance_comparison,
                }

        return {
            "valid": True,
            "message": "롤백 가능합니다",
            "performance_comparison": performance_comparison,
        }

    def get_rollback_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        롤백 히스토리 조회

        Args:
            limit: 조회 개수 (기본값: 10)

        Returns:
            List[Dict[str, Any]]: 롤백 히스토리
        """
        return self.rollback_history.get_history(limit)

    async def _get_model(self, model_id: UUID) -> Optional[MLModel]:
        """모델 조회"""
        result = await self.db_session.execute(
            select(MLModel).where(MLModel.id == model_id)
        )
        return result.scalars().first()

    async def _get_production_model(
        self, model_type: Optional[str] = None
    ) -> Optional[MLModel]:
        """프로덕션 모델 조회"""
        query = select(MLModel).where(MLModel.deployment_status == DeploymentStatus.PRODUCTION)
        if model_type:
            query = query.where(MLModel.model_type == model_type)

        result = await self.db_session.execute(query)
        return result.scalars().first()

    async def _get_previous_production_model(
        self, model_type: str
    ) -> Optional[MLModel]:
        """가장 최근 은퇴된 모델 조회 (이전 프로덕션 모델)"""
        result = await self.db_session.execute(
            select(MLModel)
            .where(
                and_(
                    MLModel.model_type == model_type,
                    MLModel.deployment_status == DeploymentStatus.RETIRED,
                    MLModel.deployed_at.isnot(None),
                )
            )
            .order_by(desc(MLModel.deployed_at))
            .limit(1)
        )
        return result.scalars().first()
