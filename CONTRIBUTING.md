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

## Areas for Contribution

### High Priority
- Distributed runtime support (Milestone E)
- Additional input adapters
- More evaluation rules and heuristics
- Performance optimizations

### Medium Priority
- Documentation improvements
- Example scenarios
- Community tools and utilities
- Integration with external systems

### Low Priority
- Code style improvements
- Comment enhancements
- Minor refactors

## Design Principles

When contributing, keep these principles in mind:

1. **Stability before intelligence** — Correct > sophisticated
2. **Observability before optimization** — Measure > premature optimization
3. **No hidden orchestration** — Explicit dependencies
4. **No implicit mutations** — All changes logged and auditable
5. **Composition over refactors** — Small iterations preferred

See [docs/architecture-decisions.md](docs/architecture-decisions.md) for detailed ADRs.

## Questions or Need Help?

- Check [docs/](docs/) for documentation
- Review [tests/](tests/) for usage examples
- Open an issue for questions or clarifications
- See [SECURITY.md](SECURITY.md) for security-related questions

## Code of Conduct

This project adheres to the Contributor Covenant. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

---

Thank you for contributing! 🎉
