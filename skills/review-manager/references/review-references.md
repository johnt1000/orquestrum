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

## Frontend Safety Checklist

> Apply this section when reviewing code that produces UI components, web pages, or mobile screens. Run in addition to the standard security and quality checks.

### XSS & Client-Side Security

- [ ] No `dangerouslySetInnerHTML` (React) or `v-html` (Vue) without explicit sanitization via DOMPurify or equivalent
- [ ] User-controlled data is never inserted into `eval()`, `Function()`, `setTimeout(string)`, or `innerHTML`
- [ ] Content Security Policy (CSP) headers configured — no `unsafe-inline` or `unsafe-eval` in production
- [ ] External links use `rel="noopener noreferrer"`
- [ ] No sensitive tokens (JWT, API keys) stored in `localStorage` — use `httpOnly` cookies or memory
- [ ] `postMessage` handlers validate `event.origin` before processing
- [ ] Third-party scripts loaded from CDN are pinned with Subresource Integrity (SRI) hashes

### Dependency & Bundle Size

- [ ] No new dependency added > 50KB gzipped without an ADR justifying it
- [ ] `npm audit` (or equivalent) shows no high/critical vulnerabilities
- [ ] Tree-shaking verified: no full library imported when only a utility is needed (e.g., `import _ from 'lodash'` → `import debounce from 'lodash/debounce'`)
- [ ] Dynamic imports used for routes/features not needed on initial load
- [ ] No duplicate packages in bundle (check with `webpack-bundle-analyzer` or equivalent)

### Accessibility (WCAG 2.1 AA)

- [ ] All `<img>` elements have `alt` attribute (empty string `""` if decorative)
- [ ] All form inputs have associated `<label>` (explicit `for`/`id` or wrapping label)
- [ ] All interactive elements (buttons, links, inputs) reachable by keyboard (Tab order logical)
- [ ] Focus is managed correctly after modals open/close and after route navigation
- [ ] Color contrast ≥ 4.5:1 for body text, ≥ 3:1 for large text (≥ 18pt or 14pt bold)
- [ ] No information conveyed by color alone (icons + text or patterns used)
- [ ] ARIA attributes used correctly — no invalid role/aria-* combinations
- [ ] Animations respect `prefers-reduced-motion` media query

### Core Web Vitals & Performance

- [ ] No synchronous layout-blocking scripts in `<head>` without `defer` or `async`
- [ ] Images have explicit `width` and `height` to prevent layout shift (CLS)
- [ ] Critical CSS inlined or loaded non-blocking; non-critical CSS deferred
- [ ] No font rendering causes FOUT/FOIT without `font-display: swap`
- [ ] Long-running operations (> 50ms) moved off the main thread (Web Workers or async)
- [ ] `React.memo` / `useMemo` / `useCallback` used where referential equality matters (not everywhere)

### Mobile-Specific (React Native / Flutter / Native)

- [ ] No hardcoded pixel values — use responsive units or platform-aware sizing
- [ ] Touch targets ≥ 44×44pt (Apple HIG) / 48×48dp (Material Design)
- [ ] No memory leaks from uncleared timers, subscriptions, or event listeners on unmount
- [ ] Network errors handled explicitly — no unhandled promise rejections that crash the app
- [ ] Deep link handling tested — invalid URLs fail gracefully
- [ ] App does not request permissions not declared in `Info.plist` / `AndroidManifest.xml`

<!-- inject:start -->
### ✅ Good Review — Frontend Component

```markdown
## Summary

**Status:** Approved
**Artifacts reviewed:** `src/components/LoginForm/LoginForm.tsx`, `LoginForm.spec.tsx`, `LoginForm.stories.tsx`
**SPEC conformance:** ✅ RF-02 (inline validation), RF-03 (loading state) implemented correctly

## Findings

| ID | Severity | File | Line | Description | Status |
|----|----------|------|------|-------------|--------|
| F-01 | Medium | `LoginForm.tsx` | 87 | Missing `aria-describedby` linking error message to input | Resolved |
| F-02 | Low | `LoginForm.tsx` | 102 | Submit button lacks explicit `type="submit"` | Resolved |

## Frontend Safety Checklist

- [x] No dangerouslySetInnerHTML usage
- [x] No new dependencies added
- [x] All inputs have associated labels
- [x] Keyboard navigation tested — Tab order correct
- [x] Color contrast verified (4.8:1 for label text)
- [x] Focus returns to trigger after modal close

## Approved Artifacts

- `src/components/LoginForm/LoginForm.tsx` — commit def5678
- `src/components/LoginForm/LoginForm.spec.tsx` — commit def5678
```

### ❌ Anti-Pattern — Review that ignores frontend concerns

```markdown
## Summary

Code looks clean. Logic is correct. No SQL injection. Approved.
```

**Why rejected:** Reviewed a form component using only backend security criteria. No accessibility check, no XSS audit for input handling, no bundle size impact, no ARIA validation. A form component approved this way could be keyboard-inaccessible to 15% of users and still pass the gate.
<!-- inject:end -->
