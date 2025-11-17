#!/bin/bash
# PostgreSQL Replication Initialization Script
# Feature: 002-production-infra
# Task: T014
# Description: Creates replicator user and sets up pg_hba.conf for streaming replication

set -e  # Exit on error

echo "[INFO] Initializing PostgreSQL streaming replication..."

# Check if running as postgres user
if [ "$(id -u)" != "$(id -u postgres 2>/dev/null || echo 999)" ]; then
    echo "[WARNING] Not running as postgres user, switching context..."
fi

# Get environment variables
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_DB=${POSTGRES_DB:-shopfds}
REPLICATION_USER=${POSTGRES_REPLICATION_USER:-replicator}
REPLICATION_PASSWORD=${POSTGRES_REPLICATION_PASSWORD:-replicator_password}

echo "[INFO] Creating replication user: $REPLICATION_USER"

# Create replication user with REPLICATION privilege
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Check if replication user already exists
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$REPLICATION_USER') THEN
            CREATE ROLE $REPLICATION_USER WITH REPLICATION PASSWORD '$REPLICATION_PASSWORD' LOGIN;
            RAISE NOTICE '[SUCCESS] Replication user created: $REPLICATION_USER';
        ELSE
            RAISE NOTICE '[INFO] Replication user already exists: $REPLICATION_USER';
        END IF;
    END
    \$\$;

    -- Grant necessary privileges
    GRANT CONNECT ON DATABASE $POSTGRES_DB TO $REPLICATION_USER;

    -- Create replication slot (will be used by replica)
    SELECT pg_create_physical_replication_slot('replica_slot_1')
    WHERE NOT EXISTS (
        SELECT 1 FROM pg_replication_slots WHERE slot_name = 'replica_slot_1'
    );
EOSQL

echo "[INFO] Configuring pg_hba.conf for replication connections..."

# Add replication entries to pg_hba.conf if not already present
PG_HBA_CONF="$PGDATA/pg_hba.conf"

if [ -f "$PG_HBA_CONF" ]; then
    # Check if replication entry already exists
    if ! grep -q "# Replication connections" "$PG_HBA_CONF"; then
        cat >> "$PG_HBA_CONF" <<-EOH

# Replication connections (added by init-postgres-replication.sh)
# Allow replication connections from replica nodes
host    replication     $REPLICATION_USER     0.0.0.0/0               md5
host    replication     $REPLICATION_USER     ::0/0                   md5

# Allow all connections from internal network (for application services)
host    all             all                   172.16.0.0/12           md5
host    all             all                   10.0.0.0/8              md5
host    all             all                   192.168.0.0/16          md5
EOH
        echo "[SUCCESS] pg_hba.conf updated with replication entries"
    else
        echo "[INFO] pg_hba.conf already configured for replication"
    fi

    # Reload PostgreSQL configuration
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "SELECT pg_reload_conf();" > /dev/null
    echo "[SUCCESS] PostgreSQL configuration reloaded"
else
    echo "[ERROR] pg_hba.conf not found at $PG_HBA_CONF"
    exit 1
fi

# Create WAL archive directory
WAL_ARCHIVE_DIR="/var/lib/postgresql/wal_archive"
if [ ! -d "$WAL_ARCHIVE_DIR" ]; then
    mkdir -p "$WAL_ARCHIVE_DIR"
    chown postgres:postgres "$WAL_ARCHIVE_DIR" 2>/dev/null || true
    chmod 700 "$WAL_ARCHIVE_DIR"
    echo "[SUCCESS] WAL archive directory created: $WAL_ARCHIVE_DIR"
else
    echo "[INFO] WAL archive directory already exists: $WAL_ARCHIVE_DIR"
fi

# Verify replication setup
echo "[INFO] Verifying replication setup..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Check replication user
    SELECT rolname, rolreplication FROM pg_roles WHERE rolname = '$REPLICATION_USER';

    -- Check replication slots
    SELECT slot_name, slot_type, active FROM pg_replication_slots;

    -- Check WAL sender settings
    SHOW wal_level;
    SHOW max_wal_senders;
    SHOW max_replication_slots;
EOSQL

echo ""
echo "[SUCCESS] PostgreSQL streaming replication initialized successfully"
echo "[INFO] Replication user: $REPLICATION_USER"
echo "[INFO] Replication slot: replica_slot_1"
echo "[INFO] WAL archive: $WAL_ARCHIVE_DIR"
echo ""
echo "[NEXT] Start the replica container to establish streaming replication"
