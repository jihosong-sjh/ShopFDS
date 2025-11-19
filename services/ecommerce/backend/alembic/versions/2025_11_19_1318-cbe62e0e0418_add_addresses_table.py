"""add addresses table

Revision ID: cbe62e0e0418
Revises: 72df8027e86f
Create Date: 2025-11-19 13:18:13.936205+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cbe62e0e0418'
down_revision: Union[str, None] = '72df8027e86f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """마이그레이션 적용 (업그레이드)"""
    # Addresses 테이블 생성
    op.create_table(
        'addresses',
        sa.Column('id', sa.Uuid, primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Uuid, nullable=False),
        sa.Column('address_name', sa.String(100), nullable=False),
        sa.Column('recipient_name', sa.String(100), nullable=False),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('zipcode', sa.String(10), nullable=False),
        sa.Column('address', sa.String(500), nullable=False),
        sa.Column('address_detail', sa.String(500), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # 인덱스 생성
    op.create_index('idx_addresses_user', 'addresses', ['user_id', sa.text('is_default DESC'), sa.text('created_at DESC')])

    # Partial Unique Index: 사용자당 하나의 기본 배송지만 허용
    op.create_index('idx_addresses_user_default', 'addresses', ['user_id'],
                    unique=True, postgresql_where=sa.text('is_default = true'))


def downgrade() -> None:
    """마이그레이션 되돌리기 (다운그레이드)"""
    op.drop_index('idx_addresses_user_default', table_name='addresses')
    op.drop_index('idx_addresses_user', table_name='addresses')
    op.drop_table('addresses')
