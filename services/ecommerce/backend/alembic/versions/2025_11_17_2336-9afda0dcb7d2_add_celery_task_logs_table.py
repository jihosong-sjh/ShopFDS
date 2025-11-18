"""add celery_task_logs table

Revision ID: 9afda0dcb7d2
Revises: 3ca4184dbe46
Create Date: 2025-11-17 23:36:26.429479+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9afda0dcb7d2'
down_revision: Union[str, None] = '3ca4184dbe46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """마이그레이션 적용 (업그레이드)"""
    # TaskStatus Enum 타입 생성
    task_status_enum = postgresql.ENUM(
        'pending', 'started', 'success', 'failure', 'retry',
        name='task_status',
        create_type=True
    )
    task_status_enum.create(op.get_bind(), checkfirst=True)

    # celery_task_logs 테이블 생성
    op.create_table(
        'celery_task_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('task_name', sa.String(255), nullable=False, index=True),
        sa.Column('status', task_status_enum, nullable=False, index=True),
        sa.Column('queued_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('traceback', sa.Text(), nullable=True),
        sa.Column('retries', sa.Integer(), nullable=False, default=0),
        sa.Column('max_retries', sa.Integer(), nullable=False, default=3),
        sa.Column('args', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('kwargs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('queue_name', sa.String(100), nullable=True, index=True),
        sa.Column('worker_name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 인덱스 생성 (성능 최적화)
    op.create_index('idx_task_logs_task_id', 'celery_task_logs', ['task_id'])
    op.create_index('idx_task_logs_task_name', 'celery_task_logs', ['task_name'])
    op.create_index('idx_task_logs_status', 'celery_task_logs', ['status'])
    op.create_index('idx_task_logs_queue_name', 'celery_task_logs', ['queue_name'])
    op.create_index('idx_task_logs_created_at', 'celery_task_logs', ['created_at'])


def downgrade() -> None:
    """마이그레이션 되돌리기 (다운그레이드)"""
    # 인덱스 삭제
    op.drop_index('idx_task_logs_created_at', table_name='celery_task_logs')
    op.drop_index('idx_task_logs_queue_name', table_name='celery_task_logs')
    op.drop_index('idx_task_logs_status', table_name='celery_task_logs')
    op.drop_index('idx_task_logs_task_name', table_name='celery_task_logs')
    op.drop_index('idx_task_logs_task_id', table_name='celery_task_logs')

    # 테이블 삭제
    op.drop_table('celery_task_logs')

    # Enum 타입 삭제
    task_status_enum = postgresql.ENUM(
        'pending', 'started', 'success', 'failure', 'retry',
        name='task_status'
    )
    task_status_enum.drop(op.get_bind(), checkfirst=True)
