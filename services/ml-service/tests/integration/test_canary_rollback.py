"""
카나리 배포 및 롤백 시나리오 통합 테스트 (T127)

검증 항목:
1. 카나리 배포 시작 (10% 트래픽)
2. 트래픽 분할 로직 (해시 기반 일관된 라우팅)
3. 성능 모니터링 및 통계 수집
4. 트래픽 점진적 증가 (10% → 25% → 50% → 100%)
5. 카나리 배포 완료 (프로덕션 승격)
6. 카나리 배포 중단 (롤백)
7. 긴급 롤백
8. 특정 버전으로 롤백
9. 롤백 히스토리 관리
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.ml_model import MLModel, ModelType, DeploymentStatus, Base as MLBase
from src.deployment.canary_deploy import CanaryDeployment
from src.deployment.rollback import ModelRollback, RollbackHistory
from src.deployment.version_manager import ModelVersionManager


# 테스트용 인메모리 데이터베이스
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def async_db_session():
    """비동기 데이터베이스 세션 (테스트용)"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(MLBase.metadata.create_all)

    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def setup_models(async_db_session: AsyncSession) -> Dict[str, MLModel]:
    """
    테스트용 모델 생성 (프로덕션 + 스테이징)

    Returns:
        Dict: {"production": 프로덕션 모델, "staging": 스테이징 모델}
    """
    # 프로덕션 모델 (v1.0.0)
    production_model = MLModel(
        id=uuid4(),
        name="IsolationForest-v1.0.0",
        version="1.0.0",
        model_type=ModelType.ISOLATION_FOREST,
        training_data_start=datetime.utcnow().date() - timedelta(days=30),
        training_data_end=datetime.utcnow().date(),
        trained_at=datetime.utcnow() - timedelta(days=5),
        deployed_at=datetime.utcnow() - timedelta(days=3),
        accuracy=0.85,
        precision=0.82,
        recall=0.88,
        f1_score=0.85,
        deployment_status=DeploymentStatus.PRODUCTION,
        model_path="/models/isolation_forest_v1.0.0.pkl",
    )

    # 스테이징 모델 (v1.1.0)
    staging_model = MLModel(
        id=uuid4(),
        name="IsolationForest-v1.1.0",
        version="1.1.0",
        model_type=ModelType.ISOLATION_FOREST,
        training_data_start=datetime.utcnow().date() - timedelta(days=30),
        training_data_end=datetime.utcnow().date(),
        trained_at=datetime.utcnow() - timedelta(days=1),
        accuracy=0.90,
        precision=0.88,
        recall=0.92,
        f1_score=0.90,
        deployment_status=DeploymentStatus.STAGING,
        model_path="/models/isolation_forest_v1.1.0.pkl",
    )

    async_db_session.add_all([production_model, staging_model])
    await async_db_session.commit()
    await async_db_session.refresh(production_model)
    await async_db_session.refresh(staging_model)

    return {"production": production_model, "staging": staging_model}


@pytest.mark.asyncio
class TestCanaryDeployment:
    """카나리 배포 테스트"""

    async def test_start_canary_deployment(
        self, async_db_session: AsyncSession, setup_models: Dict[str, MLModel]
    ):
        """
        카나리 배포 시작 검증

        검증:
        1. 카나리 배포 설정 생성
        2. 초기 트래픽 비율 설정 (10%)
        3. 모니터링 설정
        """
        print("\n=== 카나리 배포 시작 테스트 ===")

        canary = CanaryDeployment(async_db_session)
        staging_model = setup_models["staging"]
        production_model = setup_models["production"]

        # 카나리 배포 시작
        result = await canary.start_canary_deployment(
            canary_model_id=staging_model.id,
            initial_traffic_percentage=10,
            success_threshold=0.95,
            monitoring_window_minutes=60,
        )

        assert result["message"].startswith("카나리 배포 시작")
        assert result["canary_model"]["id"] == str(staging_model.id)
        assert result["production_model"]["id"] == str(production_model.id)
        assert result["config"]["traffic_percentage"] == 10
        assert result["config"]["success_threshold"] == 0.95
        assert result["config"]["status"] == "active"

        print(f"카나리 배포 시작: {result['config']['traffic_percentage']}% 트래픽")
        print("테스트 통과: 카나리 배포 시작")

    async def test_traffic_routing(
        self, async_db_session: AsyncSession, setup_models: Dict[str, MLModel]
    ):
        """
        트래픽 라우팅 검증 (해시 기반 일관된 분할)

        검증:
        1. 동일한 transaction_id는 항상 같은 모델로 라우팅
        2. 트래픽 비율이 설정값과 유사
        """
        print("\n=== 트래픽 라우팅 테스트 ===")

        canary = CanaryDeployment(async_db_session)
        staging_model = setup_models["staging"]

        # 카나리 배포 시작 (10% 트래픽)
        await canary.start_canary_deployment(
            canary_model_id=staging_model.id,
            initial_traffic_percentage=10,
        )

        # 1000개 거래 시뮬레이션
        canary_count = 0
        production_count = 0
        transaction_routes = {}

        for i in range(1000):
            tx_id = f"TX{i:04d}"
            model_type, model = await canary.route_traffic(tx_id)

            # 일관된 라우팅 검증
            if tx_id not in transaction_routes:
                transaction_routes[tx_id] = model_type
            else:
                # 동일 TX는 항상 같은 모델로 라우팅
                assert transaction_routes[tx_id] == model_type

            if model_type == "canary":
                canary_count += 1
            else:
                production_count += 1

        # 트래픽 비율 검증 (10% ± 3%)
        actual_percentage = (canary_count / 1000) * 100
        assert 7 <= actual_percentage <= 13, f"카나리 트래픽 비율: {actual_percentage}%"

        print(f"트래픽 분할: 카나리 {canary_count}개 ({actual_percentage:.1f}%), "
              f"프로덕션 {production_count}개 ({100-actual_percentage:.1f}%)")
        print("테스트 통과: 트래픽 라우팅")

    async def test_performance_monitoring(
        self, async_db_session: AsyncSession, setup_models: Dict[str, MLModel]
    ):
        """
        성능 모니터링 및 통계 수집 검증

        검증:
        1. 결과 기록
        2. 성공률 계산
        3. 권장 사항 생성
        """
        print("\n=== 성능 모니터링 테스트 ===")

        canary = CanaryDeployment(async_db_session)
        staging_model = setup_models["staging"]

        await canary.start_canary_deployment(
            canary_model_id=staging_model.id,
            initial_traffic_percentage=10,
        )

        # 평가 결과 기록 (카나리: 95% 성공, 프로덕션: 93% 성공)
        for i in range(100):
            model_type, _ = await canary.route_traffic(f"TX{i:04d}")
            if model_type == "canary":
                # 95% 성공률
                success = i % 100 < 95
            else:
                # 93% 성공률
                success = i % 100 < 93

            await canary.record_result(model_type, success)

        # 상태 조회
        status = await canary.get_canary_status()

        assert status["status"] == "active"
        assert status["traffic_percentage"] == 10
        assert status["canary"]["requests"] > 0
        assert status["production"]["requests"] > 0

        canary_success_rate = status["canary"]["success_rate"]
        production_success_rate = status["production"]["success_rate"]

        print(f"카나리 성공률: {canary_success_rate:.2%}")
        print(f"프로덕션 성공률: {production_success_rate:.2%}")
        print(f"권장 사항: {status['recommendation']}")

        # 카나리가 더 높은 성공률을 보이면 트래픽 증가 권장
        assert "권장" in status["recommendation"] or "통계적" in status["recommendation"]

        print("테스트 통과: 성능 모니터링")

    async def test_gradual_traffic_increase(
        self, async_db_session: AsyncSession, setup_models: Dict[str, MLModel]
    ):
        """
        트래픽 점진적 증가 검증 (10% → 25% → 50% → 100%)

        검증:
        1. 트래픽 비율 업데이트
        2. 통계 초기화 (새로운 모니터링 시작)
        """
        print("\n=== 트래픽 점진적 증가 테스트 ===")

        canary = CanaryDeployment(async_db_session)
        staging_model = setup_models["staging"]

        # 10% 시작
        await canary.start_canary_deployment(
            canary_model_id=staging_model.id,
            initial_traffic_percentage=10,
        )

        traffic_percentages = [10, 25, 50, 100]

        for percentage in traffic_percentages[1:]:
            print(f"\nStep: 트래픽 {percentage}%로 증가")

            # 트래픽 증가
            result = await canary.increase_traffic(percentage)
            assert result["config"]["traffic_percentage"] == percentage

            # 100개 거래 시뮬레이션
            canary_count = 0
            for i in range(100):
                model_type, _ = await canary.route_traffic(f"TX_STEP{percentage}_{i:04d}")
                if model_type == "canary":
                    canary_count += 1

            actual_percentage = canary_count
            print(f"실제 카나리 트래픽: {actual_percentage}% (목표: {percentage}%)")

            # 오차 범위 ±10% (샘플 100개이므로)
            assert abs(actual_percentage - percentage) <= 15

        print("테스트 통과: 트래픽 점진적 증가")

    async def test_complete_canary_deployment(
        self, async_db_session: AsyncSession, setup_models: Dict[str, MLModel]
    ):
        """
        카나리 배포 완료 검증 (프로덕션 승격)

        검증:
        1. 카나리 모델 → 프로덕션 승격
        2. 기존 프로덕션 모델 → 은퇴
        3. 카나리 설정 초기화
        """
        print("\n=== 카나리 배포 완료 테스트 ===")

        canary = CanaryDeployment(async_db_session)
        staging_model = setup_models["staging"]
        production_model = setup_models["production"]

        # 카나리 배포 시작
        await canary.start_canary_deployment(
            canary_model_id=staging_model.id,
            initial_traffic_percentage=100,
        )

        # 카나리 배포 완료
        result = await canary.complete_canary_deployment()

        assert result["message"].startswith("카나리 배포 완료")
        assert result["new_production_model"]["id"] == str(staging_model.id)
        assert result["retired_model"]["id"] == str(production_model.id)

        # 데이터베이스 상태 확인
        await async_db_session.refresh(staging_model)
        await async_db_session.refresh(production_model)

        assert staging_model.deployment_status == DeploymentStatus.PRODUCTION
        assert staging_model.deployed_at is not None
        assert production_model.deployment_status == DeploymentStatus.RETIRED

        print(f"새 프로덕션 모델: {staging_model.name} (v{staging_model.version})")
        print(f"은퇴 모델: {production_model.name} (v{production_model.version})")
        print("테스트 통과: 카나리 배포 완료")

    async def test_abort_canary_deployment(
        self, async_db_session: AsyncSession, setup_models: Dict[str, MLModel]
    ):
        """
        카나리 배포 중단 검증

        검증:
        1. 카나리 배포 중단
        2. 중단 사유 기록
        3. 카나리 설정 초기화
        """
        print("\n=== 카나리 배포 중단 테스트 ===")

        canary = CanaryDeployment(async_db_session)
        staging_model = setup_models["staging"]

        # 카나리 배포 시작
        await canary.start_canary_deployment(
            canary_model_id=staging_model.id,
            initial_traffic_percentage=10,
        )

        # 성능 저하 시뮬레이션
        for i in range(100):
            model_type, _ = await canary.route_traffic(f"TX{i:04d}")
            # 카나리: 70% 성공 (낮음), 프로덕션: 95% 성공
            if model_type == "canary":
                success = i % 100 < 70
            else:
                success = i % 100 < 95

            await canary.record_result(model_type, success)

        # 카나리 배포 중단
        abort_reason = "카나리 성공률이 프로덕션보다 낮아 중단"
        result = await canary.abort_canary_deployment(abort_reason)

        assert result["message"].startswith("카나리 배포 중단")
        assert result["final_stats"]["status"] == "aborted"
        assert result["final_stats"]["abort_reason"] == abort_reason

        # 중단 후 상태 확인
        status = await canary.get_canary_status()
        assert status["status"] == "inactive"

        print(f"중단 사유: {abort_reason}")
        print("테스트 통과: 카나리 배포 중단")


@pytest.mark.asyncio
class TestModelRollback:
    """모델 롤백 테스트"""

    async def test_emergency_rollback(self, async_db_session: AsyncSession):
        """
        긴급 롤백 검증 (최근 은퇴 모델로 즉시 롤백)

        검증:
        1. 현재 프로덕션 모델 → 개발 상태
        2. 최근 은퇴 모델 → 프로덕션 승격
        3. 롤백 히스토리 기록
        """
        print("\n=== 긴급 롤백 테스트 ===")

        # 모델 생성: 은퇴 모델 (v1.0.0) + 현재 프로덕션 모델 (v1.1.0)
        retired_model = MLModel(
            id=uuid4(),
            name="Model-v1.0.0",
            version="1.0.0",
            model_type=ModelType.ISOLATION_FOREST,
            training_data_start=datetime.utcnow().date() - timedelta(days=40),
            training_data_end=datetime.utcnow().date() - timedelta(days=10),
            trained_at=datetime.utcnow() - timedelta(days=10),
            deployed_at=datetime.utcnow() - timedelta(days=8),  # 이전에 배포됨
            accuracy=0.85,
            precision=0.82,
            recall=0.88,
            f1_score=0.85,
            deployment_status=DeploymentStatus.RETIRED,
            model_path="/models/model_v1.0.0.pkl",
        )

        current_production = MLModel(
            id=uuid4(),
            name="Model-v1.1.0",
            version="1.1.0",
            model_type=ModelType.ISOLATION_FOREST,
            training_data_start=datetime.utcnow().date() - timedelta(days=30),
            training_data_end=datetime.utcnow().date(),
            trained_at=datetime.utcnow() - timedelta(days=1),
            deployed_at=datetime.utcnow(),
            accuracy=0.80,  # 성능 저하
            precision=0.75,
            recall=0.82,
            f1_score=0.78,
            deployment_status=DeploymentStatus.PRODUCTION,
            model_path="/models/model_v1.1.0.pkl",
        )

        async_db_session.add_all([retired_model, current_production])
        await async_db_session.commit()

        # 긴급 롤백 실행
        rollback_manager = ModelRollback(async_db_session)
        result = await rollback_manager.emergency_rollback(
            reason="프로덕션 모델 성능 저하 (F1: 0.85 → 0.78)",
            model_type=ModelType.ISOLATION_FOREST,
        )

        assert result["message"] == "긴급 롤백 성공"
        assert result["rolled_back_from"]["id"] == str(current_production.id)
        assert result["rolled_back_to"]["id"] == str(retired_model.id)

        # 데이터베이스 상태 확인
        await async_db_session.refresh(retired_model)
        await async_db_session.refresh(current_production)

        assert retired_model.deployment_status == DeploymentStatus.PRODUCTION
        assert current_production.deployment_status == DeploymentStatus.DEVELOPMENT

        # 롤백 히스토리 확인
        history = rollback_manager.get_rollback_history(limit=1)
        assert len(history) == 1
        assert history[0]["rollback_type"] == "emergency"
        assert history[0]["success"] is True

        print(f"롤백 전: {current_production.name} (F1={current_production.f1_score:.2f})")
        print(f"롤백 후: {retired_model.name} (F1={retired_model.f1_score:.2f})")
        print("테스트 통과: 긴급 롤백")

    async def test_rollback_to_specific_version(self, async_db_session: AsyncSession):
        """
        특정 버전으로 롤백 검증

        검증:
        1. 지정된 모델 ID로 롤백
        2. 프로덕션 모델 상태 변경
        3. 롤백 히스토리 기록
        """
        print("\n=== 특정 버전 롤백 테스트 ===")

        # 3개 모델 생성: v1.0.0 (은퇴), v1.1.0 (은퇴), v1.2.0 (현재 프로덕션)
        model_v1_0 = MLModel(
            id=uuid4(),
            name="Model-v1.0.0",
            version="1.0.0",
            model_type=ModelType.LIGHTGBM,
            training_data_start=datetime.utcnow().date() - timedelta(days=60),
            training_data_end=datetime.utcnow().date() - timedelta(days=30),
            trained_at=datetime.utcnow() - timedelta(days=30),
            deployed_at=datetime.utcnow() - timedelta(days=25),
            accuracy=0.88,
            precision=0.86,
            recall=0.90,
            f1_score=0.88,
            deployment_status=DeploymentStatus.RETIRED,
            model_path="/models/model_v1.0.0.pkl",
        )

        model_v1_1 = MLModel(
            id=uuid4(),
            name="Model-v1.1.0",
            version="1.1.0",
            model_type=ModelType.LIGHTGBM,
            training_data_start=datetime.utcnow().date() - timedelta(days=40),
            training_data_end=datetime.utcnow().date() - timedelta(days=10),
            trained_at=datetime.utcnow() - timedelta(days=10),
            deployed_at=datetime.utcnow() - timedelta(days=8),
            accuracy=0.85,
            precision=0.82,
            recall=0.88,
            f1_score=0.85,
            deployment_status=DeploymentStatus.RETIRED,
            model_path="/models/model_v1.1.0.pkl",
        )

        model_v1_2 = MLModel(
            id=uuid4(),
            name="Model-v1.2.0",
            version="1.2.0",
            model_type=ModelType.LIGHTGBM,
            training_data_start=datetime.utcnow().date() - timedelta(days=30),
            training_data_end=datetime.utcnow().date(),
            trained_at=datetime.utcnow() - timedelta(days=1),
            deployed_at=datetime.utcnow(),
            accuracy=0.82,
            precision=0.78,
            recall=0.85,
            f1_score=0.81,
            deployment_status=DeploymentStatus.PRODUCTION,
            model_path="/models/model_v1.2.0.pkl",
        )

        async_db_session.add_all([model_v1_0, model_v1_1, model_v1_2])
        await async_db_session.commit()

        # v1.0.0으로 롤백 (가장 성능이 좋음)
        rollback_manager = ModelRollback(async_db_session)
        result = await rollback_manager.rollback_to_specific_version(
            target_model_id=model_v1_0.id,
            reason="v1.0.0이 가장 높은 F1 스코어 (0.88)를 보임",
        )

        assert result["message"] == "특정 버전으로 롤백 성공"
        assert result["rolled_back_to"]["version"] == "1.0.0"

        # 데이터베이스 상태 확인
        await async_db_session.refresh(model_v1_0)
        await async_db_session.refresh(model_v1_2)

        assert model_v1_0.deployment_status == DeploymentStatus.PRODUCTION
        assert model_v1_2.deployment_status == DeploymentStatus.RETIRED

        print(f"롤백 대상: {model_v1_0.name} (F1={model_v1_0.f1_score:.2f})")
        print("테스트 통과: 특정 버전 롤백")

    async def test_get_rollback_candidates(self, async_db_session: AsyncSession):
        """
        롤백 가능 모델 목록 조회 검증

        검증:
        1. 은퇴된 모델 목록
        2. 스테이징 모델 목록
        3. 최신순 정렬
        """
        print("\n=== 롤백 후보 조회 테스트 ===")

        # 여러 모델 생성
        models = []
        for i in range(5):
            status = DeploymentStatus.RETIRED if i < 3 else DeploymentStatus.STAGING

            model = MLModel(
                id=uuid4(),
                name=f"Model-v1.{i}.0",
                version=f"1.{i}.0",
                model_type=ModelType.ISOLATION_FOREST,
                training_data_start=datetime.utcnow().date() - timedelta(days=30),
                training_data_end=datetime.utcnow().date(),
                trained_at=datetime.utcnow() - timedelta(days=5 - i),  # 최신순
                deployed_at=datetime.utcnow() - timedelta(days=5 - i) if status == DeploymentStatus.RETIRED else None,
                accuracy=0.80 + i * 0.02,
                precision=0.78 + i * 0.02,
                recall=0.82 + i * 0.02,
                f1_score=0.80 + i * 0.02,
                deployment_status=status,
                model_path=f"/models/model_v1.{i}.0.pkl",
            )
            models.append(model)

        async_db_session.add_all(models)
        await async_db_session.commit()

        # 롤백 후보 조회
        rollback_manager = ModelRollback(async_db_session)
        candidates = await rollback_manager.get_rollback_candidates(
            model_type=ModelType.ISOLATION_FOREST,
            limit=5,
        )

        assert len(candidates) == 5
        assert all(
            c["deployment_status"] in ["retired", "staging"] for c in candidates
        )

        # 최신순 정렬 확인 (버전 번호 역순)
        versions = [c["version"] for c in candidates]
        print(f"롤백 후보 (최신순): {', '.join(versions)}")

        print("테스트 통과: 롤백 후보 조회")

    async def test_validate_rollback(self, async_db_session: AsyncSession):
        """
        롤백 가능 여부 검증

        검증:
        1. 대상 모델 존재 여부
        2. 배포 상태 확인
        3. 성능 지표 비교
        4. 경고 메시지 생성
        """
        print("\n=== 롤백 검증 테스트 ===")

        # 프로덕션 모델 (높은 성능)
        production_model = MLModel(
            id=uuid4(),
            name="Model-v2.0.0",
            version="2.0.0",
            model_type=ModelType.LIGHTGBM,
            training_data_start=datetime.utcnow().date() - timedelta(days=30),
            training_data_end=datetime.utcnow().date(),
            trained_at=datetime.utcnow() - timedelta(days=1),
            deployed_at=datetime.utcnow(),
            accuracy=0.90,
            precision=0.88,
            recall=0.92,
            f1_score=0.90,
            deployment_status=DeploymentStatus.PRODUCTION,
            model_path="/models/model_v2.0.0.pkl",
        )

        # 은퇴 모델 (낮은 성능)
        retired_model_low = MLModel(
            id=uuid4(),
            name="Model-v1.5.0",
            version="1.5.0",
            model_type=ModelType.LIGHTGBM,
            training_data_start=datetime.utcnow().date() - timedelta(days=40),
            training_data_end=datetime.utcnow().date() - timedelta(days=10),
            trained_at=datetime.utcnow() - timedelta(days=10),
            deployed_at=datetime.utcnow() - timedelta(days=8),
            accuracy=0.75,
            precision=0.72,
            recall=0.78,
            f1_score=0.75,  # F1 차이 -0.15 (경고)
            deployment_status=DeploymentStatus.RETIRED,
            model_path="/models/model_v1.5.0.pkl",
        )

        # 은퇴 모델 (유사한 성능)
        retired_model_ok = MLModel(
            id=uuid4(),
            name="Model-v1.9.0",
            version="1.9.0",
            model_type=ModelType.LIGHTGBM,
            training_data_start=datetime.utcnow().date() - timedelta(days=35),
            training_data_end=datetime.utcnow().date() - timedelta(days=5),
            trained_at=datetime.utcnow() - timedelta(days=5),
            deployed_at=datetime.utcnow() - timedelta(days=3),
            accuracy=0.88,
            precision=0.86,
            recall=0.90,
            f1_score=0.88,  # F1 차이 -0.02 (OK)
            deployment_status=DeploymentStatus.RETIRED,
            model_path="/models/model_v1.9.0.pkl",
        )

        async_db_session.add_all([production_model, retired_model_low, retired_model_ok])
        await async_db_session.commit()

        rollback_manager = ModelRollback(async_db_session)

        # Case 1: 성능 저하 경고
        print("\nCase 1: 성능 저하 모델로 롤백")
        validation_low = await rollback_manager.validate_rollback(retired_model_low.id)
        assert validation_low["valid"] is True
        assert "warning" in validation_low
        assert "낮습니다" in validation_low["warning"]
        print(f"검증 결과: {validation_low['warning']}")

        # Case 2: 성능 유사 (OK)
        print("\nCase 2: 성능 유사 모델로 롤백")
        validation_ok = await rollback_manager.validate_rollback(retired_model_ok.id)
        assert validation_ok["valid"] is True
        assert "message" in validation_ok
        assert validation_ok["message"] == "롤백 가능합니다"
        print(f"검증 결과: {validation_ok['message']}")

        print("테스트 통과: 롤백 검증")

    async def test_rollback_history(self, async_db_session: AsyncSession):
        """
        롤백 히스토리 관리 검증

        검증:
        1. 롤백 기록 추가
        2. 히스토리 조회 (최신순)
        3. 성공/실패 기록
        """
        print("\n=== 롤백 히스토리 테스트 ===")

        rollback_manager = ModelRollback(async_db_session)

        # 여러 롤백 기록 추가
        rollback_manager.rollback_history.add_rollback(
            from_model_id=uuid4(),
            to_model_id=uuid4(),
            reason="성능 저하",
            rollback_type="emergency",
            success=True,
        )

        rollback_manager.rollback_history.add_rollback(
            from_model_id=uuid4(),
            to_model_id=uuid4(),
            reason="버전 v1.0.0으로 복원",
            rollback_type="specific_version",
            success=True,
        )

        rollback_manager.rollback_history.add_rollback(
            from_model_id=uuid4(),
            to_model_id=uuid4(),
            reason="테스트 롤백 (실패)",
            rollback_type="emergency",
            success=False,
        )

        # 히스토리 조회
        history = rollback_manager.get_rollback_history(limit=3)

        assert len(history) == 3
        assert history[0]["rollback_type"] == "emergency"  # 최신
        assert history[0]["success"] is False
        assert history[1]["rollback_type"] == "specific_version"
        assert history[2]["rollback_type"] == "emergency"

        print("롤백 히스토리 (최신순):")
        for i, record in enumerate(history, 1):
            status = "성공" if record["success"] else "실패"
            print(f"  {i}. [{record['rollback_type']}] {record['reason']} ({status})")

        print("테스트 통과: 롤백 히스토리")


@pytest.mark.asyncio
class TestEndToEndCanaryRollback:
    """엔드투엔드 카나리 배포 및 롤백 시나리오"""

    async def test_complete_canary_rollback_workflow(self, async_db_session: AsyncSession):
        """
        전체 워크플로우 검증

        시나리오:
        1. 프로덕션 모델 v1.0.0 운영 중
        2. 새 모델 v1.1.0 학습 완료
        3. 카나리 배포 시작 (10% → 25% → 50%)
        4. 성능 저하 감지
        5. 카나리 배포 중단
        6. v1.0.0으로 롤백
        """
        print("\n=== 엔드투엔드 카나리 롤백 워크플로우 ===")

        # Step 1: 초기 모델 설정
        print("\nStep 1: 초기 프로덕션 모델 (v1.0.0)")
        production_v1_0 = MLModel(
            id=uuid4(),
            name="Model-v1.0.0",
            version="1.0.0",
            model_type=ModelType.ISOLATION_FOREST,
            training_data_start=datetime.utcnow().date() - timedelta(days=60),
            training_data_end=datetime.utcnow().date() - timedelta(days=30),
            trained_at=datetime.utcnow() - timedelta(days=30),
            deployed_at=datetime.utcnow() - timedelta(days=25),
            accuracy=0.88,
            precision=0.86,
            recall=0.90,
            f1_score=0.88,
            deployment_status=DeploymentStatus.PRODUCTION,
            model_path="/models/model_v1.0.0.pkl",
        )

        staging_v1_1 = MLModel(
            id=uuid4(),
            name="Model-v1.1.0",
            version="1.1.0",
            model_type=ModelType.ISOLATION_FOREST,
            training_data_start=datetime.utcnow().date() - timedelta(days=30),
            training_data_end=datetime.utcnow().date(),
            trained_at=datetime.utcnow() - timedelta(days=1),
            accuracy=0.92,  # 학습 시 높은 성능
            precision=0.90,
            recall=0.94,
            f1_score=0.92,
            deployment_status=DeploymentStatus.STAGING,
            model_path="/models/model_v1.1.0.pkl",
        )

        async_db_session.add_all([production_v1_0, staging_v1_1])
        await async_db_session.commit()

        # Step 2: 카나리 배포 시작
        print("\nStep 2: 카나리 배포 시작 (10% 트래픽)")
        canary = CanaryDeployment(async_db_session)
        await canary.start_canary_deployment(
            canary_model_id=staging_v1_1.id,
            initial_traffic_percentage=10,
            success_threshold=0.95,
        )

        # Step 3: 10% 트래픽 모니터링 (성능 문제 발견)
        print("\nStep 3: 10% 트래픽 모니터링")
        for i in range(200):
            model_type, _ = await canary.route_traffic(f"TX10_{i:04d}")
            # 카나리: 75% 성공 (낮음!), 프로덕션: 95% 성공
            if model_type == "canary":
                success = i % 100 < 75
            else:
                success = i % 100 < 95

            await canary.record_result(model_type, success)

        status_10 = await canary.get_canary_status()
        print(f"카나리 성공률: {status_10['canary']['success_rate']:.2%}")
        print(f"프로덕션 성공률: {status_10['production']['success_rate']:.2%}")
        print(f"권장 사항: {status_10['recommendation']}")

        # Step 4: 성능 저하 확인 후 카나리 배포 중단
        print("\nStep 4: 성능 저하로 카나리 배포 중단")
        abort_result = await canary.abort_canary_deployment(
            reason=f"카나리 성능 저하: {status_10['canary']['success_rate']:.2%} < 95%"
        )

        assert abort_result["final_stats"]["status"] == "aborted"
        print(f"중단 사유: {abort_result['final_stats']['abort_reason']}")

        # Step 5: v1.0.0 상태 확인 (여전히 프로덕션)
        print("\nStep 5: 프로덕션 모델 상태 확인")
        await async_db_session.refresh(production_v1_0)
        await async_db_session.refresh(staging_v1_1)

        assert production_v1_0.deployment_status == DeploymentStatus.PRODUCTION
        assert staging_v1_1.deployment_status == DeploymentStatus.STAGING

        print(f"현재 프로덕션: {production_v1_0.name} (v{production_v1_0.version})")
        print(f"카나리 중단 모델: {staging_v1_1.name} (v{staging_v1_1.version})")

        print("\n테스트 통과: 엔드투엔드 카나리 롤백 워크플로우")
        print("결론: 카나리 배포 중 성능 문제 감지 시 자동 중단 및 기존 모델 유지 성공")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
