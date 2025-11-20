"""
Behavior Pattern API

행동 패턴 데이터 수집 및 분석 API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid

from src.models.behavior_pattern import BehaviorPattern
from src.engines.behavior_analysis_engine import BehaviorAnalysisEngine
from src.database import get_db


router = APIRouter(prefix="/v1/fds/behavior-pattern", tags=["Behavior Pattern"])


# Pydantic 모델
class MouseMovementInput(BaseModel):
    timestamp: int = Field(..., description="타임스탬프 (milliseconds)")
    x: int = Field(..., description="X 좌표")
    y: int = Field(..., description="Y 좌표")
    speed: float = Field(..., description="속도 (pixels/sec)")
    acceleration: float = Field(..., description="가속도 (pixels/sec^2)")
    curvature: float = Field(..., description="곡률 (0-1)")


class KeyboardEventInput(BaseModel):
    timestamp: int = Field(..., description="타임스탬프 (milliseconds)")
    key: str = Field(..., description="키 (마스킹됨)")
    duration: int = Field(..., description="키 누름 시간 (milliseconds)")


class ClickstreamEventInput(BaseModel):
    page: str = Field(..., description="페이지 경로")
    timestamp: int = Field(..., description="타임스탬프 (milliseconds)")
    duration: int = Field(..., description="체류 시간 (milliseconds)")


class BehaviorPatternRequest(BaseModel):
    session_id: str = Field(..., description="세션 ID (클라이언트 생성)")
    user_id: Optional[UUID] = Field(None, description="사용자 ID (로그인 시)")
    mouse_movements: List[MouseMovementInput] = Field(
        default_factory=list, description="마우스 움직임 데이터"
    )
    keyboard_events: List[KeyboardEventInput] = Field(
        default_factory=list, description="키보드 이벤트 데이터"
    )
    clickstream: List[ClickstreamEventInput] = Field(
        default_factory=list, description="클릭스트림 데이터"
    )


class BehaviorAnalysisResponse(BaseModel):
    session_id: str
    bot_score: int = Field(..., description="봇 점수 (0-100)")
    risk_level: str = Field(..., description="위험 수준 (low/medium/high)")
    requires_additional_auth: bool = Field(..., description="추가 인증 필요 여부 (봇 점수 > 70)")
    mouse_analysis: Dict[str, Any]
    keyboard_analysis: Dict[str, Any]
    clickstream_analysis: Dict[str, Any]
    risk_factors: List[str]


@router.post(
    "/", response_model=BehaviorAnalysisResponse, status_code=status.HTTP_201_CREATED
)
async def collect_behavior_pattern(
    request: BehaviorPatternRequest, db: AsyncSession = Depends(get_db)
):
    """
    행동 패턴 데이터 수집 및 분석

    클라이언트에서 수집한 마우스 움직임, 키보드 입력, 클릭스트림 데이터를 분석하여
    봇 확률 점수를 계산합니다.

    - **session_id**: 클라이언트에서 생성한 세션 ID
    - **user_id**: 로그인한 사용자 ID (선택사항)
    - **mouse_movements**: 마우스 움직임 데이터 (속도, 가속도, 곡률 포함)
    - **keyboard_events**: 키보드 이벤트 데이터 (타이핑 속도, 백스페이스 빈도)
    - **clickstream**: 클릭스트림 데이터 (페이지 체류 시간)

    Returns:
        - **bot_score**: 0-100 (100 = 확실한 봇)
        - **risk_level**: low (0-30), medium (31-70), high (71-100)
        - **requires_additional_auth**: 봇 점수 > 70일 때 true
    """
    # 행동 패턴 분석 엔진
    engine = BehaviorAnalysisEngine()

    # 데이터 변환
    mouse_data = [m.model_dump() for m in request.mouse_movements]
    keyboard_data = [k.model_dump() for k in request.keyboard_events]
    clickstream_data = [c.model_dump() for c in request.clickstream]

    # 분석 수행
    analysis_result = engine.analyze(mouse_data, keyboard_data, clickstream_data)

    bot_score = analysis_result["bot_score"]

    # 위험 수준 판별
    if bot_score <= 30:
        risk_level = "low"
    elif bot_score <= 70:
        risk_level = "medium"
    else:
        risk_level = "high"

    # 추가 인증 필요 여부 (봇 점수 > 70)
    requires_additional_auth = bot_score > 70

    # 데이터베이스에 저장
    behavior_pattern = BehaviorPattern(
        session_id=uuid.UUID(request.session_id)
        if request.user_id
        else None,  # UUID 변환
        user_id=request.user_id,
        mouse_movements=mouse_data,
        keyboard_events=keyboard_data,
        clickstream=clickstream_data,
        bot_score=bot_score,
    )

    db.add(behavior_pattern)
    await db.commit()
    await db.refresh(behavior_pattern)

    return BehaviorAnalysisResponse(
        session_id=request.session_id,
        bot_score=bot_score,
        risk_level=risk_level,
        requires_additional_auth=requires_additional_auth,
        mouse_analysis=analysis_result["mouse_analysis"],
        keyboard_analysis=analysis_result["keyboard_analysis"],
        clickstream_analysis=analysis_result["clickstream_analysis"],
        risk_factors=analysis_result["risk_factors"],
    )


@router.get("/{session_id}", response_model=BehaviorAnalysisResponse)
async def get_behavior_pattern(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    세션 ID로 저장된 행동 패턴 조회

    Args:
        session_id: 세션 ID

    Returns:
        저장된 행동 패턴 분석 결과
    """
    # UUID로 변환 시도
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format. Must be UUID.",
        )

    # 데이터베이스 조회
    result = await db.execute(
        "SELECT * FROM behavior_patterns WHERE session_id = :session_id",
        {"session_id": session_uuid},
    )
    behavior_pattern = result.fetchone()

    if not behavior_pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Behavior pattern not found for session ID: {session_id}",
        )

    # 재분석 (저장된 데이터로)
    engine = BehaviorAnalysisEngine()
    analysis_result = engine.analyze(
        behavior_pattern.mouse_movements or [],
        behavior_pattern.keyboard_events or [],
        behavior_pattern.clickstream or [],
    )

    bot_score = behavior_pattern.bot_score

    # 위험 수준 판별
    if bot_score <= 30:
        risk_level = "low"
    elif bot_score <= 70:
        risk_level = "medium"
    else:
        risk_level = "high"

    requires_additional_auth = bot_score > 70

    return BehaviorAnalysisResponse(
        session_id=session_id,
        bot_score=bot_score,
        risk_level=risk_level,
        requires_additional_auth=requires_additional_auth,
        mouse_analysis=analysis_result["mouse_analysis"],
        keyboard_analysis=analysis_result["keyboard_analysis"],
        clickstream_analysis=analysis_result["clickstream_analysis"],
        risk_factors=analysis_result["risk_factors"],
    )
