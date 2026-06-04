# Application Integration Guide

This guide shows how to integrate your microservices with the centralized logging stack.

## Key Requirements

1. **Log Format**: JSON-formatted logs to stdout/stderr
2. **Log Fields**: Consistent field names for better aggregation
3. **Structured Logging**: Extract contextual information (request_id, user_id, etc.)

## Python Integration

### Using Python Logging + JSON Formatter

```python
import json
import logging
import sys
from datetime import datetime
import os

class StructuredLogFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": os.getenv("SERVICE_NAME", "unknown"),
            "message": record.getMessage(),
            "logger": record.name,
        }
        
        # Add request context if available
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        
        # Add service-specific fields
        if hasattr(record, "transaction_id"):
            log_obj["transaction_id"] = record.transaction_id
        if hasattr(record, "notification_type"):
            log_obj["notification_type"] = record.notification_type
            
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj)

# Setup logging
def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredLogFormatter())
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    return logger

logger = setup_logging()

# Example usage
logger.info("Payment processed", extra={"request_id": "req-12345"})
logger.error("Payment failed", extra={
    "request_id": "req-12345",
    "error_code": "INSUFFICIENT_FUNDS"
})
```

### Using Structlog

```python
import structlog
import sys
from datetime import datetime
import os

structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger()

# Usage
logger.info("event", 
    service=os.getenv("SERVICE_NAME"),
    request_id="req-12345",
    amount=100.00
)

# With context
with structlog.contextvars.clear_contextvars():
    structlog.contextvars.bind_contextvars(request_id="req-12345")
    logger.info("Processing payment", amount=100.00)
```

## Go Integration

### Using Go's Built-in Logging + JSON

```go
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"time"
)

type LogEntry struct {
	Timestamp        string      `json:"timestamp"`
	Level            string      `json:"level"`
	Service          string      `json:"service"`
	Message          string      `json:"message"`
	Logger           string      `json:"logger,omitempty"`
	RequestID        string      `json:"request_id,omitempty"`
	TransactionID    string      `json:"transaction_id,omitempty"`
	NotificationType string      `json:"notification_type,omitempty"`
	Error            string      `json:"error,omitempty"`
	Fields           interface{} `json:"fields,omitempty"`
}

func logJSON(level, message, requestID string, extra map[string]interface{}) {
	entry := LogEntry{
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Level:     level,
		Service:   os.Getenv("SERVICE_NAME"),
		Message:   message,
		RequestID: requestID,
		Fields:    extra,
	}
	
	data, _ := json.Marshal(entry)
	fmt.Fprintln(os.Stdout, string(data))
}

func main() {
	logJSON("INFO", "Payment processed", "req-12345", map[string]interface{}{
		"amount": 100.00,
		"status": "success",
	})
}
```

### Using Go's slog (Go 1.21+)

```go
package main

import (
	"log/slog"
	"os"
	"time"
)

func main() {
	// Configure JSON handler
	handler := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	})
	logger := slog.New(handler)
	
	// Usage
	logger.Info("Payment processed",
		slog.String("request_id", "req-12345"),
		slog.Float64("amount", 100.00),
		slog.String("status", "success"),
	)
	
	logger.Error("Payment failed",
		slog.String("request_id", "req-12345"),
		slog.String("error", "INSUFFICIENT_FUNDS"),
	)
}
```

## Node.js Integration

### Using Winston Logger

```javascript
const winston = require('winston');

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  defaultMeta: { 
    service: process.env.SERVICE_NAME || 'unknown',
    timestamp: new Date().toISOString()
  },
  transports: [
    new winston.transports.Stream({ stream: process.stdout })
  ]
});

// Usage
logger.info('Payment processed', {
  request_id: 'req-12345',
  amount: 100.00,
  status: 'success'
});

logger.error('Payment failed', {
  request_id: 'req-12345',
  error_code: 'INSUFFICIENT_FUNDS'
});
```

### Using Pino

```javascript
const pino = require('pino');

const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  transport: {
    target: 'pino/file',
    options: {
      destination: 1, // stdout
      colorize: false
    }
  },
  base: {
    service: process.env.SERVICE_NAME || 'unknown'
  }
});

// Usage
logger.info({ 
  request_id: 'req-12345', 
  amount: 100.00 
}, 'Payment processed');

logger.error({ 
  request_id: 'req-12345', 
  error: 'INSUFFICIENT_FUNDS' 
}, 'Payment failed');
```

## Java Integration

### Using Logback + JSON

**pom.xml**:
```xml
<dependency>
    <groupId>com.google.code.gson</groupId>
    <artifactId>gson</artifactId>
    <version>2.10.1</version>
</dependency>
<dependency>
    <groupId>ch.qos.logback</groupId>
    <artifactId>logback-classic</artifactId>
    <version>1.4.11</version>
</dependency>
```

**logback.xml**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
        <encoder class="net.logstash.logback.encoder.LogstashEncoder">
            <includeContext>true</includeContext>
            <includeMdcKeyName>requestId</includeMdcKeyName>
            <customFields>{"service":"${SERVICE_NAME}"}</customFields>
        </encoder>
    </appender>
    
    <root level="INFO">
        <appender-ref ref="STDOUT" />
    </root>
</configuration>
```

**Java Code**:
```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;

public class PaymentService {
    private static final Logger logger = LoggerFactory.getLogger(PaymentService.class);
    
    public void processPayment(String requestId, double amount) {
        MDC.put("requestId", requestId);
        try {
            logger.info("Payment processed", "amount", amount, "status", "success");
        } finally {
            MDC.clear();
        }
    }
}
```

## Request Tracing Pattern

### Correlation ID Pattern

```python
# middleware.py
import uuid
from contextvars import ContextVar

request_id_context: ContextVar[str] = ContextVar('request_id', default=None)

def get_request_id() -> str:
    """Get or create request ID"""
    request_id = request_id_context.get()
    if not request_id:
        request_id = str(uuid.uuid4())
        request_id_context.set(request_id)
    return request_id

# usage in handler
def payment_handler(request):
    request_id = get_request_id()
    logger.info("Processing payment", extra={"request_id": request_id})
    # ... payment logic
    logger.info("Payment complete", extra={"request_id": request_id})
```

## Testing Log Output

```bash
# Local test - verify JSON format
SERVICE_NAME=payment-service python your_app.py

# Check log format
kubectl logs deployment/payment-service | head -20

# Parse JSON logs
kubectl logs deployment/payment-service | jq '.level, .message, .request_id'

# Filter errors
kubectl logs deployment/payment-service | jq 'select(.level == "ERROR")'
```

## Environment Variables for Containers

```yaml
env:
  - name: SERVICE_NAME
    value: "payment-service"
  - name: LOG_LEVEL
    value: "INFO"
  - name: LOG_FORMAT
    value: "json"
  - name: HOSTNAME
    valueFrom:
      fieldRef:
        fieldPath: metadata.name
  - name: POD_NAMESPACE
    valueFrom:
      fieldRef:
        fieldPath: metadata.namespace
```

## Field Naming Convention

Use consistent field names across services for better querying:

| Field | Type | Example | Usage |
|-------|------|---------|-------|
| timestamp | ISO 8601 | 2026-06-04T10:30:45Z | Time parsing in Loki |
| level | enum | INFO, ERROR, WARN | Log level filtering |
| service | string | payment-service | Service identification |
| message | string | Payment processed | Log content |
| request_id | uuid | req-12345 | Request tracing |
| transaction_id | uuid | txn-67890 | Transaction tracking |
| notification_type | string | EMAIL, SMS | Event classification |
| error_code | string | INSUFFICIENT_FUNDS | Error categorization |
| user_id | string | user-123 | User tracking |
| duration_ms | number | 245 | Performance metrics |

## Performance Considerations

1. **Batch Writes**: Buffer logs before sending
2. **Log Level**: Use INFO in production, DEBUG locally
3. **Sensitive Data**: Never log passwords, tokens, or PII
4. **Context Limits**: Keep request context minimal
5. **Async Logging**: Use background threads for log writing

## Troubleshooting

### Logs Not Appearing

```bash
# Check if logs are being written to stdout
kubectl logs deployment/payment-service

# Verify JSON format
kubectl logs deployment/payment-service | jq '.' | head

# Check Promtail scrape config
kubectl get cm promtail-config -n logging -o yaml
```

### Wrong Service Labels

```bash
# Verify pod labels
kubectl get pods payment-service-xxx -o yaml | grep labels

# Add if missing
kubectl label pod payment-service-xxx app=payment-service --overwrite
```

## References

- [Promtail Documentation](https://grafana.com/docs/loki/latest/clients/promtail/)
- [Python Logging](https://docs.python.org/3/library/logging.html)
- [Go slog](https://pkg.go.dev/log/slog)
- [Node.js Winston](https://github.com/winstonjs/winston)
- [Structured Logging Best Practices](https://www.kartar.net/2015/12/structured-logging/)
