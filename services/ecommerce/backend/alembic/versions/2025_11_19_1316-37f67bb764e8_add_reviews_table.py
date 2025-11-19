"""add reviews table

Revision ID: 37f67bb764e8
Revises: 003_advanced_fds
Create Date: 2025-11-19 13:16:21.015154+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37f67bb764e8'
down_revision: Union[str, None] = '003_advanced_fds'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """마이그레이션 적용 (업그레이드)"""
    # Reviews 테이블 생성
    op.create_table(
        'reviews',
        sa.Column('id', sa.Uuid, primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Uuid, nullable=False),
        sa.Column('product_id', sa.Uuid, nullable=False),
        sa.Column('order_id', sa.Uuid, nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('images', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('helpful_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_verified_purchase', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_flagged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('flagged_reason', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
        sa.CheckConstraint('LENGTH(content) >= 10', name='check_content_min_length'),
        sa.CheckConstraint('helpful_count >= 0', name='check_helpful_count_non_negative'),
        sa.UniqueConstraint('user_id', 'product_id', name='uq_review_user_product'),
    )

    # 인덱스 생성
    op.create_index('idx_reviews_product_created', 'reviews', ['product_id', sa.text('created_at DESC')])
    op.create_index('idx_reviews_product_rating', 'reviews', ['product_id', sa.text('rating DESC')])
    op.create_index('idx_reviews_product_helpful', 'reviews', ['product_id', sa.text('helpful_count DESC')])
    op.create_index('idx_reviews_user', 'reviews', ['user_id'])
    op.create_index('idx_reviews_flagged', 'reviews', ['is_flagged'], postgresql_where=sa.text('is_flagged = true'))


def downgrade() -> None:
    """마이그레이션 되돌리기 (다운그레이드)"""
    op.drop_index('idx_reviews_flagged', table_name='reviews')
    op.drop_index('idx_reviews_user', table_name='reviews')
    op.drop_index('idx_reviews_product_helpful', table_name='reviews')
    op.drop_index('idx_reviews_product_rating', table_name='reviews')
    op.drop_index('idx_reviews_product_created', table_name='reviews')
    op.drop_table('reviews')
