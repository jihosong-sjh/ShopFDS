"""add products images column

Revision ID: ed2f98b46da4
Revises: 1f146947015c
Create Date: 2025-11-19 13:18:57.926428+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed2f98b46da4'
down_revision: Union[str, None] = '1f146947015c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """마이그레이션 적용 (업그레이드)"""
    # Products 테이블에 images JSONB 컬럼 추가
    op.add_column('products', sa.Column('images', sa.JSON(), nullable=False, server_default='[]'))

    # 기존 image_url 데이터를 images 배열로 마이그레이션
    op.execute("""
        UPDATE products
        SET images = jsonb_build_array(image_url)
        WHERE image_url IS NOT NULL
    """)


def downgrade() -> None:
    """마이그레이션 되돌리기 (다운그레이드)"""
    op.drop_column('products', 'images')
