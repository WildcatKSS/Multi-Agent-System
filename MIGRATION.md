# Migration Guide

## Upgrading to 1.0.0

This guide covers upgrading from pre-release versions to Multi-Agent System 1.0.0.

### Version 1.0.0 is the First Stable Release

If you were using pre-release versions (0.x.x), this is the first production-ready version of Multi-Agent System.

## Installation

### From Pre-Release to 1.0.0

**Option 1: Update via pip**

```bash
pip install --upgrade mas
```

**Option 2: Update from source**

```bash
git clone https://github.com/WildcatKSS/Multi-Agent-System.git
cd Multi-Agent-System
git checkout v1.0.0
pip install -e ".[dev]"
```

## API Changes

### What's New in 1.0.0

**New Core Modules:**
- `mas.guardrails` — Runtime enforcement of cost, TTL, retries, plan depth
- `mas.observability` — Correlation IDs, structured logging, execution metrics
- `mas.memory` — Working memory and episodic store layers

**Enhanced Classes:**
- `Runtime` — Now accepts optional `guardrails` and memory configuration
- `RunResult` — Extended with `guard_violation` field for guardrail enforcement
- `ExecutionMetrics` — Expanded metrics tracking (success_rate, cost_accumulation, step tracking)

### Breaking Changes

**None.** Version 1.0.0 maintains backward compatibility with earlier API usage.

If you were using:
```python
from mas.runtime.orchestrator import Runtime
from mas.runtime.executor import StepExecutorRegistry
from mas.domain.task import Task
from mas.domain.plan import Plan, Step
```

This code continues to work in 1.0.0 without modification.

## New Features (Recommended)

While not required, we recommend adopting these 1.0.0 features:

### 1. Guardrails Enforcement

Add runtime guardrails to prevent unbounded resource usage:

```python
from mas.guardrails import GuardrailsConfig, GuardrailsEngine
from mas.runtime.orchestrator import Runtime

# Configure limits
config = GuardrailsConfig(
    max_cost=100.0,
    max_duration_seconds=300.0,
    max_retries_per_run=10,
    max_plan_depth=20
)

# Enforce in runtime
engine = GuardrailsEngine(config)
runtime = Runtime(registry=registry, guardrails=engine)
```

### 2. Structured Logging

Enable structured JSON logging for better observability:

```bash
export LOG_LEVEL=INFO
```

Logs are now emitted as structured JSON with correlation IDs for tracing.

### 3. Memory Layer

Use episodic memory for learning from past executions:

```python
# Uses in-memory store by default
# For Redis backend: set MAS_MEMORY_BACKEND=redis
runtime = Runtime(registry=registry)
```

## Testing Your Upgrade

After upgrading, run the test suite:

```bash
source venv/bin/activate
pytest -v
```

All 450 tests should pass (< 1 second execution).

## Rollback

If you need to rollback to a pre-release version:

```bash
pip install mas==<version>
# Example: pip install mas==0.0.1
```

Note: Pre-release versions are no longer supported. We recommend staying on 1.0.x.

## Support & Questions

- **Issues**: https://github.com/WildcatKSS/Multi-Agent-System/issues
- **Security**: See [SECURITY.md](SECURITY.md)
- **Documentation**: See [README.md](README.md)

## What's Next?

After upgrading to 1.0.0:

1. Read the [Deployment Guide](docs/DEPLOYMENT.md) for production deployment
2. Review [Architecture Decisions](docs/architecture-decisions.md) for design patterns
3. Check [Performance Tuning](docs/performance-tuning.md) for optimization
4. Enable [Guardrails](docs/multi-agent-system-reference.md#guardrails) for reliability

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed release notes and feature list.

---

**Version**: 1.0.0  
**Released**: 2026-06-03  
**Support**: 1.0.x receives security updates through 2027-06-03
