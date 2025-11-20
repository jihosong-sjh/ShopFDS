"""add user_coupons table

Revision ID: f70d71c447e0
Revises: 5e50b7ae3eb7
Create Date: 2025-11-19 13:18:29.909379+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f70d71c447e0'
down_revision: Union[str, None] = '5e50b7ae3eb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """마이그레이션 적용 (업그레이드)"""
    # UserCoupons 테이블 생성
    op.create_table(
        'user_coupons',
        sa.Column('id', sa.Uuid, primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Uuid, nullable=False),
        sa.Column('coupon_id', sa.Uuid, nullable=False),
        sa.Column('order_id', sa.Uuid, nullable=True),
        sa.Column('issued_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['coupon_id'], ['coupons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.CheckConstraint('used_at IS NULL OR used_at >= issued_at', name='check_used_at_after_issued'),
    )

    # 인덱스 생성
    op.create_index('idx_user_coupons_user', 'user_coupons', ['user_id', 'used_at'])
    op.create_index('idx_user_coupons_coupon', 'user_coupons', ['coupon_id'])
    op.create_index('idx_user_coupons_order', 'user_coupons', ['order_id'],
                    unique=True, postgresql_where=sa.text('order_id IS NOT NULL'))


def downgrade() -> None:
    """마이그레이션 되돌리기 (다운그레이드)"""
    op.drop_index('idx_user_coupons_order', table_name='user_coupons')
    op.drop_index('idx_user_coupons_coupon', table_name='user_coupons')
    op.drop_index('idx_user_coupons_user', table_name='user_coupons')
    op.drop_table('user_coupons')
