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

**Implementation in progress** — Milestone A ✅ complete, Milestone B 🚧 in progress.

**Completed (9 PRs):**
- PR-01: Project Bootstrap & Repository Foundations
- PR-02: Workflow State Machine & Policy Layer
- PR-03: Core Domain Contracts
- PR-04: Single-Worker Runtime Orchestrator (Baseline)
- PR-05: Planner Agent v1
- PR-06: Tool Selection Agent v1 + Tool Registry
- PR-07: Input Adapters v1 (Email/Calendar/Document/Transcript)
- PR-08: Self-Healing Agent v1 (Retry/Fallback/Escalation)
- PR-09: Evaluator Agent v1 (Rules + Heuristics + Threshold)

**In Progress:**
- PR-10: Memory Layer v1

The work is sliced into milestones tracked in [`docs/roadmap.md`](docs/roadmap.md).

## MVP Scope

### In scope

- Planning agent
- Tool selection agent
- Self-recovery agent
- Evaluation agent
- Single-worker runtime
- Redis working memory + episodic memory
- Basic guardrails (cost, TTL, retries, plan depth)

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
├── src/mas/                         # Python library (agents, runtime, memory)
│   ├── agents/                      # Agent implementations (future)
│   ├── runtime/                     # Single-worker orchestration (future)
│   ├── memory/                      # Redis + episodic memory (future)
│   └── cli.py                       # CLI wrapper (optional, for convenience)
├── tests/                           # pytest suite
├── pyproject.toml                   # build config + dependencies
└── README.md
```

## Local Run

Create a virtual environment, install the package in editable mode with dev
extras, then run the test suite and the CLI placeholder:

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Try the CLI
python -m mas --version
python -m mas run
mas --version
```

Expected output of `python -m mas run` at this stage is a placeholder
notice — runtime behavior arrives in later milestones (see
[`docs/roadmap.md`](docs/roadmap.md)).

To exit the virtual environment later, run `deactivate`.

## Roadmap

The MVP is sliced into four milestones and fourteen issues; see
[`docs/roadmap.md`](docs/roadmap.md) for the full PR-by-PR plan and
dependency chain.
