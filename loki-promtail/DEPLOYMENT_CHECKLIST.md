# Deployment Checklist & Quick Reference

## Pre-Deployment Checklist

- [ ] Minikube running with sufficient resources (4GB+ RAM)
- [ ] kubectl configured and accessible
- [ ] All YAML files reviewed and customized for your environment
- [ ] Service Docker images available in registry
- [ ] Grafana installed and configured (optional but recommended)
- [ ] Network policies reviewed (if using)

## Deployment Steps

### Step 1: Deploy Logging Infrastructure

```bash
# Navigate to loki-promtail directory
cd loki-promtail

# Option A: Manual deployment
kubectl apply -f loki-deployment.yaml
kubectl apply -f promtail-daemonset.yaml

# Option B: Using deployment script
chmod +x deploy-logging.sh
./deploy-logging.sh

# Verify deployment
kubectl get pods -n logging
kubectl get pvc -n logging
```

**Expected Output**:
```
NAME                    READY   STATUS    RESTARTS   AGE
loki-xxxxx              1/1     Running   0          2m
promtail-xxxxx          1/1     Running   0          1m
promtail-yyyyy          1/1     Running   0          1m
...
```

### Step 2: Deploy Banking Services

```bash
# Deploy payment, transaction, and notification services
kubectl apply -f service-manifests/banking-services.yaml

# Verify deployment
kubectl get deployments
kubectl get pods -l app=payment-service
kubectl get pods -l app=transaction-service
kubectl get pods -l app=notification-service
```

### Step 3: Verify Log Collection

```bash
# Check Loki is receiving logs
kubectl exec -n logging -it deployment/loki -- \
  curl -s http://localhost:3100/loki/api/v1/status/buildinfo | jq

# Check available log streams
kubectl exec -n logging -it deployment/loki -- \
  curl -s 'http://localhost:3100/loki/api/v1/label' | jq

# Test query
kubectl port-forward -n logging svc/loki 3100:3100 &
curl 'http://localhost:3100/loki/api/v1/query?query={job="payment-service"}' | jq
```

## Quick Reference

### View Logs

**All logs from a service**:
```bash
kubectl logs deployment/payment-service
```

**Stream logs**:
```bash
kubectl logs deployment/payment-service -f
```

**From specific pod**:
```bash
kubectl logs payment-service-xxxxx
```

**Multiple services**:
```bash
kubectl logs -l app=payment-service -l app=transaction-service --all-containers=true
```

### Access Loki

**Port forward**:
```bash
kubectl port-forward -n logging svc/loki 3100:3100
```

**Test health**:
```bash
curl http://localhost:3100/loki/ready
curl http://localhost:3100/loki/api/v1/status/buildinfo | jq
```

### Common Queries

```bash
# All logs
{job="payment-service"}

# Errors only
{job="payment-service", level="ERROR"}

# Specific request
{request_id="req-12345"}

# Across all services
{job=~".*-service"}
```

### Monitor Deployment

**Check pod status**:
```bash
kubectl get pods -n logging
kubectl describe pod -n logging loki-xxxxx
```

**Check events**:
```bash
kubectl get events -n logging
```

**Check resource usage**:
```bash
kubectl top pods -n logging
kubectl top nodes
```

### Scale Services

**Scale payment service**:
```bash
kubectl scale deployment payment-service --replicas=3
```

**Scale all services**:
```bash
kubectl scale deployment -l app=payment-service --replicas=3
kubectl scale deployment -l app=transaction-service --replicas=3
kubectl scale deployment -l app=notification-service --replicas=3
```

## Common Commands

| Command | Purpose |
|---------|---------|
| `kubectl apply -f file.yaml` | Deploy manifest |
| `kubectl delete -f file.yaml` | Remove deployment |
| `kubectl logs pod-name` | View pod logs |
| `kubectl exec -it pod-name -- bash` | Connect to pod |
| `kubectl port-forward svc/loki 3100:3100` | Access service locally |
| `kubectl get pods -w` | Watch pod changes |
| `kubectl describe pod pod-name` | Get pod details |
| `kubectl rollout restart deployment/name` | Restart deployment |

## Performance Tuning

### For Minikube (4GB RAM)

**Keep settings**:
- Loki replicas: 1
- Promtail memory: 256Mi
- Log retention: Unlimited
- Chunk size: 1h

### For 8GB+ Environment

**Increase limits**:
- Loki replicas: 3
- Promtail memory: 512Mi
- Add retention policies
- Reduce chunk size to 30m

## Troubleshooting Quick Reference

### Issue: Pods not starting

```bash
# Check events
kubectl describe pod <pod-name> -n logging

# Check logs
kubectl logs <pod-name> -n logging
```

### Issue: No logs in Loki

```bash
# Verify Promtail is running
kubectl get pods -n logging -l app=promtail

# Check Promtail logs
kubectl logs -n logging -l app=promtail --tail=50

# Verify pod labels
kubectl get pods --show-labels
```

### Issue: High memory usage

```bash
# Check memory usage
kubectl top pods -n logging

# Reduce limits in promtail-daemonset.yaml
# and restart deployment
```

### Issue: Storage full

```bash
# Check usage
kubectl exec -n logging deployment/loki -- du -sh /loki

# Expand PVC
kubectl patch pvc loki-storage -n logging \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
```

## File Locations

```
loki-promtail/
├── loki-config.yaml              # Configuration file (reference)
├── promtail-config.yaml          # Configuration file (reference)
├── loki-deployment.yaml          # Deploy Loki (use this)
├── promtail-daemonset.yaml       # Deploy Promtail (use this)
├── service-manifests/
│   └── banking-services.yaml     # Deploy services
├── README.md                      # Full documentation
├── LOGQL_QUERIES.md              # Query examples
├── GRAFANA_CONFIG.md             # Grafana setup
├── APPLICATION_INTEGRATION.md    # App integration guide
├── deploy-logging.sh             # Auto-deployment script
├── troubleshoot-logging.sh       # Troubleshooting script
└── DEPLOYMENT_CHECKLIST.md       # This file
```

## Useful Links

- [Loki Documentation](https://grafana.com/docs/loki/)
- [Promtail Docs](https://grafana.com/docs/loki/latest/clients/promtail/)
- [LogQL Reference](https://grafana.com/docs/loki/latest/logql/)
- [Kubernetes Logging Architecture](https://kubernetes.io/docs/concepts/cluster-administration/logging/)
- [Grafana Datasource Setup](https://grafana.com/docs/grafana/latest/datasources/loki/)

## Recovery Procedures

### Reset Everything

```bash
# Delete logging namespace (removes all Loki/Promtail resources)
kubectl delete namespace logging

# Reapply from scratch
kubectl apply -f loki-deployment.yaml
kubectl apply -f promtail-daemonset.yaml
```

### Clear Loki Logs

```bash
# Scale down Loki
kubectl scale deployment loki -n logging --replicas=0

# Delete PVC
kubectl delete pvc loki-storage -n logging

# Scale up Loki
kubectl scale deployment loki -n logging --replicas=1
```

### Update Configuration

```bash
# Edit ConfigMap
kubectl edit cm loki-config -n logging
kubectl edit cm promtail-config -n logging

# Restart pods to apply changes
kubectl rollout restart deployment/loki -n logging
kubectl rollout restart daemonset/promtail -n logging
```

## Support Resources

- Check logs: `kubectl logs -n logging -l app=loki`
- Promtail status: `kubectl logs -n logging -l app=promtail`
- Events: `kubectl get events -n logging`
- Pod descriptions: `kubectl describe pod -n logging <pod-name>`

## Environment Customization

Edit service manifests to customize:

```yaml
env:
  - name: SERVICE_NAME
    value: "payment-service"  # Change service name
  - name: LOG_LEVEL
    value: "INFO"             # Set log level
  - name: LOG_FORMAT
    value: "json"             # Log format
```

## Validation

After deployment, verify:

1. **Loki Pod Running**:
   ```bash
   kubectl get pods -n logging -l app=loki
   ```

2. **Promtail DaemonSet Active**:
   ```bash
   kubectl get daemonset -n logging
   ```

3. **Services Deployed**:
   ```bash
   kubectl get deployments
   ```

4. **Logs Being Collected**:
   ```bash
   kubectl logs deployment/payment-service | head
   ```

5. **Loki API Accessible**:
   ```bash
   kubectl port-forward -n logging svc/loki 3100:3100 &
   curl http://localhost:3100/loki/ready
   ```

All green ✓ → Deployment successful!
