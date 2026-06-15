# Team Assignments - LLM Integration Roadmap

Defines team structure and phase leadership for v2.0.0 development.  
**For detailed phase timelines, deliverables, and dependencies, see [docs/llm-roadmap.md](../../docs/llm-roadmap.md).**

## Teams

| Team | Phases | Members | Focus |
|------|--------|---------|-------|
| **Backend** | 1-10 | TBD (5) | LLM framework, agents, memory, testing |
| **Frontend** | 11+ | TBD (2) | GUI, REST API, dashboard |
| **DevOps** | All | TBD (2) | CI/CD, deployment, monitoring |

## Phase Leadership

| Phase | Duration | Lead | Notes |
|-------|----------|------|-------|
| 1-3 | 1-2w each | TBD | Sequential; Phase 1 unblocks 2 & 3 |
| **4 (Critical)** | 3-4w | TBD | Distribute 4 agents: Planner, Tool Selector, Evaluator, Self-Healer |
| 5-7 | 1w each | TBD | Sequential; depend on Phase 4 |
| **8 (Critical)** | 2w | TBD | Testing; enable Phase 9 & 10 in parallel |
| 9-10 | 1-3w | TBD | Can run parallel after Phase 8 |

## Code Review Policy

- Minimum 1 approval per PR
- 2 approvals required for critical path (Phase 4, Phase 8)
- CODEOWNERS auto-assigned
- Target: 24-hour review turnaround

## Onboarding

New developers should:
1. Read [docs/llm-roadmap.md](../../docs/llm-roadmap.md)
2. Review MVP code: `src/mas/agents/`
3. Run tests: `pytest`
4. Create first small PR
5. Ask questions in team standup

## References

- [LLM Roadmap](../../docs/llm-roadmap.md) — Phase details, timelines, deliverables
- [GitHub Setup](./.github/QUICK_START_GITHUB.md) — Automated label/milestone creation
- [Release Checklist](./.github/RELEASE_2.0.0_CHECKLIST.md) — Phase tracking
- [CODEOWNERS](./.github/CODEOWNERS) — Auto-assigned reviewers by path
