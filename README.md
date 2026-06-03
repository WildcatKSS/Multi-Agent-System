# Multi-Agent-System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)](pyproject.toml)
[![Project Status: WIP](https://www.repostatus.org/badges/latest/wip.svg)](https://www.repostatus.org/#wip)

A generic, autonomous multi-agent system that independently analyzes tasks,
generates plans, selects tools, recovers from errors, evaluates output, and
learns from previous executions. The architecture is intentionally generic
and not tied to a specific use case. See
[`docs/multi-agent-system-reference.md`](docs/multi-agent-system-reference.md)
for the full reference architecture.

## Status

### Milestones

- **Milestone A — Foundations:** ✅ Complete (4/4 PRs)
- **Milestone B — Core Agents:** ✅ Complete (5/5 PRs)
- **Milestone C — Reliability & Operations:** ✅ Complete (3/3 PRs)
- **Milestone D — Validation & Documentation:** ✅ Complete (2/2 PRs)

### Completed (14/14 PRs) — MVP COMPLETE ✅

**Milestone A — Foundations (4/4):**
- PR-01: Project Bootstrap & Repository Foundations
- PR-02: Workflow State Machine & Policy Layer
- PR-03: Core Domain Contracts
- PR-04: Single-Worker Runtime Orchestrator (Baseline)

**Milestone B — Core Agents (5/5):**
- PR-05: Planner Agent v1
- PR-06: Tool Selection Agent v1 + Tool Registry
- PR-07: Input Adapters v1 (Email/Calendar/Document/Transcript)
- PR-08: Self-Healing Agent v1 (Retry/Fallback/Escalation)
- PR-09: Evaluator Agent v1 (Rules + Heuristics + Threshold)

**Milestone C — Reliability & Operations (3/3):**
- PR-10: Memory Layer v1 (Redis Working + Episodic Store)
- PR-11: Guardrails Engine (Cost/TTL/Retries/Depth Limits)
- PR-12: Observability Baseline (Logging/Metrics/Correlation IDs)

**Milestone D — Validation & Documentation (2/2):**
- PR-13: End-to-End MVP Scenario Pack (25 E2E Tests)
- PR-14: Documentation & Architecture Decision Records

The work is sliced into milestones tracked in [`docs/roadmap.md`](docs/roadmap.md).

## Documentation

### Core Documentation
- **[Architecture Reference](docs/multi-agent-system-reference.md)** — Complete system design and architectural principles
- **[Architecture Decision Records](docs/architecture-decisions.md)** — Key design decisions with rationale (10 ADRs)
- **[E2E Scenario Guide](docs/e2e-scenarios.md)** — All 25 E2E test scenarios with examples

### Operational Documentation
- **[Production Readiness](docs/production-readiness.md)** — Deployment, monitoring, scaling, and incident response
- **[Performance Tuning](docs/performance-tuning.md)** — Optimization techniques, profiling, and benchmarking
- **[Roadmap](docs/roadmap.md)** — MVP slicing plan and PR dependency chain

## MVP Scope

### In scope (all implemented)

- ✅ Planning agent (PR-05)
- ✅ Tool selection agent (PR-06)
- ✅ Self-recovery agent (PR-08)
- ✅ Evaluation agent (PR-09)
- ✅ Single-worker runtime (PR-04)
- ✅ Redis working memory + episodic memory (PR-10)
- ✅ Guardrails engine (cost, TTL, retries, plan depth) (PR-11)
- ✅ Structured logging & metrics (PR-12)
- ✅ Input adapters (email, calendar, document, transcript) (PR-07)

### Explicit non-goals

The following are deliberately **out of scope** for the MVP:

- Distributed runtime
- Event sourcing
- Reward modeling
- Fine-tuning
- Production security hardening
- Multi-worker orchestration

## Architectural Principles

1. Stability before intelligence
2. Observability before optimization
3. No hidden orchestration
4. No implicit state mutations
5. Small iterative extensions over large refactors
6. Every agent must remain explainable
7. Evaluation determines quality
8. Distributed systems are only introduced once the single-worker setup is stable

Full discussion in
[`docs/multi-agent-system-reference.md`](docs/multi-agent-system-reference.md).

## Design

**Library-first architecture**: `mas` is designed as a reusable library with an optional CLI wrapper.
Agent implementations (planner, tool selection, evaluator, etc.) live in `src/mas/` and are intended
for direct import and use. The CLI (`mas run`, etc.) is a convenience layer on top of the library.

This means:
- Domain logic has no dependencies on CLI infrastructure
- Code can be imported as `from mas.agents import Planner` without CLI
- Future users can build their own CLI/orchestration on top of `mas`

## Repository Layout

```
.
├── docs/                            # roadmap + reference architecture
├── src/mas/                         # Python library (agents, runtime, memory, observability)
│   ├── agents/                      # Agent implementations
│   │   ├── planner.py               # Task planning & decomposition
│   │   ├── tool_selector.py         # Tool selection logic
│   │   ├── evaluator.py             # Plan evaluation (rules + heuristics)
│   │   ├── self_healer.py           # Retry & recovery logic
│   │   ├── recovery/                # Recovery patterns (failures, escalation)
│   │   └── evaluation/              # Evaluation rules & heuristics
│   ├── runtime/                     # Single-worker runtime orchestration
│   │   ├── orchestrator.py          # Main execution loop with guardrails & metrics
│   │   └── executor.py              # Step handler registry
│   ├── guardrails/                  # Runtime enforcement (cost, TTL, retries, depth)
│   │   ├── config.py                # Guardrail limits configuration
│   │   ├── engine.py                # Guardrail validation logic
│   │   └── violations.py            # Violation types & results
│   ├── observability/               # Logging, metrics, correlation IDs
│   │   ├── correlation.py           # Correlation context & run ID management
│   │   ├── metrics.py               # ExecutionMetrics & collection
│   │   └── logging_config.py        # Structured JSON logging
│   ├── memory/                      # Redis working + episodic memory
│   │   ├── working_memory.py        # Redis-backed ephemeral state
│   │   ├── episodic_store.py        # Completed execution records
│   │   └── memory_agent.py          # Memory orchestration
│   ├── adapters/                    # Input type adapters
│   │   └── input_dispatcher.py      # Route to task from email/calendar/doc/transcript
│   ├── domain/                      # Domain contracts
│   │   ├── task.py                  # Task definition
│   │   ├── plan.py                  # Plan & Step contracts
│   │   ├── evaluation.py            # Evaluation contracts
│   │   └── annotation.py            # Metadata annotations
│   ├── tools/                       # Tool registry & contracts
│   │   ├── contract.py              # Tool interface
│   │   └── registry.py              # Tool registration & lookup
│   ├── workflow/                    # Workflow state machine
│   │   ├── state.py                 # Workflow states & transitions
│   │   └── policy.py                # State transition policy enforcement
│   └── cli.py                       # CLI wrapper (optional, for convenience)
├── tests/                           # pytest suite (422 tests)
├── pyproject.toml                   # build config + dependencies
└── README.md
```

## Quick Start

Run the installer — it installs the system dependencies, creates a virtual
environment, and installs the package with dev extras:

```bash
./install.sh
```

Then activate the environment, run the test suite, and try the CLI placeholder:

```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate

pytest -v

python -m mas --version
python -m mas run
mas --version
```

System packages are declared in [`system-packages.txt`](system-packages.txt);
Python dependencies live in [`pyproject.toml`](pyproject.toml). The installer is
idempotent and can be re-run safely.

Expected output of `python -m mas run` at this stage is a placeholder
notice — runtime behavior arrives in later milestones (see
[`docs/roadmap.md`](docs/roadmap.md)).

To exit the virtual environment later, run `deactivate`.

<details>
<summary>Manual setup (without the installer)</summary>

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

</details>

## Roadmap

The MVP is sliced into four milestones and fourteen issues; see
[`docs/roadmap.md`](docs/roadmap.md) for the full PR-by-PR plan and
dependency chain.
