# Multi-Agent System

[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)](pyproject.toml)
[![Project Status: Active](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)
[![Release: 2.0.0 (Dev)](https://img.shields.io/badge/release-2.0.0%20dev-orange?style=flat-square)](https://github.com/WildcatKSS/Multi-Agent-System)

A deterministic, autonomous multi-agent runtime that analyzes tasks, executes dependency-ordered plans, enforces runtime guardrails, recovers from failures, and evaluates output. The architecture is intentionally generic and not tied to a specific use case.

> ✅ **Status:** v1.x runtime stable. **Phase 1 (Provider Abstraction) and Phase 2 (Provider Implementations) are both complete** on `development` — all four providers (Ollama, HuggingFace, OpenAI, Anthropic), model validation, token counting, streaming, and error classification are shipped with 1200+ tests. Phase 3 (Prompt Templates) is next. See [docs/llm-roadmap.md](docs/llm-roadmap.md).

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
- 1200+ tests passing (~30s), ~95% line/branch coverage
- Typed throughout — `mypy --strict` clean, `ruff` clean
- Zero runtime dependencies (Redis optional)

### ✅ Phase 1 complete — LLM Provider Abstraction (`src/mas/llm/`)

- **`contracts.py`** — `LLMMessage`, `LLMResponse`, `LLMProvider` ABC, `LLMError` hierarchy
- **`errors.py`** — Full error taxonomy: `ConfigError`, `TimeoutError`, `APIError`, `ValidationError`, `RateLimitError`, `AuthenticationError` (transient vs permanent)
- **`base.py`** — `BaseProvider`: timeout enforcement, exponential-backoff retry, structured logging with correlation IDs and cost metrics
- **`config.py`** — `LLMConfig` + per-provider configs: `OllamaConfig`, `HuggingFaceConfig`, `OpenAIConfig`, `AnthropicConfig`
- **`provider_registry.py`** — `ProviderRegistry` factory; `from_config()` dispatch; `default_registry`
- **`runtime/orchestrator.py`** — `run_async()` for non-blocking LLM calls via thread-pool executor

### ✅ Phase 2 complete — Provider Implementations (`src/mas/llm/providers/`, `src/mas/llm/validation/`)

All four concrete providers, plus supporting infrastructure:

- **`providers/ollama.py`** — Ollama local provider (no API key, streaming-capable)
- **`providers/huggingface.py`** — HuggingFace Inference API
- **`providers/openai.py`** — OpenAI Chat Completions API
- **`providers/anthropic.py`** — Anthropic Messages API
- **`validation/model_validator.py`** — `ModelValidator`: catalog of 25 known models across all 4 providers, parameter bounds checking, capability metadata
- **`token_counter.py`** — `TokenCounter`: per-provider heuristic strategies (3.5–4.0 chars/token) with LRU caching
- **`streaming.py`** — SSE parsing, per-chunk timeout, `StreamCollector`
- **`error_classifier.py`** — `ErrorClassifier`: retry strategy (immediate/exponential/fixed-wait), `Retry-After` header support, user-facing messages
- **1200+ tests** — 100% coverage of all LLM modules, `mypy --strict` clean

### 🚧 Planned — v2.0.0 LLM roadmap (Phases 3–12)

- **Phase 3**: Prompt template system (composable YAML templates per agent)
- **Phase 4**: LLM-powered Planner / ToolSelector / Evaluator / SelfHealer
- **Phase 7**: Cascade & fallback — Ollama → HuggingFace → OpenAI/Anthropic → deterministic
- **Phase 10**: Semantic memory for pattern learning
- See **[docs/llm-roadmap.md](docs/llm-roadmap.md)** for the full 12-phase plan.

## Installation Options

**From source** (recommended):
```bash
./install.sh
```

**Docker**:
```bash
docker build -t mas:2.0.0 .
REDIS_PASSWORD=your-secret docker-compose up -d
```

> Set `REDIS_PASSWORD` before starting — the compose file binds Redis to `127.0.0.1` only and requires authentication by default.

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

**Coverage**: 1200+ tests across unit, integration, E2E scenario, guardrail, and recovery suites.

**Results**: 100% pass rate, ~30s total execution, ~95% line/branch coverage.

Quality gates (run locally or in CI):
```bash
ruff check src tests      # lint
mypy                      # strict type check
pytest --cov              # tests + coverage
```

CI runs these gates across a Python 3.12 + 3.13 matrix and enforces a minimum
coverage threshold (`pytest --cov-fail-under=90`).

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
├── llm/              # Phases 1+2 complete: all 4 providers, validation, streaming, token counting
│   ├── providers/    # OllamaProvider, OpenAIProvider, AnthropicProvider, HuggingFaceProvider
│   └── validation/   # ModelValidator (25 known models, capability metadata)
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
