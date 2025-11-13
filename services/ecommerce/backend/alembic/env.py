"""
Alembic 마이그레이션 환경 설정

이 파일은 Alembic이 데이터베이스 마이그레이션을 실행할 때 사용하는 환경을 구성합니다.
비동기 SQLAlchemy를 지원하며, 모든 모델을 자동으로 감지합니다.
"""

import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import os
import sys

# 프로젝트 루트를 sys.path에 추가하여 모델 import 가능하게 함
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Alembic Config 객체 - alembic.ini 파일의 값에 접근
config = context.config

# Python 로깅 설정 (alembic.ini의 [loggers] 섹션 사용)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy 모델의 MetaData 객체 (자동 마이그레이션 감지용)
# 여기서 모든 모델을 import하여 Alembic이 스키마 변경을 감지할 수 있도록 합니다
try:
    from src.models.base import Base
    # 향후 모델이 추가되면 여기서 import하여 자동 감지되도록 합니다
    # from src.models.user import User
    # from src.models.product import Product
    # from src.models.order import Order
    # ...
    target_metadata = Base.metadata
except ImportError:
    # 모델이 아직 생성되지 않은 경우
    target_metadata = None


def get_url():
    """
    환경 변수에서 데이터베이스 URL 가져오기

    우선순위:
    1. DATABASE_URL 환경 변수
    2. alembic.ini 파일의 sqlalchemy.url
    """
    from dotenv import load_dotenv
    load_dotenv()

    return os.getenv(
        "DATABASE_URL",
        config.get_main_option("sqlalchemy.url")
    )


def run_migrations_offline() -> None:
    """
    'offline' 모드로 마이그레이션 실행

    데이터베이스 연결 없이 SQL 스크립트만 생성합니다.
    실제 데이터베이스에 적용하려면 생성된 SQL을 수동으로 실행해야 합니다.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # 컬럼 타입 변경 감지
        compare_server_default=True,  # 기본값 변경 감지
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """실제 마이그레이션 실행 로직"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """비동기 SQLAlchemy 엔진을 사용한 마이그레이션 실행"""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    # 비동기 엔진 생성
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # 마이그레이션 시에는 연결 풀 사용 안 함
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    'online' 모드로 마이그레이션 실행

    실제 데이터베이스에 연결하여 마이그레이션을 직접 적용합니다.
    비동기 SQLAlchemy를 사용합니다.
    """
    asyncio.run(run_async_migrations())


# Alembic 컨텍스트 모드 결정
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
