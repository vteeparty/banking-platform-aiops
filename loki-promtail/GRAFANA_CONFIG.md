---
# Grafana Datasource Configuration for Loki
# Save as: grafana-provisioning/datasources/loki-datasource.yaml

apiVersion: 1
datasources:
  - name: Loki
    type: loki
    access: proxy
    url: http://loki.logging:3100
    isDefault: true
    editable: true
    jsonData:
      maxLines: 1000
      derivedFields:
        - name: Request ID
          matcherRegex: '"request_id":\s?"([^"]*)"'
          url: '/explore?left={"datasource":"Loki","queries":[{"expr":"{request_id=\\"${__value.raw}\\"}"}]}'
          datasourceName: Loki
        - name: Transaction ID
          matcherRegex: '"transaction_id":\s?"([^"]*)"'
          url: '/explore?left={"datasource":"Loki","queries":[{"expr":"{transaction_id=\\"${__value.raw}\\"}"}]}'
          datasourceName: Loki
        - name: Service
          matcherRegex: '"service":\s?"([^"]*)"'
          url: '/explore?left={"datasource":"Loki","queries":[{"expr":"{job=\\"${__value.raw}\\"} | json"}]}'
          datasourceName: Loki

---
# Dashboard Configuration
# Save as: grafana-provisioning/dashboards/banking-services-dashboard.json
# Or import manually via Grafana UI

{
  "dashboard": {
    "title": "Banking Services - Centralized Logs",
    "tags": ["loki", "banking", "microservices"],
    "timezone": "browser",
    "panels": [
      {
        "title": "Error Rate by Service",
        "targets": [
          {
            "expr": "sum by (job) (rate({level=\"ERROR\"}[5m]))",
            "refId": "A"
          }
        ],
        "type": "timeseries"
      },
      {
        "title": "Log Volume",
        "targets": [
          {
            "expr": "sum(count_over_time({job=~\".*-service\"}[5m]))",
            "refId": "A"
          }
        ],
        "type": "stat"
      },
      {
        "title": "Service Logs",
        "targets": [
          {
            "expr": "{job=~\"payment-service|transaction-service|notification-service\"}",
            "refId": "A"
          }
        ],
        "type": "logs"
      },
      {
        "title": "Recent Errors",
        "targets": [
          {
            "expr": "{level=\"ERROR\"} | json | line_format \"{{.service}}: {{.message}}\"",
            "refId": "A"
          }
        ],
        "type": "logs"
      }
    ]
  }
}
