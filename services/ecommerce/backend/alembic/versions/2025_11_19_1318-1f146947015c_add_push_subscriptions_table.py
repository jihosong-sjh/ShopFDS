"""add push_subscriptions table

Revision ID: 1f146947015c
Revises: 6ecf0d244e41
Create Date: 2025-11-19 13:18:50.590957+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f146947015c'
down_revision: Union[str, None] = '6ecf0d244e41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """마이그레이션 적용 (업그레이드)"""
    # PushSubscriptions 테이블 생성
    op.create_table(
        'push_subscriptions',
        sa.Column('id', sa.Uuid, primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Uuid, nullable=False),
        sa.Column('fcm_token', sa.Text(), nullable=False, unique=True),
        sa.Column('device_type', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_used_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # 인덱스 생성
    op.create_index('idx_push_subscriptions_user', 'push_subscriptions', ['user_id'])
    op.create_index('idx_push_subscriptions_token', 'push_subscriptions', ['fcm_token'])


def downgrade() -> None:
    """마이그레이션 되돌리기 (다운그레이드)"""
    op.drop_index('idx_push_subscriptions_token', table_name='push_subscriptions')
    op.drop_index('idx_push_subscriptions_user', table_name='push_subscriptions')
    op.drop_table('push_subscriptions')
