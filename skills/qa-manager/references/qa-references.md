# Formal Reference: Quality Assurance (QA)

## 1. What to validate

### Functional
Validate each success criterion listed in the SPEC. For each one, ask:
- Is the behavior described in the SPEC what happens in the implementation?
- Did the n8n webhook respond with JSON containing the correct fields?
- Does the endpoint return the expected HTTP status for each scenario (200, 400, 404, 500)?

### Security
- Are patient/psychologist data persisted with encryption?
- Was LGPD respected (no logs of personal data in plain text)?
- Do tokens and credentials not appear in responses or logs?

### Infrastructure
- Does the container in Proxmox remain stable after implementation?
- Is memory and CPU within the limits defined in the SPEC (Constraints)?

---

## 2. Test Case Writing Standard

Every test case must follow the **Given / When / Then** pattern:

```
Given: [initial context — system state before the action]
When: [action executed — user input or system call]
Then: [expected result — measurable and verifiable output]
```

### Filled examples

**Good:**
```
Given: an authenticated psychologist accesses /sessions
When: sends POST with { patient_id: 1, date: "2026-04-25" }
Then: receives 201 Created with { session_id: <uuid>, status: "scheduled" }
```

**Bad:**
```
When creating a session, it should work correctly.
```
→ Not testable. What does "work correctly" mean?

---

## 3. Result Severity Classification

| Status | Criterion | Next action |
|--------|---------|-------------|
| ✅ Passed | All SPEC success criteria validated | Suggestion to merge/deploy |
| ⚠️ Partial | Functional feature, minor bugs or non-blocking technical debt | Improvement task (priority Low/Medium) |
| ❌ Failed | Blocks use of the feature or success criterion not met | Mandatory correction task (priority High) |

---

## 4. Minimum Expected Coverage

A QA must not be closed as `Passed` without covering at least:

- [ ] Complete main flow (happy path)
- [ ] At least 1 expected error scenario (invalid input, resource not found)
- [ ] Basic security check (invalid token returns 401, sensitive data not exposed)
- [ ] All success criteria listed in the `Success Criteria` section of the SPEC

---

## 5. Test Coverage

QA in Tier 1 and Tier 2 validates **whether tests prove the system works**, not just whether the system works manually. Automated tests are the quality artifact — not manual execution.

### Minimum coverage criteria per Tier

| Criterion | Tier 0 | Tier 1 | Tier 2 |
|---------|:------:|:------:|:------:|
| Tests exist in Task artifacts | — | ✅ | ✅ |
| Each SC-XX has at least 1 test case | — | ✅ | ✅ |
| Happy path covered by test | — | ✅ | ✅ |
| At least 1 error scenario per SC-XX | — | ✅ | ✅ |
| Unit tests for business logic | — | Recommended | ✅ |
| Red/Green/Refactor cycle documented in log | — | — | ✅ |
| No unjustified `skip`/`xit`/`xtest` | — | ✅ | ✅ |

### What to check in each test file

1. **Exists** — test file is listed in the Task `Artifacts`
2. **Passes** — zero failures when executed
3. **Covers SC-XX** — the test name or comment references the acceptance criterion
4. **Is readable** — Given/When/Then is clear in the test body
5. **Is not fragile** — does not break due to string or formatting change unless it is a behavior change

### How to map SC-XX → verification in QA

```
SPEC SC-02:
  Given authenticated user
  When DELETE /users/:id with nonexistent id
  Then returns 404 with body { error: "User not found" }

QA verifies:
  ✅ File: src/users/users.controller.spec.ts (or equivalent)
  ✅ Test: "DELETE /users/:id with nonexistent id returns 404"
  ✅ Assertion: expect(res.status).toBe(404)
  ✅ Assertion: expect(res.body.error).toBe('User not found')
  ✅ Result: PASSED
```

---

## 6. Integration with the Pipeline

QA never ends in itself. Always generate an output trigger:

- **Passed** → record in the `Next Actions` section: "Ready for merge/deploy"
- **Partial** → create improvement Task + link in the `Issues Found` section
- **Failed** → create correction Task with High priority + trigger `learning-manager` if the cause is unexpected

---

## 6. Example of Filled Test Case in the Template

```markdown
### ✅ Passed

- **TC-01:** Valid session creation
  - Given: authenticated psychologist
  - When: POST /sessions with valid payload
  - Then: 201 + session_id in body

### ❌ Failed

- **TC-04:** Creation without authentication
  - Given: unauthenticated user
  - When: POST /sessions
  - Then expected: 401 Unauthorized
  - Actual result: 500 Internal Server Error ← BUG
```

---
