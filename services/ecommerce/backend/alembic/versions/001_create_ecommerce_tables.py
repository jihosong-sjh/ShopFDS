"""Create ecommerce tables for User Story 1

Revision ID: 001
Revises:
Create Date: 2025-11-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 열거형 타입 생성
    user_role_enum = postgresql.ENUM('customer', 'admin', 'security_team', name='user_role_enum', create_type=True)
    user_status_enum = postgresql.ENUM('active', 'suspended', 'deleted', name='user_status_enum', create_type=True)
    product_status_enum = postgresql.ENUM('available', 'out_of_stock', 'discontinued', name='product_status_enum', create_type=True)
    order_status_enum = postgresql.ENUM('pending', 'paid', 'preparing', 'shipped', 'delivered', 'cancelled', 'refunded', name='order_status_enum', create_type=True)
    payment_method_enum = postgresql.ENUM('credit_card', name='payment_method_enum', create_type=True)
    payment_status_enum = postgresql.ENUM('pending', 'completed', 'failed', 'refunded', name='payment_status_enum', create_type=True)

    user_role_enum.create(op.get_bind(), checkfirst=True)
    user_status_enum.create(op.get_bind(), checkfirst=True)
    product_status_enum.create(op.get_bind(), checkfirst=True)
    order_status_enum.create(op.get_bind(), checkfirst=True)
    payment_method_enum.create(op.get_bind(), checkfirst=True)
    payment_status_enum.create(op.get_bind(), checkfirst=True)

    # Users 테이블
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('role', user_role_enum, nullable=False, server_default='customer'),
        sa.Column('status', user_status_enum, nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_status', 'users', ['status'])
    op.create_index('ix_users_id', 'users', ['id'])

    # Products 테이블
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('stock_quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('status', product_status_enum, nullable=False, server_default='available'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('price >= 0', name='check_price_non_negative'),
        sa.CheckConstraint('stock_quantity >= 0', name='check_stock_non_negative'),
    )
    op.create_index('idx_products_category', 'products', ['category'])
    op.create_index('idx_products_status', 'products', ['status'])

    # Carts 테이블
    op.create_table(
        'carts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', name='uq_carts_user_id'),
    )

    # Cart Items 테이블
    op.create_table(
        'cart_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('cart_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('added_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('quantity > 0', name='check_cart_quantity_positive'),
        sa.ForeignKeyConstraint(['cart_id'], ['carts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('cart_id', 'product_id', name='uq_cart_product'),
    )

    # Orders 테이블
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('order_number', sa.String(20), unique=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('total_amount', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('status', order_status_enum, nullable=False, server_default='pending'),
        sa.Column('shipping_name', sa.String(100), nullable=False),
        sa.Column('shipping_address', sa.Text(), nullable=False),
        sa.Column('shipping_phone', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('shipped_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('total_amount > 0', name='check_total_amount_positive'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_orders_user_id', 'orders', ['user_id'])
    op.create_index('idx_orders_status', 'orders', ['status'])
    op.create_index('idx_orders_created_at', 'orders', ['created_at'])
    op.create_index('idx_orders_order_number', 'orders', ['order_number'])

    # Order Items 테이블
    op.create_table(
        'order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.DECIMAL(10, 2), nullable=False),
        sa.CheckConstraint('quantity > 0', name='check_order_item_quantity_positive'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
    )
    op.create_index('idx_order_items_order_id', 'order_items', ['order_id'])

    # Payments 테이블
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column('payment_method', payment_method_enum, nullable=False, server_default='credit_card'),
        sa.Column('amount', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('status', payment_status_enum, nullable=False, server_default='pending'),
        sa.Column('card_token', sa.String(255), nullable=False),
        sa.Column('card_last_four', sa.String(4), nullable=False),
        sa.Column('transaction_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('failed_reason', sa.Text(), nullable=True),
        sa.CheckConstraint('amount >= 0', name='check_payment_amount_non_negative'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
    )


def downgrade() -> None:
    # 테이블 삭제 (역순)
    op.drop_table('payments')
    op.drop_table('order_items')
    op.drop_index('idx_orders_order_number', 'orders')
    op.drop_index('idx_orders_created_at', 'orders')
    op.drop_index('idx_orders_status', 'orders')
    op.drop_index('idx_orders_user_id', 'orders')
    op.drop_table('orders')
    op.drop_table('cart_items')
    op.drop_table('carts')
    op.drop_index('idx_products_status', 'products')
    op.drop_index('idx_products_category', 'products')
    op.drop_table('products')
    op.drop_index('ix_users_id', 'users')
    op.drop_index('idx_users_status', 'users')
    op.drop_index('idx_users_email', 'users')
    op.drop_table('users')

    # 열거형 타입 삭제
    sa.Enum(name='payment_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='payment_method_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='order_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='product_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='user_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='user_role_enum').drop(op.get_bind(), checkfirst=True)
