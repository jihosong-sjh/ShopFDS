"""
데이터베이스 쿼리 최적화 유틸리티

N+1 문제 해결, 쿼리 성능 모니터링, 인덱스 활용 가이드
"""

import logging
import time
import functools
from typing import Any, Callable, List, Optional, Dict
from contextlib import asynccontextmanager
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Engine
from sqlalchemy.orm import selectinload, joinedload, contains_eager

logger = logging.getLogger(__name__)


class QueryPerformanceMonitor:
    """
    쿼리 성능 모니터링 클래스

    느린 쿼리를 자동으로 감지하고 로깅합니다.
    """

    def __init__(self, slow_query_threshold_ms: int = 100):
        """
        Args:
            slow_query_threshold_ms: 느린 쿼리로 판단할 임계값 (밀리초)
        """
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.query_stats: Dict[str, Dict[str, Any]] = {}

    def track_query(self, query_name: str, execution_time_ms: float, query_text: Optional[str] = None):
        """
        쿼리 실행 시간 추적

        Args:
            query_name: 쿼리 식별자
            execution_time_ms: 실행 시간 (밀리초)
            query_text: 쿼리 텍스트 (선택)
        """
        if query_name not in self.query_stats:
            self.query_stats[query_name] = {
                "count": 0,
                "total_time_ms": 0.0,
                "max_time_ms": 0.0,
                "min_time_ms": float('inf'),
                "slow_queries": 0,
                "query_text": query_text
            }

        stats = self.query_stats[query_name]
        stats["count"] += 1
        stats["total_time_ms"] += execution_time_ms
        stats["max_time_ms"] = max(stats["max_time_ms"], execution_time_ms)
        stats["min_time_ms"] = min(stats["min_time_ms"], execution_time_ms)

        if execution_time_ms > self.slow_query_threshold_ms:
            stats["slow_queries"] += 1
            logger.warning(
                f"느린 쿼리 감지: {query_name} - {execution_time_ms:.2f}ms "
                f"(임계값: {self.slow_query_threshold_ms}ms)"
            )
            if query_text:
                logger.debug(f"쿼리 내용: {query_text[:200]}...")

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """쿼리 통계 조회"""
        return self.query_stats.copy()

    def reset_stats(self):
        """통계 초기화"""
        self.query_stats.clear()

    def get_summary(self) -> str:
        """통계 요약 문자열 생성"""
        if not self.query_stats:
            return "쿼리 통계 없음"

        lines = ["=== 쿼리 성능 통계 ==="]
        for query_name, stats in sorted(
            self.query_stats.items(),
            key=lambda x: x[1]["total_time_ms"],
            reverse=True
        ):
            avg_time = stats["total_time_ms"] / stats["count"]
            lines.append(
                f"{query_name}: "
                f"실행 {stats['count']}회, "
                f"평균 {avg_time:.2f}ms, "
                f"최대 {stats['max_time_ms']:.2f}ms, "
                f"느린 쿼리 {stats['slow_queries']}회"
            )
        return "\n".join(lines)


# 전역 모니터 인스턴스
_query_monitor = QueryPerformanceMonitor()


def get_query_monitor() -> QueryPerformanceMonitor:
    """전역 쿼리 모니터 인스턴스 조회"""
    return _query_monitor


def monitor_query(query_name: str):
    """
    쿼리 실행 시간을 모니터링하는 데코레이터

    Usage:
        @monitor_query("get_user_orders")
        async def get_user_orders(user_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                execution_time_ms = (time.time() - start_time) * 1000
                _query_monitor.track_query(query_name, execution_time_ms)
        return wrapper
    return decorator


class QueryOptimizationHelper:
    """
    쿼리 최적화 헬퍼 클래스

    N+1 문제 방지 및 최적화 패턴 제공
    """

    @staticmethod
    def eager_load_relationships(query, *relationships):
        """
        관계를 eager load하여 N+1 문제 방지

        Args:
            query: SQLAlchemy 쿼리
            relationships: 로드할 관계들 (문자열 또는 SQLAlchemy relationship)

        Returns:
            최적화된 쿼리

        Example:
            query = select(Order)
            query = QueryOptimizationHelper.eager_load_relationships(
                query,
                Order.items,
                Order.payment
            )
        """
        for relationship in relationships:
            query = query.options(selectinload(relationship))
        return query

    @staticmethod
    def eager_load_nested(query, *relationship_chains):
        """
        중첩된 관계를 eager load

        Example:
            query = select(Order)
            query = QueryOptimizationHelper.eager_load_nested(
                query,
                (Order.items, OrderItem.product)
            )
        """
        for chain in relationship_chains:
            if isinstance(chain, tuple):
                option = selectinload(chain[0])
                for rel in chain[1:]:
                    option = option.selectinload(rel)
                query = query.options(option)
            else:
                query = query.options(selectinload(chain))
        return query

    @staticmethod
    def use_joined_load(query, *relationships):
        """
        JOIN을 사용한 eager loading (일대일, 다대일 관계에 적합)

        selectinload는 별도 쿼리를 실행하지만,
        joinedload는 JOIN을 사용하여 단일 쿼리로 처리
        """
        for relationship in relationships:
            query = query.options(joinedload(relationship))
        return query

    @staticmethod
    async def batch_load_relationships(
        db: AsyncSession,
        entities: List[Any],
        relationship_attr: str
    ) -> List[Any]:
        """
        이미 로드된 엔티티의 관계를 배치로 로드

        Args:
            db: 데이터베이스 세션
            entities: 엔티티 리스트
            relationship_attr: 로드할 관계 속성명

        Returns:
            관계가 로드된 엔티티 리스트
        """
        if not entities:
            return entities

        # 모든 엔티티의 관계를 한 번에 로드
        for entity in entities:
            await db.refresh(entity, [relationship_attr])

        return entities


@asynccontextmanager
async def query_performance_context(query_name: str):
    """
    쿼리 성능 측정 컨텍스트 매니저

    Usage:
        async with query_performance_context("get_orders"):
            result = await db.execute(query)
    """
    start_time = time.time()
    try:
        yield
    finally:
        execution_time_ms = (time.time() - start_time) * 1000
        _query_monitor.track_query(query_name, execution_time_ms)


def setup_query_logging(engine: Engine, log_queries: bool = True):
    """
    SQLAlchemy 엔진에 쿼리 로깅 설정

    Args:
        engine: SQLAlchemy 엔진
        log_queries: 모든 쿼리 로깅 여부 (개발 환경에서만 권장)
    """
    if log_queries:
        @event.listens_for(engine.sync_engine, "before_cursor_execute", retval=True)
        def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
            conn.info.setdefault('query_start_time', []).append(time.time())
            logger.debug(f"쿼리 실행: {statement[:200]}...")
            return statement, params

        @event.listens_for(engine.sync_engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, params, context, executemany):
            total_time = time.time() - conn.info['query_start_time'].pop()
            logger.debug(f"쿼리 완료: {total_time * 1000:.2f}ms")


# 인덱스 최적화 가이드 (문서화 목적)
INDEX_OPTIMIZATION_GUIDE = """
=== 데이터베이스 인덱스 최적화 가이드 ===

1. User 테이블
   - email (UNIQUE): 로그인 시 빠른 조회
   - status: 활성 사용자 필터링

2. Product 테이블
   - category: 카테고리별 조회
   - status: 상품 상태별 필터링
   - (category, status): 복합 인덱스 (자주 함께 사용)
   - name: 상품명 검색 (GIN 인덱스 권장 - PostgreSQL)

3. Order 테이블
   - user_id: 사용자별 주문 조회
   - status: 주문 상태별 필터링
   - created_at: 최근 주문 조회
   - (user_id, created_at): 복합 인덱스

4. OrderItem 테이블
   - order_id: 주문별 항목 조회
   - product_id: 상품별 주문 조회

5. Payment 테이블
   - order_id: 주문별 결제 조회
   - status: 결제 상태별 필터링

6. Cart 테이블
   - user_id (UNIQUE): 사용자별 장바구니 조회

7. CartItem 테이블
   - cart_id: 장바구니별 항목 조회
   - product_id: 상품별 장바구니 조회

8. Transaction (FDS) 테이블
   - user_id: 사용자별 거래 조회
   - created_at: 시간 범위 조회
   - risk_score: 위험도별 필터링
   - (user_id, created_at): 복합 인덱스

9. RiskFactor (FDS) 테이블
   - transaction_id: 거래별 위험 요인 조회

10. DetectionRule (FDS) 테이블
    - is_active: 활성 룰만 조회
    - rule_type: 룰 타입별 필터링

=== N+1 쿼리 방지 체크리스트 ===

1. ✓ 장바구니 조회 시 CartItem과 Product를 함께 로드
   - selectinload(Cart.items).selectinload(CartItem.product)

2. ✓ 주문 조회 시 OrderItem과 Product를 함께 로드
   - selectinload(Order.items).selectinload(OrderItem.product)

3. ✓ 주문 조회 시 Payment 정보를 함께 로드
   - selectinload(Order.payment)

4. ✓ 사용자별 주문 목록 조회 시 필요한 관계를 모두 로드
   - selectinload(Order.items), selectinload(Order.payment)

5. ⚠ 대량의 데이터 조회 시 페이지네이션 필수
   - limit와 offset 사용

6. ⚠ 집계 쿼리는 애플리케이션이 아닌 DB에서 처리
   - func.count(), func.sum() 등 사용

=== 쿼리 최적화 권장사항 ===

1. SELECT 시 필요한 컬럼만 조회 (전체 엔티티가 아닌 경우)
2. WHERE 절에 인덱스 컬럼 사용
3. JOIN 대신 서브쿼리가 더 빠를 수 있음 (상황에 따라)
4. EXPLAIN ANALYZE로 쿼리 실행 계획 확인
5. 복잡한 쿼리는 데이터베이스 뷰로 생성
6. 읽기 전용 쿼리는 읽기 복제본 사용 고려
"""


def print_index_guide():
    """인덱스 최적화 가이드 출력"""
    print(INDEX_OPTIMIZATION_GUIDE)


# 쿼리 최적화 권장 패턴
class OptimizedQueryPatterns:
    """자주 사용되는 최적화된 쿼리 패턴 모음"""

    @staticmethod
    def get_user_with_orders_pattern():
        """
        사용자와 주문을 함께 조회하는 최적화된 패턴

        Example:
            from sqlalchemy import select
            from src.models.user import User

            query = select(User).where(User.id == user_id)
            query = OptimizedQueryPatterns.get_user_with_orders_pattern(query)
            result = await db.execute(query)
            user = result.scalars().first()
        """
        from src.models.user import User
        from src.models.order import Order

        return lambda query: query.options(
            selectinload(User.orders)
            .selectinload(Order.items)
        )

    @staticmethod
    def get_order_with_details_pattern():
        """
        주문과 모든 관련 정보를 함께 조회하는 최적화된 패턴
        """
        from src.models.order import Order, OrderItem
        from src.models.payment import Payment

        return lambda query: query.options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.payment)
        )
