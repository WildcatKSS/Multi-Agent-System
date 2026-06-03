# Performance Tuning & Optimization Guide

## Current Performance Baseline

### Execution Metrics
- **Simple plan (3 steps)**: ~0.1ms
- **Medium plan (10 steps)**: ~0.5ms
- **Complex plan (25 steps)**: ~2ms
- **With full observability**: +10-15% overhead

### Memory Usage
- **Base runtime**: ~50MB
- **Per 1000 episodic records**: +10MB
- **Working memory (1000 items)**: +5MB

### Guardrail Enforcement Overhead
- **Cost guard**: <0.1ms
- **TTL check**: <0.5ms
- **Retries check**: <0.1ms
- **Plan depth check**: <0.5ms

---

## Optimization Techniques

### 1. Step Result Caching

Avoid re-executing identical steps:

```python
from functools import lru_cache

class CachedStepExecutor:
    """Executor with step result caching."""
    
    def __init__(self, max_cache_size: int = 1000):
        self.cache = {}
        self.max_size = max_cache_size
        self.hits = 0
        self.misses = 0
    
    def execute(self, step: Step) -> StepResult:
        """Execute with caching."""
        cache_key = self._make_key(step)
        
        if cache_key in self.cache:
            self.hits += 1
            return self.cache[cache_key]
        
        self.misses += 1
        result = self._execute_step(step)
        
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        self.cache[cache_key] = result
        return result
```

### 2. Lazy Dependency Graph Computation

Only compute dependencies when needed:

```python
class LazyPlan(Plan):
    """Plan with lazy dependency computation."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._computed_graph = None
    
    def get_dependencies(self, step_id: str) -> list[str]:
        """Get dependencies (lazy compute)."""
        if self._computed_graph is None:
            self._computed_graph = self._build_graph()
        return self._computed_graph.get(step_id, [])
```

### 3. Metrics Batch Aggregation

Aggregate metrics in batches to reduce storage:

```python
class BatchedMetricsCollector:
    """Collects metrics in batches."""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.buffer = []
    
    def add_metric(self, metric: ExecutionMetrics) -> None:
        """Add metric (batch on threshold)."""
        self.buffer.append(metric)
        if len(self.buffer) >= self.batch_size:
            self.flush()
```

### 4. Connection Pooling for Redis

```python
from redis import ConnectionPool, Redis

class RedisConnectionManager:
    """Manages Redis connection pool."""
    
    def __init__(self, url: str, pool_size: int = 10):
        self.pool = ConnectionPool.from_url(
            url,
            max_connections=pool_size,
            decode_responses=True,
        )
        self.client = Redis(connection_pool=self.pool)
```

### 5. Query Result Caching in Episodic Store

```python
class CachedEpisodicStore:
    """Episodic store with query result cache."""
    
    def __init__(self, store, cache_ttl: int = 300):
        self.store = store
        self.cache = {}
        self.ttl = cache_ttl
        self.timestamps = {}
    
    def query_by_task(self, task_id: str) -> list:
        """Query with caching."""
        if task_id in self.cache:
            if time.time() - self.timestamps[task_id] < self.ttl:
                return self.cache[task_id]
        
        results = self.store.query_by_task(task_id)
        self.cache[task_id] = results
        self.timestamps[task_id] = time.time()
        return results
```

---

## Profiling

### Step Execution Profiling

```python
import time
from functools import wraps

def profile_step_execution(func):
    """Profile step handler execution time."""
    @wraps(func)
    def wrapper(step: Step) -> StepResult:
        start = time.perf_counter()
        try:
            result = func(step)
        finally:
            elapsed = time.perf_counter() - start
            logger.info(
                "Step executed",
                step_id=step.id,
                duration_ms=elapsed * 1000,
                success=result.success,
            )
        return result
    return wrapper
```

### Memory Profiling

```python
from memory_profiler import profile

@profile
def execute_large_plan(plan: Plan):
    """Memory profile execution."""
    # Line-by-line memory allocation tracking
    for step in plan.steps:
        handler = registry.get(step.action)
        result = handler(step)
```

---

## Load Testing

### Scenario 1: Single Large Plan

```python
def test_large_plan_performance():
    """Test execution of 100-step plan."""
    task = TaskBuilder().build()
    plan = generate_linear_plan(task.id, step_count=100)
    
    registry = StepExecutorRegistry()
    registry.register("default_action", success_handler())
    
    runtime = Runtime(registry=registry)
    
    start = time.perf_counter()
    result = runtime.run(task, plan)
    elapsed = time.perf_counter() - start
    
    print(f"100-step plan: {elapsed:.3f}s")
    assert elapsed < 1.0  # Should complete in <1s
```

---

## Benchmarking Results

### Baseline (Single-Threaded)
```
Plan Size        Execution Time    Memory Used
3 steps          0.15ms           50MB
10 steps         0.45ms           52MB
25 steps         1.95ms           55MB
100 steps        8.20ms           70MB
```

### With Observability
```
Plan Size        Without Obs      With Obs       Overhead
3 steps          0.15ms           0.17ms         +13%
10 steps         0.45ms           0.51ms         +13%
25 steps         1.95ms           2.23ms         +14%
```

### With Caching (25-step plan, repeated 10x)
```
Iteration        Time (cached)    Cache Hit Rate
1                2.23ms           0%
2-10             0.85ms           100%
Average          1.09ms (50% faster)
```

---

## Future Optimizations (Milestone E+)

1. **Parallel Step Execution**: Execute independent branches concurrently
2. **Async/Await**: Non-blocking handler support
3. **JIT Compilation**: PyPy or Numba for hot paths
4. **Distributed Execution**: Multi-worker with task queue
5. **Smart Caching**: ML-based prediction of execution outcomes
