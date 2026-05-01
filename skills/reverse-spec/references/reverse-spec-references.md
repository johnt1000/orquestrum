<!-- inject:start -->
# References — reverse-spec

Read this file before performing any spec extraction. It defines the principles, techniques, and checklist that guide the reverse-spec.

---

## 1. Core Principle: Forensic Analyst, not Architect

The reverse-spec acts as a **requirements forensic analyst**: examines evidence in the code to infer the original intent — without inventing, without proposing, without improving. The analogy is an expert who reconstructs what happened from physical evidence.

**Fundamental distinction:**
- "The system does X" → document as current behavior
- "The system should do X" → does NOT belong in this document
- "The system seems to want to do X but does Y" → document as `⚠️ Suspicious behavior`

---

## 2. Source Trust Hierarchy

Not all evidence carries the same weight. Use this hierarchy when assigning confidence (`🟢 / 🟡 / 🔴`):

### High Confidence Sources (🟢 High)
1. **Automated tests** — especially integration tests and e2e. If a test asserts the system does X, X is a real requirement.
2. **Explicit validations** — fields with `required: true`, `@NotNull`, `validates :field, presence: true`
3. **Documented API contracts** — OpenAPI/Swagger in `openapi.yaml` or Postman collections
4. **Migrations with comments** — well-named migrations reveal intent

### Medium Confidence Sources (🟡 Medium)
1. **Business code without tests** — controllers, services with clear logic but untested
2. **Variable and function names** — `calculateDiscountForPremiumUsers` reveals an implicit requirement
3. **Configurations in `.env.example`** — lists variables the system needs, even without code

### Low Confidence Sources (🔴 Low)
1. **Code comments** — may be outdated; always compare with the actual code
2. **README and old docs** — may describe what was planned, not what exists
3. **Dead code** — functions never called may be a removed or unimplemented feature

**Golden rule:** if you derived a requirement from a comment, compare with the actual code before documenting. Comments lie; code does not.

---

## 3. Reading Tests as Specification

Tests are the richest form of evidence. For each test, extract:

### From a unit test:
```javascript
// Node.js example
it('should reject registration with duplicate email', async () => {
  await createUser({ email: 'test@example.com' })
  const result = await register({ email: 'test@example.com' })
  expect(result.status).toBe(409)
  expect(result.body.error).toBe('EMAIL_ALREADY_EXISTS')
})
```
→ Extracts: FR about email uniqueness, error code 409, error message `EMAIL_ALREADY_EXISTS`

### From fixtures/factories:
```javascript
// test factory
const userFactory = {
  email: 'user@test.com',
  role: 'standard',  // → roles exist: 'standard' + ?
  createdAt: new Date(),
  isActive: true  // → boolean status field
}
```
→ Extracts: data model with fields `role`, `isActive`, possible RBAC system

### From tested edge cases:
```python
@pytest.mark.parametrize("amount", [-1, 0, 10001])
def test_invalid_transfer_amount(amount):
    ...
```
→ Extracts: business rule — transfer values must be between 1 and 10000

---

## 4. Extracting Non-Functional Requirements

### Performance — where to find:
```javascript
// timeouts
axios.create({ timeout: 5000 })  // → requirement: API responds in < 5s

// connection pool
pool: { max: 10 }  // → supports 10 simultaneous connections

// cache
cache.set(key, value, 3600)  // → 1h TTL for cached data
```

### Security — where to find:
```javascript
// rate limiting
rateLimit({ windowMs: 15 * 60 * 1000, max: 100 })  // → 100 req/15min

// JWT
jwt.verify(token, process.env.JWT_SECRET, { expiresIn: '1h' })  // → token expires in 1h

// RBAC
if (user.role !== 'admin') throw new ForbiddenError()  // → only admin can X
```

### Resilience — where to find:
```javascript
// retry
retry({ times: 3, interval: 1000 })  // → automatic retry with 3 attempts

// circuit breaker
opossum.fallback(() => defaultValue)  // → fallback defined
```

---

## 5. Confidence Classification — Exact Criteria

| Situation | Confidence |
|----------|-----------|
| Explicit behavior in e2e or integration test | 🟢 High |
| Explicit validation with error message | 🟢 High |
| Clear business code + unit test | 🟢 High |
| Clear business code without test | 🟡 Medium |
| Inference from function/variable name | 🟡 Medium |
| Configuration in `.env.example` | 🟡 Medium |
| Derived only from comment (without code verification) | 🔴 Low |
| README or old doc without code validation | 🔴 Low |
| Dead code or unreachable branch | 🔴 Low |

---
<!-- inject:end -->

## 6. Suspicious Behavior Signals

Record as `⚠️ Suspicious behavior` when you find:

| Signal | Type of suspicion |
|-------|----------------|
| `// TODO: fix this` or `// HACK:` | Known debt |
| Missing validation on critical field (e.g.: password without min-length) | Possible security bug |
| Hardcoded value that looks like a business variable | `MAX_ITEMS = 100` — intentional? |
| Silenced exception with `catch(e) {}` | Masked failure |
| Duplicated logic with different results | Inconsistency — which is correct? |
| Nullable column that should be required by business logic | Overly permissive schema |
| Admin permission given to all users in non-prod environment | Debug backdoor? |
| Personal/sensitive data logged in plaintext | Possible LGPD violation |

**Mandatory format:**
```markdown
⚠️ Suspicious behavior BS-XX
Location: `file:line`
Behavior: {what it does}
Why suspicious: {reason}
❓ Confirm: "specific question to the user"
```

---

## 7. Comparison with Existing Documentation

If `docs/` already exists in the project, compare each section of the existing spec with the actual code:

| Situation | Action |
|----------|------|
| Spec says "system does X", code confirms | Keep with 🟢 confidence |
| Spec says "system does X", code does Y | Flag: `⚠️ Doc/code divergence` |
| Spec mentions feature, code does not have it | Flag: `⚠️ Feature documented but not implemented` |
| Code does X, spec does not mention it | Document as new inferred requirement |

**Divergence format:**
```markdown
⚠️ Doc/code divergence: {feature}
Doc says: {what the doc claims}
Code does: {what the code actually does}
❓ Confirm: "Is the doc wrong (update it) or is the code wrong (bug to fix)?"
```

---

## 8. Pre-Delivery Checklist

Before saving `spec-v0-extracted.md`, verify:

- [ ] Document status is `Draft` (never `Active` before human validation)
- [ ] Each FR has a file:line reference
- [ ] Each FR has a confidence level (🟢/🟡/🔴)
- [ ] All tests were read before starting the extraction
- [ ] Suspicious behaviors listed (or explicitly "none")
- [ ] NFR section filled in (or "not identified" explicitly)
- [ ] "Validation Pending" section lists all `❓ Confirm` from the document
- [ ] No requirement invented without evidence in the code
- [ ] Code comments were verified against the code before using as evidence
- [ ] Personal/sensitive data was identified and flagged if logged insecurely

---

## 9. LGPD — Special Attention

If the system processes personal or sensitive data, mandatorily record:

| LGPD Verification | Found? | File |
|-----------------|-------------|---------|
| Personal data identified (name, email, CPF) | Yes/No | `{file}` |
| Sensitive data identified (health, biometrics, etc.) | Yes/No | `{file}` |
| Consent mechanism | Yes/No | `{file}` |
| Logs with personal data in plaintext | Yes/No | `{file}` |
| Deletion/portability endpoint | Yes/No | `{file}` |
| Encryption of sensitive data at rest | Yes/No | `{file}` |

Any `Yes` in the negative items (plaintext logs, no encryption) must become a `⚠️ Suspicious behavior` with `❓ Confirm`.

---

## 10. Do Not Extract — Prohibition List

Never document as a requirement:
- What the README says the system will do (future)
- What a comment says the code does (if the code says otherwise)
- What you think the system should do
- Functionality from dead code (never called)
- Development-environment-only configurations
