"""Scenario data and constants for E2E testing."""

from typing import Any

# Happy path scenario definitions
HAPPY_PATH_SCENARIOS = {
    "simple_linear": {
        "description": "Simple linear task with 3 steps",
        "step_count": 3,
        "action": "default_action",
    },
    "multi_step": {
        "description": "Multi-step linear execution",
        "step_count": 5,
        "action": "default_action",
    },
    "with_dependencies": {
        "description": "Steps with complex dependencies",
        "type": "diamond",
    },
}

# Input adapter scenario definitions
INPUT_ADAPTER_SCENARIOS = {
    "email": {
        "source": "email",
        "description": "Process email input",
        "sender": "user@example.com",
        "subject": "Action Required: Process Request",
        "body": "Please process this urgent request and provide status update.",
    },
    "calendar": {
        "source": "calendar",
        "description": "Process calendar event",
        "event_title": "Team Standup",
        "start_time": "2026-06-03T09:00:00Z",
        "end_time": "2026-06-03T09:30:00Z",
        "attendees": ["alice@example.com", "bob@example.com"],
    },
    "document": {
        "source": "document",
        "description": "Process document",
        "doc_type": "proposal",
        "filename": "proposal.pdf",
        "content": "This is a proposal document requiring review and approval.",
    },
    "transcript": {
        "source": "transcript",
        "description": "Process transcript",
        "speaker_count": 2,
        "duration_seconds": 300,
        "content": "Alice: Let's discuss the project. Bob: Sure, what's on your mind?",
    },
}

# Guardrail violation scenario definitions
GUARDRAIL_SCENARIOS = {
    "cost_exceeded": {
        "guard_type": "cost",
        "description": "Plan exceeds maximum cost limit",
        "plan_cost": 150.0,
        "max_limit": 100.0,
        "step_count": 3,
        "cost_per_step": 50.0,
    },
    "ttl_exceeded": {
        "guard_type": "ttl",
        "description": "Execution exceeds maximum duration",
        "plan_duration_seconds": 600.0,
        "max_limit": 300.0,
        "step_count": 2,
    },
    "retries_exceeded": {
        "guard_type": "retries",
        "description": "Total retries exceed limit",
        "max_limit": 2,
        "step_count": 3,
        "max_retries_per_step": 2,
    },
    "plan_depth_exceeded": {
        "guard_type": "plan_depth",
        "description": "Plan depth exceeds limit",
        "plan_depth": 25,
        "max_limit": 20,
        "step_count": 25,
    },
}

# Recovery scenario definitions
RECOVERY_SCENARIOS = {
    "single_retry": {
        "description": "Step fails once then succeeds",
        "fail_count": 1,
        "max_retries": 1,
    },
    "multi_retry": {
        "description": "Step fails multiple times then succeeds",
        "fail_count": 2,
        "max_retries": 3,
    },
    "partial_recovery": {
        "description": "Some steps fail, some recover",
        "step_count": 4,
        "failing_steps": [0, 2],
        "max_retries_per_step": 1,
    },
}

# Complex plan scenario definitions
COMPLEX_PLAN_SCENARIOS = {
    "diamond": {
        "description": "Diamond dependency graph",
        "pattern": "diamond",
    },
    "multi_branch": {
        "description": "Multiple independent branches",
        "pattern": "branched",
        "branch_count": 3,
        "steps_per_branch": 2,
    },
    "skip_cascading": {
        "description": "Skip cascades through dependencies",
        "pattern": "linear",
        "step_count": 5,
        "fail_step_index": 1,
    },
}

# Memory integration scenario definitions
MEMORY_SCENARIOS = {
    "single_execution": {
        "description": "Record single execution in episodic store",
        "step_count": 3,
    },
    "multiple_executions": {
        "description": "Record multiple executions for same task",
        "execution_count": 3,
        "step_count": 2,
    },
    "execution_history": {
        "description": "Query execution history by task",
        "step_count": 4,
    },
}

# Observability scenario definitions
OBSERVABILITY_SCENARIOS = {
    "correlation_propagation": {
        "description": "Verify correlation ID propagates through execution",
        "step_count": 3,
    },
    "metrics_completeness": {
        "description": "All metrics fields populated correctly",
        "step_count": 5,
    },
    "success_rate_calculation": {
        "description": "Success rate calculated accurately",
        "completed_steps": 3,
        "failed_steps": 1,
        "expected_success_rate": 0.75,
    },
    "guard_violation_metrics": {
        "description": "Guard violation recorded in metrics",
        "guard_type": "cost",
    },
    "structured_logging": {
        "description": "Structured JSON logs include correlation context",
        "step_count": 2,
    },
}
