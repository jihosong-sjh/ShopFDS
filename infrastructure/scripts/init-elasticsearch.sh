#!/bin/bash

# Elasticsearch Initialization Script
# Purpose: Apply index templates and ILM policies

set -e

ELASTICSEARCH_HOST="${ELASTICSEARCH_HOST:-http://localhost:9200}"
TEMPLATE_FILE="/usr/share/elasticsearch/config/index-template.json"
RETRY_COUNT=30
RETRY_DELAY=5

echo "[INFO] Waiting for Elasticsearch to be ready..."

# Wait for Elasticsearch to be available
for i in $(seq 1 $RETRY_COUNT); do
  if curl -f -s "$ELASTICSEARCH_HOST/_cluster/health" > /dev/null 2>&1; then
    echo "[SUCCESS] Elasticsearch is ready"
    break
  fi
  
  if [ $i -eq $RETRY_COUNT ]; then
    echo "[FAIL] Elasticsearch not available after $RETRY_COUNT attempts"
    exit 1
  fi
  
  echo "[INFO] Attempt $i/$RETRY_COUNT: Elasticsearch not ready, retrying in ${RETRY_DELAY}s..."
  sleep $RETRY_DELAY
done

echo "[INFO] Creating ILM policy for log retention (30 days)..."

# Create ILM policy (Index Lifecycle Management)
curl -X PUT "$ELASTICSEARCH_HOST/_ilm/policy/shopfds-logs-policy" \
  -H 'Content-Type: application/json' \
  -d '{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_size": "50gb",
            "max_age": "1d"
          },
          "set_priority": {
            "priority": 100
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "forcemerge": {
            "max_num_segments": 1
          },
          "shrink": {
            "number_of_shards": 1
          },
          "set_priority": {
            "priority": 50
          }
        }
      },
      "delete": {
        "min_age": "30d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}'

if [ $? -eq 0 ]; then
  echo ""
  echo "[SUCCESS] ILM policy created successfully"
else
  echo "[WARNING] Failed to create ILM policy (may already exist)"
fi

echo "[INFO] Applying index template..."

# Apply index template
if [ -f "$TEMPLATE_FILE" ]; then
  curl -X PUT "$ELASTICSEARCH_HOST/_index_template/shopfds-logs" \
    -H 'Content-Type: application/json' \
    -d @$TEMPLATE_FILE
  
  if [ $? -eq 0 ]; then
    echo ""
    echo "[SUCCESS] Index template applied successfully"
  else
    echo "[FAIL] Failed to apply index template"
    exit 1
  fi
else
  echo "[WARNING] Index template file not found at $TEMPLATE_FILE"
fi

echo "[INFO] Creating initial indices..."

# Create initial indices for each service
for service in ecommerce fds ml-service admin-dashboard; do
  INDEX_NAME="shopfds-$service-$(date +%Y.%m.%d)"
  
  echo "[INFO] Creating index: $INDEX_NAME"
  
  curl -X PUT "$ELASTICSEARCH_HOST/$INDEX_NAME" \
    -H 'Content-Type: application/json' \
    -d '{
      "aliases": {
        "shopfds-logs": {}
      }
    }' > /dev/null 2>&1
  
  if [ $? -eq 0 ]; then
    echo "[SUCCESS] Index $INDEX_NAME created"
  else
    echo "[INFO] Index $INDEX_NAME may already exist"
  fi
done

echo ""
echo "[SUCCESS] Elasticsearch initialization completed"
echo ""
echo "Index template: shopfds-logs"
echo "ILM policy: shopfds-logs-policy (30 days retention)"
echo "Index pattern: shopfds-{service}-{date}"
echo ""
echo "You can verify with:"
echo "  curl $ELASTICSEARCH_HOST/_cat/indices?v"
echo "  curl $ELASTICSEARCH_HOST/_index_template/shopfds-logs"
echo "  curl $ELASTICSEARCH_HOST/_ilm/policy/shopfds-logs-policy"
