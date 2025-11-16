"""
A/B 테스트 관리 API 엔드포인트

보안팀이 FDS 룰이나 ML 모델의 성능을 비교하기 위한
A/B 테스트를 설정하고 결과를 조회할 수 있는 API를 제공합니다.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# FDS 모델 임포트
import sys
import os

# FDS 서비스 경로를 Python 경로에 추가
fds_service_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../fds/src")
)
if fds_service_path not in sys.path:
    sys.path.insert(0, fds_service_path)

from models.ab_test import ABTest, ABTestStatus, ABTestType
from src.database import get_db

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/ab-tests", tags=["A/B Tests"])


# --- Pydantic Schemas ---


class ABTestCreateRequest(BaseModel):
    """A/B 테스트 생성 요청"""

    name: str = Field(..., description="테스트 이름", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="테스트 설명 및 목적")
    test_type: str = Field(..., description="테스트 유형 (rule, model, threshold, hybrid)")
    group_a_config: dict = Field(..., description="그룹 A 설정 (기존 룰/모델 ID 또는 파라미터)")
    group_b_config: dict = Field(..., description="그룹 B 설정 (새 룰/모델 ID 또는 파라미터)")
    traffic_split_percentage: int = Field(
        50, description="그룹 B에 할당할 트래픽 비율 (0-100%)", ge=0, le=100
    )
    planned_duration_hours: Optional[int] = Field(
        None, description="계획된 테스트 기간 (시간)", ge=1
    )

    @validator("test_type")
    def validate_test_type(cls, v):
        """테스트 유형 검증"""
        valid_types = [tt.value for tt in ABTestType]
        if v not in valid_types:
            raise ValueError(
                f"Invalid test_type. Must be one of: {', '.join(valid_types)}"
            )
        return v

    @validator("group_a_config", "group_b_config")
    def validate_config(cls, v):
        """그룹 설정 검증"""
        if not isinstance(v, dict):
            raise ValueError("Config must be a dictionary")
        if not v:
            raise ValueError("Config cannot be empty")
        return v


class ABTestUpdateRequest(BaseModel):
    """A/B 테스트 수정 요청"""

    description: Optional[str] = Field(None, description="테스트 설명")
    traffic_split_percentage: Optional[int] = Field(
        None, description="그룹 B 트래픽 비율 (0-100%)", ge=0, le=100
    )
    planned_duration_hours: Optional[int] = Field(
        None, description="계획된 테스트 기간 (시간)", ge=1
    )


class ABTestStatusRequest(BaseModel):
    """A/B 테스트 상태 변경 요청"""

    action: str = Field(..., description="액션 (start, pause, resume, complete, cancel)")
    winner: Optional[str] = Field(None, description="승자 (A, B, tie) - complete 시 선택 사항")
    confidence_level: Optional[float] = Field(
        None, description="통계적 신뢰 수준 (0-1) - complete 시 선택 사항", ge=0, le=1
    )

    @validator("action")
    def validate_action(cls, v):
        """액션 검증"""
        valid_actions = ["start", "pause", "resume", "complete", "cancel"]
        if v not in valid_actions:
            raise ValueError(
                f"Invalid action. Must be one of: {', '.join(valid_actions)}"
            )
        return v

    @validator("winner")
    def validate_winner(cls, v):
        """승자 검증"""
        if v is not None and v not in ["A", "B", "tie"]:
            raise ValueError("Winner must be one of: A, B, tie")
        return v


class ABTestGroupMetrics(BaseModel):
    """A/B 테스트 그룹별 성과 지표"""

    total_transactions: int
    true_positives: int
    false_positives: int
    false_negatives: int
    avg_evaluation_time_ms: Optional[float]
    precision: Optional[float]
    recall: Optional[float]
    f1_score: Optional[float]
    false_positive_rate: Optional[float]


class ABTestResponse(BaseModel):
    """A/B 테스트 응답"""

    id: str
    name: str
    description: Optional[str]
    test_type: str
    status: str
    group_a_config: dict
    group_b_config: dict
    traffic_split_percentage: int
    start_time: Optional[str]
    end_time: Optional[str]
    planned_duration_hours: Optional[int]
    actual_duration_hours: Optional[float]
    created_by: Optional[str]
    group_a: ABTestGroupMetrics
    group_b: ABTestGroupMetrics
    winner: Optional[str]
    confidence_level: Optional[float]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ABTestListResponse(BaseModel):
    """A/B 테스트 목록 응답"""

    total: int
    tests: List[ABTestResponse]


class ABTestResultsResponse(BaseModel):
    """A/B 테스트 결과 비교 응답"""

    test_id: str
    test_name: str
    test_type: str
    status: str
    duration_hours: Optional[float]
    group_a: ABTestGroupMetrics
    group_b: ABTestGroupMetrics
    comparison: dict  # 그룹 A vs B 비교 결과
    recommendation: str  # 권장 사항
    winner: Optional[str]
    confidence_level: Optional[float]


# --- API Endpoints ---


@router.get("/", response_model=ABTestListResponse, summary="A/B 테스트 목록 조회")
async def list_ab_tests(
    test_type: Optional[str] = Query(None, description="테스트 유형 필터"),
    status: Optional[str] = Query(None, description="테스트 상태 필터"),
    skip: int = Query(0, description="건너뛸 개수", ge=0),
    limit: int = Query(100, description="조회할 개수", ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """
    A/B 테스트 목록을 조회합니다.

    **필터링 옵션**:
    - `test_type`: 특정 테스트 유형만 조회 (rule, model, threshold, hybrid)
    - `status`: 테스트 상태로 필터링 (draft, running, paused, completed, cancelled)

    **정렬**: 시작 시간 내림차순 (최근 테스트가 먼저)
    """
    try:
        # 기본 쿼리
        query = select(ABTest)

        # 필터 적용
        if test_type:
            query = query.where(ABTest.test_type == test_type)

        if status:
            query = query.where(ABTest.status == status)

        # 정렬: 시작 시간 내림차순, 생성일 기준
        query = query.order_by(
            ABTest.start_time.desc().nulls_last(), ABTest.created_at.desc()
        )

        # 전체 개수 조회
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 페이지네이션 적용
        query = query.offset(skip).limit(limit)

        # 테스트 조회
        result = await db.execute(query)
        tests = result.scalars().all()

        return ABTestListResponse(
            total=total, tests=[ABTestResponse(**test.to_dict()) for test in tests]
        )

    except Exception as e:
        logger.error(f"A/B 테스트 목록 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A/B 테스트 목록 조회 중 오류가 발생했습니다.",
        )


@router.get("/{test_id}", response_model=ABTestResponse, summary="A/B 테스트 상세 조회")
async def get_ab_test(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    특정 A/B 테스트의 상세 정보를 조회합니다.

    **응답**:
    - 테스트 설정 및 실시간 성과 지표 포함
    """
    try:
        # 테스트 조회
        query = select(ABTest).where(ABTest.id == test_id)
        result = await db.execute(query)
        test = result.scalar_one_or_none()

        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"A/B 테스트를 찾을 수 없습니다: {test_id}",
            )

        return ABTestResponse(**test.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"A/B 테스트 상세 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A/B 테스트 상세 조회 중 오류가 발생했습니다.",
        )


@router.post(
    "/",
    response_model=ABTestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="새 A/B 테스트 생성",
)
async def create_ab_test(
    request: ABTestCreateRequest,
    db: AsyncSession = Depends(get_db),
    # TODO: current_user: User = Depends(get_current_user),
):
    """
    새로운 A/B 테스트를 생성합니다.

    **주의**:
    - 테스트 이름은 고유해야 합니다.
    - 생성 후에는 `draft` 상태이며, `/status` 엔드포인트로 시작해야 합니다.

    **예시 설정**:
    - **룰 테스트**:
      ```json
      {
        "group_a_config": {"rule_id": "uuid-of-existing-rule"},
        "group_b_config": {"rule_id": "uuid-of-new-rule"}
      }
      ```
    - **모델 테스트**:
      ```json
      {
        "group_a_config": {"model_id": "uuid-of-current-model"},
        "group_b_config": {"model_id": "uuid-of-new-model"}
      }
      ```
    """
    try:
        # 테스트 이름 중복 확인
        existing_query = select(ABTest).where(ABTest.name == request.name)
        existing_result = await db.execute(existing_query)
        existing_test = existing_result.scalar_one_or_none()

        if existing_test:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"이미 존재하는 A/B 테스트 이름입니다: {request.name}",
            )

        # 새 테스트 생성
        new_test = ABTest(
            name=request.name,
            description=request.description,
            test_type=ABTestType(request.test_type),
            group_a_config=request.group_a_config,
            group_b_config=request.group_b_config,
            traffic_split_percentage=request.traffic_split_percentage,
            planned_duration_hours=request.planned_duration_hours,
            # created_by=current_user.id,  # TODO: 인증 구현 후 활성화
        )

        db.add(new_test)
        await db.commit()
        await db.refresh(new_test)

        logger.info(f"새 A/B 테스트 생성 완료: {new_test.name} (ID: {new_test.id})")

        return ABTestResponse(**new_test.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"A/B 테스트 생성 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A/B 테스트 생성 중 오류가 발생했습니다.",
        )


@router.put("/{test_id}", response_model=ABTestResponse, summary="A/B 테스트 수정")
async def update_ab_test(
    test_id: UUID,
    request: ABTestUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    기존 A/B 테스트를 수정합니다.

    **주의**:
    - `draft` 또는 `paused` 상태에서만 수정 가능합니다.
    - `running` 또는 `completed` 상태에서는 수정할 수 없습니다.
    """
    try:
        # 테스트 조회
        query = select(ABTest).where(ABTest.id == test_id)
        result = await db.execute(query)
        test = result.scalar_one_or_none()

        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"A/B 테스트를 찾을 수 없습니다: {test_id}",
            )

        # 수정 가능 상태 확인
        if test.status not in [ABTestStatus.DRAFT, ABTestStatus.PAUSED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{test.status}' 상태의 테스트는 수정할 수 없습니다. (draft 또는 paused 상태만 가능)",
            )

        # 수정 사항 적용
        if request.description is not None:
            test.description = request.description
        if request.traffic_split_percentage is not None:
            test.traffic_split_percentage = request.traffic_split_percentage
        if request.planned_duration_hours is not None:
            test.planned_duration_hours = request.planned_duration_hours

        await db.commit()
        await db.refresh(test)

        logger.info(f"A/B 테스트 수정 완료: {test.name} (ID: {test.id})")

        return ABTestResponse(**test.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"A/B 테스트 수정 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A/B 테스트 수정 중 오류가 발생했습니다.",
        )


@router.patch(
    "/{test_id}/status", response_model=ABTestResponse, summary="A/B 테스트 상태 변경"
)
async def update_ab_test_status(
    test_id: UUID,
    request: ABTestStatusRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    A/B 테스트의 상태를 변경합니다.

    **액션**:
    - `start`: 테스트 시작 (draft → running)
    - `pause`: 테스트 일시 중지 (running → paused)
    - `resume`: 테스트 재개 (paused → running)
    - `complete`: 테스트 완료 (running/paused → completed)
    - `cancel`: 테스트 취소 (draft/running/paused → cancelled)

    **완료 시 선택 사항**:
    - `winner`: 승자 지정 (A, B, tie), 없으면 F1 스코어 기준 자동 계산
    - `confidence_level`: 통계적 신뢰 수준 (0-1)
    """
    try:
        # 테스트 조회
        query = select(ABTest).where(ABTest.id == test_id)
        result = await db.execute(query)
        test = result.scalar_one_or_none()

        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"A/B 테스트를 찾을 수 없습니다: {test_id}",
            )

        # 액션 실행
        try:
            if request.action == "start":
                test.start()
            elif request.action == "pause":
                test.pause()
            elif request.action == "resume":
                test.resume()
            elif request.action == "complete":
                test.complete(
                    winner=request.winner, confidence=request.confidence_level
                )
            elif request.action == "cancel":
                test.cancel()

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        await db.commit()
        await db.refresh(test)

        logger.info(
            f"A/B 테스트 상태 변경 완료: {test.name} (ID: {test.id}), "
            f"action={request.action}, new_status={test.status}"
        )

        return ABTestResponse(**test.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"A/B 테스트 상태 변경 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A/B 테스트 상태 변경 중 오류가 발생했습니다.",
        )


@router.get(
    "/{test_id}/results", response_model=ABTestResultsResponse, summary="A/B 테스트 결과 조회"
)
async def get_ab_test_results(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    A/B 테스트 결과를 집계하고 비교 분석을 제공합니다.

    **응답**:
    - 그룹 A/B의 상세 성과 지표
    - 정탐률, 오탐률, F1 스코어 비교
    - 평균 평가 시간 비교
    - 권장 사항 (어느 그룹이 우수한지)

    **권장 사항 로직**:
    - F1 스코어가 높은 그룹 선택
    - F1 스코어가 동일하면 오탐률이 낮은 그룹 선택
    - 모든 지표가 동일하면 평가 시간이 짧은 그룹 선택
    """
    try:
        # 테스트 조회
        query = select(ABTest).where(ABTest.id == test_id)
        result = await db.execute(query)
        test = result.scalar_one_or_none()

        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"A/B 테스트를 찾을 수 없습니다: {test_id}",
            )

        # 그룹별 성과 지표
        group_a_metrics = ABTestGroupMetrics(
            total_transactions=test.group_a_total_transactions,
            true_positives=test.group_a_true_positives,
            false_positives=test.group_a_false_positives,
            false_negatives=test.group_a_false_negatives,
            avg_evaluation_time_ms=test.group_a_avg_evaluation_time_ms,
            precision=test.calculate_precision("A"),
            recall=test.calculate_recall("A"),
            f1_score=test.calculate_f1_score("A"),
            false_positive_rate=test.calculate_false_positive_rate("A"),
        )

        group_b_metrics = ABTestGroupMetrics(
            total_transactions=test.group_b_total_transactions,
            true_positives=test.group_b_true_positives,
            false_positives=test.group_b_false_positives,
            false_negatives=test.group_b_false_negatives,
            avg_evaluation_time_ms=test.group_b_avg_evaluation_time_ms,
            precision=test.calculate_precision("B"),
            recall=test.calculate_recall("B"),
            f1_score=test.calculate_f1_score("B"),
            false_positive_rate=test.calculate_false_positive_rate("B"),
        )

        # 비교 분석
        comparison = {}

        # F1 스코어 비교
        if (
            group_a_metrics.f1_score is not None
            and group_b_metrics.f1_score is not None
        ):
            f1_diff = group_b_metrics.f1_score - group_a_metrics.f1_score
            comparison["f1_score_difference"] = f1_diff
            comparison["f1_score_improvement_percentage"] = (
                (f1_diff / group_a_metrics.f1_score * 100)
                if group_a_metrics.f1_score > 0
                else None
            )

        # 오탐률 비교
        if (
            group_a_metrics.false_positive_rate is not None
            and group_b_metrics.false_positive_rate is not None
        ):
            fpr_diff = (
                group_b_metrics.false_positive_rate
                - group_a_metrics.false_positive_rate
            )
            comparison["fpr_difference"] = fpr_diff
            comparison["fpr_reduction_percentage"] = (
                (-fpr_diff / group_a_metrics.false_positive_rate * 100)
                if group_a_metrics.false_positive_rate > 0
                else None
            )

        # 평가 시간 비교
        if (
            group_a_metrics.avg_evaluation_time_ms is not None
            and group_b_metrics.avg_evaluation_time_ms is not None
        ):
            time_diff = (
                group_b_metrics.avg_evaluation_time_ms
                - group_a_metrics.avg_evaluation_time_ms
            )
            comparison["evaluation_time_difference_ms"] = time_diff
            comparison["evaluation_time_change_percentage"] = (
                (time_diff / group_a_metrics.avg_evaluation_time_ms * 100)
                if group_a_metrics.avg_evaluation_time_ms > 0
                else None
            )

        # 권장 사항 생성
        recommendation = _generate_recommendation(
            test, group_a_metrics, group_b_metrics, comparison
        )

        return ABTestResultsResponse(
            test_id=str(test.id),
            test_name=test.name,
            test_type=test.test_type.value,
            status=test.status.value,
            duration_hours=test.duration_hours,
            group_a=group_a_metrics,
            group_b=group_b_metrics,
            comparison=comparison,
            recommendation=recommendation,
            winner=test.winner,
            confidence_level=test.confidence_level,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"A/B 테스트 결과 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A/B 테스트 결과 조회 중 오류가 발생했습니다.",
        )


@router.delete(
    "/{test_id}", status_code=status.HTTP_204_NO_CONTENT, summary="A/B 테스트 삭제"
)
async def delete_ab_test(
    test_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    A/B 테스트를 삭제합니다.

    **주의**:
    - 테스트를 삭제하면 모든 결과 데이터가 영구적으로 손실됩니다.
    - 대신 `cancel` 액션으로 취소하는 것을 권장합니다.
    - `running` 상태의 테스트는 삭제할 수 없습니다.
    """
    try:
        # 테스트 조회
        query = select(ABTest).where(ABTest.id == test_id)
        result = await db.execute(query)
        test = result.scalar_one_or_none()

        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"A/B 테스트를 찾을 수 없습니다: {test_id}",
            )

        # running 상태 확인
        if test.status == ABTestStatus.RUNNING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="진행 중인 테스트는 삭제할 수 없습니다. 먼저 pause 또는 cancel 하세요.",
            )

        # 테스트 삭제
        await db.delete(test)
        await db.commit()

        logger.info(f"A/B 테스트 삭제 완료: {test.name} (ID: {test.id})")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"A/B 테스트 삭제 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A/B 테스트 삭제 중 오류가 발생했습니다.",
        )


# --- Helper Functions ---


def _generate_recommendation(
    test: ABTest,
    group_a: ABTestGroupMetrics,
    group_b: ABTestGroupMetrics,
    comparison: dict,
) -> str:
    """
    A/B 테스트 결과를 기반으로 권장 사항 생성

    Args:
        test: ABTest 객체
        group_a: 그룹 A 성과 지표
        group_b: 그룹 B 성과 지표
        comparison: 비교 결과

    Returns:
        str: 권장 사항 메시지
    """
    # 충분한 데이터가 없는 경우
    min_transactions = 100
    if (
        group_a.total_transactions < min_transactions
        or group_b.total_transactions < min_transactions
    ):
        return (
            f"아직 충분한 데이터가 수집되지 않았습니다. "
            f"(최소 {min_transactions}건 필요, "
            f"현재 A: {group_a.total_transactions}건, B: {group_b.total_transactions}건)"
        )

    # F1 스코어 기준 비교
    if group_a.f1_score is not None and group_b.f1_score is not None:
        f1_diff = group_b.f1_score - group_a.f1_score

        if abs(f1_diff) < 0.01:  # 1% 이내 차이면 무승부
            # 오탐률 비교
            if (
                group_a.false_positive_rate is not None
                and group_b.false_positive_rate is not None
            ):
                fpr_diff = group_b.false_positive_rate - group_a.false_positive_rate
                if fpr_diff < -0.01:  # B가 오탐률이 낮음
                    return (
                        f"그룹 B 권장: F1 스코어는 유사하지만 오탐률이 "
                        f"{abs(fpr_diff)*100:.2f}% 낮습니다."
                    )
                elif fpr_diff > 0.01:  # A가 오탐률이 낮음
                    return (
                        f"그룹 A 권장: F1 스코어는 유사하지만 오탐률이 "
                        f"{abs(fpr_diff)*100:.2f}% 낮습니다."
                    )

            # 평가 시간 비교
            if (
                group_a.avg_evaluation_time_ms is not None
                and group_b.avg_evaluation_time_ms is not None
            ):
                time_diff = (
                    group_b.avg_evaluation_time_ms - group_a.avg_evaluation_time_ms
                )
                if time_diff < -10:  # B가 10ms 이상 빠름
                    return (
                        f"그룹 B 권장: 성능 지표는 유사하지만 평가 시간이 "
                        f"{abs(time_diff):.2f}ms 더 빠릅니다."
                    )
                elif time_diff > 10:  # A가 10ms 이상 빠름
                    return (
                        f"그룹 A 권장: 성능 지표는 유사하지만 평가 시간이 "
                        f"{abs(time_diff):.2f}ms 더 빠릅니다."
                    )

            return "무승부: 두 그룹의 성능이 거의 동일합니다. 현재 설정 유지를 권장합니다."

        elif f1_diff > 0:  # B가 우수
            improvement_pct = comparison.get("f1_score_improvement_percentage", 0)
            return (
                f"그룹 B 권장: F1 스코어가 {f1_diff:.4f} ({improvement_pct:.2f}%) 더 높습니다. "
                f"새로운 설정으로 전환을 권장합니다."
            )
        else:  # A가 우수
            return f"그룹 A 권장: F1 스코어가 {abs(f1_diff):.4f} 더 높습니다. " f"기존 설정 유지를 권장합니다."

    return "데이터 부족: 정확한 비교를 위해 더 많은 데이터가 필요합니다."
