# Multi-Agent-System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)](pyproject.toml)
[![Project Status: Concept](https://www.repostatus.org/badges/latest/concept.svg)](https://www.repostatus.org/#concept)

A generic, autonomous multi-agent system that independently analyzes tasks,
generates plans, selects tools, recovers from errors, evaluates output, and
learns from previous executions. The architecture is intentionally generic
and not tied to a specific use case. See
[`docs/multi-agent-system-reference.md`](docs/multi-agent-system-reference.md)
for the full reference architecture.

## Status

Early MVP scaffold. This repository currently contains only the project
skeleton; agent logic, runtime orchestration, and memory integrations are
not yet implemented. The work is sliced into milestones tracked in
[`docs/roadmap.md`](docs/roadmap.md).

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

## Repository Layout

```
.
├── docs/                            # roadmap + reference architecture
├── src/mas/                         # Python package (MVP scaffold)
├── tests/                           # pytest suite
├── pyproject.toml                   # build config + dependencies
└── README.md
```

## Local Run

Install the package in editable mode with the dev extras, then run the test
suite and the CLI placeholder:

```bash
pip install -e ".[dev]"
pytest -v
python -m mas --version
python -m mas run
mas --version
```

Expected output of `python -m mas run` at this stage is a placeholder
notice — runtime behavior arrives in later milestones (see
[`docs/roadmap.md`](docs/roadmap.md)).

## Roadmap

The MVP is sliced into four milestones and fourteen issues; see
[`docs/roadmap.md`](docs/roadmap.md) for the full PR-by-PR plan and
dependency chain.
