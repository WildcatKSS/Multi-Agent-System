# Deployment Guide

## Overview

This guide covers production deployment of Multi-Agent System 1.0.0 with best practices for observability, reliability, and security.

## Pre-Deployment Checklist

- [ ] Python 3.12+ installed and verified
- [ ] All 450 tests passing: `pytest -v`
- [ ] Security policy reviewed: [SECURITY.md](../SECURITY.md)
- [ ] Guardrails configuration finalized
- [ ] Logging configuration prepared
- [ ] Monitoring and alerting setup
- [ ] Incident response plan documented
- [ ] Redis (optional) provisioned and tested

## Deployment Options

### Option 1: Direct Python Installation

**Recommended for:** Development, testing, single-machine deployments

```bash
# 1. Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# 2. Install Multi-Agent System
pip install mas

# 3. Verify installation
python -c "from mas import __version__; print(f'MAS v{__version__}')"

# 4. Run tests (optional)
pip install pytest fakeredis
git clone https://github.com/WildcatKSS/Multi-Agent-System.git
cd Multi-Agent-System
pytest -v
```

### Option 2: Docker Deployment

**Recommended for:** Production, containerized environments, multiple machines

```bash
# 1. Build image
docker build -t mas:1.0.0 .

# 2. Run container
docker run -e LOG_LEVEL=INFO \
  -e MAS_MAX_COST=100.0 \
  -e MAS_MAX_DURATION_SECONDS=300 \
  mas:1.0.0

# 3. With Redis (optional)
docker-compose up -d
```

### Option 3: Docker Compose (Full Stack)

**Recommended for:** Complete deployment with Redis memory layer

```bash
# Start services (MAS + Redis)
docker-compose up -d

# View logs
docker-compose logs -f

# Run tests
docker-compose exec mas pytest -v

# Stop services
docker-compose down
```

## Configuration

### Environment Variables

| Variable                  | Default | Description                |
|--------------------------|---------|----------------------------|
| `LOG_LEVEL`              | `INFO`  | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `MAS_MAX_COST`           | `100.0` | Max accumulated cost per run |
| `MAS_MAX_DURATION_SECONDS` | `300`   | Max wall-clock seconds per run |
| `MAS_MAX_RETRIES_PER_RUN` | `10`    | Max total retries per run  |
| `MAS_MAX_PLAN_DEPTH`     | `20`    | Max steps in a plan        |
| `MAS_MEMORY_BACKEND`     | `memory` | Memory backend (`memory` or `redis`) |
| `MAS_REDIS_HOST`         | `localhost` | Redis hostname        |
| `MAS_REDIS_PORT`         | `6379`  | Redis port                |

### Python Configuration

```python
from mas.guardrails import GuardrailsConfig, GuardrailsEngine
from mas.runtime.orchestrator import Runtime

# Configure guardrails
config = GuardrailsConfig(
    max_cost=100.0,
    max_duration_seconds=300.0,
    max_retries_per_run=10,
    max_plan_depth=20
)

# Create engine
engine = GuardrailsEngine(config)

# Inject into runtime
runtime = Runtime(guardrails=engine)
```

## Monitoring & Observability

### Logging

The framework provides structured JSON logging:

```json
{
  "timestamp": "2026-06-03T14:30:45.123Z",
  "correlation_id": "a1b2c3d4",
  "level": "INFO",
  "message": "Step completed",
  "step_id": "step-1",
  "duration_ms": 45,
  "success": true
}
```

**Configure logging level:**
```bash
export LOG_LEVEL=DEBUG  # Verbose
export LOG_LEVEL=INFO   # Standard
export LOG_LEVEL=WARNING # Minimal
```

### Metrics

Monitor these key metrics:

- **Execution time**: ms per task
- **Success rate**: % of completed tasks
- **Cost accumulation**: per-step cost tracking
- **Guardrail violations**: cost, TTL, retries, depth
- **Memory usage**: episodic store and working memory
- **Error rates**: by step type or agent

### Alerts

Set up alerts for:

- `guardrail_violation_count > 0` — Cost/TTL/retries exceeded
- `task_failure_rate > 5%` — Elevated failure rate
- `memory_usage > 500MB` — Memory pressure
- `redis_connection_failed` — Redis unavailable
- `avg_execution_time > 500ms` — Performance degradation

## Health Checks

### Docker Health Check

```bash
# Container is healthy if this succeeds
docker healthcheck
```

### Manual Health Check

```python
from mas import __version__
print(f"MAS v{__version__} running")
```

### Redis Health Check

```bash
redis-cli ping
# Expected: PONG
```

## Post-Deployment Verification

After deploying:

1. **Verify installation:**
   ```bash
   python -c "from mas import __version__; print(__version__)"
   ```

2. **Check logs for errors:**
   ```bash
   docker-compose logs | grep ERROR
   ```

3. **Run smoke tests:**
   ```bash
   pytest tests/test_runtime.py -v -k "smoke"
   ```

4. **Verify guardrails:**
   ```python
   from mas.guardrails import GuardrailsConfig, GuardrailsEngine
   config = GuardrailsConfig()
   engine = GuardrailsEngine(config)
   print(f"Cost limit: {config.max_cost}")
   ```

5. **Test with sample task:**
   ```python
   from mas.domain.task import Task
   from mas.domain.plan import Plan, Step
   from mas.runtime.orchestrator import Runtime
   from mas.runtime.executor import StepExecutorRegistry, StepResult
   
   task = Task(id="test", description="Verify deployment", goal="Success")
   plan = Plan(id="plan-1", task_id="test", steps=[Step(id="step-1", action="test", inputs={})])
   registry = StepExecutorRegistry()
   registry.register("test", lambda s: StepResult(success=True))
   runtime = Runtime(registry=registry)
   result = runtime.run(task, plan)
   assert result.succeeded
   ```

## Scaling Considerations

### Current Limitations (1.0.0)

- **Single-worker**: No built-in distributed execution
- **In-process only**: Single Python process
- **Sequential steps**: No parallel execution

### Scaling Strategies

**For increased throughput:**
1. Run multiple instances with load balancing
2. Use external task queue (not included)
3. Implement retry logic at application layer

**For future distributed scenarios (Milestone E):**
- Multi-worker runtime support planned
- Parallel step execution
- Event streaming integration

## Troubleshooting

### Issue: Redis Connection Failed

```
ERROR: Cannot connect to Redis at localhost:6379
```

**Solution:**
```bash
# Check Redis is running
docker ps | grep redis

# Restart Redis
docker-compose restart redis

# Verify connection
redis-cli ping
```

### Issue: High Memory Usage

**Cause:** Large episodic store

**Solution:**
1. Reduce TTL for episodic records
2. Implement cleanup policies
3. Monitor with `docker stats`

### Issue: Slow Execution

**Cause:** Too many steps or high step complexity

**Solution:**
1. Profile with correlation IDs in logs
2. Reduce plan depth
3. Optimize step handlers
4. See [docs/performance-tuning.md](performance-tuning.md)

### Issue: Tests Failing in Production

**Verify:**
1. Same Python version (3.12+)
2. Same dependencies installed
3. No environment variable mismatches
4. Redis availability (if using redis backend)

## Maintenance

### Regular Tasks

- [ ] **Daily**: Monitor logs and alerts
- [ ] **Weekly**: Review failure rates and performance
- [ ] **Monthly**: Security updates for Python
- [ ] **Quarterly**: Update dependencies if needed

### Backup & Recovery

- **Episodic store**: Backup Redis data regularly
- **Logs**: Archive logs for compliance
- **Configuration**: Version control guardrails config

## Support

- **Issues**: [GitHub Issues](https://github.com/WildcatKSS/Multi-Agent-System/issues)
- **Security**: [SECURITY.md](../SECURITY.md)
- **Contributing**: [CONTRIBUTING.md](../CONTRIBUTING.md)

---

**Version**: 1.0.0  
**Last Updated**: 2026-06-03
