# Team Assignments - LLM Integration Roadmap

This document defines team structure, roles, and assignments for the LLM integration project (Phases 1-12).

## Team Structure

### Backend Team (Phases 1-10)
**Focus**: Core LLM framework, agents, memory, testing

**Responsibilities**:
- Implement LLM provider abstraction and providers
- Build LLM agents (Planner, Tool Selector, Evaluator, Self-Healer)
- Semantic memory layer
- Testing infrastructure
- Cost tracking and observability
- Configuration management

**Team Members** (assign your team):
- [ ] Member A
- [ ] Member B
- [ ] Member C
- [ ] Member D
- [ ] Member E

**Team Handle**: `@backend-team` (GitHub team)

---

### Frontend Team (Phase 11+)
**Focus**: GUI dashboard, REST API, web interface

**Responsibilities**:
- Web dashboard (React/Vue)
- REST API design and implementation
- Authentication UI
- Admin panel

**Team Members** (future, assign when starting Phase 11):
- [ ] Member F
- [ ] Member G

**Team Handle**: `@frontend-team` (GitHub team)

---

### DevOps Team
**Focus**: CI/CD, deployment, infrastructure, monitoring

**Responsibilities**:
- GitHub Actions setup
- Docker/Kubernetes deployment
- Monitoring and observability
- Release management
- Infrastructure automation

**Team Members** (assign your team):
- [ ] Member H
- [ ] Member I

**Team Handle**: `@devops-team` (GitHub team)

---

## Phase Leads & Assignments

### Backend Track Phase Leads

| Phase | Duration | Lead | Responsibility |
|-------|----------|------|-----------------|
| **Phase 1** | 1-2w | [TBD] | Provider abstraction, contracts, base |
| **Phase 2** | 2-3w | [TBD] | Ollama, HuggingFace, OpenAI, Anthropic providers |
| **Phase 3** | 1-2w | [TBD] | Prompt template system + YAML templates |
| **Phase 4** | 3-4w | [TBD] Lead, [TBD] Planner, [TBD] Tool, [TBD] Eval | 4 LLM agents (distribute work) |
| **Phase 5** | 1w | [TBD] | Cost tracking, metrics, guardrails |
| **Phase 6** | 1w | [TBD] | Configuration, env vars, config files |
| **Phase 7** | 1w | [TBD] | Cascade, fallback strategy |
| **Phase 8** | 2w | [TBD] | Testing patterns, mock LLM, cassettes |
| **Phase 9** | 1-2w | [TBD] | Documentation, guides, examples |
| **Phase 10** | 2-3w | [TBD] | Semantic memory, pattern learning |

### Phase 4 Agent Distribution (Recommended)

Since Phase 4 is most complex, assign one developer per agent:

| Agent | Developer | Responsibilities |
|-------|-----------|------------------|
| **Planner** | [TBD] | LLMPlanner class, task decomposition, plan generation |
| **Tool Selector** | [TBD] | LLMToolSelector, capability matching |
| **Evaluator** | [TBD] | LLMEvaluator, quality judgment, rules + heuristics + LLM |
| **Self-Healer** | [TBD] | LLMSelfHealer, failure analysis, recovery |

---

## Synchronization Schedule

### Daily Standup (15 min)
- **Time**: [TBD] (suggest 9:30 AM daily)
- **Format**: Slack or in-person
- **Topics**: Blockers, progress, help needed
- **Attendees**: All team members

### Weekly Planning (1 hour)
- **Time**: [TBD] (suggest Thursday 10:00 AM)
- **Agenda**:
  1. Review past week's progress
  2. Identify blockers (status:blocked issues)
  3. Plan next week's work
  4. Assign priorities
- **Attendees**: Phase lead, team leads
- **Notes**: Shared in #general Slack

### Phase Reviews (1 hour)
- **When**: At end of each phase milestone
- **Attendees**: Entire backend team
- **Topics**:
  1. Phase completion review
  2. Lessons learned
  3. Velocity metrics
  4. Planning for next phase
  5. Blockers/risks

### Release Planning (1 hour)
- **When**: Before releases (Phases 1, 4, 8, 10)
- **Attendees**: Backend lead, DevOps lead
- **Topics**:
  1. What's included in release
  2. Breaking changes
  3. Migration path
  4. Deployment strategy

---

## Code Review Rotation

**Code Review Policy**:
- Every PR needs **minimum 1 approval**
- Critical path PRs (Phase 4) need **2 approvals**
- CODEOWNERS automatically assigned
- Reviewers must be different from author
- Reviews within 24 hours target

**Review Rotation** (promote knowledge sharing):

```
Phase 1 Reviews:  Member A, Member B
Phase 2 Reviews:  Member B, Member C
Phase 3 Reviews:  Member A, Member D
Phase 4 Reviews:  All backend team (2 approvals per PR)
Phase 5-7 Reviews: Member C, Member D, Member E
Phase 8 Reviews:  All backend team
Phase 9 Reviews:  Any backend member (docs can be async)
Phase 10 Reviews: Member E, Member D
```

---

## Knowledge Transfer & Pairing

### Recommended Pair Programming

- **Phase 1**: New developer pairs with experienced dev
- **Phase 4**: Cross-pair agents (e.g., Planner dev reviews Tool Selector PR)
- **Phase 8**: Testing lead pairs with new testers

### Documentation Responsibility

Each phase lead writes design ADR (Architecture Decision Record):
- Where: `docs/adr/` directory
- Template: See existing ADRs in `docs/architecture-decisions.md`
- Timing: At end of phase
- Topics: Design choices, trade-offs, rationale

---

## Onboarding Checklist

New developers joining backend team should:

- [ ] Read `docs/llm-roadmap.md`
- [ ] Read `docs/multi-agent-system-reference.md`
- [ ] Review MVP code: `src/mas/agents/` (deterministic agents)
- [ ] Review tests: `tests/test_agents*.py`
- [ ] Set up local development (see CONTRIBUTING.md)
- [ ] Run all tests: `pytest` (should pass)
- [ ] Create first small PR to get familiar with workflow
- [ ] Attend standup + weekly planning
- [ ] Ask questions (no question too small!)

---

## Escalation Path

If blocked or stuck:
1. Ask in standup (15 min)
2. Pair with another developer
3. Escalate to phase lead
4. Request team meeting to unblock

**Goal**: No one stays blocked more than 1 day.

---

## Performance Metrics

Track team velocity and health:

### Per Phase:
- Issues closed / Issues planned
- PRs merged / Issues closed (ratio)
- Average PR review time
- Average issue resolution time
- Test coverage (target: 80%)
- Velocity (story points completed)

### Overall:
- Time vs estimate
- Number of blockers
- Number of regressions
- Team satisfaction (retrospective)

---

## Retrospectives

After each phase:
- **Format**: 30-min meeting
- **Attendees**: Phase team
- **Topics**:
  - What went well?
  - What was hard?
  - What to improve for next phase?
  - Recognition for good work
- **Outcome**: Action items for next phase

---

## Communication Channels

- **#announcements**: Major updates, releases
- **#phase-X**: Phase-specific work (create when starting)
- **#code-review**: PR reviews, code questions
- **#help**: Questions, blockers, pairing requests
- **GitHub Issues**: Technical discussion, decisions
- **Weekly email**: Summary of progress, upcoming priorities

---

## Appendix: GitHub Team Setup

Create teams in GitHub Settings:

```bash
# Create backend team
gh api /orgs/{org}/teams \
  -f name="Backend" \
  -f description="Core LLM framework developers"

# Add members
gh api /orgs/{org}/teams/backend/memberships/{username} \
  -f role=member

# Same for frontend and devops
```

Update CODEOWNERS with team handles:
```
/src/mas/llm/  @wildcatkss/backend-team
/src/gui/      @wildcatkss/frontend-team
.github/       @wildcatkss/devops-team
```

---

## Questions?

See:
- [docs/llm-roadmap.md](../../docs/llm-roadmap.md) - Full roadmap
- [.github/QUICK_START_GITHUB.md](./QUICK_START_GITHUB.md) - GitHub setup
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Development guidelines
