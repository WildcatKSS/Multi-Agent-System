# GitHub Setup Quick Start

Get your team up and running with the LLM integration roadmap.

## Prerequisites

- [GitHub CLI](https://cli.github.com/) installed (`gh --version`)
- Personal access token with `repo` scope ([create one](https://github.com/settings/tokens/new?scopes=repo))
- Write access to the repository

## Step 1: Set Up Environment

```bash
# Export your GitHub token
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Verify it works
gh auth status
```

## Step 2: Create Labels (One-Time Setup)

Run the label setup script to create all 40+ labels:

```bash
# From repository root
bash .github/setup-labels.sh wildcatkss/multi-agent-system
```

**Output**:
```
✓ type:feature
✓ type:enhancement
✓ priority:critical
...
✓ phase:10-semantic
✓ team:backend
✓ component:llm
... (40+ total)
```

## Step 3: Create Milestones (One-Time Setup)

Run the milestone setup script to create all 12 phases:

```bash
bash .github/setup-milestones.sh wildcatkss/multi-agent-system
```

**Output**:
```
Creating milestone: Phase 1: Provider Abstraction ... created
Creating milestone: Phase 2: LLM Providers ... created
...
Creating milestone: Phase 12: Commercialization ... created
```

Verify in GitHub: Settings → Milestones (should show 12 items)

## Step 4: Assign Team Members

In GitHub repository:

1. Go to **Settings** → **Collaborators** (if not already invited)
2. Assign people to the team
3. Create GitHub teams (Backend, Frontend, DevOps)
4. Update `.github/CODEOWNERS` with team handles

## Step 5: Create GitHub Project Board

```bash
# Create a Project for the roadmap
gh project create --format json \
  --title "LLM Integration Roadmap" \
  --owner wildcatkss/multi-agent-system

# Note the project ID, then configure:
# Columns: Backlog, In Progress, Review, Testing, Done
# Filter: phase label, component label
```

Or create manually:
1. Go to repo → **Projects** → **New Project**
2. Select **Table** view
3. Name: "LLM Integration Roadmap"
4. Add fields: Phase, Component, Priority, Estimate

## Step 6: Start Creating Issues

Use the issue template:

```bash
# Create a task for Phase 1
gh issue create \
  --title "[Phase 1] Create LLM provider contracts" \
  --body "See phase-task template" \
  --label "phase:1-provider,type:feature,priority:critical" \
  --milestone "Phase 1: Provider Abstraction"

# Or use the web interface
# Go to repo → Issues → New Issue → Choose "Phase Task" template
```

## Useful gh Commands

```bash
# List all Phase 1 issues
gh issue list --label "phase:1-provider" --state open

# List by priority
gh issue list --label "priority:critical" --state open

# Assign to team member
gh issue edit 123 --assignee "username"

# Add labels to existing issue
gh issue edit 123 --add-label "phase:1-provider,status:in-progress"

# Add to milestone
gh issue edit 123 --milestone "Phase 1: Provider Abstraction"

# Create draft PR
gh pr create --draft --body "WIP: Phase 4 Planner"

# Link PR to issue
gh pr edit 456 --body "Closes #123" --body-append "..."
```

## Team Workflow

### Weekly Team Sync

1. **Check Dashboard**:
   ```bash
   # Overview of all open issues
   gh issue list --label "phase:1-provider" --state open
   ```

2. **Identify Blockers**:
   ```bash
   gh issue list --label "status:blocked" --state open
   ```

3. **Review Progress**:
   - Backlog → In Progress → Review → Testing → Done
   - Update GitHub Project board

### Creating a Task

1. Click "New Issue"
2. Select "Phase Task" template
3. Fill in Phase, Type, Priority, Component
4. Link to milestone
5. Add estimate
6. Assign to team member
7. Add labels

### Working on a Task

1. Assign to yourself
2. Move to "In Progress" on project board
3. Create branch: `git checkout -b phase-X/task-description`
4. Create draft PR: `gh pr create --draft`
5. When ready: Mark "Ready for Review"

### Code Review

1. Require 1 approval (2 for critical)
2. Use CODEOWNERS for auto-assignment
3. PR checks must pass:
   - Type checking (mypy)
   - Linting (ruff)
   - Tests (pytest)
   - Security scan

### Merging & Closing

1. Merge to feature branch (`claude/agentic-framework-roadmap-23jNl`)
2. Update issue: Mark "status:testing"
3. When phase complete: Close milestone
4. Release v1.1.0-phase-X

## GitHub Actions Setup

The repository should have CI/CD workflows:

```bash
# View all workflow runs
gh run list

# View latest run for phase
gh run list --workflow "pytest.yml" --limit 5

# View logs for failed run
gh run view 12345 --log
```

## Continuous Integration

Every PR automatically runs:
- ✓ Type checking (mypy)
- ✓ Linting (ruff)
- ✓ Tests (pytest)
- ✓ Coverage checks
- ✓ Security scanning

All checks must pass before merge.

## Release Process

When a phase is complete:

```bash
# Tag the version
git tag -a v1.1.0-phase-4 -m "Phase 4: LLM Agents complete"
git push origin v1.1.0-phase-4

# Create release on GitHub
gh release create v1.1.0-phase-4 \
  --title "Phase 4: LLM Agents" \
  --notes "All 4 agents now use LLM reasoning with fallbacks"

# Close the milestone
gh api repos/wildcatkss/multi-agent-system/milestones \
  --input <(jq -n '{state:"closed"}') \
  | jq '.number'
```

## Troubleshooting

### GITHUB_TOKEN not working

```bash
# Verify token
gh auth status

# Re-authenticate
gh auth login

# Select: GitHub.com, HTTPS, y (authenticate with token)
```

### Label/milestone already exists

Scripts skip existing items - this is normal. Re-run anytime without issues.

### PR checks failing

Check the "Checks" tab in PR for details:
- Type errors? Run `mypy src/ tests/`
- Lint errors? Run `ruff check src/`
- Test failures? Run `pytest`

## Helpful Links

- [GitHub CLI Reference](https://cli.github.com/manual)
- [GitHub Issues Guide](https://guides.github.com/features/issues/)
- [GitHub Project Boards](https://docs.github.com/en/issues/planning-and-tracking-with-projects)
- [PR Checklist](../../CONTRIBUTING.md)
- [Roadmap Details](../../docs/llm-roadmap.md)

## Next Steps

1. ✓ Run `setup-labels.sh`
2. ✓ Run `setup-milestones.sh`
3. ✓ Create GitHub Project board
4. ✓ Assign team members
5. → Start Phase 1: Create first issue
6. → Begin development!

---

**Questions?** See [docs/llm-roadmap.md](../../docs/llm-roadmap.md) for full details.
