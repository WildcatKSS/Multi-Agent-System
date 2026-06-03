# Security Policy

## Supported Versions

| Version | Supported          | End of Support |
|---------|-------------------|-----------------|
| 1.0.x   | ✅ Yes            | 2027-06-03     |
| < 1.0.0 | ❌ No             | N/A            |

Security updates for version 1.0.x will be released as 1.0.z patch versions and are available at no additional cost.

## Reporting a Vulnerability

**Do not open public issues for security vulnerabilities.** Instead, please follow this process:

### Step 1: Report Responsibly
Use GitHub's private vulnerability disclosure: https://github.com/WildcatKSS/Multi-Agent-System/security/advisories

Include:
- Description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact
- Suggested fix (if you have one)

### Step 2: Acknowledgment
You will receive an acknowledgment within **48 hours** confirming receipt and next steps.

### Step 3: Responsible Disclosure
- We will investigate and develop a fix
- You will be credited as the reporter (unless you prefer anonymity)
- A security advisory will be published when a patch is released

### Step 4: Publication
Security advisories are published via:
- GitHub Security Advisories
- Release notes with [SECURITY] tag
- Project security page

## Security Practices

### Code Review
All contributions are reviewed for:
- Input validation and sanitization
- Secure error handling
- Cryptographic correctness
- No hardcoded secrets
- Safe dependency usage

### Testing
- 450+ comprehensive tests including security-focused tests
- Automated testing on all pull requests
- Manual security review of critical paths

### Dependencies
The 1.0.0 release has **zero external dependencies** (optional Redis for advanced use cases).

### Python Version
Supported on Python 3.12+ with security updates.

## Security Features

### Input Validation
- All configuration values are validated at initialization
- Guardrails enforce runtime limits (cost, TTL, retries, depth)
- No deserialization of untrusted data

### Observability
- Structured JSON logging for audit trails
- Correlation IDs for end-to-end tracing
- Metrics for monitoring and alerting

### Memory Safety
- Type hints throughout codebase
- No unsafe operations or eval()
- Safe memory management via Python's garbage collection

## Threat Model

The Multi-Agent System is designed with the following assumptions:

**Trusted Inputs:**
- Task definitions and plans come from trusted sources
- Tool registrations are controlled by system administrators
- Configuration is set by operators or code

**Defense Mechanisms:**
- Guardrails prevent unbounded resource usage
- Structured logging enables forensic analysis
- Separation of concerns limits blast radius

## Best Practices for Users

1. **Configuration Security**
   - Do not expose guardrails configuration in logs
   - Store sensitive credentials outside the framework

2. **Monitoring**
   - Monitor execution metrics and logs
   - Set up alerts for guardrail violations

3. **Updates**
   - Keep Python 3.12+ updated
   - Subscribe to security advisories
   - Apply 1.0.x patches promptly

4. **Deployment**
   - Run in minimal containers
   - Restrict network access
   - Use environment variables for configuration

## Known Limitations

- **Single-worker runtime**: Not designed for distributed deployments (Milestone E)
- **No built-in rate limiting**: Must be implemented at application layer
- **No cryptographic operations**: Not a crypto library; use industry-standard crypto libraries

## Incident Response

If you discover a security incident:
1. **Immediate**: Contact maintainers with details
2. **Assessment**: We will evaluate severity
3. **Fix**: Patch will be developed
4. **Release**: Security update released ASAP
5. **Disclosure**: Advisory published with details and workarounds

---

For questions about security, see [CONTRIBUTING.md](CONTRIBUTING.md) or contact maintainers.

**Last Updated**: 2026-06-03
