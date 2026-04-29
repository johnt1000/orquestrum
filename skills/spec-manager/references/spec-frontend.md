## Frontend & Mobile Requirement Patterns

### Assumptions to Document for UI Projects

When writing a SPEC for a product with a frontend or mobile client, document these assumptions before writing requirements:

| Assumption category | Example assumption | Risk if false |
|--------------------|-------------------|--------------|
| Browser support | The system targets Chrome, Firefox, Safari (last 2 versions) and iOS Safari 15+ | CSS/JS features may not work on excluded browsers |
| Performance budget | The initial page load must score ≥ 85 on Lighthouse Performance on a 3G connection | UX degrades; Core Web Vitals penalties in search ranking |
| Accessibility level | The product must meet WCAG 2.1 AA | Legal risk (ADA, EN 301 549); excludes users with disabilities |
| Offline capability | The product requires a stable internet connection — no offline mode | Users on poor connections will see errors, not fallbacks |
| Device range | The product supports screens from 375px (iPhone SE) to 1920px (desktop) | Layouts break on excluded screen sizes |
| Native platform | The mobile app targets iOS 15+ and Android 10+ | Newer APIs unavailable; larger potential user base |
| App store review | Features must comply with Apple App Store and Google Play guidelines | Submission rejected; feature removed post-launch |

### Non-Functional Requirements for UI Projects

Add these to the NFR section of any SPEC that includes a frontend client:

| ID | Priority | Requirement |
|----|----------|------------|
| RNF-UI-01 | M | The system MUST achieve a Lighthouse Performance score ≥ 85 on a simulated 3G connection |
| RNF-UI-02 | M | The system MUST meet WCAG 2.1 Level AA for all user-facing pages and interactive elements |
| RNF-UI-03 | M | The initial JavaScript bundle MUST be ≤ 300KB gzipped |
| RNF-UI-04 | S | LCP MUST be < 2.5s; CLS MUST be < 0.1; INP MUST be < 200ms (Core Web Vitals Good thresholds) |
| RNF-UI-05 | S | The system SHOULD support offline display of the last loaded content via Service Worker caching |
| RNF-MOB-01 | M | The mobile app MUST launch in < 3 seconds on a mid-range device (e.g., iPhone 12, Pixel 5) |
| RNF-MOB-02 | M | The mobile app MUST NOT crash on loss of network connectivity |
| RNF-MOB-03 | S | The mobile app SHOULD support background refresh to pre-load content before user opens the app |

### Success Criteria Patterns for UI

When writing SC-XX criteria for UI features, include observable UI state, not just API state:

**Pattern — Form validation:**
```
Given [user has filled in an invalid email]
When [user submits the login form]
Then [an inline error message "Invalid email format" is shown below the email field within 100ms, without a page reload]
```

**Pattern — Loading state:**
```
Given [user submits valid credentials]
When [API request is in flight]
Then [submit button is disabled and shows a loading spinner]
```

**Pattern — Mobile navigation:**
```
Given [user is on the Profile screen]
When [user taps the Back button or swipes right]
Then [app navigates to the previous screen with the correct transition animation (slide from left on iOS)]
```

**Pattern — Offline behavior:**
```
Given [user has no network connection]
When [user opens the app]
Then [cached content from the last session is displayed with an "Offline" banner — no crash, no blank screen]
```

<!-- inject:start -->
### ✅ Good SPEC Assumption Block — Mobile App

```markdown
## Assumptions

| # | Assumption | Risk if false | Validated? |
|---|-----------|--------------|-----------|
| A1 | Users have devices running iOS 15+ or Android 10+ | Features using newer APIs unavailable; user base reduced | ✅ Yes |
| A2 | The app requires internet for initial load but can display cached content offline | Offline architecture pattern needed from day 1 | ❓ Not validated |
| A3 | Both App Store (Apple) and Play Store (Google) releases are required simultaneously | Android/iOS divergence adds scope | ✅ Yes |
| A4 | The product must comply with WCAG 2.1 AA (required by client contract) | Legal and contractual risk | ✅ Yes |
| A5 | Initial bundle performance budget: Lighthouse ≥ 85 on 3G | Poor UX and SEO penalties if not enforced from architecture phase | ❓ Not validated |
```

### ❌ Anti-Pattern — SPEC for a web app with no UI assumptions

```markdown
## Assumptions

| # | Assumption | Risk if false |
|---|-----------|--------------|
| A1 | Users have a valid email address | Registration fails |
| A2 | Payment provider is available 99.9% of the time | Checkout fails |
```

**Why rejected:** This SPEC is for an e-commerce SPA but documents zero frontend assumptions — no browser support, no performance budget, no accessibility level, no offline requirement. architecture-manager will design a backend-only system. The first sprint will discover that "add to cart" needs to work offline, which is a Tier 2 upgrade mid-flight.
<!-- inject:end -->
