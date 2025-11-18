#!/bin/bash

# ========================================
# Docker Image Push Script
# ========================================
# ShopFDS Platform - Push Docker images to registry
#
# Usage:
#   ./push-images.sh [VERSION]
#
# Examples:
#   ./push-images.sh         # Push images with 'latest' tag
#   ./push-images.sh v1.2.0  # Push images with specific version tag
#
# Prerequisites:
#   - Docker login to registry: docker login [REGISTRY]
#   - Images must be built first: ./build-images.sh
#
# Environment Variables:
#   REGISTRY: Docker registry URL (default: shopfds)
#   VERSION: Image version tag (default: latest)
# ========================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGISTRY="${REGISTRY:-shopfds}"
VERSION="${1:-${VERSION:-latest}}"

echo "=========================================="
echo "ShopFDS Docker Image Push"
echo "=========================================="
echo "Registry: $REGISTRY"
echo "Version:  $VERSION"
echo "=========================================="
echo ""

# List of services to push
SERVICES=(
    "ecommerce-backend"
    "fds-service"
    "ml-service"
    "admin-dashboard-backend"
    "ecommerce-frontend"
    "admin-dashboard-frontend"
)

# Function to push Docker image
push_image() {
    local SERVICE_NAME=$1
    local IMAGE_TAG="${REGISTRY}/${SERVICE_NAME}:${VERSION}"
    local IMAGE_TAG_LATEST="${REGISTRY}/${SERVICE_NAME}:latest"

    echo -e "${YELLOW}[PUSH] Pushing ${SERVICE_NAME}...${NC}"
    echo "  Image: ${IMAGE_TAG}"

    # Check if image exists
    if ! docker image inspect "$IMAGE_TAG" > /dev/null 2>&1; then
        echo -e "${RED}[FAIL] Image ${IMAGE_TAG} not found. Build it first!${NC}"
        echo ""
        return 1
    fi

    # Push versioned tag
    if docker push "$IMAGE_TAG"; then
        echo -e "${GREEN}[OK] Pushed ${IMAGE_TAG}${NC}"
    else
        echo -e "${RED}[FAIL] Failed to push ${IMAGE_TAG}${NC}"
        echo ""
        return 1
    fi

    # Push latest tag (only if version is not 'latest')
    if [ "$VERSION" != "latest" ]; then
        if docker push "$IMAGE_TAG_LATEST"; then
            echo -e "${GREEN}[OK] Pushed ${IMAGE_TAG_LATEST}${NC}"
        else
            echo -e "${RED}[FAIL] Failed to push ${IMAGE_TAG_LATEST}${NC}"
            echo ""
            return 1
        fi
    fi

    echo ""
    return 0
}

# Track push status
FAILED_PUSHES=()

# Push all services
for service in "${SERVICES[@]}"; do
    if ! push_image "$service"; then
        FAILED_PUSHES+=("$service")
    fi
done

# ========================================
# Push Summary
# ========================================

echo ""
echo "=========================================="
echo "Push Summary"
echo "=========================================="

if [ ${#FAILED_PUSHES[@]} -eq 0 ]; then
    echo -e "${GREEN}[SUCCESS] All images pushed successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Update Kubernetes manifests with new version: ${VERSION}"
    echo "  2. Deploy to Kubernetes: kubectl apply -k infrastructure/k8s/"
    echo "  3. Verify deployment: kubectl get pods -n shopfds"
    exit 0
else
    echo -e "${RED}[FAIL] Failed to push the following images:${NC}"
    for service in "${FAILED_PUSHES[@]}"; do
        echo "  - $service"
    done
    echo ""
    echo "Please check the error messages above and ensure:"
    echo "  1. You are logged in to the registry: docker login $REGISTRY"
    echo "  2. You have push permissions"
    echo "  3. The images exist locally: docker images | grep $REGISTRY"
    exit 1
fi
