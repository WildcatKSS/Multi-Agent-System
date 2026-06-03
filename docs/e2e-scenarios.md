# E2E MVP Scenario Pack

## Purpose

The End-to-End MVP Scenario Pack provides comprehensive integration testing for the complete Multi-Agent System. It validates that all components (Planner, Tool Selection, Self-Healing, Evaluator, Memory, Guardrails, Observability) work together correctly across realistic scenarios.

## Test Organization

All E2E tests are located in `tests/test_e2e_scenarios.py` and organized by scenario category:

- **TestE2EHappyPath** — Basic happy path execution
- **TestE2EInputAdapters** — Integration with all 4 input adapter types
- **TestE2EGuardrailViolations** — Guardrail enforcement (cost, TTL, retries, depth)
- **TestE2ERecovery** — Failure and recovery scenarios
- **TestE2EComplexPlans** — Complex dependency resolution
- **TestE2EMemoryIntegration** — Episodic store recording
- **TestE2EObservability** — Metrics, correlation IDs, logging

## Scenario Categories

### 1. Happy Path Scenarios

**Purpose:** Verify basic end-to-end execution flow works correctly.

**Scenarios:**
- `test_happy_path_simple_linear_plan` — 3-step linear plan execution
- `test_happy_path_multi_step_plan` — 5-step plan execution
- `test_happy_path_complex_dependencies` — Diamond dependency graph execution
- `test_happy_path_with_metrics_collection` — Verify metrics are collected

**What's Validated:**
- Tasks transition to COMPLETED
- Plans execute all steps in dependency order
- All metrics fields populated correctly
- Success rate calculated as 1.0
- No failures or guard violations

**Example Output:**
```python
assert result.succeeded is True
assert result.final_state == WorkflowState.COMPLETED
assert result.completed_steps == 3
assert result.metrics.success_rate == 1.0
assert result.metrics.elapsed_seconds > 0
```

---

### 2. Input Adapter Scenarios

**Purpose:** Validate that all 4 input adapter types work end-to-end.

**Scenarios:**
- `test_email_input_scenario` — Email input with sender/subject/body context
- `test_calendar_input_scenario` — Calendar event with attendees and time
- `test_document_input_scenario` — Document with type and filename
- `test_transcript_input_scenario` — Transcript with speaker count and duration

**What's Validated:**
- Task context is set correctly per input type
- Plan generation works with each input type
- Execution completes successfully
- Input source metadata is preserved

**Example Output:**
```python
assert task.context["source_type"] == "email"
assert task.context["sender"] == "alice@example.com"
assert result.succeeded is True
```

---

### 3. Guardrail Violation Scenarios

**Purpose:** Verify that guardrails enforce cost, TTL, retries, and plan depth limits.

**Scenarios:**
- `test_cost_guard_violation` — Rejects plan exceeding max_cost
- `test_plan_depth_guard_violation` — Rejects plan with too many steps
- `test_retries_guard_violation` — Halts execution when retries exceeded

**What's Validated:**
- Plans exceeding cost limit are rejected pre-execution
- Plans exceeding depth limit are rejected pre-execution
- Execution halts when retries budget exceeded during run
- Guard violation type recorded in metrics and result
- Task status remains PENDING (no workflow registered for pre-run violations)

**Example Output:**
```python
assert result.succeeded is False
assert result.guard_violation is not None
assert result.guard_violation.guard_type == GuardType.COST
assert result.metrics.guard_violation == "cost"
```

---

### 4. Recovery Scenarios

**Purpose:** Validate self-healing with retries and failure recovery.

**Scenarios:**
- `test_recovery_single_retry` — Step fails once, retries, and succeeds
- `test_recovery_multi_retry` — Step fails multiple times then succeeds
- `test_recovery_partial_failure` — Mix of recovery and failure

**What's Validated:**
- Steps with failures retry up to max_retries limit
- Execution continues after successful retry
- Total retry count tracked in metrics
- Plan eventually completes successfully after recovery

**Example Output:**
```python
assert result.succeeded is True
assert result.metrics.total_retries >= 1
assert result.completed_steps == expected_completed
```

---

### 5. Complex Plan Scenarios

**Purpose:** Validate dependency resolution and failure cascading.

**Scenarios:**
- `test_diamond_dependency_execution` — A → B,C; B,C → D graph
- `test_skip_cascading_on_dependency_failure` — Failed dependency skips downstream
- `test_multiple_independent_branches` — Multiple independent execution branches

**What's Validated:**
- Steps execute in dependency order (no step before its dependencies)
- Failed step causes downstream steps to be SKIPPED
- Independent branches execute correctly
- Skipped steps recorded in metrics

**Example Output:**
```python
assert execution_order.index("step-A") < execution_order.index("step-B")
assert execution_order.index("step-B") < execution_order.index("step-D")
assert result.skipped_steps == 2  # step-2 and step-3 skipped due to step-1 failure
```

---

### 6. Memory Integration Scenarios

**Purpose:** Validate that completed executions are recorded in episodic memory.

**Scenarios:**
- `test_execution_produces_metrics_for_storage` — Execution metrics available for storage
- `test_multiple_execution_attempts_tracked` — Multiple executions tracked independently

**What's Validated:**
- Completed execution produces metrics record
- Metrics contain all fields needed for episodic storage
- Multiple executions of same task have unique run IDs
- Metrics can be serialized for storage

**Example Output:**
```python
assert result.metrics.run_id is not None
assert result.metrics.task_id == task.id
assert len(set(run_ids)) == 3  # 3 unique run IDs for 3 executions
```

---

### 7. Observability Scenarios

**Purpose:** Validate metrics collection, correlation ID propagation, and logging.

**Scenarios:**
- `test_correlation_id_propagation` — Run ID in metrics and logs
- `test_metrics_completeness` — All metrics fields populated
- `test_success_rate_calculation_all_success` — Success rate is 1.0 for all successes
- `test_success_rate_calculation_partial_success` — Success rate correct for mixed outcomes
- `test_guard_violation_recorded_in_metrics` — Guard type in metrics
- `test_metrics_serialization_to_dict` — Metrics convertible to dict

**What's Validated:**
- Run ID is 8-character hex UUID
- All metrics fields populated after execution
- Success rate calculated as completed_steps / (completed_steps + failed_steps)
- Metrics serializable to dictionary
- Guard violations recorded with type name

**Example Output:**
```python
assert len(result.metrics.run_id) == 8
assert all(c in "0123456789abcdef" for c in result.metrics.run_id)
assert result.metrics.success_rate == 0.75  # 3 succeeded, 1 failed
metrics_dict = result.metrics.to_dict()
assert "success_rate" in metrics_dict
```

---

## Running the Tests

### Run all E2E scenarios
```bash
pytest tests/test_e2e_scenarios.py -v
```

### Run a specific test class
```bash
pytest tests/test_e2e_scenarios.py::TestE2EHappyPath -v
pytest tests/test_e2e_scenarios.py::TestE2EGuardrailViolations -v
```

### Run a specific test
```bash
pytest tests/test_e2e_scenarios.py::TestE2EHappyPath::test_happy_path_simple_linear_plan -v
```

### Run with coverage
```bash
pytest tests/test_e2e_scenarios.py -v --cov=src/mas --cov-report=html
```

### Run all tests including E2E
```bash
pytest -v
```

---

## Helper Builders and Factories

The E2E tests use helper builders to construct test scenarios:

### TaskBuilder
```python
from tests.e2e_scenario_builders import TaskBuilder

task = TaskBuilder() \
    .with_id("task-1") \
    .with_goal("Complete the work") \
    .with_context({"source_type": "email"}) \
    .build()
```

### PlanBuilder
```python
from tests.e2e_scenario_builders import PlanBuilder, generate_linear_plan, generate_diamond_plan

# Linear 3-step plan
plan = generate_linear_plan("task-1", step_count=3)

# Diamond dependency graph
plan = generate_diamond_plan("task-1")

# Custom steps
plan = PlanBuilder("task-1") \
    .with_custom_steps([
        {"id": "step-0", "action": "work"},
        {"id": "step-1", "action": "work", "depends_on": ["step-0"], "cost": 2.0},
    ]) \
    .build()
```

### StepHandlerFactory
```python
from tests.e2e_scenario_builders import StepHandlerFactory

# Always succeeds
registry.register("work", StepHandlerFactory.success_handler())

# Always fails
registry.register("work", StepHandlerFactory.failure_handler())

# Fails N times then succeeds
registry.register("work", StepHandlerFactory.retry_handler(fail_count=2))

# Mix of success/failure
registry.register("work", StepHandlerFactory.mixed_handler([True, False, True]))
```

---

## Extending with New Scenarios

To add a new scenario:

1. **Identify the scenario category** (Happy Path, Input Adapter, Guardrail, Recovery, etc.)
2. **Add a test method** to the appropriate test class:
   ```python
   def test_my_scenario(self) -> None:
       """Scenario description."""
       task = TaskBuilder().build()
       plan = generate_linear_plan(task.id, step_count=3)
       
       registry = StepExecutorRegistry()
       registry.register("action", StepHandlerFactory.success_handler())
       
       runtime = Runtime(registry=registry)
       result = runtime.run(task, plan)
       
       # Assertions
       assert result.succeeded is True
   ```

3. **Follow the pattern**: Setup → Execute → Assert
4. **Document the test** with a docstring explaining what's validated

---

## Test Coverage Summary

| Category | Tests | Coverage |
|----------|-------|----------|
| Happy Path | 4 | Basic execution, linear, dependencies, metrics |
| Input Adapters | 4 | Email, calendar, document, transcript |
| Guardrail Violations | 3 | Cost, depth, retries limits |
| Recovery | 3 | Single retry, multi-retry, partial |
| Complex Plans | 3 | Diamond, cascading, branching |
| Memory Integration | 2 | Storage, multi-execution |
| Observability | 6 | Correlation ID, metrics, success rate, serialization |
| **Total** | **25** | **Complete MVP validation** |

---

## Expected Test Results

All 25 tests should pass with:
- ✅ 0 failures
- ✅ 0 skipped
- ✅ 425+ total tests (including existing)
- ✅ No regressions to existing tests

Example output:
```
tests/test_e2e_scenarios.py::TestE2EHappyPath::test_happy_path_simple_linear_plan PASSED
tests/test_e2e_scenarios.py::TestE2EInputAdapters::test_email_input_scenario PASSED
tests/test_e2e_scenarios.py::TestE2EGuardrailViolations::test_cost_guard_violation PASSED
...
======================== 25 passed in 0.85s =========================
```

---

## Troubleshooting

### Test Fails: "No handler registered for action X"
**Cause:** Step action not registered in StepExecutorRegistry
**Fix:** Register the handler before running:
```python
registry.register("my_action", StepHandlerFactory.success_handler())
```

### Test Fails: "Correlation ID not set"
**Cause:** Correlation context not cleaned up between tests
**Fix:** Tests use `@pytest.fixture(autouse=True)` for automatic cleanup. Ensure it's present.

### Test Fails: Unexpected metrics values
**Cause:** Handler behavior doesn't match test expectations
**Fix:** Verify handler returns `StepResult(success=True/False)` as expected.

---

## Integration with CI/CD

E2E tests are designed to run in CI/CD:
- No external dependencies required
- All mocking via StepHandlerFactory
- Deterministic results (no flakiness)
- Fast execution (~1 second for all 25 tests)
- Part of standard `pytest` suite

---

## MVP Validation Checklist

PR-13 validates these MVP requirements:

- ✅ Single-worker runtime executes end-to-end
- ✅ All input adapter types work (email, calendar, document, transcript)
- ✅ Planner + Tool Selection + Self-Healing + Evaluator integrated
- ✅ Guardrails enforce cost, TTL, retries, plan depth
- ✅ Working memory + episodic memory operational
- ✅ Observability baseline (logs, metrics, correlation IDs) in place
- ✅ E2E test pack passes in CI
