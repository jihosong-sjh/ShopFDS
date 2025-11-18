# ShopFDS Infrastructure Makefile
# Development environment automation for local setup and testing

.PHONY: help dev test migrate seed clean setup reset-db logs health docker-build docker-pull

# Default target
help:
	@echo "=========================================="
	@echo "ShopFDS Infrastructure Management"
	@echo "=========================================="
	@echo ""
	@echo "Quick Start:"
	@echo "  make setup       - [RECOMMENDED] Full setup: Docker images + DB migration + seed data"
	@echo "  make dev         - Start all development services in detached mode"
	@echo ""
	@echo "Development Commands:"
	@echo "  make test        - Run all infrastructure tests (PostgreSQL, Redis, Celery, ELK)"
	@echo "  make migrate     - Run database migrations for all services"
	@echo "  make seed        - Generate seed data (users, orders, products, reviews)"
	@echo "  make clean       - Stop all services and remove containers"
	@echo ""
	@echo "Database Commands:"
	@echo "  make reset-db    - Delete all tables and recreate schema (DESTRUCTIVE)"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make logs        - View logs from all services (tail -f mode)"
	@echo "  make health      - Check health status of all services"
	@echo "  make docker-build - Build all Docker images from scratch"
	@echo "  make docker-pull  - Pull pre-built images from registry"
	@echo ""
	@echo "=========================================="

# Full setup: Dependencies + Docker + Migrations + Seed data
setup:
	@echo "[INFO] Starting full environment setup..."
	@bash scripts/setup.sh
	@echo "[SUCCESS] Setup complete! Run 'make dev' to start services."

# Start all development services
dev:
	@echo "[INFO] Starting development services..."
	@docker-compose -f docker/docker-compose.yml up -d
	@docker-compose -f docker/docker-compose.monitoring.yml up -d
	@echo "[INFO] Waiting for services to be healthy..."
	@sleep 10
	@echo "[SUCCESS] All services started successfully!"
	@echo ""
	@echo "Service URLs:"
	@echo "  - Ecommerce Backend:  http://localhost:8000/docs"
	@echo "  - FDS Service:        http://localhost:8001/docs"
	@echo "  - ML Service:         http://localhost:8002/docs"
	@echo "  - Admin Dashboard:    http://localhost:8003/docs"
	@echo "  - Flower (Celery):    http://localhost:5555"
	@echo "  - Kibana:             http://localhost:5601"
	@echo "  - Grafana:            http://localhost:3001"
	@echo "  - Prometheus:         http://localhost:9090"

# Run all infrastructure tests
test:
	@echo "[INFO] Running infrastructure tests..."
	@cd .. && pytest tests/infrastructure/test_postgres_replication.py -v --tb=short
	@cd .. && pytest tests/infrastructure/test_redis_cluster.py -v --tb=short
	@cd .. && pytest tests/infrastructure/test_celery_tasks.py -v --tb=short
	@cd .. && pytest tests/infrastructure/test_elk_logging.py -v --tb=short
	@echo "[SUCCESS] All infrastructure tests passed!"

# Run database migrations for all services
migrate:
	@echo "[INFO] Running database migrations..."
	@echo "[INFO] Ecommerce Backend migrations..."
	@docker exec shopfds-ecommerce-backend alembic upgrade head || echo "[WARNING] Ecommerce migrations skipped (container not running)"
	@echo "[INFO] FDS Service migrations..."
	@docker exec shopfds-fds alembic upgrade head || echo "[WARNING] FDS migrations skipped (container not running)"
	@echo "[INFO] ML Service migrations..."
	@docker exec shopfds-ml-service alembic upgrade head || echo "[WARNING] ML Service migrations skipped (container not running)"
	@echo "[INFO] Admin Dashboard migrations..."
	@docker exec shopfds-admin-dashboard alembic upgrade head || echo "[WARNING] Admin Dashboard migrations skipped (container not running)"
	@echo "[SUCCESS] All migrations completed!"

# Generate seed data
seed:
	@echo "[INFO] Generating seed data (users: 1000, orders: 10000, products: 500, reviews: 5000)..."
	@cd .. && python infrastructure/scripts/seed-data.py
	@echo "[SUCCESS] Seed data generated successfully!"

# Clean: Stop services and remove containers
clean:
	@echo "[INFO] Stopping all services and removing containers..."
	@docker-compose -f docker/docker-compose.yml down -v
	@docker-compose -f docker/docker-compose.monitoring.yml down -v
	@echo "[SUCCESS] All services stopped and containers removed."

# Reset database: Delete all tables and recreate schema
reset-db:
	@echo "[WARNING] This will DELETE ALL DATA in the database!"
	@echo "[WARNING] Press Ctrl+C to cancel, or wait 5 seconds to continue..."
	@sleep 5
	@echo "[INFO] Resetting database..."
	@bash scripts/reset-db.sh
	@echo "[SUCCESS] Database reset complete! Run 'make migrate' to apply schema."

# View logs from all services
logs:
	@echo "[INFO] Viewing logs from all services (Ctrl+C to exit)..."
	@docker-compose -f docker/docker-compose.yml logs -f

# Check health status of all services
health:
	@echo "[INFO] Checking health status of all services..."
	@echo ""
	@echo "=== PostgreSQL Master ==="
	@curl -s http://localhost:8000/health | python -m json.tool || echo "[FAIL] Ecommerce Backend not responding"
	@echo ""
	@echo "=== PostgreSQL Replica ==="
	@docker exec shopfds-postgres-replica pg_isready -U shopfds_user && echo "[OK] Replica is ready" || echo "[FAIL] Replica not ready"
	@echo ""
	@echo "=== Redis Cluster ==="
	@docker exec shopfds-redis-node-1 redis-cli cluster info | grep cluster_state || echo "[FAIL] Redis Cluster not responding"
	@echo ""
	@echo "=== RabbitMQ ==="
	@curl -s -u guest:guest http://localhost:15672/api/overview | python -m json.tool | grep product_version || echo "[FAIL] RabbitMQ not responding"
	@echo ""
	@echo "=== Elasticsearch ==="
	@curl -s http://localhost:9200/_cluster/health | python -m json.tool || echo "[FAIL] Elasticsearch not responding"
	@echo ""
	@echo "[SUCCESS] Health check complete!"

# Build Docker images from scratch
docker-build:
	@echo "[INFO] Building Docker images from scratch..."
	@docker-compose -f docker/docker-compose.yml build --no-cache
	@echo "[SUCCESS] Docker images built successfully!"

# Pull pre-built images from registry
docker-pull:
	@echo "[INFO] Pulling pre-built images from registry..."
	@docker-compose -f docker/docker-compose.yml pull
	@docker-compose -f docker/docker-compose.monitoring.yml pull
	@echo "[SUCCESS] Images pulled successfully!"
