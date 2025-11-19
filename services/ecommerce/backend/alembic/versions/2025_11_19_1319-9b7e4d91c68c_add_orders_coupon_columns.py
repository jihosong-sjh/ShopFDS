"""add orders coupon columns

Revision ID: 9b7e4d91c68c
Revises: ed2f98b46da4
Create Date: 2025-11-19 13:19:04.927344+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b7e4d91c68c'
down_revision: Union[str, None] = 'ed2f98b46da4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """마이그레이션 적용 (업그레이드)"""
    # Orders 테이블에 coupon_id, discount_amount 컬럼 추가
    op.add_column('orders', sa.Column('coupon_id', sa.Uuid, nullable=True))
    op.add_column('orders', sa.Column('discount_amount', sa.DECIMAL(10, 2), nullable=False, server_default='0'))

    # Foreign Key 제약 추가
    op.create_foreign_key('fk_orders_coupon_id', 'orders', 'coupons', ['coupon_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """마이그레이션 되돌리기 (다운그레이드)"""
    op.drop_constraint('fk_orders_coupon_id', 'orders', type_='foreignkey')
    op.drop_column('orders', 'discount_amount')
    op.drop_column('orders', 'coupon_id')
