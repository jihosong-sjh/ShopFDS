"""
데이터베이스 인덱스 전략 구현

이 모듈은 성능 최적화를 위한 인덱스 정의와 생성 유틸리티를 제공합니다.
data-model.md의 인덱스 섹션에 정의된 전략을 구현합니다.
"""

from sqlalchemy import Index, text
from sqlalchemy.ext.asyncio import AsyncSession


# 인덱스 명명 규칙
# - 단일 컬럼: idx_{table_name}_{column_name}
# - 복합 컬럼: idx_{table_name}_{column1}_{column2}
# - 부분 인덱스: idx_{table_name}_{column}_partial
# - 전문 검색: idx_{table_name}_{column}_fulltext


class IndexManager:
    """
    데이터베이스 인덱스 관리 클래스

    인덱스 생성, 삭제, 최적화를 담당합니다.
    """

    @staticmethod
    def create_user_indexes():
        """
        User 테이블 인덱스

        - 이메일 조회 (로그인)
        - 계정 상태 필터링
        - 역할 기반 조회
        """
        return [
            # 이메일은 UNIQUE 제약으로 자동 인덱스 생성되므로 별도 불필요
            Index("idx_users_status", "status"),
            Index("idx_users_role", "role"),
            Index("idx_users_last_login", "last_login_at"),  # 최근 활동 사용자 조회
        ]

    @staticmethod
    def create_product_indexes():
        """
        Product 테이블 인덱스

        - 카테고리별 상품 목록
        - 상품 상태 필터링 (available, out_of_stock)
        - 가격 범위 검색
        """
        return [
            Index("idx_products_category", "category"),
            Index("idx_products_status", "status"),
            Index("idx_products_price", "price"),  # 가격 정렬용
            # 복합 인덱스: 카테고리 + 상태 (자주 함께 필터링)
            Index("idx_products_category_status", "category", "status"),
            # 전문 검색 인덱스 (PostgreSQL GIN)
            # Index("idx_products_name_fulltext", text("to_tsvector('korean', name)"), postgresql_using="gin"),
        ]

    @staticmethod
    def create_order_indexes():
        """
        Order 테이블 인덱스

        - 사용자별 주문 내역
        - 주문 상태별 조회
        - 주문 생성일 기준 정렬
        """
        return [
            Index("idx_orders_user_id", "user_id"),
            Index("idx_orders_status", "status"),
            Index("idx_orders_created_at", "created_at", postgresql_using="btree"),
            # 복합 인덱스: 사용자 + 생성일 (내 주문 내역 조회 최적화)
            Index("idx_orders_user_created", "user_id", "created_at"),
            # 주문 번호는 UNIQUE 제약으로 자동 인덱스
        ]

    @staticmethod
    def create_transaction_indexes():
        """
        Transaction 테이블 인덱스 (FDS)

        - 사용자별 거래 내역
        - IP 주소 기반 조회
        - 위험 수준별 필터링
        - 시계열 조회
        """
        return [
            Index("idx_transactions_user_id", "user_id"),
            Index("idx_transactions_ip_address", "ip_address", postgresql_using="hash"),
            Index("idx_transactions_risk_level", "risk_level"),
            Index("idx_transactions_created_at", "created_at", postgresql_using="brin"),  # 시계열 데이터에 최적
            # 복합 인덱스: 사용자 + 생성일 (사용자 거래 패턴 분석)
            Index("idx_transactions_user_created", "user_id", "created_at"),
            # GiST 인덱스: IP 주소 범위 검색 (선택 사항)
            # Index("idx_transactions_ip_gist", "ip_address", postgresql_using="gist"),
        ]

    @staticmethod
    def create_risk_factor_indexes():
        """
        RiskFactor 테이블 인덱스

        - 거래별 위험 요인 조회
        - 요인 유형별 집계
        """
        return [
            Index("idx_risk_factors_transaction_id", "transaction_id"),
            Index("idx_risk_factors_factor_type", "factor_type"),
            # 복합 인덱스: 거래 + 요인 유형
            Index("idx_risk_factors_trans_type", "transaction_id", "factor_type"),
        ]

    @staticmethod
    def create_threat_intelligence_indexes():
        """
        ThreatIntelligence 테이블 인덱스

        - 위협 유형 + 값 조합 조회 (UNIQUE + HASH)
        - 만료일 기준 정리
        """
        return [
            # UNIQUE 제약으로 자동 인덱스 생성: (threat_type, value)
            Index(
                "idx_threat_intel_type_value",
                "threat_type",
                "value",
                unique=True,
                postgresql_using="hash",  # O(1) 조회
            ),
            Index("idx_threat_intel_expires_at", "expires_at"),  # 만료 항목 배치 삭제용
            Index("idx_threat_intel_active", "is_active"),
        ]

    @staticmethod
    def create_user_behavior_log_indexes():
        """
        UserBehaviorLog 테이블 인덱스 (TimescaleDB 하이퍼테이블)

        - 사용자별 행동 시계열
        - 액션 유형별 집계
        - 세션별 행동 추적
        """
        return [
            # 복합 인덱스: 사용자 + 시간 (시계열 조회 최적화)
            Index(
                "idx_user_behavior_user_time",
                "user_id",
                "action_timestamp",
                postgresql_using="btree",
            ),
            Index("idx_user_behavior_session", "session_id"),
            Index("idx_user_behavior_action_type", "action_type"),
        ]

    @staticmethod
    def create_review_queue_indexes():
        """
        ReviewQueue 테이블 인덱스

        - 검토 상태별 필터링
        - 담당자별 할당
        - 추가일 기준 정렬
        """
        return [
            Index("idx_review_queue_status", "status"),
            Index("idx_review_queue_assigned_to", "assigned_to"),
            Index("idx_review_queue_added_at", "added_at"),
            # 복합 인덱스: 상태 + 추가일 (대기 중인 항목 우선순위)
            Index("idx_review_queue_status_added", "status", "added_at"),
        ]


async def create_custom_indexes(session: AsyncSession) -> None:
    """
    커스텀 인덱스 생성 (SQL 직접 실행)

    Alembic 마이그레이션에서 처리하기 어려운 고급 인덱스를 생성합니다.

    Args:
        session: 비동기 데이터베이스 세션
    """
    # PostgreSQL 전문 검색 인덱스 (한국어 지원)
    await session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_products_name_fulltext
            ON products USING gin(to_tsvector('korean', name))
            """
        )
    )

    # JSONB 인덱스 (geolocation 검색)
    await session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_transactions_geolocation
            ON transactions USING gin(geolocation)
            """
        )
    )

    # 부분 인덱스 (활성 사용자만)
    await session.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS idx_users_active_email
            ON users(email)
            WHERE status = 'active'
            """
        )
    )

    await session.commit()


async def analyze_table_statistics(session: AsyncSession, table_name: str) -> None:
    """
    테이블 통계 업데이트 (쿼리 플래너 최적화)

    PostgreSQL의 ANALYZE 명령을 실행하여 테이블 통계를 갱신합니다.
    대량 데이터 삽입 후 실행하면 쿼리 성능이 향상됩니다.

    Args:
        session: 비동기 데이터베이스 세션
        table_name: 분석할 테이블 이름
    """
    await session.execute(text(f"ANALYZE {table_name}"))
    await session.commit()


async def get_index_usage_stats(session: AsyncSession) -> list:
    """
    인덱스 사용 통계 조회

    사용되지 않는 인덱스를 찾아 삭제할 수 있습니다.

    Returns:
        list: 인덱스별 사용 통계
    """
    result = await session.execute(
        text(
            """
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan AS index_scans,
                idx_tup_read AS tuples_read,
                idx_tup_fetch AS tuples_fetched
            FROM pg_stat_user_indexes
            ORDER BY idx_scan ASC
            """
        )
    )
    return result.fetchall()


async def get_missing_indexes(session: AsyncSession) -> list:
    """
    누락된 인덱스 제안

    자주 스캔되지만 인덱스가 없는 컬럼을 찾습니다.

    Returns:
        list: 인덱스 생성 제안
    """
    result = await session.execute(
        text(
            """
            SELECT
                schemaname,
                tablename,
                attname AS column_name,
                n_distinct AS distinct_values,
                correlation
            FROM pg_stats
            WHERE schemaname = 'public'
              AND n_distinct > 100
              AND correlation < 0.5
            ORDER BY n_distinct DESC
            """
        )
    )
    return result.fetchall()
