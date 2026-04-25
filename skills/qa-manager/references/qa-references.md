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

## Frontend & Mobile QA Criteria

> Apply this section when the task under QA produces UI components, web pages, or mobile screens.

### E2E Testing Requirements

| Tool | Use case | Minimum coverage |
|------|----------|-----------------|
| Playwright | Web apps, SPAs, server-rendered pages | All critical user journeys (happy path + top 3 error cases) |
| Cypress | React/Vue/Angular component + integration | All SC-XX that involve user interaction |
| Detox | React Native mobile screens | All screens with form input or navigation |
| XCUITest / Espresso | Native iOS / Native Android | Smoke test for each release build |

**Minimum bar:** at least one E2E test must exist per Success Criterion (SC-XX) that involves a user-facing interaction.

### Visual Regression Testing

| Tool | When to require |
|------|----------------|
| Chromatic (Storybook) | Component library or design system changes |
| Percy | Full-page visual snapshots for marketing or critical flows |
| BackstopJS | Self-hosted visual regression for any project |

**Rule:** any PR that changes a shared UI component MUST include a visual regression baseline update or explicit approval that the visual change is intentional.

### Performance Budget (Core Web Vitals)

| Metric | Target (Good) | Minimum acceptable |
|--------|--------------|-------------------|
| LCP (Largest Contentful Paint) | < 2.5s | < 4.0s |
| FID / INP (Interaction to Next Paint) | < 100ms | < 200ms |
| CLS (Cumulative Layout Shift) | < 0.1 | < 0.25 |
| Bundle size (initial JS) | < 200KB gzipped | < 500KB gzipped |
| Lighthouse Performance score | ≥ 90 | ≥ 75 |

**How to measure:** run `npx lighthouse <url> --output json` or use Vercel/Netlify analytics. Document the score in the QA artifact.

### Accessibility (WCAG 2.1 AA)

Minimum requirements for every UI change:

- [ ] All images have `alt` text (or `alt=""` for decorative)
- [ ] All interactive elements are keyboard-accessible (Tab, Enter, Space, Escape)
- [ ] Color contrast ratio ≥ 4.5:1 for normal text, ≥ 3:1 for large text
- [ ] Focus indicator visible on all focusable elements
- [ ] Form inputs have associated `<label>` elements
- [ ] Error messages are programmatically associated with their fields
- [ ] No content relies on color alone to convey meaning
- [ ] Page/screen has a descriptive `<title>` or screen reader announcement

**Tools:** `axe-core` (automated), `WAVE` browser extension (manual), `@axe-core/playwright` (in E2E suite).

### Cross-Browser / Cross-Device Matrix

| Browser / Platform | Minimum support |
|-------------------|----------------|
| Chrome (desktop) | Last 2 major versions |
| Firefox (desktop) | Last 2 major versions |
| Safari (macOS) | Last 2 major versions |
| Chrome (Android) | Last 2 major versions |
| Safari (iOS) | iOS 15+ |
| Edge (Windows) | Last 2 major versions |

**Mobile breakpoints to test:** 375px (iPhone SE), 390px (iPhone 14), 768px (iPad), 1024px (desktop min).

### Mobile-Specific Checks (React Native / Flutter / Native)

- [ ] App runs without crash on minimum supported OS version (iOS 15 / Android 10)
- [ ] All screens tested on physical device or emulator (not just simulator)
- [ ] Deep links / universal links tested
- [ ] Push notification permission flow tested
- [ ] Offline state handled gracefully (no uncaught network errors)
- [ ] Back button behavior correct on Android
- [ ] Keyboard does not obscure input fields

### QA Approval Gate — Frontend/Mobile

Before setting QA status to `Passed`, confirm:

- [ ] All SC-XX have at least one E2E test passing
- [ ] Lighthouse score meets the performance budget targets above
- [ ] Accessibility audit run (automated + manual spot check)
- [ ] Tested on at least 2 browsers or 2 devices from the matrix
- [ ] Visual regression baseline approved (if shared component changed)
- [ ] No open critical accessibility violations (axe-core severity: critical or serious)

<!-- inject:start -->
### ✅ Good QA Output — Frontend Feature

```markdown
## Test Results

| SC-ID | Description | Result | Evidence |
|-------|-------------|--------|---------|
| SC-01 | Given unauthenticated user When visits /dashboard Then redirected to /login | ✅ Pass | `auth.e2e.ts:14` (Playwright) |
| SC-02 | Given login form When submits invalid email Then inline error shown | ✅ Pass | `login.e2e.ts:38` (Playwright) |
| SC-03 | Given login form When submits valid credentials Then navigates to /dashboard | ✅ Pass | `login.e2e.ts:55` (Playwright) |

## Performance

Lighthouse (production build, throttled 3G):
- LCP: 1.8s ✅
- CLS: 0.04 ✅
- INP: 87ms ✅
- Performance score: 94 ✅

## Accessibility

axe-core: 0 critical, 0 serious violations
Manual check: keyboard navigation verified on login form ✅

## Cross-browser

Tested on: Chrome 124, Firefox 125, Safari 17 (macOS), Safari iOS 17 ✅

**Status: Passed** — ready for changelog-manager.
```

### ❌ Anti-Pattern — API-only QA for a UI feature

```markdown
## Test Results

All 16 unit tests pass. POST /login returns 200. Done.
```

**Why rejected:** The task produced a login form (UI). QA validated only the backend endpoint — no E2E tests, no accessibility check, no cross-browser verification. The SC criteria for the UI flow were not tested. This would be blocked at Gate 4→5.
<!-- inject:end -->
