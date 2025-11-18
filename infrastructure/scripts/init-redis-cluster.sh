#!/bin/bash
# Redis Cluster Initialization Script
# ShopFDS Production Infrastructure - User Story 2

set -e

echo "[INFO] Initializing Redis Cluster (6 nodes: 3 masters + 3 replicas)"

# Wait for all Redis nodes to be ready
echo "[INFO] Waiting for Redis nodes to start..."
for port in 7000 7001 7002 7003 7004 7005; do
    until redis-cli -h redis-node-$((port - 7000 + 1)) -p 6379 ping > /dev/null 2>&1; do
        echo "[INFO] Waiting for redis-node-$((port - 7000 + 1))..."
        sleep 2
    done
    echo "[OK] redis-node-$((port - 7000 + 1)) is ready"
done

# Create cluster with 3 masters and 3 replicas
echo "[INFO] Creating Redis Cluster..."
redis-cli --cluster create \
    redis-node-1:6379 \
    redis-node-2:6379 \
    redis-node-3:6379 \
    redis-node-4:6379 \
    redis-node-5:6379 \
    redis-node-6:6379 \
    --cluster-replicas 1 \
    --cluster-yes

echo "[OK] Redis Cluster created successfully"

# Verify cluster status
echo "[INFO] Verifying cluster status..."
redis-cli -c -h redis-node-1 -p 6379 cluster info

# Display cluster nodes
echo "[INFO] Cluster nodes:"
redis-cli -c -h redis-node-1 -p 6379 cluster nodes

echo "[SUCCESS] Redis Cluster initialization complete!"
echo "[INFO] Cluster endpoint: redis-node-1:6379,redis-node-2:6379,redis-node-3:6379"
