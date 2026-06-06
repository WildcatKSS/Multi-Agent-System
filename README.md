# Multi-Agent System

[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)](pyproject.toml)
[![Project Status: Active](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![Release: 2.0.0 (Dev)](https://img.shields.io/badge/release-2.0.0%20dev-orange?style=flat-square)](https://github.com/WildcatKSS/Multi-Agent-System)

A deterministic, autonomous multi-agent runtime that analyzes tasks, executes dependency-ordered plans, enforces runtime guardrails, recovers from failures, and evaluates output. The architecture is intentionally generic and not tied to a specific use case.

> ⚠️ **Status:** v1.x runtime is shipped and stable. LLM integration (Ollama, Claude, GPT, provider fallback) is the **planned v2.0.0 roadmap** — see [docs/llm-roadmap.md](docs/llm-roadmap.md). It is **not yet implemented**.

[Quick Start](#quick-start) • [Features](#features) • [Documentation](#documentation) • [License](LICENSE)

## Quick Start

### Install

Install from source (the project is not published on PyPI):

```bash
git clone https://github.com/WildcatKSS/Multi-Agent-System.git
cd Multi-Agent-System
./install.sh   # creates venv/ and installs with dev extras
```

> Note: the PyPI name `mas` is taken by an unrelated package — do **not** `pip install mas`.

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

### ✅ Shipped (v1.x)

**Runtime foundation**
- Single-worker runtime orchestration with dependency resolution
- 4 input adapters: Email, Calendar, Document, Transcript
- Runtime guardrails: Cost, TTL, Retries, Plan Depth
- Working + Episodic memory layers (optional Redis backend)

**Reliability & operations**
- Structured observability: correlation IDs, JSON logging, metrics
- Error recovery with retries, escalation, and adaptive strategies
- Deterministic, rules + heuristics based evaluation

**Quality**
- 450 tests passing (~1s), 94% line/branch coverage
- Typed throughout — `mypy --strict` clean, `ruff` clean
- Zero runtime dependencies (Redis optional)

### 🚧 Planned — v2.0.0 LLM roadmap (not yet implemented)

- LLM-powered Planner / ToolSelector / Evaluator / SelfHealer
- Provider abstraction: Ollama → HuggingFace → OpenAI/Anthropic with fallback cascade
- Semantic memory for pattern learning
- See **[docs/llm-roadmap.md](docs/llm-roadmap.md)** for the 12-phase plan.

## Installation Options

**From source** (recommended):
```bash
./install.sh
```

**Docker**:
```bash
docker build -t mas:2.0.0 .
docker-compose up -d
```

**Requirements**: Python 3.12+ | **Optional**: Redis 7+ (for the Redis-backed working memory)

## Documentation

### Getting Started
- **[LLM Roadmap](docs/llm-roadmap.md)** — v2.0.0 12-phase LLM integration plan
- **[Quick Start: GitHub Setup](.github/QUICK_START_GITHUB.md)** — Set up for team development

### Core Architecture
- **[Architecture Guide](docs/multi-agent-system-reference.md)** — System design and planned LLM layers

### Operational
- **[Team Assignments](.github/TEAM_ASSIGNMENTS.md)** — Phase leads and role definitions

### Governance
- **[Security Policy](SECURITY.md)** — Vulnerability reporting
- **[License](LICENSE)** — MIT License

## Testing

```bash
source venv/bin/activate
pytest -v
```

**Coverage**: 450 tests across unit, integration, E2E scenario, guardrail, and recovery suites.

**Results**: 100% pass rate, ~1s total execution, 94% line/branch coverage.

Quality gates (run locally or in CI):
```bash
ruff check src tests      # lint
mypy                      # strict type check
pytest --cov              # tests + coverage
```

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

**Version**: 2.0.0 (Development) | **Target Release**: 2026-12-31 | **Status**: v1.x runtime stable; LLM integration planned

## License

Released under the [MIT License](LICENSE).
