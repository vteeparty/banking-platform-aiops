# Centralized Logging Setup for Banking Microservices

This setup provides a complete centralized logging solution using **Grafana Loki** and **Promtail** for your Kubernetes microservices. The configuration is optimized for Minikube and resource-constrained environments.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│              Kubernetes Cluster (Minikube)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Logging Namespace                                           │
│  ┌────────────────────────────────────────────────────┐     │
│  │                                                    │     │
│  │  Promtail DaemonSet (on each node)                │     │
│  │  ├─ Reads logs from:                              │     │
│  │  │  ├─ /var/log/*                                 │     │
│  │  │  ├─ /var/lib/docker/containers/*               │     │
│  │  │  └─ Kubernetes API discovery                   │     │
│  │  │                                                │     │
│  │  └─ Pushes to → Loki Service (3100)              │     │
│  │                                                    │     │
│  │  Loki Deployment (1 replica)                      │     │
│  │  ├─ Ingests logs via HTTP API                     │     │
│  │  ├─ Stores in filesystem (PVC)                    │     │
│  │  ├─ Processes log lines and labels                │     │
│  │  └─ Queryable via LogQL                           │     │
│  │                                                    │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  Default Namespace                                           │
│  ┌────────────────────────────────────────────────────┐     │
│  │                                                    │     │
│  │  ┌──────────────────┐   ┌──────────────────┐     │     │
│  │  │ Payment Service  │   │ Transaction Srv  │     │     │
│  │  │ (2 replicas)     │   │ (2 replicas)     │     │     │
│  │  │ stdout → logs    │   │ stdout → logs    │     │     │
│  │  └──────────────────┘   └──────────────────┘     │     │
│  │                                                    │     │
│  │  ┌──────────────────┐                             │     │
│  │  │Notification Srv  │                             │     │
│  │  │ (2 replicas)     │                             │     │
│  │  │ stdout → logs    │                             │     │
│  │  └──────────────────┘                             │     │
│  │                                                    │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Components

### Loki
- **Role**: Central log aggregation and storage backend
- **Image**: `grafana/loki:2.9.3`
- **Deployment**: Single instance (StatefulSet alternative possible)
- **Storage**: 10GB PVC using Minikube's `standard` storage class
- **Features**:
  - In-memory ring for data locality
  - Filesystem-based storage (Minikube compatible)
  - BoltDB index with shipper for log retrieval
  - Compression (gzip) to reduce storage
  - Rate limiting to prevent overload

### Promtail
- **Role**: Log shipper and pipeline processor
- **Image**: `grafana/promtail:2.9.3`
- **Deployment**: DaemonSet (one pod per node)
- **Features**:
  - Kubernetes service discovery (auto-finds pods)
  - JSON log parsing and label extraction
  - Timestamp normalization
  - Resource-light (50m CPU, 64MB memory minimum)

### Services
Three banking microservices configured for centralized logging:
- **Payment Service**: Handles payment processing
- **Transaction Service**: Manages transactions with unique tracking
- **Notification Service**: Sends notifications with type tracking

## File Structure

```
loki-promtail/
├── loki-config.yaml              # Standalone Loki config
├── promtail-config.yaml          # Standalone Promtail config
├── loki-deployment.yaml          # Kubernetes manifest for Loki
├── promtail-daemonset.yaml       # Kubernetes manifest for Promtail
├── service-manifests/
│   └── banking-services.yaml     # Deployment manifests for three services
└── README.md                      # This file
```

## Quick Start

### Prerequisites
- Minikube running with at least 4GB memory
- `kubectl` configured
- Grafana installed (for visualization)

### 1. Deploy Logging Infrastructure

```bash
# Create logging namespace and deploy Loki
kubectl apply -f loki-deployment.yaml

# Deploy Promtail DaemonSet
kubectl apply -f promtail-daemonset.yaml

# Verify deployment
kubectl get pods -n logging
kubectl logs -n logging -l app=loki --tail=50
```

### 2. Deploy Banking Services

```bash
# Deploy services with logging enabled
kubectl apply -f service-manifests/banking-services.yaml

# Verify services
kubectl get pods -l app=payment-service
kubectl get pods -l app=transaction-service
kubectl get pods -l app=notification-service
```

### 3. Verify Log Collection

```bash
# Check Promtail is collecting logs
kubectl logs -n logging -l app=promtail --tail=100

# Check Loki is receiving logs
kubectl exec -n logging -it deployment/loki -- \
  curl -s http://localhost:3100/loki/api/v1/status/buildinfo | jq
```

## Querying Logs

### Via LogQL (Loki Query Language)

```logql
# Get all logs
{job="payment-service"}

# Filter by level
{job="payment-service", level="ERROR"}

# Search for specific request
{request_id="abc123"}

# Get transaction logs with ID
{job="transaction-service", transaction_id!=""}

# Aggregate error counts
sum by (level) (count_over_time({service="payment-service"}[5m]))
```

### Integration with Grafana

1. **Add Data Source**:
   - URL: `http://loki.logging:3100`
   - Type: Loki

2. **Sample Dashboards**:
   - Service logs by level
   - Error rates per service
   - Request tracing via `request_id`

## Log Format Requirements

Services must output JSON-formatted logs to stdout/stderr:

```json
{
  "timestamp": "2026-06-04T10:30:45Z",
  "level": "INFO",
  "service": "payment-service",
  "message": "Payment processed successfully",
  "request_id": "req-12345",
  "transaction_id": "txn-67890"
}
```

### Python Example

```python
import json
import logging
import sys
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": "payment-service",
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", ""),
        }
        return json.dumps(log_obj)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logger = logging.getLogger(__name__)
logger.addHandler(handler)
```

### Go Example

```go
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"time"
)

type LogEntry struct {
	Timestamp   string `json:"timestamp"`
	Level       string `json:"level"`
	Service     string `json:"service"`
	Message     string `json:"message"`
	RequestID   string `json:"request_id,omitempty"`
}

func logJSON(level, message, requestID string) {
	entry := LogEntry{
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Level:     level,
		Service:   "payment-service",
		Message:   message,
		RequestID: requestID,
	}
	data, _ := json.Marshal(entry)
	fmt.Fprintln(os.Stdout, string(data))
}
```

## Configuration Details

### Loki Storage
- **Backend**: Filesystem (local PVC)
- **Retention**: Disabled (logs kept indefinitely)
- **Chunk Encoding**: gzip compression
- **Index**: BoltDB with daily rotation

### Promtail Pipeline Stages

1. **JSON Stage**: Parses JSON to extract fields
2. **Labels Stage**: Adds labels for filtering and grouping
3. **Timestamp Stage**: Normalizes timestamps
4. **Output Stage**: Sets log line content

### Service Discovery

Promtail uses Kubernetes SD with pod label matching:

```yaml
relabel_configs:
  - source_labels: [__meta_kubernetes_pod_label_app]
    action: keep
    regex: payment-service
```

This automatically discovers pods labeled `app=payment-service`.

## Troubleshooting

### Logs Not Appearing in Loki

```bash
# Check Promtail logs
kubectl logs -n logging -l app=promtail -f

# Check network connectivity
kubectl exec -n logging promtail-xxxxx -- \
  curl -v http://loki.logging:3100/loki/api/v1/push

# Verify service discovery
kubectl get pods -A --show-labels | grep payment-service
```

### High Memory Usage

Reduce Promtail memory limits if needed:
```yaml
resources:
  limits:
    memory: 128Mi  # Reduce if needed
```

### Disk Space Issues

Check PVC usage:
```bash
kubectl exec -n logging -it deployment/loki -- \
  df -h /loki
```

Expand PVC if needed:
```bash
kubectl patch pvc loki-storage -n logging -p \
  '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
```

## Performance Tuning

### For Minikube (4GB RAM)
- Loki replicas: 1
- Promtail memory limit: 256Mi
- Log retention: Unlimited (consider time-based limits)
- Chunk age: 1 hour

### For Production (8GB+ RAM)
- Loki replicas: 3 (with StatefulSet)
- Promtail memory limit: 512Mi
- Log retention: 7-30 days
- Add Loki caching layer

## Network Policies (Optional)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: loki-netpol
  namespace: logging
spec:
  podSelector:
    matchLabels:
      app: loki
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: logging
      ports:
        - protocol: TCP
          port: 3100
```

## Cleanup

```bash
# Remove all logging infrastructure
kubectl delete namespace logging

# Remove services (if needed)
kubectl delete -f service-manifests/banking-services.yaml
```

## Security Considerations

1. **RBAC**: Promtail uses ServiceAccount with minimal required permissions
2. **Network**: Restrict Loki access using NetworkPolicies
3. **Logs**: No auth_enabled (set to true in production with auth_config)
4. **Storage**: PVC uses default SC (add encryption in production)

## Next Steps

1. **Add Promtail Scrape Config** for custom applications
2. **Implement Log Retention** policies
3. **Configure Grafana** dashboards and alerts
4. **Set up Loki Retention** with time-based purging
5. **Add TLS** for secure communication
6. **Implement Log-Based Metrics** with metric_relabel_configs

## Support & Documentation

- [Loki Documentation](https://grafana.com/docs/loki/)
- [Promtail Configuration](https://grafana.com/docs/loki/latest/clients/promtail/configuration/)
- [LogQL Guide](https://grafana.com/docs/loki/latest/logql/)
- [Kubernetes Monitoring](https://grafana.com/docs/loki/latest/clients/promtail/scrape_configs/kubernetes/)
