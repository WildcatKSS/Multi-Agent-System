# Architecture Decision Records (ADRs)

## ADR-001: Single-Threaded Execution Model

### Status
ACCEPTED (MVP) — Milestone E will add distributed execution

### Context
The Multi-Agent System needs to execute task plans reliably with clear semantics for error handling and state management.

### Decision
Implement single-threaded, synchronous execution with explicit dependency-driven scheduling.

### Rationale
1. **Simplicity**: Easier to reason about execution order and state
2. **Debugging**: Deterministic execution for reproducible failures
3. **Correctness**: No race conditions, no deadlocks
4. **Testing**: Can verify execution order in tests
5. **MVP Focus**: Gets to MVP faster, distributed execution deferred to Milestone E

### Consequences
- ✅ Predictable behavior
- ✅ Easy to implement guardrails
- ⚠️ Cannot parallelize independent steps (future optimization)
- ⚠️ Blocking handlers will block entire execution (design constraint)

---

## ADR-002: Dependency Injection for Core Components

### Status
ACCEPTED

### Context
The runtime needs to be flexible, testable, and support multiple implementations.

### Decision
Use constructor-based dependency injection for PolicyEngine, StepExecutorRegistry, and GuardrailsEngine.

### Rationale
1. **Testability**: Easy to inject mocks/fakes in tests
2. **Flexibility**: Can swap implementations without code changes
3. **Explicit**: Dependencies are visible in constructor signature
4. **Pythonic**: Common pattern in Python frameworks

### Consequences
- ✅ Fully testable
- ✅ Supports multiple configurations
- ⚠️ Requires boilerplate in calling code

---

## ADR-003: Immutable Domain Objects

### Status
ACCEPTED

### Context
Domain objects represent the problem being solved and shouldn't be modified during execution.

### Decision
Use frozen dataclasses for all domain contracts with defensive copying on input.

### Rationale
1. **Safety**: Prevents accidental mutations
2. **Traceability**: Original task/plan can always be compared to execution state
3. **Parallelization**: Immutable objects are thread-safe (future Milestone E)
4. **Debugging**: Easier to understand what changed

### Consequences
- ✅ Type-safe, no side effects
- ✅ Thread-safe by default
- ⚠️ Cannot directly modify step status

---

## ADR-004: Structured Observability with Correlation IDs

### Status
ACCEPTED

### Context
Execution traces need to be correlated across logs, metrics, and errors for operational visibility.

### Decision
Use UUID4-based correlation IDs (8-char hex) with contextvars for thread-safe propagation.

### Rationale
1. **Traceability**: All logs/metrics for a run are linked by run_id
2. **Thread-safe**: contextvars work with async and threads
3. **Low overhead**: UUID4 generation is <1μs
4. **Standardized**: Follows OpenTelemetry patterns

### Consequences
- ✅ Perfect execution traceability
- ✅ Works with async/threading
- ✅ Enables distributed tracing (future)
- ⚠️ Requires context reset between tests

---

## ADR-005: Optional Redis with In-Memory Fallback

### Status
ACCEPTED

### Context
Memory layer needs to support both development (no dependencies) and production (Redis) scenarios.

### Decision
Make Redis optional with in-memory store as default, configurable at runtime.

### Rationale
1. **Development**: No Redis dependency needed for testing
2. **Flexibility**: Same code works in all environments
3. **Staging**: Can test with both backends
4. **Gradual Adoption**: Start with in-memory, migrate to Redis when needed

### Consequences
- ✅ No mandatory external dependencies
- ✅ Easier local development
- ✅ Flexibility for testing
- ⚠️ In-memory store is not persistent

---

## ADR-006: Frozen Metrics with Defensive Validation

### Status
ACCEPTED

### Context
Metrics are written to storage and used for analysis; invalid metrics break downstream systems.

### Decision
Use frozen dataclasses with `__post_init__` validation for all metrics.

### Rationale
1. **Safety**: Invalid metrics caught at creation time
2. **Immutability**: Metrics cannot be accidentally modified
3. **Defensive**: Validation prevents NaN/Infinity/negative values
4. **Debuggability**: Clear error messages for misconfiguration

### Consequences
- ✅ Type-safe metrics
- ✅ Catch errors early
- ✅ Serializable to JSON/storage
- ⚠️ Cannot modify metrics after creation

---

## ADR-007: Four-Guard Enforcement Model

### Status
ACCEPTED

### Context
Runtime needs to enforce resource limits without breaking semantics of individual agents.

### Decision
Implement four independent guards (cost, TTL, retries, plan depth) checked at specific points.

### Rationale
1. **Clear Semantics**: Each guard has a specific purpose
2. **Early Detection**: Plan depth checked before execution
3. **Budget Tracking**: Cost and retries checked during execution
4. **Fail-Fast**: TTL violation stops execution immediately

### Consequences
- ✅ Predictable behavior
- ✅ Prevents resource exhaustion
- ✅ Clear violation messages
- ⚠️ Four separate checks

---

## ADR-008: No Implicit State Mutations

### Status
ACCEPTED

### Context
Complex systems with hidden state changes become hard to debug and maintain.

### Decision
All mutable state (run context, metrics, step status) is explicitly tracked and logged.

### Rationale
1. **Debuggability**: Can trace all state changes
2. **Auditability**: Complete record of execution
3. **Correctness**: Fewer hidden side effects
4. **Testing**: Can assert on state transitions

### Consequences
- ✅ Clear execution flow
- ✅ Complete audit trail
- ✅ Easy to debug
- ⚠️ More verbose code

---

## ADR-009: Defensive Input Validation

### Status
ACCEPTED

### Context
Misconfigured values (negative costs, NaN durations) can cause silent failures.

### Decision
Validate all inputs at system boundaries and in critical paths.

### Rationale
1. **Fail-Fast**: Catch bugs immediately
2. **Error Messages**: Clear feedback for misconfiguration
3. **Security**: Prevent injection attacks
4. **Reliability**: Prevent cascading failures

### Consequences
- ✅ Early error detection
- ✅ Clear error messages
- ✅ Robust system
- ⚠️ Validation overhead

---

## ADR-010: Test-Driven Development with Builder Pattern

### Status
ACCEPTED

### Context
E2E tests need to construct realistic scenarios without mocking core domain objects.

### Decision
Use builder pattern for test scenarios (TaskBuilder, PlanBuilder, StepHandlerFactory).

### Rationale
1. **Readability**: Test setup is clear and fluent
2. **Reusability**: Builders used across multiple test suites
3. **Maintainability**: Changes to test data in one place
4. **Realistic**: No mocking of domain objects

### Consequences
- ✅ Tests are clear and readable
- ✅ Builder code is reusable
- ✅ Test setup is maintainable
- ⚠️ Additional builder code to maintain

---

## Decision Log

| Date | Decision | Rationale | Status |
|------|----------|-----------|--------|
| 2026-05-01 | Single-threaded | MVP simplicity | ACCEPTED |
| 2026-05-05 | Dependency injection | Testability | ACCEPTED |
| 2026-05-08 | Immutable domain | Thread-safety | ACCEPTED |
| 2026-05-15 | Correlation IDs | Observability | ACCEPTED |
| 2026-05-20 | Optional Redis | Dev/prod flexibility | ACCEPTED |
| 2026-05-25 | Frozen metrics | Safety | ACCEPTED |
| 2026-06-01 | Four guards | Resource limits | ACCEPTED |
| 2026-06-02 | No implicit mutations | Debuggability | ACCEPTED |
| 2026-06-02 | Defensive validation | Robustness | ACCEPTED |
| 2026-06-03 | Builder pattern | Test clarity | ACCEPTED |
