# Multi Agent System — Reference Architecture

## Status
Architectuurvoorstel voor een generiek multi-agent systeem met MVP- en researchfasen.

---

# Doel

Dit document beschrijft een generieke architectuur voor een autonoom multi-agent systeem.

Het systeem moet:

- zelfstandig taken analyseren
- dynamisch plannen maken
- tools selecteren
- fouten detecteren en herstellen
- output evalueren
- leren van eerdere uitvoeringen
- schaalbaar kunnen samenwerken via meerdere workers

De architectuur is bewust generiek opgezet en niet gekoppeld aan één specifieke use-case.

---

# Kernprincipes

1. Eerst stabiliteit, daarna intelligentie
2. Eerst observability, daarna optimalisatie
3. Geen verborgen orchestration
4. Geen impliciete state-mutaties
5. Kleine iteratieve uitbreidingen boven grote refactors
6. Elke agent moet uitlegbaar blijven
7. Evaluatie bepaalt kwaliteit
8. Distributed systems pas toevoegen wanneer single-worker stabiel is

---

# Managementsamenvatting

De architectuur bestaat uit meerdere gespecialiseerde agenten die samenwerken via expliciete workflowstaten en beleidsregels.

Het systeem is opgesplitst in twee trajecten:

## MVP-traject (week 1–8)

Doel:
bewijzen dat autonome workflow-uitvoering stabiel werkt binnen een eenvoudige runtime.

## Research-traject (week 9–14)

Doel:
onderzoeken hoe schaalbaarheid, distributed orchestration en adaptief leren toegevoegd kunnen worden.

Complexe onderdelen zoals reward modeling, fine-tuning en volledige distributed governance worden bewust uitgesteld totdat de basis stabiel werkt.

---

# Architectuurlagen

## Laag 1 — Planning

### Verantwoordelijkheid

- taakanalyse
- strategie bepalen
- plan genereren
- subproblemen opdelen
- recursieve planning

### Mogelijke technologieën

- LangGraph
- ReAct loops
- State machines

### MVP

Eenvoudige lineaire planning.

### Research

Recursieve planning en capability-aware planning.

---

## Laag 2 — Toolselectie

### Verantwoordelijkheid

- relevante tools selecteren
- context bepalen
- juiste data ophalen
- geschikte LLM-routes kiezen

### Voorbeelden

- API calls
- retrieval
- document parsing
- semantic search
- code execution
- structured generation

### Ontwerpprincipe

Geen hardcoded toolflows.

---

## Laag 3 — Zelfherstel

### Verantwoordelijkheid

- fouten detecteren
- retries uitvoeren
- alternatieve strategieën proberen
- escaleren indien nodig

### Mogelijke fouten

- timeout
- parsing failure
- invalid response
- hallucination
- dependency failure

### Retry-beleid

- maximaal 3 retries
- daarna escalatie

---

## Laag 4 — Evaluatie

### Verantwoordelijkheid

Beoordelen van outputkwaliteit.

### Evaluatiecomponenten

1. Deterministische regels
2. Heuristische regels
3. LLM-judgement

### Voorbeelden van criteria

- volledigheid
- consistentie
- structuur
- correctheid
- taakafhandeling

### Minimale score

8.0/10

### Belangrijke observatie

De evaluator is feitelijk een policy engine.

---

## Laag 5 — Runtime

### MVP

Single-worker runtime.

### Research

Distributed runtime met:

- parallelle workers
- eventbus
- merge-logica
- deterministic execution

### Ontwerpprincipe

Uitvoering, coördinatie en merging blijven expliciet gescheiden.

---

## Laag 6 — Geheugenarchitectuur

### Working Memory

- tijdelijke taakstatus
- single writer
- korte TTL

### Episodic Memory

- uitvoeringsgeschiedenis
- append-only

### Semantic Memory

- patronen
- strategieën
- herbruikbare kennis

### Event Log

- immutable events
- auditability
- replay capability

---

# Workflow Lifecycle

## Toegestane toestanden

1. GEMAAKT
2. IN_WACHTRIJ
3. LOPEND
4. WACHTEN_OP_RETRY
5. GEBLOKKEERD
6. MISLUKT
7. VOLTOOID
8. GEANNULEERD

## Kernregel

Workflowstaten mogen uitsluitend aangepast worden via de beleidslaag.

Doelen:

- voorkomen van race conditions
- voorkomen van zombie tasks
- betere debugging
- betere replay
- betere observability

---

# MVP Scope

## In scope

- planning-agent
- toolselectie-agent
- zelfherstel-agent
- evaluatie-agent
- single-worker runtime
- Redis + episodic memory
- basis guardrails

## Niet in scope

- distributed runtime
- event sourcing
- reward modeling
- fine-tuning
- productie-security
- multi-worker orchestration

---

# Research Scope

## Toevoegingen

- distributed orchestration
- adaptive learning
- event sourcing
- observability
- causality tracking
- policy engines

## Experimenteel

- reward modeling
- fine-tuning
- mode collapse detection

---

# Design Debt

## Planner DSL

### MVP

Ongestructureerde LLM-output.

### Toekomst

Migratie naar:

- JSON schema
- TypedDict
- formele plancontracten

---

## Memory Governance

Nog expliciete keuzes nodig voor:

- retention
- ownership
- consistency
- poisoning defense

---

## Evaluator Versioning

Benodigd:

- evaluator versions
- audit trails
- score breakdowns
- reproduceerbaarheid

---

## Security

Bewust buiten MVP-scope.

Later nodig:

- capability tokens
- sandboxing
- prompt injection defense
- audit logging
- network isolation

---

# Technologische Richting

## Core

- Python
- LangGraph
- Pydantic
- FastAPI

## Memory

- Redis
- PostgreSQL
- Vector database

## Observability

- OpenTelemetry
- structured logging
- tracing

## Runtime

- Celery
- Temporal
- Ray

---

# Aanbevolen Repositorystructuur

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

# README-richtlijnen

README moet expliciet uitleggen:

- wat het systeem doet
- wat MVP betekent
- wat niet gebouwd mag worden
- architectuurprincipes
- coding conventions
- PR-richtlijnen
- observability-vereisten

---

# Implementatiestrategie

## Fase 1

- workflow engine
- planning
- toolselectie
- logging

## Fase 2

- zelfherstel
- evaluator
- retry-beleid

## Fase 3

- memory layer
- semantic retrieval
- episodic storage

## Fase 4

- guardrails
- budgetbeheer
- TTL policies

## Fase 5

- distributed runtime
- learning loops
- event sourcing
- orchestration

---

# Samenvatting

Deze architectuur beschrijft een gefaseerde aanpak voor een autonoom multi-agent systeem.

Het MVP focust bewust op:

- eenvoud
- stabiliteit
- observability
- reproduceerbaarheid

Complexiteit zoals distributed orchestration en adaptief leren wordt pas toegevoegd nadat de basis aantoonbaar stabiel werkt.
