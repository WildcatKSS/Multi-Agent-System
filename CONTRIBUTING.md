# Contributing to Multi-Agent System

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.12+
- Git
- Bash (for install.sh)

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/WildcatKSS/Multi-Agent-System.git
   cd Multi-Agent-System
   ```

2. Run the installer:
   ```bash
   ./install.sh
   ```

3. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

4. Run tests to verify setup:
   ```bash
   pytest -v
   ```

## Development Workflow

### Code Style

- **Formatting**: Follow Python 3.12+ conventions
- **Type Hints**: Full type hints required for public APIs
- **Imports**: Organize imports alphabetically
- **Line Length**: 100 characters preferred
- **Docstrings**: Clear, concise docstrings for public functions and classes

### Making Changes

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes:
   - Keep commits focused and atomic
   - Write clear commit messages
   - Update tests alongside code changes

3. Run tests:
   ```bash
   pytest -v
   ```

4. All tests must pass before submitting a PR

### Testing Requirements

- Write tests for all new features
- Maintain or improve code coverage
- Tests should follow project conventions:
  - Class-based organization
  - No pytest fixtures (use helper functions instead)
  - Clear test names describing what is tested

### Commit Messages

Follow these guidelines:
- Start with a verb (feat:, fix:, docs:, test:, refactor:)
- Be concise and descriptive
- Reference issues where relevant
- Example: `feat: Add correlation ID support for distributed tracing`

## Submitting Pull Requests

1. Push your branch to GitHub:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Create a PR with:
   - Clear title (under 70 characters)
   - Description explaining WHY the change is needed
   - Testing approach
   - Any breaking changes clearly noted

3. Ensure all checks pass:
   - ✅ All 450+ tests passing
   - ✅ No type errors
   - ✅ Code follows style guidelines

4. Be responsive to review feedback

## Code Review Process

PRs are reviewed for:
- **Correctness** — Does it work as intended?
- **Architecture** — Does it fit the design?
- **Tests** — Are there adequate tests?
- **Documentation** — Is it clear and complete?
- **Security** — Are there any vulnerabilities?
- **Performance** — Are there performance concerns?

## Contributing to v2.0.0 (LLM Integration)

The v2.0.0 release focuses on LLM integration with open source models (Ollama, Llama2, Mistral) and optional proprietary APIs.

### Getting Started with LLM Development

For detailed roadmap and team structure:
- **Read**: [docs/llm-roadmap.md](docs/llm-roadmap.md) — 12-phase development plan
- **Setup**: [.github/QUICK_START_GITHUB.md](.github/QUICK_START_GITHUB.md) — GitHub automation
- **Team**: [.github/TEAM_ASSIGNMENTS.md](.github/TEAM_ASSIGNMENTS.md) — Phase leads and roles

### LLM Development Phases

| Phase | Focus | Status | Lead |
|-------|-------|--------|------|
| **1** | Provider Abstraction | Coming soon | TBD |
| **2** | LLM Providers (Ollama, HuggingFace, OpenAI, Anthropic) | Coming soon | TBD |
| **3** | Prompt Templates (YAML-based) | Coming soon | TBD |
| **4** | LLM Agents (Planner, Tool Selector, Evaluator, Self-Healer) | Coming soon | TBD |
| **5-10** | Cost Tracking, Config, Cascade, Testing, Docs, Semantic Memory | Coming soon | TBD |

### High Priority (v2.0.0)
- LLM provider abstraction layer
- Ollama provider implementation (local, free)
- LLM-based agents with deterministic fallback
- Semantic memory and pattern learning
- Prompt template system

### Medium Priority (v2.0+)
- Additional LLM providers (Gemini, Cohere, etc.)
- Distributed runtime support
- Advanced prompt engineering tools
- Model fine-tuning support

### Low Priority (Future)
- GUI dashboard (Phase 11)
- Commercialization/SaaS (Phase 12)
- Reward modeling
- Adaptive learning

## Design Principles

When contributing, keep these principles in mind:

1. **Stability before intelligence** — Correct > sophisticated
2. **Observability before optimization** — Measure > premature optimization
3. **No hidden orchestration** — Explicit dependencies
4. **No implicit mutations** — All changes logged and auditable
5. **Composition over refactors** — Small iterations preferred

See [docs/v1.0.0-architecture-decisions.md](docs/v1.0.0-architecture-decisions.md) for detailed v1.0.0 ADRs.
See [docs/multi-agent-system-reference.md](docs/multi-agent-system-reference.md) for v2.0.0 architecture.

## Questions or Need Help?

- Check [docs/](docs/) for documentation
- Review [tests/](tests/) for usage examples
- Open an issue for questions or clarifications
- See [SECURITY.md](SECURITY.md) for security-related questions

## Code of Conduct

This project adheres to the Contributor Covenant. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

---

Thank you for contributing! 🎉
