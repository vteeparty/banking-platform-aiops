#!/bin/bash
# Quick deployment script for Loki + Promtail stack
# Usage: ./deploy-logging.sh

set -e

NAMESPACE="logging"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Deploying Centralized Logging Stack ==="
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed"
    exit 1
fi

# Create namespace if it doesn't exist
echo "[1/4] Creating logging namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Deploy Loki
echo "[2/4] Deploying Loki..."
kubectl apply -f "$SCRIPT_DIR/loki-deployment.yaml"

# Wait for Loki to be ready
echo "Waiting for Loki to be ready..."
kubectl wait --for=condition=available --timeout=300s \
  deployment/loki -n $NAMESPACE || true

# Deploy Promtail
echo "[3/4] Deploying Promtail..."
kubectl apply -f "$SCRIPT_DIR/promtail-daemonset.yaml"

# Wait for Promtail DaemonSet to be ready
echo "Waiting for Promtail to be ready..."
kubectl wait --for=condition=ready pod \
  -l app=promtail \
  -n $NAMESPACE \
  --timeout=300s || true

# Deploy banking services
echo "[4/4] Deploying banking services..."
kubectl apply -f "$SCRIPT_DIR/service-manifests/banking-services.yaml"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Check status:"
echo "  kubectl get pods -n $NAMESPACE"
echo "  kubectl get pods -l app=payment-service"
echo ""
echo "View logs:"
echo "  kubectl logs -n $NAMESPACE -l app=loki --tail=50"
echo "  kubectl logs -n $NAMESPACE -l app=promtail --tail=50"
echo ""
echo "Access Loki API:"
echo "  kubectl port-forward -n $NAMESPACE svc/loki 3100:3100 &"
echo "  curl http://localhost:3100/loki/api/v1/status/buildinfo"
echo ""
