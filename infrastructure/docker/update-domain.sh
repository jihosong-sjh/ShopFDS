#!/bin/bash

# ========================================
# ShopFDS Domain Update Script
# ========================================
# Usage:
#   ./update-domain.sh YOUR_DOMAIN
#
# Example:
#   ./update-domain.sh myshop.com
#
# This will replace all instances of:
#   shopfds.example.com → YOUR_DOMAIN
# ========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if domain argument is provided
if [ -z "$1" ]; then
    echo -e "${RED}[ERROR] Domain not provided!${NC}"
    echo ""
    echo "Usage: $0 YOUR_DOMAIN"
    echo "Example: $0 myshop.com"
    exit 1
fi

NEW_DOMAIN="$1"
OLD_DOMAIN="shopfds.example.com"
ENV_FILE=".env.production"

# Check if .env.production exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}[ERROR] $ENV_FILE not found!${NC}"
    echo "Please run this script from infrastructure/docker/ directory"
    exit 1
fi

echo "=========================================="
echo "ShopFDS Domain Update"
echo "=========================================="
echo "Old Domain: $OLD_DOMAIN"
echo "New Domain: $NEW_DOMAIN"
echo "File:       $ENV_FILE"
echo "=========================================="
echo ""

# Create backup
BACKUP_FILE="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$ENV_FILE" "$BACKUP_FILE"
echo -e "${GREEN}[OK] Backup created: $BACKUP_FILE${NC}"

# Count occurrences before replacement
BEFORE_COUNT=$(grep -o "$OLD_DOMAIN" "$ENV_FILE" | wc -l)
echo -e "${YELLOW}[INFO] Found $BEFORE_COUNT occurrences of '$OLD_DOMAIN'${NC}"
echo ""

# Show what will be changed
echo "Will update the following lines:"
echo "----------------------------------------"
grep -n "$OLD_DOMAIN" "$ENV_FILE"
echo "----------------------------------------"
echo ""

# Ask for confirmation
read -p "Continue with replacement? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}[CANCELLED] No changes made.${NC}"
    rm "$BACKUP_FILE"
    exit 0
fi

# Perform replacement
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/$OLD_DOMAIN/$NEW_DOMAIN/g" "$ENV_FILE"
else
    # Linux
    sed -i "s/$OLD_DOMAIN/$NEW_DOMAIN/g" "$ENV_FILE"
fi

# Count occurrences after replacement
AFTER_COUNT=$(grep -o "$OLD_DOMAIN" "$ENV_FILE" | wc -l)

echo ""
echo "=========================================="
echo "Update Complete!"
echo "=========================================="
echo -e "${GREEN}[OK] Replaced $BEFORE_COUNT occurrences${NC}"
echo -e "${GREEN}[OK] Remaining occurrences: $AFTER_COUNT${NC}"
echo ""
echo "Updated lines:"
echo "----------------------------------------"
grep -n "$NEW_DOMAIN" "$ENV_FILE" | head -10
echo "----------------------------------------"
echo ""
echo "Next steps:"
echo "  1. Review changes: vi $ENV_FILE"
echo "  2. Configure DNS for your domain:"
echo "     - $NEW_DOMAIN                → [Server IP]"
echo "     - api.$NEW_DOMAIN            → [Server IP]"
echo "     - fds.$NEW_DOMAIN            → [Server IP]"
echo "     - ml.$NEW_DOMAIN             → [Server IP]"
echo "     - admin.$NEW_DOMAIN          → [Server IP]"
echo "     - admin-api.$NEW_DOMAIN      → [Server IP]"
echo "  3. Deploy: docker-compose -f docker-compose.prod.yml up -d"
echo ""
echo "Backup saved at: $BACKUP_FILE"
echo "=========================================="
