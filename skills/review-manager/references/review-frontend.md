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
