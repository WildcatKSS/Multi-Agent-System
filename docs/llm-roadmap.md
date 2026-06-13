# LLM Integration Roadmap: Fully Agentic Framework with Open Source Models

**Version**: 1.0  
**Date**: 2026-06-06  
**Status**: Phase 1 (Provider Abstraction) complete — contracts, BaseProvider, LLMConfig, ProviderRegistry, error hierarchy, async support, observability hooks, and 200+ tests delivered. Phase 2 (LLM Provider Implementations) is next.  
**Target**: Transform deterministic MVP (v1.0.0) into fully agentic system with LLM integration

---

## Executive Summary

The Multi-Agent System MVP (v1.0.0) is production-ready with complete orchestration, guardrails, and observability. However, all 4 core agents (Planner, Tool Selector, Self-Healer, Evaluator) are **fully deterministic** with no LLM integration.

This roadmap transforms the framework into a **fully agentic system with open source models** (Ollama, Llama, Mistral) as primary, while optionally supporting proprietary APIs (OpenAI, Anthropic) as fallbacks.

**End State**: Framework implements all 6 layers of the architecture reference with LLM-powered agents and full memory integration.

---

## Phase Overview

### Track 1: Core LLM Integration (Phases 1-10)
12-21 weeks to fully agentic framework with all memory types

### Track 2: Product Layer (Phases 11-12)  
7-9 weeks additional for GUI and commercialization (future)

---

## Track 1: Core LLM Integration

### ✅ Phase 1: LLM Provider Abstraction — COMPLETE
**Goal**: Build pluggable abstraction for any LLM provider

**Deliverables** (all merged to `development`):
- ✅ `src/mas/llm/contracts.py` — `LLMMessage`, `LLMResponse`, `LLMProvider` ABC
- ✅ `src/mas/llm/errors.py` — `LLMError` hierarchy (6 subclasses, transient/permanent)
- ✅ `src/mas/llm/base.py` — `BaseProvider`: timeout, exponential-backoff retry, structured logging
- ✅ `src/mas/llm/config.py` — `LLMConfig` + `OllamaConfig`, `HuggingFaceConfig`, `OpenAIConfig`, `AnthropicConfig`
- ✅ `src/mas/llm/provider_registry.py` — `ProviderRegistry` factory with `from_config()` dispatch
- ✅ `src/mas/observability/correlation.py` — `ContextVar`-based correlation ID (propagates to async tasks)
- ✅ `src/mas/runtime/orchestrator.py` extended — `run_async()` for non-blocking LLM calls
- ✅ 200+ tests — 100% coverage, `mypy --strict` clean

**Key Design**:
- Frozen dataclasses matching existing patterns (`Task`, `Plan`, `Step`)
- Async-first for future distributed execution
- Zero mandatory external dependencies
- Template method pattern: `call()` → `_attempt()` → `_invoke()`

**GitHub**:
- Issues: #47–#54 (8 issues, 8 PRs — Issues 01–08)
- All merged to `development` branch

---

### Phase 2: LLM Provider Implementations (2-3 weeks)
**Goal**: Support Ollama (primary) + HuggingFace + optional OpenAI/Anthropic

**Deliverables**:
- `src/mas/llm/providers/ollama.py` - Ollama provider (local, free)
- `src/mas/llm/providers/huggingface.py` - HuggingFace Inference API
- `src/mas/llm/providers/openai.py` - OpenAI (optional dependency)
- `src/mas/llm/providers/anthropic.py` - Anthropic (optional dependency)
- Comprehensive tests (mocked HTTP, error handling, token counting)

**Key Features**:
- Model validation (check model availability before use)
- Token counting (accurate where available; estimate if not)
- Streaming support for long-running agents
- Proper error classification (transient vs permanent)

**GitHub**:
- Milestone: "Phase 2: LLM Providers"
- ~10 issues, ~5 PRs
- Estimate: 80-120 hours

---

### Phase 3: Prompt Template System (1-2 weeks)
**Goal**: Composable, versioned prompts for reproducible agent behavior

**Deliverables**:
- `src/mas/llm/prompts/contracts.py` - PromptTemplate, PromptRegistry
- `src/mas/llm/prompts/templates.py` - Rendering engine with variables
- YAML templates for each agent:
  - Planner: decompose_task, refine_plan, estimate_complexity
  - Tool Selector: select_tool, capability_matching
  - Evaluator: evaluate_output, generate_feedback, identify_issues
  - Self-Healer: analyze_failure, suggest_recovery, classify_error

**Key Design**:
- Templates stored in version-controlled YAML
- System + user message structure
- Required variable validation
- JSON output validation for LLM responses

**GitHub**:
- Milestone: "Phase 3: Prompt Templates"
- ~8 issues, ~3-4 PRs
- Estimate: 40-60 hours

---

### Phase 4: LLM-Based Agents (3-4 weeks)
**Goal**: Replace deterministic agents with LLM-powered reasoning

**Deliverables**:
- `src/mas/agents/planner_llm.py` - LLMPlanner (task decomposition via LLM)
- `src/mas/agents/tool_selector_llm.py` - LLMToolSelector (capability matching)
- `src/mas/agents/evaluator_llm.py` - LLMEvaluator (quality judgment)
- `src/mas/agents/self_healer_llm.py` - LLMSelfHealer (failure analysis)
- `src/mas/agents/factory.py` - AgentFactory for LLM or deterministic selection
- `src/mas/runtime/orchestrator.py` (extended) - Async `run_async()` method

**Key Design**:
- All LLM agents inherit from deterministic base (drop-in replacement)
- Automatic fallback to deterministic agent on LLM failure
- Immutable domain objects preserved (Task, Plan, Step)
- Async methods for non-blocking LLM calls
- Sync wrapper for backward compatibility

**Architecture**:
- Implements Layer 1 (Planning), Layer 2 (Tool Selection), Layer 3 (Self-Recovery) with LLM reasoning
- Implements Layer 4 (Evaluation) with LLM judgment component
- Supports Layer 5 (Runtime) async for future distribution

**GitHub**:
- Milestone: "Phase 4: LLM Agents"
- ~15 issues, ~8-10 PRs
- Estimate: 120-160 hours (highest complexity)
- Assign 4 developers (1 per agent type)

---

### Phase 5: Cost Tracking & Observability (1 week)
**Goal**: Track LLM usage, cost, and enforce guardrails

**Deliverables**:
- `src/mas/observability/llm_metrics.py` - LLMMetrics, cost tracking
- `src/mas/llm/pricing.py` - Cost estimation for popular models
- Extended `GuardrailsConfig` with `max_llm_cost` limit
- Metrics propagation to observability layer

**Key Features**:
- Token counting and cost estimation
- Guardrails enforcement (max_llm_cost per run)
- Free: Local Ollama models (llama2:7b, etc.)
- Pricing: OpenAI GPT, Anthropic Claude, HuggingFace

**GitHub**:
- Milestone: "Phase 5: Cost Tracking"
- ~5 issues, ~2-3 PRs
- Estimate: 30-40 hours

---

### Phase 6: Configuration Management (1 week)
**Goal**: Easy LLM setup via files and environment variables

**Deliverables**:
- `src/mas/config/llm_config_loader.py` - Config file loading
- Environment variable support: `MAS_LLM_PROVIDER`, `MAS_LLM_MODEL`, `MAS_LLM_API_KEY`
- Config file locations: `~/.mas/llm_config.yaml`, `/etc/mas/llm_config.yaml`

**Example Config**:
```yaml
provider: ollama
model: llama2:7b
base_url: http://localhost:11434
temperature: 0.7
max_tokens: 2000

fallback_providers:
  - provider: openai
    model: gpt-3.5-turbo
    api_key: ${OPENAI_API_KEY}
```

**GitHub**:
- Milestone: "Phase 6: Configuration"
- ~5 issues, ~2-3 PRs
- Estimate: 30-40 hours

---

### Phase 7: Cascade & Fallback Strategy (1 week)
**Goal**: Multi-provider failover for high availability

**Deliverables**:
- `src/mas/llm/cascade.py` - ProviderCascade, CascadingLLMProvider
- Fallback chain: Ollama → HuggingFace → OpenAI/Anthropic → Deterministic

**Example Cascade**:
```
Primary: Ollama (local, free)
  ↓ (timeout/error)
Fallback 1: HuggingFace
  ↓ (fails)
Fallback 2: OpenAI (expensive)
  ↓ (fails)
Fallback 3: Deterministic (always works)
```

**GitHub**:
- Milestone: "Phase 7: Cascade & Fallback"
- ~4 issues, ~2 PRs
- Estimate: 25-35 hours

---

### Phase 8: Testing Patterns (2 weeks)
**Goal**: Comprehensive testing without real LLMs in CI

**Deliverables**:
- `/tests/fixtures/mock_llm.py` - MockLLMProvider with canned responses
- `/tests/fixtures/llm_cassettes.py` - Record/replay pattern
- 100+ unit + integration tests
- Optional: E2E tests with real Ollama (marked with pytest.mark)

**Test Coverage**:
- Unit tests (mocked LLM): Fast, deterministic
- Integration tests (mock + real agents): End-to-end pipeline
- E2E tests (real Ollama): Optional in CI
- Backward compatibility: All 450 existing tests still pass

**GitHub**:
- Milestone: "Phase 8: Testing Patterns"
- ~10 issues, ~4-5 PRs
- Estimate: 60-80 hours

---

### Phase 9: Documentation & Examples (1-2 weeks)
**Goal**: Easy adoption and troubleshooting

**Deliverables**:
- `docs/llm-integration.md` - Architecture overview + design decisions
- `docs/llm-providers.md` - Setup guide for each provider
- `docs/llm-prompting.md` - Prompt template best practices
- `docs/llm-cost-tracking.md` - Cost monitoring and guardrails
- `docs/llm-migration-guide.md` - Migrate from deterministic to LLM
- `docs/llm-troubleshooting.md` - Common issues and solutions
- `/examples/llm_planner_example.py` - Minimal usage
- `/examples/llm_full_pipeline.py` - End-to-end example
- `/examples/ollama_local_setup.sh` - Quick Ollama setup

**GitHub**:
- Milestone: "Phase 9: Documentation"
- ~8 issues, ~3-4 PRs
- Estimate: 40-60 hours
- Can run parallel with Phase 10

---

### Phase 10: Semantic Memory Layer (2-3 weeks)
**Goal**: Enable agents to learn and reuse patterns across executions

**Deliverables**:
- `src/mas/memory/semantic_store.py` - Semantic memory storage
- `src/mas/memory/semantic_contracts.py` - SemanticRecord, Pattern contracts
- Pattern extraction from episodic records
- Agent integration: Planner, Tool Selector, Evaluator query semantic memory

**Key Features**:
- Store reusable patterns, strategies, success metrics
- Automatic indexing from episodic memory
- Vector embeddings for similarity search
- Learning from evaluation results

**Memory Stack Completion**:
- Working Memory (existing) ✅
- Episodic Memory (existing) ✅
- Semantic Memory (Phase 10) ✅
- Event Log (via episodic store) ✅

**GitHub**:
- Milestone: "Phase 10: Semantic Memory"
- ~12 issues, ~5-6 PRs
- Estimate: 80-120 hours

---

## Track 2: Product Layer (Future Milestones)

### Phase 11: GUI Dashboard & REST API (3-4 weeks)
Web dashboard and REST API for non-technical users
- Milestone: "Phase 11: GUI & REST API"
- Depends on: Phase 8 complete
- Estimate: ~120 hours

### Phase 12: Commercialization (4-5 weeks)
Multi-tenant, billing, security, enterprise deployment
- Milestone: "Phase 12: Commercialization"
- Depends on: Phase 11 complete
- Estimate: ~160 hours

---

## Implementation Timeline

### Track 1 Milestones
- **Critical Path** (MVP LLM): Phases 1, 2 (Ollama), 3, 4, 8 = **12-16 weeks**
- **Full Agentic** (all 10 phases): **15-21 weeks** (with Phase 9+10 parallel)

### Overall Timeline
```
Week 1-2:   Phase 1 (Provider Abstraction)
Week 3-5:   Phase 2 (LLM Providers)
Week 4-7:   Phase 3 (Prompt Templates) [parallel with Phase 2]
Week 7-11:  Phase 4 (LLM Agents)
Week 12-13: Phase 5 (Cost Tracking)
Week 13-14: Phase 6 (Configuration)
Week 14-15: Phase 7 (Cascade)
Week 15-19: Phase 8 (Testing)
Week 13-18: Phase 9 (Documentation) [parallel with Phases 5-8]
Week 19-22: Phase 10 (Semantic Memory)
─────────────────────────────────────────
Total: 15-22 weeks for fully agentic framework

Week 23-27: Phase 11 (GUI) [if proceeding to product]
Week 28-32: Phase 12 (Commercialization)
```

---

## Architecture Alignment

This roadmap implements the full Multi-Agent System Reference Architecture:

| Layer | Component | Implementation | Status |
|-------|-----------|-----------------|--------|
| **Layer 1** | Planning | LLMPlanner (Phase 4) | Replaces deterministic |
| **Layer 2** | Tool Selection | LLMToolSelector (Phase 4) | Replaces deterministic |
| **Layer 3** | Self-Recovery | LLMSelfHealer (Phase 4) | Replaces deterministic |
| **Layer 4** | Evaluation | LLMEvaluator + rules + heuristics (Phase 4) | Completes component |
| **Layer 5** | Runtime | Async runtime + future distribution (Phase 4) | Prepares for Phase 11+ |
| **Layer 6** | Memory | Working + Episodic + **Semantic** + Event Log (Phase 10) | Completes layer |

**End State**: Framework is fully agentic with all agents using LLM reasoning and all memory types integrated.

---

## GitHub Integration

All phases are structured for GitHub team collaboration:

- **12 Milestones**: One per phase with due dates and descriptions
- **40+ Labels**: Type, Priority, Phase, Component, Status, Team
- **~80 Issues**: All detailed with acceptance criteria and estimates
- **Templates**: PR template, issue templates, release checklist
- **Automation**: Auto-labeling, CI/CD workflows, GitHub Actions
- **Team Structure**: Backend, Frontend, DevOps role definitions

See `.github/QUICK_START_GITHUB.md` for setup instructions.

---

## Team Requirements

### Recommended Team Size
- **Backend**: 4-5 developers (Phases 1-10)
  - Provider/LLM lead (Phase 1-2)
  - Agent development (Phase 4) - 4 developers
  - Testing lead (Phase 8)
  - Semantic memory (Phase 10)
- **Frontend**: 2-3 developers (Phase 11+, future)
- **DevOps**: 1-2 engineers (CI/CD, infrastructure)

### Skills Required
- Python 3.12+ (type-safe async development)
- LLM/AI knowledge (prompting, token management)
- Testing (pytest, mocking, integration testing)
- Git/GitHub workflow
- Optional: REST API design, web frontend (Phase 11+)

---

## Key Design Principles

1. **Provider abstraction first**: All LLM interactions via abstract interface
2. **Open source priority**: Ollama/Llama as primary; proprietary as optional fallback
3. **Configuration-driven**: Model, prompts, parameters all configurable
4. **Graceful degradation**: Deterministic fallback if LLM unavailable
5. **Zero mandatory LLM deps**: Core framework unchanged; LLM optional
6. **Immutable configs**: Frozen dataclasses, no runtime mutations
7. **Async-first agents**: Support future distributed execution
8. **Observable**: Correlation IDs, metrics, cost tracking

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| LLM API outage | Automatic fallback to deterministic agent |
| Invalid LLM output | Output validation + JSON schema checks |
| Cost overrun | Guardrails enforce max_llm_cost limit |
| Latency impact | Async execution; timeout enforcement |
| Prompt injection | Prompts from code/YAML only; no user input |

---

## Success Criteria

- ✅ All 650+ existing tests pass (450 original + 200+ new LLM tests)
- ✅ 200+ new LLM tests pass (Phase 1 target exceeded)
- ✅ Real Ollama integration test passes
- ✅ Framework is fully agentic (all agents use LLM reasoning)
- ✅ All memory types integrated (Working, Episodic, Semantic, Event Log)
- ✅ Cost tracking accurate
- ✅ Fallback cascade works end-to-end
- ✅ Documentation complete
- ✅ Team can productionize (Phase 11+)

---

## Next Steps

1. **Phase 2 Kickoff** — LLM Provider Implementations
   - Implement `OllamaProvider` (primary local provider, no API key required)
   - Implement `HuggingFaceProvider`, `OpenAIProvider`, `AnthropicProvider`
   - All extend `BaseProvider`; concrete `_invoke()` + HTTP client per provider
   - Target: `Phase-02/` branch series

2. **Merge `development` → `main`** (when Phase 2 starts)
   - Phase 1 is complete and stable on `development`
   - Merge to `main` to unblock Phase 2 as the new base

3. **Weekly Syncs**
   - Daily 15-min standups
   - Weekly 1-hour planning
   - Phase reviews every 1-2 weeks

---

## Related Documents

- `docs/multi-agent-system-reference.md` - Architecture reference (updated for LLM layers)
- `docs/production-readiness.md` - Deployment guide
- `.github/QUICK_START_GITHUB.md` - GitHub setup for team
- `CONTRIBUTING.md` - Development guidelines
