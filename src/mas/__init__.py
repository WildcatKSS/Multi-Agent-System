"""Multi-Agent System: Generic autonomous agent orchestration framework.

A production-ready, single-worker runtime for executing task plans with:
- Automatic task decomposition via Planner agent
- Tool selection via tool registry
- Failure recovery via Self-Healing agent
- Output evaluation via Evaluator agent
- Runtime guardrails enforcement (cost, TTL, retries, depth)
- Structured observability (correlation IDs, metrics, JSON logging)
- In-memory and Redis-backed memory stores

## Quick Start

```python
from mas.domain.task import Task
from mas.domain.plan import Plan, Step
from mas.runtime.orchestrator import Runtime
from mas.runtime.executor import StepExecutorRegistry, StepResult

# Create a task
task = Task(id="task-1", description="Process data", goal="Complete successfully")

# Create a plan with steps
plan = Plan(
    id="plan-1",
    task_id="task-1",
    steps=[Step(id="step-1", action="process", inputs={})],
    estimated_cost=1.0,
    estimated_time_seconds=10.0,
    reasoning="Linear decomposition"
)

# Register step handlers
registry = StepExecutorRegistry()
registry.register("process", lambda step: StepResult(success=True))

# Execute
runtime = Runtime(registry=registry)
result = runtime.run(task, plan)
assert result.succeeded is True
```

## Architecture

Single-worker runtime with modular agent design:
1. **Planner**: Task decomposition into linear steps
2. **Tool Selector**: Maps steps to registered handlers
3. **Runtime**: Executes steps in dependency order
4. **Guardrails**: Enforces limits (cost, TTL, retries, depth)
5. **Self-Healer**: Recovers from failures via retries
6. **Evaluator**: Scores execution quality
7. **Observability**: Tracks metrics, logs, correlation IDs
8. **Memory**: Stores episodic records and working state

## Key Features

- **Type-Safe**: Full Python 3.12+ type hints
- **Thread-Safe**: Async-aware via contextvars
- **Well-Tested**: 450+ tests (100% passing)
- **Extensible**: Plugin architecture for custom agents
- **Observable**: Structured JSON logging, correlation IDs, metrics
- **Production-Ready**: No external dependencies (Redis optional)
"""

from importlib.metadata import version

__version__ = version("mas")

__all__ = ["__version__"]
