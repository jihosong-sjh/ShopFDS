#!/usr/bin/env python3
"""
seed-data.py - Generate seed data for development environment
Usage: python seed-data.py [--append] [--users N] [--orders N] [--products N] [--reviews N]

Windows compatibility: ASCII characters only, no emojis
"""

import sys
import os
import random
import argparse
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Database imports
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

# Model imports
from services.ecommerce.backend.src.models.user import User, UserRole, UserStatus
from services.ecommerce.backend.src.models.product import Product, ProductStatus
from services.ecommerce.backend.src.models.order import Order, OrderItem, OrderStatus
from services.ecommerce.backend.src.models.payment import Payment, PaymentMethod, PaymentStatus

# Faker for realistic data
try:
    from faker import Faker
    fake = Faker(['ko_KR'])  # Korean locale for realistic Korean names/addresses
except ImportError:
    print("[ERROR] Faker library is required. Install with: pip install faker")
    sys.exit(1)

# Database connection
DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://shopfds_user:shopfds_password@localhost:5432/shopfds_db"
)


# Sample product categories and names
CATEGORIES = [
    "Electronics", "Fashion", "Home & Garden", "Sports & Outdoors",
    "Books & Media", "Toys & Games", "Health & Beauty", "Automotive"
]

PRODUCT_NAMES = {
    "Electronics": ["Laptop", "Smartphone", "Tablet", "Headphones", "Camera", "Smartwatch"],
    "Fashion": ["T-Shirt", "Jeans", "Dress", "Sneakers", "Jacket", "Handbag"],
    "Home & Garden": ["Sofa", "Table", "Lamp", "Plant Pot", "Bed Frame", "Rug"],
    "Sports & Outdoors": ["Yoga Mat", "Dumbbell Set", "Bicycle", "Tent", "Running Shoes", "Water Bottle"],
    "Books & Media": ["Novel", "Textbook", "Magazine", "DVD", "Board Game", "Puzzle"],
    "Toys & Games": ["Action Figure", "Doll", "LEGO Set", "Video Game", "RC Car", "Stuffed Animal"],
    "Health & Beauty": ["Face Cream", "Shampoo", "Vitamin", "Perfume", "Makeup Set", "Toothbrush"],
    "Automotive": ["Car Tire", "Motor Oil", "Car Vacuum", "Floor Mat", "Phone Mount", "Dash Cam"]
}


def create_database_session():
    """Create SQLAlchemy database session"""
    engine = create_engine(DB_URL, echo=False)
    Session = sessionmaker(bind=engine)
    return Session()


def check_existing_data(session):
    """Check if data already exists in database"""
    user_count = session.scalar(select(func.count()).select_from(User))
    product_count = session.scalar(select(func.count()).select_from(Product))
    order_count = session.scalar(select(func.count()).select_from(Order))

    return {
        "users": user_count or 0,
        "products": product_count or 0,
        "orders": order_count or 0,
    }


def generate_users(session, count=1000, append=False):
    """Generate user accounts"""
    print(f"[INFO] Generating {count} users...")

    if not append:
        # Delete existing users
        session.query(User).delete()
        session.commit()

    users = []

    # Create 1 admin user
    admin = User(
        id=uuid.uuid4(),
        email="admin@shopfds.com",
        password_hash="$2b$12$KIXm8uwvH8b7G.Hq/VqF4.N5B5v5h5H5H5H5H5H5H5H5H5H5H5H5H5",  # hashed "admin123"
        name="System Admin",
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
        created_at=datetime.utcnow() - timedelta(days=365),
    )
    users.append(admin)

    # Create regular customers
    for i in range(count - 1):
        user = User(
            id=uuid.uuid4(),
            email=fake.unique.email(),
            password_hash="$2b$12$KIXm8uwvH8b7G.Hq/VqF4.N5B5v5h5H5H5H5H5H5H5H5H5H5H5H5H5",  # hashed "password123"
            name=fake.name(),
            role=UserRole.CUSTOMER.value,
            status=random.choice([UserStatus.ACTIVE.value] * 95 + [UserStatus.SUSPENDED.value] * 5),  # 95% active
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 730)),  # Up to 2 years ago
        )
        users.append(user)

    session.bulk_save_objects(users)
    session.commit()

    print(f"[SUCCESS] Generated {len(users)} users")
    return users


def generate_products(session, count=500, append=False):
    """Generate product catalog"""
    print(f"[INFO] Generating {count} products...")

    if not append:
        # Delete existing products
        session.query(Product).delete()
        session.commit()

    products = []

    for i in range(count):
        category = random.choice(CATEGORIES)
        product_name = random.choice(PRODUCT_NAMES[category])
        brand = fake.company()

        product = Product(
            id=uuid.uuid4(),
            name=f"{brand} {product_name}",
            description=fake.text(max_nb_chars=200),
            price=Decimal(str(random.uniform(10, 5000))).quantize(Decimal('0.01')),
            stock_quantity=random.randint(0, 1000),
            category=category,
            image_url=f"https://via.placeholder.com/300?text={product_name.replace(' ', '+')}",
            status=random.choice([ProductStatus.AVAILABLE.value] * 90 + [ProductStatus.OUT_OF_STOCK.value] * 10),  # 90% available
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 365)),
        )
        products.append(product)

    session.bulk_save_objects(products)
    session.commit()

    print(f"[SUCCESS] Generated {len(products)} products")
    return products


def generate_orders(session, users, products, count=10000, append=False):
    """Generate orders with items and payments"""
    print(f"[INFO] Generating {count} orders (this may take a few minutes)...")

    if not append:
        # Delete existing orders (cascade will delete order items and payments)
        session.query(Order).delete()
        session.commit()

    # Distribution: 85% normal, 10% suspicious, 5% fraudulent
    normal_count = int(count * 0.85)
    suspicious_count = int(count * 0.10)
    fraudulent_count = count - normal_count - suspicious_count

    orders = []
    order_items = []
    payments = []

    for i in range(count):
        # Determine order type
        if i < normal_count:
            order_type = "normal"
        elif i < normal_count + suspicious_count:
            order_type = "suspicious"
        else:
            order_type = "fraudulent"

        # Select random user (fraudulent orders may use suspended users)
        if order_type == "fraudulent":
            user = random.choice(users)
        else:
            active_users = [u for u in users if u.status == UserStatus.ACTIVE.value]
            user = random.choice(active_users)

        # Create order
        order_id = uuid.uuid4()
        order_date = datetime.utcnow() - timedelta(days=random.randint(0, 365))

        # Select 1-5 random products
        num_items = random.randint(1, 5)
        selected_products = random.sample(products, min(num_items, len(products)))

        total_amount = Decimal(0)
        for product in selected_products:
            quantity = random.randint(1, 3)
            item_price = product.price * quantity
            total_amount += item_price

            order_item = OrderItem(
                id=uuid.uuid4(),
                order_id=order_id,
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price,
                subtotal=item_price,
                created_at=order_date,
            )
            order_items.append(order_item)

        # Determine order status
        if order_type == "fraudulent":
            status = random.choice([OrderStatus.CANCELLED.value, OrderStatus.REFUNDED.value])
        elif order_type == "suspicious":
            status = random.choice([OrderStatus.PENDING.value, OrderStatus.PAID.value, OrderStatus.CANCELLED.value])
        else:
            status = random.choice([
                OrderStatus.DELIVERED.value,
                OrderStatus.SHIPPED.value,
                OrderStatus.PAID.value,
                OrderStatus.PREPARING.value,
            ])

        order = Order(
            id=order_id,
            order_number=f"ORD{order_date.strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}",
            user_id=user.id,
            total_amount=total_amount,
            status=status,
            shipping_name=fake.name(),
            shipping_address=fake.address(),
            shipping_phone=fake.phone_number(),
            created_at=order_date,
            paid_at=order_date + timedelta(minutes=random.randint(1, 60)) if status != OrderStatus.PENDING.value else None,
            shipped_at=order_date + timedelta(days=random.randint(1, 3)) if status in [OrderStatus.SHIPPED.value, OrderStatus.DELIVERED.value] else None,
            delivered_at=order_date + timedelta(days=random.randint(3, 7)) if status == OrderStatus.DELIVERED.value else None,
            cancelled_at=order_date + timedelta(hours=random.randint(1, 24)) if status == OrderStatus.CANCELLED.value else None,
        )
        orders.append(order)

        # Create payment
        payment_method = random.choice([PaymentMethod.CREDIT_CARD.value, PaymentMethod.BANK_TRANSFER.value, PaymentMethod.PAYPAL.value])

        if status in [OrderStatus.PAID.value, OrderStatus.PREPARING.value, OrderStatus.SHIPPED.value, OrderStatus.DELIVERED.value]:
            payment_status = PaymentStatus.COMPLETED.value
        elif status == OrderStatus.REFUNDED.value:
            payment_status = PaymentStatus.REFUNDED.value
        elif status == OrderStatus.CANCELLED.value:
            payment_status = PaymentStatus.FAILED.value
        else:
            payment_status = PaymentStatus.PENDING.value

        payment = Payment(
            id=uuid.uuid4(),
            order_id=order_id,
            amount=total_amount,
            payment_method=payment_method,
            status=payment_status,
            transaction_id=f"TXN{uuid.uuid4().hex[:16].upper()}",
            card_last_four=str(random.randint(1000, 9999)) if payment_method == PaymentMethod.CREDIT_CARD.value else None,
            created_at=order_date,
            completed_at=order.paid_at if payment_status == PaymentStatus.COMPLETED.value else None,
        )
        payments.append(payment)

        # Progress indicator
        if (i + 1) % 1000 == 0:
            print(f"[INFO] Generated {i + 1}/{count} orders...")

    # Bulk insert (more efficient than individual inserts)
    session.bulk_save_objects(orders)
    session.bulk_save_objects(order_items)
    session.bulk_save_objects(payments)
    session.commit()

    print(f"[SUCCESS] Generated {len(orders)} orders with {len(order_items)} items and {len(payments)} payments")
    print(f"[INFO] Distribution: {normal_count} normal (85%), {suspicious_count} suspicious (10%), {fraudulent_count} fraudulent (5%)")
    return orders


def main():
    parser = argparse.ArgumentParser(description="Generate seed data for ShopFDS")
    parser.add_argument("--append", action="store_true", help="Append data instead of replacing (idempotent mode)")
    parser.add_argument("--users", type=int, default=1000, help="Number of users to generate (default: 1000)")
    parser.add_argument("--products", type=int, default=500, help="Number of products to generate (default: 500)")
    parser.add_argument("--orders", type=int, default=10000, help="Number of orders to generate (default: 10000)")
    parser.add_argument("--reviews", type=int, default=5000, help="Number of reviews to generate (default: 5000)")

    args = parser.parse_args()

    print("==========================================")
    print("ShopFDS Seed Data Generator")
    print("==========================================")
    print("")

    # Create database session
    try:
        session = create_database_session()
        print("[SUCCESS] Database connection established")
    except Exception as e:
        print(f"[ERROR] Failed to connect to database: {e}")
        sys.exit(1)

    # Check existing data
    existing = check_existing_data(session)
    print(f"[INFO] Existing data: {existing['users']} users, {existing['products']} products, {existing['orders']} orders")

    if not args.append and (existing['users'] > 0 or existing['products'] > 0 or existing['orders'] > 0):
        print("[WARNING] Data already exists. This will DELETE ALL EXISTING DATA.")
        response = input("Continue? (yes/no): ").strip().lower()
        if response != "yes":
            print("[INFO] Seed data generation cancelled.")
            sys.exit(0)

    # Generate data
    start_time = datetime.utcnow()

    users = generate_users(session, count=args.users, append=args.append)
    products = generate_products(session, count=args.products, append=args.append)
    orders = generate_orders(session, users, products, count=args.orders, append=args.append)

    # TODO: Generate reviews (future enhancement)
    if args.reviews > 0:
        print(f"[INFO] Review generation not yet implemented (requested: {args.reviews})")

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    # Final summary
    print("")
    print("==========================================")
    print("[SUCCESS] Seed Data Generation Complete!")
    print("==========================================")
    print(f"Duration: {duration:.2f} seconds")
    print("")
    print("Generated:")
    print(f"  - Users:    {len(users)}")
    print(f"  - Products: {len(products)}")
    print(f"  - Orders:   {len(orders)}")
    print("")
    print("Next steps:")
    print("  1. Verify data: psql -U shopfds_user -d shopfds_db -c 'SELECT COUNT(*) FROM users;'")
    print("  2. Start services: cd infrastructure && make dev")
    print("  3. Test API: curl http://localhost:8000/docs")
    print("")
    print("==========================================")


if __name__ == "__main__":
    main()
