"""add review_votes table

Revision ID: 8995e589d77b
Revises: 37f67bb764e8
Create Date: 2025-11-19 13:17:35.455919+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8995e589d77b'
down_revision: Union[str, None] = '37f67bb764e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """마이그레이션 적용 (업그레이드)"""
    # ReviewVotes 테이블 생성
    op.create_table(
        'review_votes',
        sa.Column('review_id', sa.Uuid, nullable=False),
        sa.Column('user_id', sa.Uuid, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('review_id', 'user_id'),
    )

    # 인덱스 생성
    op.create_index('idx_review_votes_user', 'review_votes', ['user_id'])


def downgrade() -> None:
    """마이그레이션 되돌리기 (다운그레이드)"""
    op.drop_index('idx_review_votes_user', table_name='review_votes')
    op.drop_table('review_votes')
