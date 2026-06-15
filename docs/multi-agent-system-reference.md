# Multi Agent System — Reference Architecture

## Status

Architecture proposal for a generic multi-agent system with MVP and research phases.

---

# Purpose

This document describes a generic architecture for an autonomous multi-agent system.

The system must:

* independently analyze tasks
* dynamically generate plans
* select tools
* detect and recover from errors
* evaluate output
* learn from previous executions
* scale collaboration across multiple workers

The architecture is intentionally designed to be generic and not tied to a specific use case.

---

# Core Principles

1. Stability before intelligence
2. Observability before optimization
3. No hidden orchestration
4. No implicit state mutations
5. Small iterative extensions over large refactors
6. Every agent must remain explainable
7. Evaluation determines quality
8. Distributed systems are only introduced once the single-worker setup is stable

---

# Executive Summary

The architecture consists of multiple specialized agents collaborating through explicit workflow states and policy rules.

The system is divided into two tracks:

## MVP Track (Week 1–8)

Goal:
prove that autonomous workflow execution operates reliably within a simple runtime.

## Research Track (Week 9–14)

Goal:
explore how scalability, distributed orchestration, and adaptive learning can be added.

Complex components such as reward modeling, fine-tuning, and full distributed governance are intentionally postponed until the foundation is stable.

---

# Architecture Layers

## Layer 1 — Planning

### Responsibilities

* task analysis
* strategy selection
* plan generation
* decomposition of subproblems
* recursive planning

### Possible Technologies

* LangGraph
* ReAct loops
* State machines

### MVP

Simple linear planning.

### Research

Recursive planning and capability-aware planning.

---

## Layer 2 — Tool Selection

### Responsibilities

* selecting relevant tools
* determining context
* retrieving the correct data
* selecting appropriate LLM routes

### Examples

* API calls
* retrieval
* document parsing
* semantic search
* code execution
* structured generation

### Design Principle

No hardcoded tool flows.

---

## Layer 3 — Self-Recovery

### Responsibilities

* detecting failures
* executing retries
* attempting alternative strategies
* escalating when necessary

### Possible Failures

* timeout
* parsing failure
* invalid response
* hallucination
* dependency failure

### Retry Policy

* maximum of 3 retries
* escalation afterward

---

## Layer 4 — Evaluation

### Responsibilities

Assessing output quality.

### Evaluation Components

1. Deterministic rules
2. Heuristic rules
3. LLM judgment

### Example Criteria

* completeness
* consistency
* structure
* correctness
* task completion

### Minimum Score

8.0/10

### Important Observation

The evaluator effectively functions as a policy engine.

---

## Layer 5 — Runtime

### MVP

Single-worker runtime.

### Research

Distributed runtime with:

* parallel workers
* event bus
* merge logic
* deterministic execution

### Design Principle

Execution, coordination, and merging remain explicitly separated.

---

## Layer 6 — Memory Architecture

### Working Memory

* temporary task state
* single writer
* short TTL

### Episodic Memory

* execution history
* append-only

### Semantic Memory

* patterns
* strategies
* reusable knowledge

### Event Log

* immutable events
* auditability
* replay capability

---

# Workflow Lifecycle

## Allowed States

1. CREATED
2. QUEUED
3. RUNNING
4. WAITING_FOR_RETRY
5. BLOCKED
6. FAILED
7. COMPLETED
8. CANCELLED

## Core Rule

Workflow states may only be modified through the policy layer.

Goals:

* preventing race conditions
* preventing zombie tasks
* improving debugging
* improving replayability
* improving observability

---

# MVP Scope

## In Scope

* planning agent
* tool selection agent
* self-recovery agent
* evaluation agent
* single-worker runtime
* Redis + episodic memory
* basic guardrails

## Out of Scope

* distributed runtime
* event sourcing
* reward modeling
* fine-tuning
* production security
* multi-worker orchestration

---

# Research Scope

## Additions

* distributed orchestration
* adaptive learning
* event sourcing
* observability
* causality tracking
* policy engines

## Experimental

* reward modeling
* fine-tuning
* mode collapse detection

---

---

## LLM Implementation Strategy (Roadmap v1.1+)

As of version 1.1.0, the architecture layers are implemented with LLM agents while maintaining backward compatibility with deterministic fallbacks.

### Layer 1 — Planning (with LLM)

**MVP Implementation** (v1.0.0): Deterministic keyword-based planning

**LLM Implementation** (v1.1.0 - Phase 4):
- LLMPlanner uses language model for task decomposition
- Accepts natural language task description
- Generates structured Plan with Steps using LLM reasoning
- Prompt template: `prompts/planner/decompose_task.yaml`
- Fallback: Deterministic Planner if LLM unavailable

**Technologies**:
- Primary: Ollama (local, free models: Llama2, Mistral)
- Optional: OpenAI, Anthropic, HuggingFace

---

### Layer 2 — Tool Selection (with LLM)

**MVP Implementation** (v1.0.0): Direct action→tool name mapping

**LLM Implementation** (v1.1.0 - Phase 4):
- LLMToolSelector uses language model for capability-aware selection
- Analyzes step action and available tool descriptions
- Scores tools by relevance using LLM reasoning
- Prompt template: `prompts/tool_selector/capability_matching.yaml`
- Confidence thresholding: Falls back to deterministic if confidence < threshold
- Fallback: Deterministic ToolSelector if LLM fails

**Technologies**: Same as Layer 1

---

### Layer 3 — Self-Recovery (with LLM)

**MVP Implementation** (v1.0.0): Deterministic retry policy + fixed escalation

**LLM Implementation** (v1.1.0 - Phase 4):
- LLMSelfHealer uses language model for failure analysis
- Analyzes error message, context, and failure type
- LLM classifies error as recoverable vs permanent
- Suggests recovery strategies (beyond simple retries)
- Prompt template: `prompts/self_healer/analyze_failure.yaml`
- Fallback: Deterministic SelfHealer if LLM fails

**Technologies**: Same as Layer 1

---

### Layer 4 — Evaluation (Complete)

**MVP Implementation** (v1.0.0): Deterministic rules + heuristic scoring

**LLM Implementation** (v1.1.0 - Phase 4):
- LLMEvaluator adds LLM judgment component (completing architecture)
- Three evaluation components working together:
  1. **Deterministic rules**: Fixed pass/fail criteria
  2. **Heuristic scoring**: Weighted scoring for quality metrics
  3. **LLM judgment**: Language model assessment of output quality
- Combined score = (rules + heuristics + llm_judgment) / 3
- Prompt template: `prompts/evaluator/evaluate_output.yaml`
- Fallback: Deterministic + heuristic evaluation if LLM fails

**Technologies**: Same as Layer 1

---

### Layer 5 — Runtime (with Async Support)

**MVP Implementation** (v1.0.0): Synchronous single-worker orchestrator

**Phase 1 delivery** (v2.0.0-dev — `development` branch):
- `run_async()` delivered as part of Phase 1 (not Phase 4 as originally planned)
- `async def run_async(task: Task) -> RunResult` added to `src/mas/runtime/orchestrator.py`
- Preserves existing synchronous `run()` for backward compatibility
- Handles async LLM provider calls without blocking via thread-pool executor

**LLM Agent Integration** (v1.1.0 - Phase 4):
- LLM-based agents (Planner, ToolSelector, Evaluator, SelfHealer) plug into existing async runtime
- Prepares foundation for distributed execution (future phases)

**Technologies**: Python asyncio

---

### Layer 6 — Memory Architecture (Complete)

**MVP Implementation** (v1.0.0): Working + Episodic memory

**LLM Implementation Enhancement** (v1.1.0 - Phase 10):
- Added Semantic Memory layer for pattern learning
- Four memory types now fully integrated:

1. **Working Memory** (existing):
   - Temporary task state
   - Redis-backed with TTL
   - Single writer

2. **Episodic Memory** (existing):
   - Execution history (append-only)
   - All past task runs and results
   - Used for historical analysis

3. **Semantic Memory** (v1.1.0):
   - Reusable patterns extracted from episodic records
   - Stores successful strategies by task type
   - Tool effectiveness metrics
   - Plan templates from successful runs
   - Used by agents to guide new execution

4. **Event Log** (via episodic store):
   - Immutable audit trail
   - Complete state transition history
   - Replay capability

**Learning Loop**:
```
Task Execution
    ↓
Episodic Record Created
    ↓
Success? → Extract Patterns
    ↓
Semantic Memory Updated
    ↓
Future Tasks Query Semantic Memory
    ↓
LLM Agents Use Patterns as Examples
    ↓
Improved Planning, Tool Selection, Evaluation
```

**Technologies**: Redis, optional vector embeddings

---

## Implementation Roadmap

| Layer | MVP (v1.0.0) | v1.1.0 (Phase 4) | v1.2.0 (Phase 10) |
|-------|---|---|---|
| **Layer 1: Planning** | Deterministic | **LLM-based** | Enhanced with semantic patterns |
| **Layer 2: Tool Selection** | Deterministic | **LLM-based** | Learn tool effectiveness |
| **Layer 3: Self-Recovery** | Deterministic | **LLM-based** | Learn recovery strategies |
| **Layer 4: Evaluation** | Rules + Heuristics | **+ LLM Judgment** | Learn evaluation criteria |
| **Layer 5: Runtime** | Sync single-worker | **Async support** | Distributed (future) |
| **Layer 6: Memory** | Working + Episodic | **+ Async ops** | **+ Semantic Memory** |

---

## Backward Compatibility

- ✅ Existing deterministic agents still work in v1.1.0
- ✅ LLM agents are **opt-in** (requires LLMConfig)
- ✅ Automatic fallback to deterministic on LLM failure
- ✅ Zero breaking changes to public APIs
- ✅ All 650+ tests continue to pass (450 original + 200+ Phase 1 LLM tests)
- ✅ Sync wrapper available for sync-only codebases

---

## LLM Provider Strategy

### Open Source (Primary)
- **Ollama**: Local deployment, free, no API keys
  - Llama 2 (7B, 13B, 70B)
  - Mistral 7B
  - Neural Chat
  - Orca

### Proprietary (Optional Fallbacks)
- **OpenAI**: GPT-3.5-turbo, GPT-4 (cost-based)
- **Anthropic**: Claude 3 family (cost-based)
- **HuggingFace**: Inference API (flexible)

### Selection Strategy
1. Try primary provider (Ollama by default)
2. If unavailable → Fallback provider (OpenAI, Anthropic)
3. If all LLM providers fail → Deterministic agent

---

## For More Details

See `docs/llm-roadmap.md` for:
- Detailed 12-phase implementation plan
- GitHub milestone structure
- Team requirements and estimates
- Timeline and dependencies
- Risk mitigation strategies

---

## Memory Governance

Explicit decisions are still required for:

* retention
* ownership
* consistency
* poisoning defense

---

## Evaluator Versioning

Required:

* evaluator versions
* audit trails
* score breakdowns
* reproducibility

---

## Security

Intentionally outside MVP scope.

Later required:

* capability tokens
* sandboxing
* prompt injection defense
* audit logging
* network isolation

---

# Technology Direction

## Core

* Python
* LangGraph
* Pydantic
* FastAPI

## Memory

* Redis
* PostgreSQL
* Vector database

## Observability

* OpenTelemetry
* structured logging
* tracing

## Runtime

* Celery
* Temporal
* Ray

---

# Recommended Repository Structure

```text
repo/
├── docs/
│   ├── architecture/
│   │   └── multi-agent-system-reference.md
│   ├── roadmap.md
│   └── decisions/
│       └── adr-001-mvp-scope.md
├── src/
├── tests/
├── README.md
└── pyproject.toml
```

---

# README Guidelines

The README should explicitly explain:

* what the system does
* what the MVP means
* what must not be built
* architectural principles
* coding conventions
* PR guidelines
* observability requirements

---

# Implementation Strategy

## Phase 1

* workflow engine
* planning
* tool selection
* logging

## Phase 2

* self-recovery
* evaluator
* retry policy

## Phase 3

* memory layer
* semantic retrieval
* episodic storage

## Phase 4

* guardrails
* budget management
* TTL policies

## Phase 5

* distributed runtime
* learning loops
* event sourcing
* orchestration

---

# Summary

This architecture describes a phased approach for an autonomous multi-agent system.

The MVP intentionally focuses on:

* simplicity
* stability
* observability
* reproducibility

Complexity such as distributed orchestration and adaptive learning is only introduced after the foundation has demonstrably proven stable. 
