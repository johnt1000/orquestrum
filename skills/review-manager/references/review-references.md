# Review References

## Mandatory Security Checklist

### Secret Exposure
- [ ] No credentials, API keys, or tokens hardcoded in the code
- [ ] Environment variables used for sensitive data (`.env` not committed)
- [ ] Logs do not expose user data or session tokens

### Input Validation
- [ ] All external inputs validated before processing (schema validation, sanitization)
- [ ] SQL query parameters parameterized (no string concatenation)
- [ ] File uploads with type and size validation

### LGPD / Privacy
- [ ] Patient and psychologist data stored with encryption at rest
- [ ] Access to personal data controlled by authentication and authorization
- [ ] Audit logs present in operations that access sensitive data
- [ ] Data deletion mechanism implemented (right to be forgotten)

### OWASP Top 10 (basic checklist)
- [ ] A01 Broken Access Control: protected routes, no privilege escalation
- [ ] A02 Cryptographic Failures: TLS in transit, bcrypt/argon2 hash for passwords
- [ ] A03 Injection: no SQL injection, command injection, or template injection
- [ ] A05 Security Misconfiguration: security HTTP headers present
- [ ] A07 Auth Failures: rate limiting on login endpoints, tokens with expiration

### Quality and Maintainability

**Principles — check each one with the corresponding code smell:**

| Principle | Code smell to look for | Severity |
|-----------|----------------------|-----------|
| **DRY** | Identical or very similar logic in 2+ files | 🟡 Medium |
| **KISS** | Abstraction/class created for a single use in the codebase | 🟢 Minor |
| **YAGNI** | Parameter, method, or class that no SPEC/Task required | 🟡 Medium |
| **SRP** | Function/class that does 2+ distinct things (compound naming: `saveAndSend`) | 🟡 Medium |
| **Open/Closed** | `if/switch` in business logic that grows with each new variant | 🟡 Medium |
| **Dependency Inversion** | `new ConcreteClass()` inside service/controller (direct coupling) | 🟡 Medium |
| **Fail Fast** | Validation after processing, partially modified state on error | 🔴 Critical |
| **SoC** | Business logic in controller, SQL in service, formatting in model | 🟡 Medium |
| **Law of Demeter** | Chained access `a.b.c.d()` through 3+ objects | 🟢 Minor |
| **Composition** | Deep inheritance (3+ levels) for behavior reuse | 🟡 Medium |

**Existing checklists:**
- [ ] Functions with single responsibility (SRP verified above)
- [ ] Explicit error handling (no empty `catch(e) {}`)
- [ ] No dead or commented-out code without justification (`// TODO` without an issue is debt)

## Severity Criteria

| Severity | Criterion | Action |
|-----------|---------|------|
| 🔴 Critical | Active security vulnerability, logic failure that corrupts data | Reject (Rejected) |
| 🟡 Medium | Relevant technical debt, missing validation in non-critical layer | Request changes (Changes Requested) |
| 🟢 Minor | Naming, formatting, refactoring suggestion | Approve with observation |

## Git & Versioning

### Conventional Commits
- [ ] Every commit follows the format `{type}({scope}): {description}`
- [ ] Type is one of the allowed ones: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`
- [ ] Breaking changes marked with `!` and described in the footer with `BREAKING CHANGE:`
- [ ] No commit with a vague message (`update`, `fix stuff`, `wip`, `temp`)
- [ ] Each commit has a single cohesive purpose (no `and` in the title)

### Trunk-Based Development
- [ ] Branch named with pattern `{type}/{T-ID}-{kebab-description}`
- [ ] Branch created from an up-to-date `main`
- [ ] Branch has at most 2 days of life (if more, flag for rebase or task subdivision)
- [ ] No direct commits to `main` (except critical hotfix documented)
- [ ] Incomplete code that merges early uses a feature flag

**Severity of git failures:**

| Violation | Severity |
|---------|-----------|
| Breaking change without `!` and without migration notes in CHANGELOG | 🔴 Critical |
| Commit with vague message or without type | 🟡 Medium |
| Long-lived branch (> 2 days without merge to `main`) | 🟡 Medium |
| Branch does not follow `{type}/{T-ID}-*` naming | 🟢 Minor |

---

## External References

- OWASP Top 10: https://owasp.org/Top10/
- LGPD (Law 13.709/2018): Art. 46 — technical and administrative security measures
- Twelve-Factor App: https://12factor.net/ (III. Config — store config in the environment)

---
