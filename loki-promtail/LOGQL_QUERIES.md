# Common LogQL Queries for Banking Services

## Payment Service Queries

### All Payment Service Logs
```logql
{job="payment-service"}
```

### Payment Service Errors Only
```logql
{job="payment-service", level="ERROR"}
```

### Payment Service Errors in Last Hour
```logql
{job="payment-service", level="ERROR"} | __error__=""
```

### Payment Service by Log Level
```logql
{job="payment-service"} | pattern "<level>"
```

### Payment Latency (if in logs)
```logql
{job="payment-service"} | json | duration > 1000ms
```

### Track Specific Request
```logql
{request_id="req-12345"}
```

## Transaction Service Queries

### All Transaction Logs
```logql
{job="transaction-service"}
```

### Transactions by Status
```logql
{job="transaction-service", level="ERROR"}
```

### Track Transaction Flow
```logql
{job="transaction-service", transaction_id="txn-67890"}
```

### Transactions in Last 5 Minutes
```logql
{job="transaction-service"} | __error__=""
```

### High-Value Transactions (if in logs)
```logql
{job="transaction-service"} | json | amount > 10000
```

## Notification Service Queries

### All Notification Service Logs
```logql
{job="notification-service"}
```

### Notifications by Type
```logql
{job="notification-service", notification_type="EMAIL"}
```

### Failed Notifications
```logql
{job="notification-service", level="ERROR"}
```

### Notification Delivery Status
```logql
{job="notification-service"} | json | status="delivered"
```

## Cross-Service Queries

### Errors Across All Services
```logql
{level="ERROR"}
```

### All Services (Payment + Transaction + Notification)
```logql
{job=~"payment-service|transaction-service|notification-service"}
```

### Service Availability
```logql
avg by (job) (rate({job=~".*-service"}[5m]))
```

### Error Rate by Service
```logql
sum by (job) (rate({level="ERROR"}[5m]))
```

### Request Success Rate
```logql
sum by (job) (rate({level!="ERROR"}[5m])) / sum by (job) (rate({job=~".*-service"}[5m]))
```

### Performance by Service (avg response time)
```logql
avg by (job) (rate({job=~".*-service", level="INFO"} | json | duration [5m]))
```

## Metric Extraction

### Count Errors in Last Hour
```logql
count_over_time({level="ERROR"}[1h])
```

### Error Rate Over Time
```logql
rate({level="ERROR"}[5m])
```

### Logs Per Service
```logql
sum by (job) (count_over_time({job!=""}[5m]))
```

### Top Error Types
```logql
topk(10, sum by (error_type) (count_over_time({level="ERROR"}[1h])))
```

## Advanced Queries

### Complex Request Tracing
```logql
{request_id=~"req-.*"} 
| json 
| service=~".*service" 
| (level="INFO" or level="ERROR")
```

### Multi-Step Transaction Tracking
```logql
{transaction_id=~"txn-.*"} 
| json 
| line_format "{{.timestamp}} {{.service}}: {{.message}}"
```

### Performance Analysis
```logql
{job="payment-service"} 
| json 
| unwrap duration 
| __error__="" 
| quantile_over_time(0.95, [5m])
```

### Exception Messages
```logql
{level="ERROR"} 
| json 
| line_format "{{.service}} - {{.message}}"
```

## Grafana Dashboard Queries

### Panel: Service Error Count
```logql
sum by (job) (rate({level="ERROR"}[5m]))
```

### Panel: Request Rate
```logql
sum by (job) (rate({job=~".*-service"}[1m]))
```

### Panel: Log Volume Over Time
```logql
sum(count_over_time({job=~".*-service"}[5m]))
```

### Panel: Service Availability
```logql
sum by (job) (rate({job=~".*-service", level!="ERROR"}[5m])) 
/ 
sum by (job) (rate({job=~".*-service"}[5m]))
```

### Panel: Latest Errors
```logql
{level="ERROR"} | json | line_format "{{.service}}: {{.message}}"
```

## Tips & Tricks

1. **Use pipe operators** for filtering and formatting:
   ```logql
   {job="payment-service"} | json | level="ERROR"
   ```

2. **Pattern matching** for unstructured logs:
   ```logql
   {job="payment-service"} | pattern "<ip> - <user> [<timestamp>] \"<method> <path>\" <status>"
   ```

3. **Multiple conditions**:
   ```logql
   {job="payment-service", level="ERROR"} | "timeout"
   ```

4. **Exclude patterns**:
   ```logql
   {job="payment-service"} | "200 OK" = ""
   ```

5. **Extract and format**:
   ```logql
   {job="payment-service"} | json | line_format "{{.timestamp}} - {{.level}} - {{.message}}"
   ```

6. **Aggregation over time**:
   ```logql
   sum by (level) (count_over_time({job="payment-service"}[1h]))
   ```

7. **Rate calculation**:
   ```logql
   rate({level="ERROR"}[5m])  # per second
   rate({level="ERROR"}[1m]) * 60  # per minute
   ```

## Testing Queries

```bash
# Port-forward to Loki
kubectl port-forward -n logging svc/loki 3100:3100 &

# Test query endpoint
curl -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={job="payment-service"}' | jq

# Query range (time range)
curl -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={job="payment-service"}' \
  --data-urlencode 'start=3600s' \
  --data-urlencode 'end=0s' | jq
```
