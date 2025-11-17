#!/bin/bash
# setup.sh - Automated development environment setup script
# Usage: bash setup.sh

set -e  # Exit on error

echo "=========================================="
echo "ShopFDS Development Environment Setup"
echo "=========================================="
echo ""

# Color codes for output (compatible with Windows)
INFO="[INFO]"
SUCCESS="[SUCCESS]"
WARNING="[WARNING]"
ERROR="[ERROR]"

# Function: Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Step 1: Check prerequisites
echo "$INFO Step 1/7: Checking prerequisites..."

if ! command_exists docker; then
    echo "$ERROR Docker is not installed. Please install Docker Desktop."
    echo "  Download: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! command_exists docker-compose; then
    echo "$ERROR docker-compose is not installed. Please install Docker Compose."
    exit 1
fi

if ! command_exists python; then
    echo "$ERROR Python 3.11+ is not installed. Please install Python."
    exit 1
fi

echo "$SUCCESS Prerequisites check passed (Docker, docker-compose, Python)"

# Step 2: Check Docker daemon
echo ""
echo "$INFO Step 2/7: Checking Docker daemon..."

if ! docker info >/dev/null 2>&1; then
    echo "$ERROR Docker daemon is not running. Please start Docker Desktop."
    exit 1
fi

echo "$SUCCESS Docker daemon is running"

# Step 3: Create .env file if not exists
echo ""
echo "$INFO Step 3/7: Setting up environment variables..."

cd "$(dirname "$0")/../docker"

if [ ! -f .env ]; then
    echo "$INFO Creating .env file from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "$SUCCESS .env file created"
    else
        echo "$ERROR .env.example not found in infrastructure/docker/"
        exit 1
    fi
else
    echo "$INFO .env file already exists, skipping..."
fi

# Step 4: Pull Docker images
echo ""
echo "$INFO Step 4/7: Pulling Docker images (this may take 5-10 minutes)..."

docker-compose pull || {
    echo "$WARNING Failed to pull some images, will try to build locally..."
}

if [ -f docker-compose.monitoring.yml ]; then
    docker-compose -f docker-compose.monitoring.yml pull || {
        echo "$WARNING Failed to pull monitoring images..."
    }
fi

echo "$SUCCESS Docker images pulled"

# Step 5: Start infrastructure services
echo ""
echo "$INFO Step 5/7: Starting infrastructure services (PostgreSQL, Redis, RabbitMQ, ELK)..."

docker-compose up -d postgres redis-node-1 redis-node-2 redis-node-3 redis-node-4 redis-node-5 redis-node-6 rabbitmq elasticsearch logstash kibana

echo "$INFO Waiting for services to be healthy (30 seconds)..."
sleep 30

# Initialize Redis Cluster
echo "$INFO Initializing Redis Cluster..."
if [ -f ../scripts/init-redis-cluster.sh ]; then
    bash ../scripts/init-redis-cluster.sh || echo "$WARNING Redis Cluster initialization failed (may already be initialized)"
else
    echo "$WARNING init-redis-cluster.sh not found, skipping..."
fi

echo "$SUCCESS Infrastructure services started"

# Step 6: Run database migrations
echo ""
echo "$INFO Step 6/7: Running database migrations..."

cd ../../  # Back to project root

# Wait for PostgreSQL to be ready
echo "$INFO Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if docker exec shopfds-postgres-master pg_isready -U shopfds_user -d shopfds_db >/dev/null 2>&1; then
        echo "$SUCCESS PostgreSQL is ready"
        break
    fi
    echo "$INFO Waiting for PostgreSQL... ($i/30)"
    sleep 2
done

# Run migrations for each service
echo "$INFO Running Alembic migrations for all services..."

services=("ecommerce/backend" "fds" "ml-service" "admin-dashboard/backend")

for service in "${services[@]}"; do
    service_path="services/$service"
    if [ -d "$service_path" ]; then
        echo "$INFO Migrating $service..."
        cd "$service_path"

        # Check if alembic directory exists
        if [ -d "alembic" ]; then
            # Run migrations
            python -m alembic upgrade head || echo "$WARNING Migration failed for $service (may already be up to date)"
        else
            echo "$WARNING No alembic directory found for $service, skipping..."
        fi

        cd - >/dev/null
    else
        echo "$WARNING Service directory not found: $service_path"
    fi
done

echo "$SUCCESS Database migrations completed"

# Step 7: Initialize Elasticsearch
echo ""
echo "$INFO Step 7/7: Initializing Elasticsearch indices..."

if [ -f infrastructure/scripts/init-elasticsearch.sh ]; then
    bash infrastructure/scripts/init-elasticsearch.sh || echo "$WARNING Elasticsearch initialization failed (may already be initialized)"
else
    echo "$WARNING init-elasticsearch.sh not found, skipping..."
fi

# Final summary
echo ""
echo "=========================================="
echo "$SUCCESS Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Start all services:     cd infrastructure && make dev"
echo "  2. Generate seed data:     cd infrastructure && make seed"
echo "  3. Run tests:              cd infrastructure && make test"
echo ""
echo "Service URLs (after 'make dev'):"
echo "  - Ecommerce Backend:  http://localhost:8000/docs"
echo "  - FDS Service:        http://localhost:8001/docs"
echo "  - ML Service:         http://localhost:8002/docs"
echo "  - Admin Dashboard:    http://localhost:8003/docs"
echo "  - Flower (Celery):    http://localhost:5555"
echo "  - Kibana:             http://localhost:5601"
echo "  - Grafana:            http://localhost:3001"
echo "  - Prometheus:         http://localhost:9090"
echo ""
echo "Troubleshooting:"
echo "  - View logs:          cd infrastructure && make logs"
echo "  - Check health:       cd infrastructure && make health"
echo "  - Reset database:     cd infrastructure && make reset-db"
echo ""
echo "=========================================="
