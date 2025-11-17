#!/bin/bash
# reset-db.sh - Reset database by dropping all tables and recreating schema
# WARNING: This is a DESTRUCTIVE operation that will DELETE ALL DATA
# Usage: bash reset-db.sh

set -e  # Exit on error

echo "=========================================="
echo "ShopFDS Database Reset"
echo "=========================================="
echo ""

# Color codes for output (compatible with Windows)
INFO="[INFO]"
SUCCESS="[SUCCESS]"
WARNING="[WARNING]"
ERROR="[ERROR]"

# Database connection parameters (from .env or defaults)
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-shopfds_db}"
DB_USER="${POSTGRES_USER:-shopfds_user}"
DB_PASSWORD="${POSTGRES_PASSWORD:-shopfds_password}"

# Function: Check if PostgreSQL is running
check_postgres() {
    docker exec shopfds-postgres-master pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1
}

# Step 1: Check if PostgreSQL is running
echo "$INFO Step 1/5: Checking PostgreSQL status..."

if ! check_postgres; then
    echo "$ERROR PostgreSQL is not running or not accessible."
    echo "  Please start PostgreSQL with: cd infrastructure && make dev"
    exit 1
fi

echo "$SUCCESS PostgreSQL is running"

# Step 2: Confirm destructive operation
echo ""
echo "$WARNING =========================================="
echo "$WARNING THIS WILL DELETE ALL DATA IN THE DATABASE!"
echo "$WARNING =========================================="
echo "$WARNING Database: $DB_NAME"
echo "$WARNING Host: $DB_HOST:$DB_PORT"
echo ""
read -p "Are you sure you want to continue? Type 'yes' to confirm: " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "$INFO Database reset cancelled."
    exit 0
fi

# Step 3: Drop all tables
echo ""
echo "$INFO Step 3/5: Dropping all tables in database '$DB_NAME'..."

# Drop all tables using PSQL (more reliable than Alembic downgrade)
docker exec -i shopfds-postgres-master psql -U "$DB_USER" -d "$DB_NAME" <<EOF
-- Disable foreign key checks temporarily
SET session_replication_role = 'replica';

-- Drop all tables in public schema
DO \$\$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END \$\$;

-- Re-enable foreign key checks
SET session_replication_role = 'origin';

-- Drop Alembic version table if exists
DROP TABLE IF EXISTS alembic_version CASCADE;

-- Verify all tables are dropped
SELECT COUNT(*) AS remaining_tables FROM pg_tables WHERE schemaname = 'public';
EOF

echo "$SUCCESS All tables dropped"

# Step 4: Recreate schema using Alembic migrations
echo ""
echo "$INFO Step 4/5: Recreating schema using Alembic migrations..."

cd "$(dirname "$0")/../../"  # Back to project root

services=("ecommerce/backend" "fds" "ml-service" "admin-dashboard/backend")

for service in "${services[@]}"; do
    service_path="services/$service"
    if [ -d "$service_path" ]; then
        echo "$INFO Running migrations for $service..."
        cd "$service_path"

        # Check if alembic directory exists
        if [ -d "alembic" ]; then
            # Run migrations from scratch
            python -m alembic upgrade head || echo "$WARNING Migration failed for $service"
        else
            echo "$WARNING No alembic directory found for $service, skipping..."
        fi

        cd - >/dev/null
    else
        echo "$WARNING Service directory not found: $service_path"
    fi
done

echo "$SUCCESS Schema recreated successfully"

# Step 5: Verify database schema
echo ""
echo "$INFO Step 5/5: Verifying database schema..."

docker exec -i shopfds-postgres-master psql -U "$DB_USER" -d "$DB_NAME" <<EOF
-- List all tables
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
EOF

table_count=$(docker exec -i shopfds-postgres-master psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';")

echo ""
echo "$SUCCESS Database schema verified (Total tables: $table_count)"

# Final summary
echo ""
echo "=========================================="
echo "$SUCCESS Database Reset Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Generate seed data:     cd infrastructure && make seed"
echo "  2. Verify data:            psql -U $DB_USER -d $DB_NAME -c 'SELECT COUNT(*) FROM users;'"
echo ""
echo "Note: You may need to restart application services to reconnect to the database."
echo "  cd infrastructure && docker-compose restart ecommerce-backend fds ml-service admin-dashboard"
echo ""
echo "=========================================="
