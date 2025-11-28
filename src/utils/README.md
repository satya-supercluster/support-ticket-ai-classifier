# Logging & Monitoring Usage Guide

## Overview

You now have comprehensive **logging and monitoring** modules that provide:

- ✅ **Structured JSON logging** - Machine-readable logs
- ✅ **Azure Application Insights integration** - Cloud monitoring
- ✅ **Prometheus metrics** - Industry-standard metrics
- ✅ **Performance tracking** - Automatic duration monitoring
- ✅ **Error tracking** - Centralized error recording
- ✅ **Health checks** - System health monitoring

---

## Files Created

### 1. `src/utils/logging.py`

- Structured logging with JSON format
- Azure Application Insights integration
- Context managers for contextual logging
- Performance logging helpers
- Custom formatters

### 2. `src/utils/monitoring.py`

- Prometheus metrics (counters, histograms, gauges)
- Azure metrics exporter
- Decorators for automatic monitoring
- Health check system
- Metrics aggregation

---

## Quick Start

### Basic Logging

```python
from utils.logging import get_logger

logger = get_logger(__name__)

# Simple logging
logger.info("Application started")
logger.warning("Low memory warning")
logger.error("Failed to connect to database")
```

### Structured Logging

```python
from utils.logging import get_logger

logger = get_logger(__name__)

# Add structured data
logger.info(
    "Ticket classified",
    extra={
        'ticket_id': 'TKT-001',
        'category': 'Technical',
        'priority': 'High',
        'confidence': 0.95
    }
)
```

**Output (JSON):**

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "logger": "classifier",
  "message": "Ticket classified",
  "ticket_id": "TKT-001",
  "category": "Technical",
  "priority": "High",
  "confidence": 0.95,
  "application": "AI Ticket Classifier",
  "version": "1.0.0"
}
```

### Context Logging

```python
from utils.logging import get_logger, LogContext

logger = get_logger(__name__)

with LogContext(ticket_id="TKT-001", user="admin@example.com"):
    logger.info("Starting processing")
    # ... do work ...
    logger.info("Processing complete")

# Both log messages will include ticket_id and user automatically
```

### Performance Logging

```python
from utils.logging import get_logger, PerformanceLogger

logger = get_logger(__name__)

with PerformanceLogger("classification", logger, ticket_id="TKT-001"):
    result = classify_ticket(ticket)
    # Automatically logs: "classification completed in 1234ms"
```

---

## Monitoring with Decorators

### Monitor Classification

```python
from utils.monitoring import monitor_classification

@monitor_classification
async def classify_ticket(ticket: TicketInput) -> ClassificationOutput:
    # Your classification logic
    result = await classifier.classify_ticket(ticket)
    return result

# Automatically tracks:
# - Duration
# - Success/failure
# - Category distribution
# - Confidence scores
```

### Monitor API Requests

```python
from fastapi import FastAPI
from utils.monitoring import monitor_api_request

app = FastAPI()

@app.post("/classify")
@monitor_api_request
async def classify_endpoint(ticket_data: dict):
    # Your endpoint logic
    return classification_result

# Automatically tracks:
# - Request count
# - Response time
# - Status codes
# - Error rates
```

### Monitor Custom Operations

```python
from utils.monitoring import monitor_performance

@monitor_performance("database_query")
async def fetch_tickets_from_db():
    # Your database logic
    return tickets

# Tracks duration and errors for this operation
```

---

## Manual Metrics Recording

```python
from utils.monitoring import MetricsRecorder

# Record classification
MetricsRecorder.record_classification(
    category="Technical",
    priority="High",
    confidence=0.95,
    duration_seconds=1.234,
    success=True
)

# Record evaluation
MetricsRecorder.record_evaluation(
    evaluation_score=0.92,
    category_correct=True,
    priority_correct=True
)

# Record error
MetricsRecorder.record_error(
    error_type="ValueError",
    operation="classification"
)
```

---

## Integration with FastAPI

### Updated main.py with Logging & Monitoring

```python
from fastapi import FastAPI, Request
from utils.logging import get_logger, PerformanceLogger, log_classification
from utils.monitoring import (
    monitor_classification, 
    monitor_api_request,
    get_prometheus_metrics,
    health_checker
)

logger = get_logger(__name__)
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")

@app.get("/health")
async def health_check():
    """Enhanced health check with system checks"""
    health_status = health_checker.check_health()
    return health_status

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from starlette.responses import Response
    return Response(
        content=get_prometheus_metrics(),
        media_type="text/plain"
    )

@app.post("/classify")
@monitor_api_request
async def classify_ticket_endpoint(ticket_data: dict, request: Request):
    """Classify a ticket with full logging and monitoring"""
    
    # Create ticket
    ticket = TicketInput(**ticket_data)
    
    logger.info(
        "Received classification request",
        extra={'ticket_id': ticket.ticket_id}
    )
    
    # Classify with performance monitoring
    with PerformanceLogger("classification", logger, ticket_id=ticket.ticket_id):
        classification = await classify_ticket(ticket)
    
    # Log classification result
    log_classification(
        logger=logger,
        ticket_id=ticket.ticket_id,
        category=classification.category,
        priority=classification.priority,
        confidence=classification.confidence,
        duration_ms=1234  # You would calculate this
    )
    
    return classification
```

---

## Prometheus Metrics Available

### Counters

- `ticket_classifications_total{category, priority, status}` - Total classifications
- `ticket_evaluations_total{result}` - Total evaluations
- `errors_total{error_type, operation}` - Total errors
- `api_requests_total{method, endpoint, status_code}` - Total API requests

### Histograms

- `classification_duration_seconds{category}` - Classification time distribution
- `evaluation_duration_seconds` - Evaluation time distribution
- `api_request_duration_seconds{method, endpoint}` - API response time

### Gauges

- `active_classifications` - Current classifications in progress
- `classification_confidence_current{category}` - Latest confidence score

### Example Prometheus Queries

```promql
# Average classification time by category
rate(classification_duration_seconds_sum[5m]) 
/ 
rate(classification_duration_seconds_count[5m])

# Error rate
rate(errors_total[5m])

# Classifications per minute
rate(ticket_classifications_total[1m]) * 60

# 95th percentile response time
histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))
```

---

## Azure Application Insights Queries

### View All Classifications

```kusto
traces
| where customDimensions.event_type == "classification"
| project 
    timestamp,
    ticket_id = customDimensions.ticket_id,
    category = customDimensions.category,
    priority = customDimensions.priority,
    confidence = customDimensions.confidence,
    duration_ms = customDimensions.duration_ms
| order by timestamp desc
```

### Error Analysis

```kusto
traces
| where severityLevel >= 3  // Error and above
| summarize count() by 
    tostring(customDimensions.error_type),
    tostring(customDimensions.operation)
| order by count_ desc
```

### Performance Trends

```kusto
traces
| where customDimensions.event_type == "classification"
| extend duration = todouble(customDimensions.duration_ms)
| summarize 
    avg_duration = avg(duration),
    p95_duration = percentile(duration, 95),
    count = count()
  by bin(timestamp, 5m)
| render timechart
```

### Category Distribution

```kusto
traces
| where customDimensions.event_type == "classification"
| summarize count() by tostring(customDimensions.category)
| render piechart
```

---

## Health Checks

### Register Custom Health Checks

```python
from utils.monitoring import health_checker

def check_database_connection() -> bool:
    """Check if database is accessible"""
    try:
        # Your database check logic
        return True
    except Exception:
        return False

def check_openai_availability() -> bool:
    """Check if OpenAI API is accessible"""
    try:
        # Your OpenAI check logic
        return True
    except Exception:
        return False

# Register checks
health_checker.register_check('database', check_database_connection)
health_checker.register_check('openai', check_openai_availability)
```

### Health Check Response

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.123Z",
  "checks": {
    "metrics": {
      "status": "healthy",
      "timestamp": "2024-01-15T10:30:00.123Z"
    },
    "database": {
      "status": "healthy",
      "timestamp": "2024-01-15T10:30:00.124Z"
    },
    "openai": {
      "status": "healthy",
      "timestamp": "2024-01-15T10:30:00.125Z"
    }
  }
}
```

---

## Best Practices

### 1. Use Appropriate Log Levels

```python
logger.debug("Detailed diagnostic info")     # Development only
logger.info("Normal operation events")       # Production
logger.warning("Warning but not critical")   # Production
logger.error("Error occurred")               # Production
logger.critical("Critical system failure")   # Production
```

### 2. Include Context in Logs

```python
# Bad
logger.info("Processing ticket")

# Good
logger.info(
    "Processing ticket",
    extra={
        'ticket_id': ticket.ticket_id,
        'category': ticket.category,
        'user': user.email
    }
)
```

### 3. Use Helper Functions

```python
from utils.logging import log_classification, log_error

# Instead of manual logging
log_classification(
    logger=logger,
    ticket_id=ticket.ticket_id,
    category=result.category,
    priority=result.priority,
    confidence=result.confidence,
    duration_ms=duration
)

# For errors
try:
    result = process()
except Exception as e:
    log_error(
        logger=logger,
        error=e,
        operation="processing",
        ticket_id=ticket.ticket_id
    )
```

### 4. Monitor Critical Paths

```python
# Use decorators for important functions
@monitor_classification
@monitor_performance("critical_operation")
async def critical_function():
    pass
```

### 5. Regular Metrics Review

- Check error rates daily
- Review performance trends weekly
- Analyze category distribution monthly
- Set up alerts for anomalies

---

## Environment Configuration

### Development (.env)

```bash
LOG_LEVEL=DEBUG
APPLICATIONINSIGHTS_CONNECTION_STRING=  # Optional in dev
```

### Production (.env)

```bash
LOG_LEVEL=INFO
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=xxx;IngestionEndpoint=https://...
```

---

## Grafana Dashboard (Optional)

Create a Grafana dashboard using Prometheus data source:

### Panel 1: Classifications per Minute

```promql
rate(ticket_classifications_total[1m]) * 60
```

### Panel 2: Average Response Time

```promql
rate(api_request_duration_seconds_sum[5m]) 
/ 
rate(api_request_duration_seconds_count[5m])
```

### Panel 3: Error Rate

```promql
rate(errors_total[5m])
```

### Panel 4: Active Classifications

```promql
active_classifications
```

---

## Troubleshooting

### Logs Not Appearing

**Check:**

1. Log level is appropriate (DEBUG, INFO, etc.)
2. File permissions for log directory
3. Application Insights connection string is valid

```python
# Verify logging is configured
import logging
logging.getLogger().handlers  # Should show handlers
```

### Metrics Not Updating

**Check:**

1. Prometheus endpoint `/metrics` is accessible
2. Decorators are applied correctly
3. Functions are actually being called

```python
# Test metrics manually
from utils.monitoring import classification_counter
classification_counter.labels(category='Test', priority='High', status='success').inc()
```

### Azure Insights Not Receiving Data

**Check:**

1. Connection string is correct
2. Network connectivity to Azure
3. Instrumentation key is valid

```bash
# Test connection
curl https://dc.services.visualstudio.com/v2/track -d '{}'
```

---

## Summary

You now have:

✅ **Structured JSON Logging**

- Development-friendly format
- Production JSON format
- Azure integration

✅ **Prometheus Metrics**

- 8+ metric types
- Automatic collection
- Industry-standard format

✅ **Performance Monitoring**

- Automatic duration tracking
- Error tracking
- Distribution analysis

✅ **Health Checks**

- System health monitoring
- Custom check registration
- Status endpoints

✅ **Azure Integration**

- Application Insights
- Custom metrics
- Log analytics

This is **production-grade observability** that will help you understand your system's behavior, troubleshoot issues, and optimize performance! 🚀
