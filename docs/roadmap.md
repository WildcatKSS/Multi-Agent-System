# MVP Roadmap and PR Slicing Map

## Purpose
This roadmap translates the MVP architecture into small, reviewable pull requests with explicit dependencies.

## Milestones

### Milestone A — Foundations
- Issue 1: Project Bootstrap & Repository Foundations
- Issue 2: Workflow State Machine & Policy Layer
- Issue 3: Core Domain Contracts
- Issue 4: Single-Worker Runtime Orchestrator (Baseline)

### Milestone B — Core Agent Capabilities
- Issue 5: Planner Agent v1
- Issue 6: Tool Selection Agent v1 + Tool Registry
- Issue 7: Input Adapters (Email/Calendar/Document/Transcript)
- Issue 8: Self-Healing Agent v1
- Issue 9: Evaluator Agent v1

### Milestone C — Reliability & Operations
- Issue 10: Memory Layer v1 (Redis Working + Episodic Store)
- Issue 11: Guardrails Engine
- Issue 12: Observability Baseline

### Milestone D — Validation & Documentation
- Issue 13: End-to-End MVP Scenario Pack
- Issue 14: Documentation & ADRs

## PR Slicing Map

| PR | Issue | Title | Complexity | Depends on |
|---|---:|---|---|---|
| PR-01 | #1 | Project Bootstrap & Repository Foundations | S | - |
| PR-02 | #2 | Workflow State Machine & Policy Layer | S-M | #1 |
| PR-03 | #3 | Core Domain Contracts | M | #1 |
| PR-04 | #4 | Single-Worker Runtime Orchestrator (Baseline) | M | #2, #3 |
| PR-05 | #5 | Planner Agent v1 | M | #4 |
| PR-06 | #6 | Tool Selection Agent v1 + Tool Registry | M | #4 |
| PR-07 | #7 | Input Adapters | M | #3, #6 |
| PR-08 | #8 | Self-Healing Agent v1 | M | #4 |
| PR-09 | #9 | Evaluator Agent v1 | M-L | #4 |
| PR-10a | #10 | Memory interfaces + episodic abstraction | M | #3, #4 |
| PR-10b | #10 | Redis working memory adapter + integration | M | PR-10a |
| PR-11 | #11 | Guardrails Engine | M | #5, #8, #10b |
| PR-12 | #12 | Observability Baseline | M | #4 |
| PR-13 | #13 | End-to-End MVP Scenario Pack | M-L | #5, #7, #8, #9, #11, #12 |
| PR-14 | #14 | Documentation & ADRs | S-M | #13 |

## GitHub Setup (tracking issue + milestones)

### 1) Create milestones in GitHub
Create these 4 milestones in this order:
1. `Milestone A — Foundations`
2. `Milestone B — Core Agent Capabilities`
3. `Milestone C — Reliability & Operations`
4. `Milestone D — Validation & Documentation`

Suggested due-date cadence:
- Milestone A: week 2
- Milestone B: week 5
- Milestone C: week 7
- Milestone D: week 8

### 2) Create tracking issue in GitHub (not in-repo)
Create one GitHub issue named `Tracking Issue: MVP Execution Plan` and paste this body:

```md
Use this issue as the canonical execution checklist for the MVP.

## Milestone A — Foundations
- [ ] #1 Project Bootstrap & Repository Foundations (PR-01)
- [ ] #2 Workflow State Machine & Policy Layer (PR-02)
- [ ] #3 Core Domain Contracts (PR-03)
- [ ] #4 Single-Worker Runtime Orchestrator (Baseline) (PR-04)

## Milestone B — Core Agent Capabilities
- [ ] #5 Planner Agent v1 (PR-05)
- [ ] #6 Tool Selection Agent v1 + Tool Registry (PR-06)
- [ ] #7 Input Adapters (Email/Calendar/Document/Transcript) (PR-07)
- [ ] #8 Self-Healing Agent v1 (PR-08)
- [ ] #9 Evaluator Agent v1 (PR-09)

## Milestone C — Reliability & Operations
- [ ] #10 Memory Layer v1 (Redis Working + Episodic Store) (PR-10a / PR-10b)
- [ ] #11 Guardrails Engine (PR-11)
- [ ] #12 Observability Baseline (PR-12)

## Milestone D — Validation & Documentation
- [ ] #13 End-to-End MVP Scenario Pack (PR-13)
- [ ] #14 Documentation & ADRs (PR-14)

## Dependency Chain
`#1 -> #2/#3 -> #4 -> #5/#6/#8/#9 -> #7/#10 -> #11/#12 -> #13 -> #14`

## Definition of Done (MVP)
- [ ] Single-worker runtime executes end-to-end for all four input classes.
- [ ] Planner, tool selection, self-healing, evaluator are integrated.
- [ ] Guardrails for cost, TTL, retries, and plan depth are enforced.
- [ ] Working + episodic memory are operational.
- [ ] Observability baseline (structured logs + run correlation + key metrics) is in place.
- [ ] E2E test pack passes in CI.
```

## GitHub Issue Templates (copy/paste)

Use this shared issue template:

```md
## Goal

## Scope

## Out of Scope

## Technical Approach

## Acceptance Criteria
- [ ]

## Test Approach
- [ ]

## Estimated Complexity
**Complexity:** S/M/L
```

### Issue 1 — Project Bootstrap & Repository Foundations
- Milestone: `Milestone A — Foundations`
- Complexity: `S`

### Issue 2 — Workflow State Machine & Policy Layer
- Milestone: `Milestone A — Foundations`
- Complexity: `S-M`

### Issue 3 — Core Domain Contracts
- Milestone: `Milestone A — Foundations`
- Complexity: `M`

### Issue 4 — Single-Worker Runtime Orchestrator (Baseline)
- Milestone: `Milestone A — Foundations`
- Complexity: `M`

### Issue 5 — Planner Agent v1
- Milestone: `Milestone B — Core Agent Capabilities`
- Complexity: `M`

### Issue 6 — Tool Selection Agent v1 + Tool Registry
- Milestone: `Milestone B — Core Agent Capabilities`
- Complexity: `M`

### Issue 7 — Input Adapters (Email/Calendar/Document/Transcript)
- Milestone: `Milestone B — Core Agent Capabilities`
- Complexity: `M`

### Issue 8 — Self-Healing Agent v1
- Milestone: `Milestone B — Core Agent Capabilities`
- Complexity: `M`

### Issue 9 — Evaluator Agent v1
- Milestone: `Milestone B — Core Agent Capabilities`
- Complexity: `M-L`

### Issue 10 — Memory Layer v1 (Redis Working + Episodic Store)
- Milestone: `Milestone C — Reliability & Operations`
- Complexity: `L`

### Issue 11 — Guardrails Engine
- Milestone: `Milestone C — Reliability & Operations`
- Complexity: `M`

### Issue 12 — Observability Baseline
- Milestone: `Milestone C — Reliability & Operations`
- Complexity: `M`

### Issue 13 — End-to-End MVP Scenario Pack
- Milestone: `Milestone D — Validation & Documentation`
- Complexity: `M-L`

### Issue 14 — Documentation & ADRs
- Milestone: `Milestone D — Validation & Documentation`
- Complexity: `S-M`

## Execution Notes
- Keep each PR narrowly scoped to one issue whenever possible.
- Prefer feature flags or stubs over broad refactors.
- Merge order should follow dependency chain above.
- No distributed runtime work before Milestone D completion.
