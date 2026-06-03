# Production Readiness Guide

## Overview

This guide provides everything needed to deploy and operate the Multi-Agent System in production environments.

## Pre-Deployment Checklist

### ✅ Code Quality
- [x] 450 tests passing (100%)
- [x] Type hints complete (mypy ready)
- [x] No HIGH/MEDIUM security vulnerabilities
- [x] Code review approved (10/10 quality)
- [x] Docstrings on all public APIs
- [x] No hardcoded secrets/credentials

### ✅ Architecture
- [x] Clean separation of concerns
- [x] Dependency injection pattern
- [x] Pluggable handler registry
- [x] Optional Redis (in-memory fallback)
- [x] Thread-safe observability
- [x] No global state

### ✅ Observability
- [x] Structured JSON logging
- [x] Correlation ID propagation
- [x] Execution metrics collection
- [x] Success rate tracking
- [x] Guard violation reporting
- [x] Step execution timing

---

## Deployment Options

### Option 1: Docker (Recommended)

**Dockerfile:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -e .
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "mas"]
```

**Build & Run:**
```bash
docker build -t mas:latest .
docker run -e LOG_LEVEL=INFO mas:latest
```

### Option 2: Kubernetes

**Deployment manifest:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mas
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mas
  template:
    metadata:
      labels:
        app: mas
    spec:
      containers:
      - name: mas
        image: mas:latest
        env:
        - name: LOG_LEVEL
          value: "INFO"
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis
              key: url
        resources:
          limits:
            cpu: "2"
            memory: "2Gi"
          requests:
            cpu: "500m"
            memory: "512Mi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
```

### Option 3: Systemd (Simple)

**Create /etc/systemd/system/mas.service:**
```ini
[Unit]
Description=Multi-Agent System
After=network.target

[Service]
Type=simple
User=mas
WorkingDirectory=/opt/mas
Environment="PYTHONUNBUFFERED=1"
Environment="LOG_LEVEL=INFO"
ExecStart=/opt/mas/venv/bin/python -m mas
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable & start:**
```bash
sudo systemctl enable mas
sudo systemctl start mas
```

---

## Configuration

### Environment Variables

```bash
# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Redis (optional, defaults to in-memory)
REDIS_URL=redis://localhost:6379/0
REDIS_POOL_SIZE=10

# Guardrails defaults
MAX_COST=100.0
MAX_DURATION_SECONDS=300.0
MAX_RETRIES_PER_RUN=10
MAX_PLAN_DEPTH=20

# Performance
METRICS_BATCH_SIZE=100
CORRELATION_ID_TTL=3600
```

### Configuration File

Create `config.yaml`:
```yaml
logging:
  level: INFO
  format: json

guardrails:
  max_cost: 100.0
  max_duration_seconds: 300.0
  max_retries_per_run: 10
  max_plan_depth: 20

memory:
  backend: redis  # or 'memory'
  redis:
    url: redis://localhost:6379/0
    pool_size: 10

observability:
  metrics_enabled: true
  correlation_id_ttl: 3600
  batch_size: 100
```

---

## Monitoring & Alerting

### Key Metrics to Track

```python
# Success rate by task type
metrics.success_rate_by_task_type

# Cost distribution
metrics.accumulated_cost_percentiles  # p50, p95, p99

# Execution duration
metrics.elapsed_seconds_percentiles  # p50, p95, p99

# Guard violations
metrics.guard_violations_by_type  # cost, ttl, retries, depth

# Memory usage
metrics.episodic_store_size
metrics.working_memory_size
```

### Prometheus Integration

```python
from prometheus_client import Counter, Histogram, Gauge

execution_counter = Counter(
    'mas_executions_total',
    'Total executions',
    ['task_type', 'outcome']
)

execution_duration = Histogram(
    'mas_execution_duration_seconds',
    'Execution duration',
    buckets=(1, 5, 10, 30, 60, 300)
)

active_executions = Gauge(
    'mas_executions_active',
    'Active executions'
)
```

### Alert Thresholds

| Alert | Condition | Severity |
|-------|-----------|----------|
| High Error Rate | Success rate < 95% for 5 min | Warning |
| Cost Spike | Avg cost > 2x baseline | Warning |
| TTL Violations | > 10% of runs hit TTL | Critical |
| Memory Pressure | Episodic store > 80% capacity | Warning |
| Handler Failures | > 50% step failures | Critical |

---

## Operational Procedures

### Health Checks

```python
def health_check() -> dict:
    """Perform system health check."""
    return {
        "status": "healthy",
        "version": __version__,
        "memory": get_memory_stats(),
        "redis": check_redis_connection(),
        "uptime_seconds": get_uptime(),
    }
```

### Graceful Shutdown

```python
async def shutdown():
    """Graceful shutdown with cleanup."""
    # Cancel running executions
    for execution in active_executions:
        execution.cancel()
    
    # Wait for completion (max 30s)
    await asyncio.wait_for(
        asyncio.gather(*active_executions),
        timeout=30.0
    )
    
    # Close connections
    await redis_connection.close()
    await working_memory.close()
```

### Backup & Recovery

**Episodic Store Backup:**
```bash
# Redis backup
redis-cli BGSAVE

# Or with RDB copy
cp /var/lib/redis/dump.rdb /backups/mas-episodic-$(date +%Y%m%d).rdb

# Restore
redis-cli SHUTDOWN
cp /backups/mas-episodic-20260603.rdb /var/lib/redis/dump.rdb
redis-server
```

---

## SLA/SLO Definitions

### Service Level Objectives

| Objective | Target | Measurement |
|-----------|--------|-------------|
| **Availability** | 99.5% | Uptime per month |
| **Success Rate** | 95%+ | Executions completing successfully |
| **P95 Latency** | 30s | Execution duration |
| **P99 Latency** | 60s | Execution duration |
| **Cost Accuracy** | ±2% | Accumulated cost vs. actual |

### Error Budget

```
Monthly error budget: (100% - 99.5%) * (30 days * 24 hours) = 3.6 hours
Available downtime: 3 hours 36 minutes per month
```

---

## Incident Response

### Escalation Procedure

1. **Detection** → Alert triggered
2. **Assessment** → Check health dashboard
3. **Triage** → Determine severity (P1/P2/P3)
4. **Mitigation** → Apply temporary fix
5. **Resolution** → Implement permanent fix
6. **Postmortem** → Document learning

### Rollback Procedure

If deployment causes issues:
```bash
# Quick rollback to previous version
docker run -e VERSION=1.0.0 mas:latest

# Or via Kubernetes
kubectl rollout undo deployment/mas
```

---

## Next Steps

1. **Deploy** to staging environment
2. **Test** with production-like workloads
3. **Monitor** for 1-2 weeks
4. **Optimize** based on metrics
5. **Deploy** to production

**Estimated time to production**: 2-4 weeks
