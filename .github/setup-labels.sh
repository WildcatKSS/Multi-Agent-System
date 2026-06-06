#!/bin/bash
# Setup GitHub labels for LLM roadmap phases
# Usage: export GITHUB_TOKEN=... && bash .github/setup-labels.sh wildcatkss/multi-agent-system

REPO="${1:-wildcatkss/multi-agent-system}"
GH_TOKEN="${GITHUB_TOKEN}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ -z "$GH_TOKEN" ]; then
    echo -e "${RED}Error: GITHUB_TOKEN not set${NC}"
    echo "Usage: export GITHUB_TOKEN=your_token && bash .github/setup-labels.sh"
    exit 1
fi

echo "Setting up labels for $REPO..."
echo ""

# Define labels: name,color,description
labels=(
    'type:feature,#28a745,New feature (agent, provider, memory layer)'
    'type:enhancement,#ffd700,Improvement to existing feature'
    'type:bugfix,#d73a49,Bug fix'
    'type:docs,#0075ca,Documentation, examples'
    'type:test,#a371f7,Tests, testing infrastructure'
    'type:refactor,#fbca04,Code refactoring, cleanup'

    'priority:critical,#FF0000,Blocks other work, must be first'
    'priority:high,#FF6600,Important, do soon'
    'priority:medium,#FFFF00,Normal priority'
    'priority:low,#90EE90,Nice to have, defer if needed'

    'phase:1-provider,#1f6feb,Phase 1: Provider Abstraction'
    'phase:2-providers,#1f6feb,Phase 2: LLM Providers'
    'phase:3-prompts,#1f6feb,Phase 3: Prompt Templates'
    'phase:4-agents,#1f6feb,Phase 4: LLM Agents'
    'phase:5-observability,#1f6feb,Phase 5: Cost Tracking'
    'phase:6-config,#1f6feb,Phase 6: Configuration'
    'phase:7-cascade,#1f6feb,Phase 7: Cascade & Fallback'
    'phase:8-testing,#1f6feb,Phase 8: Testing'
    'phase:9-docs,#1f6feb,Phase 9: Documentation'
    'phase:10-semantic,#1f6feb,Phase 10: Semantic Memory'
    'phase:11-gui,#d4af37,Phase 11: GUI & API (Future)'
    'phase:12-commercial,#d4af37,Phase 12: Commercialization (Future)'

    'component:planner,#17a2b8,Planner agent'
    'component:tool-selector,#17a2b8,Tool Selector agent'
    'component:evaluator,#17a2b8,Evaluator agent'
    'component:self-healer,#17a2b8,Self-Healer agent'
    'component:runtime,#17a2b8,Runtime/Orchestrator'
    'component:memory,#17a2b8,Memory layer'
    'component:observability,#17a2b8,Logging, metrics'
    'component:guardrails,#17a2b8,Guardrails engine'
    'component:llm,#17a2b8,LLM provider layer'

    'status:ready,#90EE90,Ready to start'
    'status:in-progress,#FFB6C6,Currently being worked'
    'status:blocked,#FF6B6B,Blocked by another issue'
    'status:review,#FFA500,Waiting for code review'
    'status:testing,#87CEEB,Testing/QA phase'
    'status:done,#90EE90,Completed'

    'team:backend,#0075ca,Core framework'
    'team:frontend,#0075ca,GUI/Dashboard'
    'team:devops,#0075ca,Deployment, CI/CD'
    'team:research,#0075ca,Architecture, exploration'
)

created=0
skipped=0
failed=0

for label in "${labels[@]}"; do
    IFS=',' read -r name color description <<< "$label"

    # Remove # from color for gh command
    color_clean="${color//\#/}"

    # Try to create label
    result=$(gh label create "$name" \
        --repo "$REPO" \
        --color "$color_clean" \
        --description "$description" 2>&1)

    if echo "$result" | grep -q "already exists"; then
        echo -e "${YELLOW}⊘${NC} '$name' already exists"
        ((skipped++))
    elif echo "$result" | grep -q "404"; then
        echo -e "${RED}✗${NC} '$name' failed (repo not found)"
        ((failed++))
    elif echo "$result" | grep -q "error"; then
        echo -e "${RED}✗${NC} '$name' failed"
        ((failed++))
    else
        echo -e "${GREEN}✓${NC} '$name'"
        ((created++))
    fi
done

echo ""
echo "============================================"
echo "Summary:"
echo -e "  ${GREEN}Created${NC}: $created"
echo -e "  ${YELLOW}Skipped${NC}: $skipped (already exist)"
echo -e "  ${RED}Failed${NC}: $failed"
echo "============================================"

if [ $failed -gt 0 ]; then
    exit 1
fi

echo -e "${GREEN}Label setup complete!${NC}"
