#!/bin/bash
# Troubleshooting and monitoring script for Loki + Promtail
# Usage: ./troubleshoot-logging.sh

set -e

NAMESPACE="logging"
TIMEOUT=30

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_status() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed"
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  Loki + Promtail Logging Stack Troubleshooting Tool   ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# 1. Check namespace
print_status "Checking logging namespace..."
if kubectl get namespace $NAMESPACE &>/dev/null; then
    print_success "Namespace '$NAMESPACE' exists"
else
    print_error "Namespace '$NAMESPACE' not found"
    exit 1
fi

echo ""

# 2. Check Loki deployment
print_status "Checking Loki deployment..."
LOKI_REPLICAS=$(kubectl get deployment -n $NAMESPACE loki -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
LOKI_READY=$(kubectl get deployment -n $NAMESPACE loki -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")

if [ "$LOKI_REPLICAS" == "0" ]; then
    print_error "Loki deployment not found"
else
    if [ "$LOKI_READY" -eq "$LOKI_REPLICAS" ]; then
        print_success "Loki: $LOKI_READY/$LOKI_REPLICAS replicas ready"
    else
        print_warning "Loki: $LOKI_READY/$LOKI_REPLICAS replicas ready (expected $LOKI_REPLICAS)"
    fi
fi

# 3. Check Promtail DaemonSet
print_status "Checking Promtail DaemonSet..."
PROMTAIL_DESIRED=$(kubectl get daemonset -n $NAMESPACE promtail -o jsonpath='{.status.desiredNumberScheduled}' 2>/dev/null || echo "0")
PROMTAIL_READY=$(kubectl get daemonset -n $NAMESPACE promtail -o jsonpath='{.status.numberReady}' 2>/dev/null || echo "0")

if [ "$PROMTAIL_DESIRED" == "0" ]; then
    print_error "Promtail DaemonSet not found"
else
    if [ "$PROMTAIL_READY" -eq "$PROMTAIL_DESIRED" ]; then
        print_success "Promtail: $PROMTAIL_READY/$PROMTAIL_DESIRED pods ready"
    else
        print_warning "Promtail: $PROMTAIL_READY/$PROMTAIL_DESIRED pods ready (expected $PROMTAIL_DESIRED)"
    fi
fi

echo ""

# 4. Check PVC
print_status "Checking storage..."
PVC_STATUS=$(kubectl get pvc -n $NAMESPACE loki-storage -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
if [ "$PVC_STATUS" == "Bound" ]; then
    print_success "Storage PVC: Bound"
    STORAGE_SIZE=$(kubectl get pvc -n $NAMESPACE loki-storage -o jsonpath='{.status.capacity.storage}' 2>/dev/null)
    STORAGE_USED=$(kubectl exec -n $NAMESPACE deployment/loki -- \
        du -sh /loki 2>/dev/null | awk '{print $1}' || echo "N/A")
    echo "  Size: $STORAGE_SIZE / Used: $STORAGE_USED"
else
    print_warning "Storage PVC: $PVC_STATUS"
fi

echo ""

# 5. Check Loki connectivity
print_status "Checking Loki connectivity..."
LOKI_POD=$(kubectl get pods -n $NAMESPACE -l app=loki -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -z "$LOKI_POD" ]; then
    print_error "Loki pod not found"
else
    if kubectl exec -n $NAMESPACE "$LOKI_POD" -- \
        curl -s http://localhost:3100/loki/api/v1/status/buildinfo >/dev/null 2>&1; then
        print_success "Loki API responding"
        BUILD_INFO=$(kubectl exec -n $NAMESPACE "$LOKI_POD" -- \
            curl -s http://localhost:3100/loki/api/v1/status/buildinfo | grep -o '"version":"[^"]*' | cut -d'"' -f4)
        echo "  Version: $BUILD_INFO"
    else
        print_error "Loki API not responding"
    fi
fi

echo ""

# 6. Check log ingestion
print_status "Checking log ingestion..."
if [ -n "$LOKI_POD" ]; then
    LOG_ENTRIES=$(kubectl exec -n $NAMESPACE "$LOKI_POD" -- \
        curl -s 'http://localhost:3100/loki/api/v1/query?query={job!=""}' | \
        grep -o '"stream":' | wc -l 2>/dev/null || echo "0")
    
    if [ "$LOG_ENTRIES" -gt 0 ]; then
        print_success "Log ingestion active: $LOG_ENTRIES log streams found"
    else
        print_warning "No log streams found (this may be normal for new deployments)"
    fi
fi

echo ""

# 7. Check service logs
print_status "Checking banking services..."
for SERVICE in payment-service transaction-service notification-service; do
    PODS=$(kubectl get pods -l app=$SERVICE -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")
    if [ -z "$PODS" ]; then
        print_warning "Service '$SERVICE': No pods found"
    else
        POD_COUNT=$(echo $PODS | wc -w)
        print_success "Service '$SERVICE': $POD_COUNT pod(s) running"
    fi
done

echo ""

# 8. Check recent errors
print_status "Checking for recent errors..."
echo "  Loki logs:"
kubectl logs -n $NAMESPACE -l app=loki --tail=10 2>/dev/null | grep -i error || echo "    No errors found"

echo "  Promtail logs:"
PROMTAIL_POD=$(kubectl get pods -n $NAMESPACE -l app=promtail -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
if [ -n "$PROMTAIL_POD" ]; then
    kubectl logs -n $NAMESPACE "$PROMTAIL_POD" --tail=10 2>/dev/null | grep -i error || echo "    No errors found"
fi

echo ""

# 9. Port forwarding tips
print_status "Quick access commands..."
echo ""
echo "  Port-forward to Loki:"
echo "    kubectl port-forward -n $NAMESPACE svc/loki 3100:3100 &"
echo ""
echo "  Test Loki API:"
echo "    curl -s http://localhost:3100/loki/api/v1/status/buildinfo | jq ."
echo ""
echo "  Query logs:"
echo "    curl -s 'http://localhost:3100/loki/api/v1/query?query={job=\"payment-service\"}' | jq ."
echo ""
echo "  Watch Promtail logs:"
echo "    kubectl logs -n $NAMESPACE -l app=promtail -f"
echo ""
echo "  Watch Loki logs:"
echo "    kubectl logs -n $NAMESPACE -l app=loki -f"
echo ""

# 10. Common issues
print_status "Checking common issues..."

# Check resource limits
PROMTAIL_CPU=$(kubectl get daemonset -n $NAMESPACE promtail -o jsonpath='{.spec.template.spec.containers[0].resources.limits.cpu}' 2>/dev/null)
PROMTAIL_MEM=$(kubectl get daemonset -n $NAMESPACE promtail -o jsonpath='{.spec.template.spec.containers[0].resources.limits.memory}' 2>/dev/null)
echo "  Promtail limits: CPU=$PROMTAIL_CPU / Memory=$PROMTAIL_MEM"

# Check node status
NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}' 2>/dev/null | wc -w)
NODES_READY=$(kubectl get nodes --no-headers 2>/dev/null | grep -c " Ready " || echo "0")
if [ "$NODES_READY" -eq "$NODES" ]; then
    print_success "All $NODES nodes are ready"
else
    print_warning "$NODES_READY/$NODES nodes are ready"
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║              Troubleshooting Complete                  ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
