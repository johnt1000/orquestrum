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
