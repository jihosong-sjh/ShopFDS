"""add oauth_accounts table

Revision ID: 6ecf0d244e41
Revises: f70d71c447e0
Create Date: 2025-11-19 13:18:37.099893+09:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ecf0d244e41'
down_revision: Union[str, None] = 'f70d71c447e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """마이그레이션 적용 (업그레이드)"""
    # OAuthAccounts 테이블 생성
    op.create_table(
        'oauth_accounts',
        sa.Column('id', sa.Uuid, primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.Uuid, nullable=False),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('provider_user_id', sa.String(200), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('profile_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.CheckConstraint("provider IN ('GOOGLE', 'KAKAO', 'NAVER')", name='check_oauth_provider'),
        sa.UniqueConstraint('provider', 'provider_user_id', name='uq_oauth_provider_user'),
    )

    # 인덱스 생성
    op.create_index('idx_oauth_accounts_user', 'oauth_accounts', ['user_id'])
    op.create_index('idx_oauth_accounts_provider', 'oauth_accounts', ['provider', 'provider_user_id'])


def downgrade() -> None:
    """마이그레이션 되돌리기 (다운그레이드)"""
    op.drop_index('idx_oauth_accounts_provider', table_name='oauth_accounts')
    op.drop_index('idx_oauth_accounts_user', table_name='oauth_accounts')
    op.drop_table('oauth_accounts')
