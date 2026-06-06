#!/bin/bash
# Setup GitHub milestones for LLM roadmap phases
# Usage: export GITHUB_TOKEN=... && bash .github/setup-milestones.sh wildcatkss/multi-agent-system

REPO="${1:-wildcatkss/multi-agent-system}"
GH_TOKEN="${GITHUB_TOKEN}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ -z "$GH_TOKEN" ]; then
    echo -e "${RED}Error: GITHUB_TOKEN not set${NC}"
    echo "Usage: export GITHUB_TOKEN=your_token && bash .github/setup-milestones.sh"
    exit 1
fi

echo "Setting up milestones for $REPO..."
echo ""

# Calculate due dates from today (starting 2026-06-06, adjust as needed)
# Phase 1: 1-2 weeks (2 weeks from start = 2026-06-20)
milestones=(
    'Phase 1: Provider Abstraction|Create LLM provider abstraction layer, contracts, base implementation. ~8 issues, ~3 PRs.|2026-07-04'
    'Phase 2: LLM Providers|Implement Ollama, HuggingFace, OpenAI, Anthropic providers. ~10 issues, ~5 PRs.|2026-07-25'
    'Phase 3: Prompt Templates|Create prompt template system with YAML configuration. ~8 issues, ~3-4 PRs.|2026-08-08'
    'Phase 4: LLM Agents|Build LLM-based Planner, Tool Selector, Evaluator, Self-Healer agents. ~15 issues, ~8-10 PRs.|2026-09-05'
    'Phase 5: Cost Tracking|Add LLM metrics, pricing models, guardrails integration. ~5 issues, ~2-3 PRs.|2026-09-19'
    'Phase 6: Configuration|Implement config files, environment variables. ~5 issues, ~2-3 PRs.|2026-10-03'
    'Phase 7: Cascade & Fallback|Build provider cascade system with failover logic. ~4 issues, ~2 PRs.|2026-10-17'
    'Phase 8: Testing Patterns|Comprehensive testing with mock LLM, record/replay, real model tests. ~10 issues, ~4-5 PRs.|2026-11-14'
    'Phase 9: Documentation|Write docs, guides, examples, migration guide. ~8 issues, ~3-4 PRs.|2026-12-05'
    'Phase 10: Semantic Memory|Implement semantic memory layer for pattern learning. ~12 issues, ~5-6 PRs.|2027-01-02'
    'Phase 11: GUI & REST API|Web dashboard and REST API layer (Future). Team-dependent timeline.|2027-02-06'
    'Phase 12: Commercialization|Multi-tenant, billing, security, deployment (Future). Team-dependent timeline.|2027-03-13'
)

created=0
skipped=0
failed=0

for milestone in "${milestones[@]}"; do
    IFS='|' read -r title description due_date <<< "$milestone"

    echo -n "Creating milestone: $title ... "

    result=$(gh milestone create "$title" \
        --repo "$REPO" \
        --description "$description" \
        --due-date "$due_date" 2>&1)

    if echo "$result" | grep -q "already exists"; then
        echo -e "${YELLOW}already exists${NC}"
        ((skipped++))
    elif echo "$result" | grep -q "404"; then
        echo -e "${RED}failed (repo not found)${NC}"
        ((failed++))
    elif echo "$result" | grep -q "error"; then
        echo -e "${RED}failed${NC}"
        ((failed++))
    else
        echo -e "${GREEN}created${NC}"
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

echo -e "${GREEN}Milestone setup complete!${NC}"
