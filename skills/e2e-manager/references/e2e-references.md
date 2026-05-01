<!-- inject:start -->
# Formal Reference: End-to-End (E2E) Testing

## 1. What E2E tests validate

E2E tests validate **complete user flows** from the user's perspective — not isolated functions or modules. A passing E2E test proves that all components (UI, API, database, external services) work together as the SPEC intended.

**E2E is NOT a replacement for unit or integration tests.** It complements them by covering the cross-component seam. Use the test pyramid as a guide:

```
       /‾‾‾‾‾‾‾‾‾\
      /  E2E (few) \      ← Slow, brittle, expensive — use for Critical User Paths only
     /‾‾‾‾‾‾‾‾‾‾‾‾‾\
    / Integration    \    ← Medium speed — external deps, API boundaries
   /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
  /   Unit (many)     \   ← Fast, isolated — business logic, edge cases
 /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
```

**Signals that E2E is required (not just recommended):**
- SC-XX involves a user journey spanning ≥2 services or layers
- SC-XX involves authentication, payment, or personal data submission
- SC-XX is on a Critical User Path (onboarding, primary feature delivery)

---

## 2. Scenario Writing Standard

Every E2E scenario follows the **Given / When / Then** pattern, identical to SPEC Success Criteria — this enables direct traceability.

```
Given: [system state + user preconditions before the test]
When:  [user action or system trigger — specific, automatable]
Then:  [observable outcome — measurable, not vague]
```

### Good scenario

```
Given: a registered user with email "test@example.com" exists
When:  the user submits the login form with correct credentials
Then:  the user is redirected to /dashboard
       AND the session cookie is set
       AND the response time is < 2s
```

### Bad scenario

```
When the user logs in, they should see the dashboard.
```
→ Not automatable. No precondition, no measurable assertion.

---

## 3. Scenario Types

| Type | Purpose | Coverage goal |
|------|---------|--------------|
| `happy` | Nominal flow — everything valid | 1 per SC-XX (mandatory) |
| `error` | Invalid input, missing auth, boundary violation | ≥1 per SC-XX (mandatory) |
| `edge` | Boundary values, concurrent requests, timeouts | Recommended for SC-XX on critical paths |
| `regression` | Previously failing scenario now expected to pass | Add when fixing a bug that had an E2E failure |

---

## 4. Environment Preconditions

E2E tests require a real (or realistic) environment. Document these preconditions explicitly:

- **Database state:** seeded fixture data, reset between runs
- **External services:** real sandbox (preferred), mock server (acceptable with justification), or skipped with `Blocked` status
- **Auth state:** test user with known credentials pre-created in seed
- **Network:** target service must be reachable — check before marking `Failed` vs `Blocked`

---

## 5. Failure Classification

When a scenario fails in Regression mode, classify before routing:

| Failure type | Signal | Action |
|-------------|--------|--------|
| `code bug` | Assertion fails — system behavior differs from SPEC | New correction Task (Forge) |
| `environment` | Service unavailable, timeout, seed missing | Flux backlog — not a code failure |
| `spec drift` | System works, but SPEC no longer matches what was built | Lore → SPEC update (or ADR revision) |
| `flaky` | Fails intermittently without code change | Investigate stability; don't mark as Passed until stable |

---

## 6. Coverage Score Calculation

```
coverage_score = (SC-XX with ≥1 Passed scenario) / (total SC-XX in scope) × 100%
```

A SC-XX is considered "covered" only when:
- It has ≥1 happy-path scenario with status `Passed`
- It has ≥1 error-case scenario with status `Passed` or `Skipped` (with justification)

A SC-XX with only `Pending` or `Blocked` scenarios contributes 0 to the score.

---

## 7. Integration with qa-manager

In Regression mode, the E2E-{ref} artifact is the primary evidence for `validation_method: e2e` in qa-manager. The handoff data:

- List of SC-XX with final status (Passed / Failed / Blocked)
- `coverage_score` for the release scope
- Any `Failed` scenarios that block release (Critical User Paths)

qa-manager maps these results to its Test Cases table and sets the QA status accordingly.
<!-- inject:end -->
