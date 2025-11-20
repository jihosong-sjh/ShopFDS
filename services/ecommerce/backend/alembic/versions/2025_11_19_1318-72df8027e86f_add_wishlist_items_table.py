"""add wishlist_items table

Revision ID: 72df8027e86f
Revises: 8995e589d77b
Create Date: 2025-11-19 13:18:06.639532+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72df8027e86f'
down_revision: Union[str, None] = '8995e589d77b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """마이그레이션 적용 (업그레이드)"""
    # WishlistItems 테이블 생성
    op.create_table(
        'wishlist_items',
        sa.Column('id', sa.Uuid, primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Uuid, nullable=False),
        sa.Column('product_id', sa.Uuid, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'product_id', name='uq_wishlist_user_product'),
    )

    # 인덱스 생성
    op.create_index('idx_wishlist_user', 'wishlist_items', ['user_id', sa.text('created_at DESC')])
    op.create_index('idx_wishlist_product', 'wishlist_items', ['product_id'])


def downgrade() -> None:
    """마이그레이션 되돌리기 (다운그레이드)"""
    op.drop_index('idx_wishlist_product', table_name='wishlist_items')
    op.drop_index('idx_wishlist_user', table_name='wishlist_items')
    op.drop_table('wishlist_items')
