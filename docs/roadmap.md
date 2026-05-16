 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/docs/roadmap.md b/docs/roadmap.md
new file mode 100644
index 0000000000000000000000000000000000000000..5682e55c4962f47a7116b2c6289cf39913c9826b
--- /dev/null
+++ b/docs/roadmap.md
@@ -0,0 +1,54 @@
+# MVP Roadmap and PR Slicing Map
+
+## Purpose
+This roadmap translates the MVP architecture into small, reviewable pull requests with explicit dependencies.
+
+## Milestones
+
+### Milestone A — Foundations
+- Issue 1: Project Bootstrap & Repository Foundations
+- Issue 2: Workflow State Machine & Policy Layer
+- Issue 3: Core Domain Contracts
+- Issue 4: Single-Worker Runtime Orchestrator (Baseline)
+
+### Milestone B — Core Agent Capabilities
+- Issue 5: Planner Agent v1
+- Issue 6: Tool Selection Agent v1 + Tool Registry
+- Issue 7: Input Adapters (Email/Calendar/Document/Transcript)
+- Issue 8: Self-Healing Agent v1
+- Issue 9: Evaluator Agent v1
+
+### Milestone C — Reliability & Operations
+- Issue 10: Memory Layer v1 (Redis Working + Episodic Store)
+- Issue 11: Guardrails Engine
+- Issue 12: Observability Baseline
+
+### Milestone D — Validation & Documentation
+- Issue 13: End-to-End MVP Scenario Pack
+- Issue 14: Documentation & ADRs
+
+## PR Slicing Map
+
+| PR | Issue | Title | Complexity | Depends on |
+|---|---:|---|---|---|
+| PR-01 | #1 | Project Bootstrap & Repository Foundations | S | - |
+| PR-02 | #2 | Workflow State Machine & Policy Layer | S-M | #1 |
+| PR-03 | #3 | Core Domain Contracts | M | #1 |
+| PR-04 | #4 | Single-Worker Runtime Orchestrator (Baseline) | M | #2, #3 |
+| PR-05 | #5 | Planner Agent v1 | M | #4 |
+| PR-06 | #6 | Tool Selection Agent v1 + Tool Registry | M | #4 |
+| PR-07 | #7 | Input Adapters | M | #3, #6 |
+| PR-08 | #8 | Self-Healing Agent v1 | M | #4 |
+| PR-09 | #9 | Evaluator Agent v1 | M-L | #4 |
+| PR-10a | #10 | Memory interfaces + episodic abstraction | M | #3, #4 |
+| PR-10b | #10 | Redis working memory adapter + integration | M | PR-10a |
+| PR-11 | #11 | Guardrails Engine | M | #5, #8, #10b |
+| PR-12 | #12 | Observability Baseline | M | #4 |
+| PR-13 | #13 | End-to-End MVP Scenario Pack | M-L | #5, #7, #8, #9, #11, #12 |
+| PR-14 | #14 | Documentation & ADRs | S-M | #13 |
+
+## Execution Notes
+- Keep each PR narrowly scoped to one issue whenever possible.
+- Prefer feature flags or stubs over broad refactors.
+- Merge order should follow dependency chain above.
+- No distributed runtime work before Milestone D completion.
 
EOF
)
