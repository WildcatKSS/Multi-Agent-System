# Multi-Agent System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)](pyproject.toml)
[![Project Status: Active](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![Release: 1.0.0](https://img.shields.io/badge/release-1.0.0-brightgreen?style=flat-square)](https://github.com/WildcatKSS/Multi-Agent-System/releases/tag/v1.0.0)

A generic, autonomous multi-agent system that independently analyzes tasks, generates plans, selects tools, recovers from errors, and evaluates output. The architecture is intentionally generic and not tied to a specific use case.

[Quick Start](#quick-start) • [Features](#features) • [Documentation](#documentation) • [Contributing](CONTRIBUTING.md) • [License](LICENSE)

## Quick Start

### Install

```bash
pip install mas
```

Or from source:
```bash
git clone https://github.com/WildcatKSS/Multi-Agent-System.git
cd Multi-Agent-System
./install.sh
```

### Basic Usage

```python
from mas.domain.task import Task
from mas.domain.plan import Plan, Step
from mas.runtime.orchestrator import Runtime
from mas.runtime.executor import StepExecutorRegistry, StepResult

# Create a task
task = Task(id="task-1", description="Process data", goal="Complete")

# Create a plan
plan = Plan(
    id="plan-1",
    task_id="task-1",
    steps=[Step(id="step-1", action="process", inputs={})],
    estimated_cost=1.0,
    estimated_time_seconds=10.0
)

# Register handlers and run
registry = StepExecutorRegistry()
registry.register("process", lambda step: StepResult(success=True))

runtime = Runtime(registry=registry)
result = runtime.run(task, plan)

print(f"Success: {result.succeeded}")
```

## Features

✅ **Production-Ready MVP**
- Single-worker runtime orchestration with dependency resolution
- 4 core agents: Planner, Tool Selection, Self-Healing, Evaluator
- 4 input adapters: Email, Calendar, Document, Transcript
- Runtime guardrails: Cost, TTL, Retries, Plan Depth

✅ **Reliability & Operations**
- Memory layer with working memory and episodic store
- Structured observability: correlation IDs, JSON logging, metrics
- Error recovery with retries and fallbacks
- Thread-safe execution via contextvars

✅ **Quality & Testing**
- 450 comprehensive tests (100% passing, ~0.5s execution)
- Type-safe with full Python 3.12+ type hints
- 0 security vulnerabilities
- 10 Architecture Decision Records

✅ **Well-Documented**
- API reference and architecture guides
- Production readiness documentation
- Performance tuning and benchmarks
- E2E scenarios with 25 realistic examples

## Installation Options

**PyPI** (recommended):
```bash
pip install mas
```

**Docker**:
```bash
docker build -t mas:1.0.0 .
docker-compose up -d
```

**Requirements**: Python 3.12+ | **Optional**: Redis 7+ (for advanced memory features)

## Documentation

### Core
- **[API Reference](src/mas/README.md)** — Complete module documentation
- **[Architecture Guide](docs/multi-agent-system-reference.md)** — System design and patterns
- **[Architecture Decisions](docs/architecture-decisions.md)** — 10 ADRs explaining design choices

### Operational
- **[Performance Tuning](docs/performance-tuning.md)** — Benchmarks and optimization strategies
- **[E2E Scenarios](docs/e2e-scenarios.md)** — 25 realistic usage examples
- **[Production Readiness](docs/production-readiness.md)** — Deployment and monitoring
- **[Roadmap](docs/roadmap.md)** — Feature roadmap and milestones

### Governance
- **[Contributing](CONTRIBUTING.md)** — How to contribute
- **[Code of Conduct](CODE_OF_CONDUCT.md)** — Community standards
- **[Changelog](CHANGELOG.md)** — Release history
- **[Versioning](VERSIONING.md)** — SemVer 2.0.0 policy

## Testing

```bash
source venv/bin/activate
pytest -v
```

**Coverage**: 450 tests
- Unit tests: 200+
- Integration tests: 150+
- E2E scenarios: 25+
- Guardrail tests: 50+
- Recovery tests: 25+

**Results**: 100% pass rate, ~0.5s total execution, 0% flakiness

## Performance

| Plan Size | Time    |
|-----------|---------|
| 3 steps   | ~0.15ms |
| 10 steps  | ~0.5ms  |
| 25 steps  | ~2ms    |
| 100 steps | ~8ms    |

**Memory**: Base runtime ~50MB + episodic store (~10MB per 1000 records)

See [Performance Tuning](docs/performance-tuning.md) for detailed benchmarks.

## Architecture

**Library-first design** — `mas` is a reusable Python library with optional CLI wrapper.

```python
from mas.agents import Planner
from mas.runtime.orchestrator import Runtime
from mas.guardrails import GuardrailsEngine
```

### Key Modules

```
src/mas/
├── agents/           # Planner, Tool Selection, Evaluator, Self-Healer
├── runtime/          # Orchestrator + Executor Registry
├── guardrails/       # Cost, TTL, Retries, Depth enforcement
├── observability/    # Logging, Metrics, Correlation IDs
├── memory/           # Working + Episodic memory stores
├── adapters/         # Email, Calendar, Document, Transcript inputs
├── domain/           # Task, Plan, Step contracts
├── tools/            # Tool registry
└── workflow/         # State machine + Policy engine
```

### Design Principles

1. **Stability before intelligence** — Correct > sophisticated
2. **Observability before optimization** — Measure > premature optimization
3. **No hidden orchestration** — Explicit dependencies
4. **No implicit mutations** — All changes are logged
5. **Composition over refactors** — Small iterations preferred
6. **Explainability** — Every decision is traceable
7. **Metrics drive quality** — Evaluation determines improvements
8. **Single-worker baseline** — Distributed when needed

## Release Information

**Version**: 1.0.0 | **Released**: 2026-06-03 | **Status**: Production Ready

[Changelog](CHANGELOG.md) • [Contributing](CONTRIBUTING.md)

## License

MIT License — see [LICENSE](LICENSE) for details.

---

Built with ❤️ by the Multi-Agent System team
