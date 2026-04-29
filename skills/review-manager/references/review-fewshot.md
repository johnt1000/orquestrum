## Few-Shot Examples

<!-- inject:start -->
### ✅ Good Output — Approved Review

```markdown
## Summary

**Status:** Approved
**Artifacts reviewed:** `src/auth/register.ts`, `src/auth/register.spec.ts`, `src/validators/email.ts`
**SPEC conformance:** ✅ All RF-01, RF-02, RF-03 implemented correctly

## Findings

| ID | Severity | File | Line | Description | Status |
|----|----------|------|------|-------------|--------|
| F-01 | Low | `src/auth/register.ts` | 42 | Magic number 100 (max password length) — extract to constant | Resolved |

## Security Checklist

- [x] Input validation present (RF-01, RF-02 confirmed)
- [x] No SQL injection vectors (parameterized queries used)
- [x] No sensitive data in logs
- [x] Rate limiting applied at route level
- [x] LGPD: no PII stored beyond necessary fields

## Approved Artifacts

- `src/auth/register.ts` — commit abc1234
- `src/validators/email.ts` — commit abc1234
```

### ❌ Anti-Pattern — Review without evidence

```markdown
## Summary

Looks good to me. Code is clean and follows the patterns.
Approved.
```

**Why rejected:** No specific findings documented. No security checklist. No artifact list with versions. No SPEC conformance check. QA cannot use this as a handoff — it has no traceability to what was actually reviewed.
<!-- inject:end -->

---
