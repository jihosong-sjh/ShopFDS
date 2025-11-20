"""add coupons table

Revision ID: 5e50b7ae3eb7
Revises: cbe62e0e0418
Create Date: 2025-11-19 13:18:22.240794+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e50b7ae3eb7'
down_revision: Union[str, None] = 'cbe62e0e0418'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """마이그레이션 적용 (업그레이드)"""
    # Coupons 테이블 생성
    op.create_table(
        'coupons',
        sa.Column('id', sa.Uuid, primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('coupon_code', sa.String(50), nullable=False, unique=True),
        sa.Column('coupon_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('discount_type', sa.String(20), nullable=False),
        sa.Column('discount_value', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('max_discount_amount', sa.DECIMAL(10, 2), nullable=True),
        sa.Column('min_purchase_amount', sa.DECIMAL(10, 2), nullable=False, server_default='0'),
        sa.Column('valid_from', sa.DateTime(), nullable=False),
        sa.Column('valid_until', sa.DateTime(), nullable=False),
        sa.Column('max_usage_count', sa.Integer(), nullable=True),
        sa.Column('max_usage_per_user', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('current_usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('discount_value > 0', name='check_discount_value_positive'),
        sa.CheckConstraint('valid_until > valid_from', name='check_valid_date_range'),
        sa.CheckConstraint("discount_type IN ('FIXED', 'PERCENT')", name='check_discount_type'),
    )

    # 인덱스 생성
    op.create_index('idx_coupons_code', 'coupons', ['coupon_code'],
                    postgresql_where=sa.text('is_active = true'))
    op.create_index('idx_coupons_valid', 'coupons', ['valid_from', 'valid_until'],
                    postgresql_where=sa.text('is_active = true'))


def downgrade() -> None:
    """마이그레이션 되돌리기 (다운그레이드)"""
    op.drop_index('idx_coupons_valid', table_name='coupons')
    op.drop_index('idx_coupons_code', table_name='coupons')
    op.drop_table('coupons')
