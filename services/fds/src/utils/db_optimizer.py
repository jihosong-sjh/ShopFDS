"""
데이터베이스 최적화 유틸리티

연결 풀 설정, 인덱스 권장사항, 쿼리 최적화를 제공합니다.

**최적화 전략**:
- 연결 풀: 최소 5, 최대 20, 오버플로우 10
- 인덱스: 자주 조회되는 컬럼에 복합 인덱스
- 쿼리: Eager Loading으로 N+1 문제 방지
"""

import logging
from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """
    데이터베이스 최적화 매니저

    연결 풀 설정, 인덱스 권장, 쿼리 분석을 제공합니다.
    """

    # 권장 인덱스 목록 (성능 최적화를 위한 복합 인덱스)
    RECOMMENDED_INDEXES = [
        {
            "table": "transactions",
            "columns": ["user_id", "created_at"],
            "name": "idx_transactions_user_created",
            "reason": "사용자별 거래 이력 조회 최적화",
        },
        {
            "table": "transactions",
            "columns": ["ip_address", "created_at"],
            "name": "idx_transactions_ip_created",
            "reason": "IP별 거래 패턴 분석 최적화",
        },
        {
            "table": "transactions",
            "columns": ["risk_level", "evaluation_status"],
            "name": "idx_transactions_risk_status",
            "reason": "위험도별 거래 필터링 최적화",
        },
        {
            "table": "transactions",
            "columns": ["evaluated_at"],
            "name": "idx_transactions_evaluated_at",
            "reason": "시계열 분석 최적화",
        },
        {
            "table": "device_fingerprints",
            "columns": ["device_id", "created_at"],
            "name": "idx_device_fingerprints_device_created",
            "reason": "디바이스 이력 조회 최적화",
        },
        {
            "table": "behavior_patterns",
            "columns": ["user_id", "created_at"],
            "name": "idx_behavior_patterns_user_created",
            "reason": "사용자 행동 패턴 분석 최적화",
        },
        {
            "table": "network_analyses",
            "columns": ["ip_address", "created_at"],
            "name": "idx_network_analyses_ip_created",
            "reason": "IP 분석 이력 조회 최적화",
        },
        {
            "table": "fraud_rules",
            "columns": ["category", "is_active"],
            "name": "idx_fraud_rules_category_active",
            "reason": "활성화된 룰 조회 최적화",
        },
        {
            "table": "rule_executions",
            "columns": ["transaction_id", "created_at"],
            "name": "idx_rule_executions_tx_created",
            "reason": "거래별 룰 실행 이력 조회 최적화",
        },
        {
            "table": "blacklist_entries",
            "columns": ["entry_type", "value"],
            "name": "idx_blacklist_type_value",
            "reason": "블랙리스트 조회 최적화",
        },
    ]

    @staticmethod
    def get_connection_pool_config() -> Dict[str, Any]:
        """
        권장 연결 풀 설정 반환

        Returns:
            Dict: SQLAlchemy 연결 풀 설정
        """
        return {
            "pool_size": 10,  # 기본 연결 수
            "max_overflow": 20,  # 추가 연결 수 (최대 30개 연결)
            "pool_timeout": 30,  # 연결 대기 타임아웃 (초)
            "pool_recycle": 3600,  # 연결 재사용 시간 (1시간)
            "pool_pre_ping": True,  # 연결 유효성 사전 확인
            "echo": False,  # SQL 로그 출력 (프로덕션에서는 False)
            "echo_pool": False,  # 연결 풀 로그 출력
        }

    @staticmethod
    async def check_indexes(db: AsyncSession) -> List[Dict[str, Any]]:
        """
        현재 인덱스 상태 확인 및 권장사항 제공

        Args:
            db: 데이터베이스 세션

        Returns:
            List[Dict]: 인덱스 상태 및 권장사항
        """
        results = []

        for index_config in DatabaseOptimizer.RECOMMENDED_INDEXES:
            table_name = index_config["table"]
            index_name = index_config["name"]

            try:
                # PostgreSQL 인덱스 존재 확인
                query = text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM pg_indexes
                        WHERE tablename = :table_name
                        AND indexname = :index_name
                    ) as exists
                    """
                )

                result = await db.execute(
                    query, {"table_name": table_name, "index_name": index_name}
                )
                exists = result.scalar()

                results.append(
                    {
                        "table": table_name,
                        "index_name": index_name,
                        "columns": index_config["columns"],
                        "exists": exists,
                        "reason": index_config["reason"],
                        "status": "OK" if exists else "MISSING",
                    }
                )

            except Exception as e:
                logger.error(
                    f"인덱스 확인 실패: table={table_name}, index={index_name}, error={e}"
                )
                results.append(
                    {
                        "table": table_name,
                        "index_name": index_name,
                        "columns": index_config["columns"],
                        "exists": False,
                        "reason": index_config["reason"],
                        "status": "ERROR",
                        "error": str(e),
                    }
                )

        return results

    @staticmethod
    async def create_missing_indexes(db: AsyncSession) -> List[str]:
        """
        누락된 인덱스 생성

        Args:
            db: 데이터베이스 세션

        Returns:
            List[str]: 생성된 인덱스 이름 목록
        """
        created_indexes = []

        for index_config in DatabaseOptimizer.RECOMMENDED_INDEXES:
            table_name = index_config["table"]
            index_name = index_config["name"]
            columns = index_config["columns"]

            try:
                # 인덱스 존재 확인
                check_query = text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM pg_indexes
                        WHERE tablename = :table_name
                        AND indexname = :index_name
                    ) as exists
                    """
                )

                result = await db.execute(
                    check_query, {"table_name": table_name, "index_name": index_name}
                )
                exists = result.scalar()

                if not exists:
                    # 인덱스 생성
                    columns_str = ", ".join(columns)
                    create_query = text(
                        f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} "
                        f"ON {table_name} ({columns_str})"
                    )

                    await db.execute(create_query)
                    await db.commit()

                    created_indexes.append(index_name)
                    logger.info(
                        f"[INDEX CREATED] {index_name} on {table_name}({columns_str})"
                    )

            except Exception as e:
                logger.error(
                    f"인덱스 생성 실패: table={table_name}, index={index_name}, error={e}"
                )
                await db.rollback()

        return created_indexes

    @staticmethod
    async def analyze_table_stats(db: AsyncSession, table_name: str) -> Dict[str, Any]:
        """
        테이블 통계 분석

        Args:
            db: 데이터베이스 세션
            table_name: 테이블 이름

        Returns:
            Dict: 테이블 통계 (행 수, 크기, 인덱스 수 등)
        """
        try:
            # 테이블 행 수
            count_query = text(f"SELECT COUNT(*) FROM {table_name}")
            count_result = await db.execute(count_query)
            row_count = count_result.scalar()

            # 테이블 크기
            size_query = text(
                """
                SELECT
                    pg_size_pretty(pg_total_relation_size(:table_name)) as total_size,
                    pg_size_pretty(pg_relation_size(:table_name)) as table_size,
                    pg_size_pretty(pg_indexes_size(:table_name)) as indexes_size
                """
            )
            size_result = await db.execute(size_query, {"table_name": table_name})
            size_row = size_result.fetchone()

            # 인덱스 목록
            indexes_query = text(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = :table_name
                """
            )
            indexes_result = await db.execute(indexes_query, {"table_name": table_name})
            indexes = [
                {"name": row[0], "definition": row[1]}
                for row in indexes_result.fetchall()
            ]

            return {
                "table_name": table_name,
                "row_count": row_count,
                "total_size": size_row[0] if size_row else "N/A",
                "table_size": size_row[1] if size_row else "N/A",
                "indexes_size": size_row[2] if size_row else "N/A",
                "indexes": indexes,
                "index_count": len(indexes),
            }

        except Exception as e:
            logger.error(f"테이블 통계 분석 실패: table={table_name}, error={e}")
            return {
                "table_name": table_name,
                "error": str(e),
            }

    @staticmethod
    async def vacuum_analyze(db: AsyncSession, table_name: str):
        """
        VACUUM ANALYZE 실행 (테이블 통계 갱신)

        Args:
            db: 데이터베이스 세션
            table_name: 테이블 이름
        """
        try:
            query = text(f"VACUUM ANALYZE {table_name}")
            await db.execute(query)
            logger.info(f"[VACUUM ANALYZE] {table_name} completed")

        except Exception as e:
            logger.error(f"VACUUM ANALYZE 실패: table={table_name}, error={e}")


class QueryPerformanceTracker:
    """
    쿼리 성능 추적기

    느린 쿼리를 자동으로 감지하고 로깅합니다.
    """

    def __init__(self, slow_query_threshold_ms: int = 100):
        """
        Args:
            slow_query_threshold_ms: 느린 쿼리 임계값 (밀리초)
        """
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.slow_queries: List[Dict[str, Any]] = []

    def track_query(self, query_name: str, duration_ms: int, result_count: int = 0):
        """
        쿼리 성능 추적

        Args:
            query_name: 쿼리 이름
            duration_ms: 실행 시간 (밀리초)
            result_count: 결과 행 수
        """
        if duration_ms > self.slow_query_threshold_ms:
            slow_query = {
                "query_name": query_name,
                "duration_ms": duration_ms,
                "result_count": result_count,
                "timestamp": None,  # 실제로는 datetime.now() 사용
            }

            self.slow_queries.append(slow_query)
            logger.warning(
                f"[SLOW QUERY] {query_name} took {duration_ms}ms "
                f"(threshold: {self.slow_query_threshold_ms}ms), "
                f"result_count={result_count}"
            )

            # 최근 100개만 유지
            if len(self.slow_queries) > 100:
                self.slow_queries.pop(0)

    def get_slow_queries(self) -> List[Dict[str, Any]]:
        """
        느린 쿼리 목록 조회

        Returns:
            List[Dict]: 느린 쿼리 목록
        """
        return self.slow_queries

    def reset(self):
        """느린 쿼리 기록 초기화"""
        self.slow_queries = []


# 전역 쿼리 성능 추적기 인스턴스
query_performance_tracker = QueryPerformanceTracker()
