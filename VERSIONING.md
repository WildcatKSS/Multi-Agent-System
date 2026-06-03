# Versioning Policy

Multi-Agent System follows [Semantic Versioning 2.0.0](https://semver.org/).

## Version Format

Versions are expressed as `MAJOR.MINOR.PATCH`:

- **MAJOR**: Incompatible API changes
- **MINOR**: Backward-compatible functionality additions
- **PATCH**: Backward-compatible bug fixes and security patches

Example: `1.0.0` → `1.1.0` (new feature) → `1.1.1` (bug fix) → `2.0.0` (breaking change)

## API Stability Guarantees

### 1.0.0 Release

The 1.0.0 release includes these stability guarantees:

**What's Stable:**
- All public classes and functions in `src/mas/` (except those marked `@internal`)
- Function signatures and return types
- Configuration schemas (GuardrailsConfig, etc.)
- Runtime behavior and semantics

**What May Change (1.x):**
- Internal implementation details
- Undocumented behaviors
- Experimental features (if any)
- Performance characteristics

### Backward Compatibility

**1.x versions (1.0.0, 1.1.0, 1.2.0, etc.)** maintain backward compatibility:
- Code written for 1.0.0 will work with 1.1.0, 1.2.0, etc.
- Deprecated features are supported with warnings for at least one minor release
- Breaking changes require a major version bump (2.0.0)

**Example Compatibility:**
```python
# Code written for 1.0.0
from mas.runtime.orchestrator import Runtime
runtime = Runtime(registry=registry)
result = runtime.run(task, plan)

# Still works in 1.1.0, 1.2.0, etc.
# May not work in 2.0.0
```

## Deprecation Policy

When an API becomes deprecated:

1. **Notice**: Announced in release notes and migration guide
2. **Transition Period**: Feature supported with `DeprecationWarning` for at least one full minor release
3. **Removal**: Feature removed in next major version

Example timeline:
- **1.0.0**: Feature `old_api` introduced
- **1.2.0**: `old_api` deprecated in favor of `new_api`, raises `DeprecationWarning`
- **1.3.0**: `old_api` still works, deprecated
- **2.0.0**: `old_api` removed, `new_api` becomes standard

## Release Cycle

### Major Releases (1.0.0 → 2.0.0)
- Long-term planning (6+ months)
- Comprehensive feature set
- Breaking changes allowed
- Manual testing + full test suite
- Security review required

### Minor Releases (1.0.0 → 1.1.0)
- Feature additions
- Backward compatible
- Quarterly or as needed
- Full test suite required
- No breaking changes

### Patch Releases (1.0.0 → 1.0.1)
- Bug fixes and security updates
- No new features (exception: critical security patches)
- High priority for security patches
- As needed (typically within days of discovery)

## Support Lifecycle

| Phase       | Duration   | Support Level                          |
|-------------|-----------|----------------------------------------|
| Active      | 1 year    | Full support, security + bug fixes     |
| Maintenance | 1 year    | Security patches only                  |
| EOL         | Ongoing   | Community support only                 |

**1.0.x Timeline:**
- **Active Phase**: 2026-06-03 to 2027-06-03
- **Maintenance Phase**: 2027-06-03 to 2028-06-03
- **EOL**: After 2028-06-03

## Version Numbering Constraints

To maintain clarity:
- Pre-release versions use format `1.0.0-alpha.1`, `1.0.0-rc.1`
- Development versions not published to PyPI
- Build metadata (if needed) uses `+` notation: `1.0.0+20260603`

## How to Check Version

```python
from mas import __version__
print(__version__)  # "1.0.0"
```

Or via CLI:
```bash
pip show mas | grep Version
# Version: 1.0.0
```

## Migration Guides

When breaking changes occur between major versions:
- A `MIGRATION.md` guide is provided
- Includes upgrade instructions and compatibility notes
- Examples of old vs. new API usage

## Questions?

- Check [CHANGELOG.md](CHANGELOG.md) for version history
- See [CONTRIBUTING.md](CONTRIBUTING.md) for development info
- Open an issue for version-related questions

---

**Effective Date**: 2026-06-03 (Version 1.0.0)
