#!/bin/bash

# ========================================
# Docker Image Build Script
# ========================================
# ShopFDS Platform - Build all Docker images
#
# Usage:
#   ./build-images.sh [VERSION]
#
# Examples:
#   ./build-images.sh         # Build with 'latest' tag
#   ./build-images.sh v1.2.0  # Build with specific version tag
#
# Environment Variables:
#   REGISTRY: Docker registry URL (default: shopfds)
#   VERSION: Image version tag (default: latest)
#   NO_CACHE: Set to 1 to build without cache
# ========================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REGISTRY="${REGISTRY:-shopfds}"
VERSION="${1:-${VERSION:-latest}}"
BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
NO_CACHE_FLAG=""

if [ "${NO_CACHE}" == "1" ]; then
    NO_CACHE_FLAG="--no-cache"
    echo -e "${YELLOW}[INFO] Building with --no-cache flag${NC}"
fi

# Git commit hash for traceability
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "=========================================="
echo "ShopFDS Docker Image Build"
echo "=========================================="
echo "Registry:    $REGISTRY"
echo "Version:     $VERSION"
echo "Build Date:  $BUILD_DATE"
echo "Git Commit:  $GIT_COMMIT"
echo "=========================================="
echo ""

# Function to build Docker image
build_image() {
    local SERVICE_NAME=$1
    local DOCKERFILE_PATH=$2
    local BUILD_CONTEXT=$3
    local IMAGE_TAG="${REGISTRY}/${SERVICE_NAME}:${VERSION}"
    local IMAGE_TAG_LATEST="${REGISTRY}/${SERVICE_NAME}:latest"

    echo -e "${YELLOW}[BUILD] Building ${SERVICE_NAME}...${NC}"
    echo "  Image: ${IMAGE_TAG}"
    echo "  Dockerfile: ${DOCKERFILE_PATH}"
    echo "  Context: ${BUILD_CONTEXT}"

    # Build the image
    if docker build $NO_CACHE_FLAG \
        --tag "$IMAGE_TAG" \
        --tag "$IMAGE_TAG_LATEST" \
        --label "version=${VERSION}" \
        --label "build-date=${BUILD_DATE}" \
        --label "git-commit=${GIT_COMMIT}" \
        --file "$DOCKERFILE_PATH" \
        "$BUILD_CONTEXT"; then
        echo -e "${GREEN}[OK] ${SERVICE_NAME} built successfully${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}[FAIL] Failed to build ${SERVICE_NAME}${NC}"
        echo ""
        return 1
    fi
}

# Track build status
FAILED_BUILDS=()

# ========================================
# Build Backend Services
# ========================================

echo "=========================================="
echo "Building Backend Services"
echo "=========================================="
echo ""

# Ecommerce Backend
if ! build_image \
    "ecommerce-backend" \
    "$PROJECT_ROOT/services/ecommerce/backend/Dockerfile" \
    "$PROJECT_ROOT/services/ecommerce/backend"; then
    FAILED_BUILDS+=("ecommerce-backend")
fi

# FDS Service
if ! build_image \
    "fds-service" \
    "$PROJECT_ROOT/services/fds/Dockerfile" \
    "$PROJECT_ROOT/services/fds"; then
    FAILED_BUILDS+=("fds-service")
fi

# ML Service
if ! build_image \
    "ml-service" \
    "$PROJECT_ROOT/services/ml-service/Dockerfile" \
    "$PROJECT_ROOT/services/ml-service"; then
    FAILED_BUILDS+=("ml-service")
fi

# Admin Dashboard Backend
if ! build_image \
    "admin-dashboard-backend" \
    "$PROJECT_ROOT/services/admin-dashboard/backend/Dockerfile" \
    "$PROJECT_ROOT/services/admin-dashboard/backend"; then
    FAILED_BUILDS+=("admin-dashboard-backend")
fi

# ========================================
# Build Frontend Services
# ========================================

echo "=========================================="
echo "Building Frontend Services"
echo "=========================================="
echo ""

# Ecommerce Frontend
if ! build_image \
    "ecommerce-frontend" \
    "$PROJECT_ROOT/services/ecommerce/frontend/Dockerfile" \
    "$PROJECT_ROOT/services/ecommerce/frontend"; then
    FAILED_BUILDS+=("ecommerce-frontend")
fi

# Admin Dashboard Frontend
if ! build_image \
    "admin-dashboard-frontend" \
    "$PROJECT_ROOT/services/admin-dashboard/frontend/Dockerfile" \
    "$PROJECT_ROOT/services/admin-dashboard/frontend"; then
    FAILED_BUILDS+=("admin-dashboard-frontend")
fi

# ========================================
# Build Summary
# ========================================

echo ""
echo "=========================================="
echo "Build Summary"
echo "=========================================="

if [ ${#FAILED_BUILDS[@]} -eq 0 ]; then
    echo -e "${GREEN}[SUCCESS] All images built successfully!${NC}"
    echo ""
    echo "Built images:"
    docker images --filter "label=version=${VERSION}" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    echo ""
    echo "Next steps:"
    echo "  1. Test images locally: docker-compose -f docker-compose.prod.yml up -d"
    echo "  2. Push to registry: ./push-images.sh ${VERSION}"
    echo "  3. Deploy to Kubernetes: kubectl apply -k infrastructure/k8s/"
    exit 0
else
    echo -e "${RED}[FAIL] Failed to build the following images:${NC}"
    for service in "${FAILED_BUILDS[@]}"; do
        echo "  - $service"
    done
    echo ""
    echo "Please check the error messages above and fix the issues."
    exit 1
fi
