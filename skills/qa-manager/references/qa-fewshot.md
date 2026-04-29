## Few-Shot Examples

<!-- inject:start -->
### ✅ Good Output — QA document with full SC coverage

```markdown
## Test Results

| SC-ID | Description | Result | Evidence |
|-------|-------------|--------|---------|
| SC-01 | Given valid email/password When POST /register Then 201 + user created | ✅ Pass | `register.integration.spec.ts:12` |
| SC-02 | Given duplicate email When POST /register Then 409 | ✅ Pass | `register.integration.spec.ts:28` |
| SC-03 | Given invalid email format When POST /register Then 422 | ✅ Pass | `register.spec.ts:44` |

**Summary:** 16/16 tests passed. 0 blocked. 0 failed.

## Approval Status

**Status: Passed**
All Must requirements validated. Ready for changelog-manager.
```

### ❌ Anti-Pattern — QA without SC traceability

```markdown
## Testing

Ran the tests. Most things work. There were a couple of issues but they seem minor.
Overall it looks okay to ship.
```

**Why rejected:** No SC-XX IDs referenced. No test evidence. "Most things work" and "couple of issues" are not measurable. Cast cannot generate a release from a QA document with no structured approval — this would be blocked at Gate 4→5.
<!-- inject:end -->

---
