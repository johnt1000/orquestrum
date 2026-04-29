## Frontend & Mobile Task Artifacts

> When the task produces UI components, web pages, or mobile screens, the Artifacts section must include test files, stories, and a11y tests — not just source files.

### Frontend Task — Artifact Checklist

A completed frontend task MUST list:

| Artifact type | Example path | Required? |
|---------------|-------------|-----------|
| Component source | `src/components/LoginForm/LoginForm.tsx` | ✅ Always |
| Component unit test | `src/components/LoginForm/LoginForm.spec.tsx` | ✅ Always |
| Storybook story | `src/components/LoginForm/LoginForm.stories.tsx` | ✅ If shared component |
| E2E test | `e2e/auth/login.e2e.ts` | ✅ If touches a user journey |
| Accessibility test | `src/components/LoginForm/LoginForm.a11y.spec.tsx` | ✅ If interactive element |
| CSS/Styles | `src/components/LoginForm/LoginForm.module.css` | If applicable |
| Types/interfaces | `src/types/auth.types.ts` | If new types added |

### Mobile Task — Artifact Checklist

A completed mobile task MUST list:

| Artifact type | Example path | Required? |
|---------------|-------------|-----------|
| Screen component | `src/screens/OnboardingScreen.tsx` | ✅ Always |
| Unit test | `src/screens/OnboardingScreen.spec.tsx` | ✅ Always |
| E2E test (Detox) | `e2e/onboarding.e2e.ts` | ✅ If user-facing screen |
| Platform-specific code | `src/screens/OnboardingScreen.ios.tsx` | If platform diverges |
| Navigation config | `src/navigation/AppNavigator.tsx` | If new route added |
| Permissions manifest update | `ios/Info.plist`, `android/AndroidManifest.xml` | If new permission |

<!-- inject:start -->
### ✅ Good Output — Frontend Task Artifacts

```markdown
## Artifacts

- `src/components/LoginForm/LoginForm.tsx` — login form component with email/password fields
- `src/components/LoginForm/LoginForm.spec.tsx` — unit tests (8 cases: validation, loading state, error state)
- `src/components/LoginForm/LoginForm.stories.tsx` — Storybook stories (Default, WithError, Loading)
- `src/components/LoginForm/LoginForm.module.css` — scoped styles
- `e2e/auth/login.e2e.ts` — Playwright E2E (3 cases: happy path, invalid credentials, network error)
- `src/components/LoginForm/LoginForm.a11y.spec.tsx` — axe-core accessibility test

## Acceptance Criteria

- [x] Form renders with email and password fields
- [x] Invalid email shows inline error without submitting
- [x] Loading spinner shown during API call
- [x] Error banner shown on 401 response
- [x] All 11 tests pass (8 unit + 3 E2E)
- [x] axe-core: 0 violations
```

### ✅ Good Output — Mobile Task Artifacts

```markdown
## Artifacts

- `src/screens/OnboardingScreen.tsx` — onboarding carousel screen (3 slides)
- `src/screens/OnboardingScreen.spec.tsx` — unit tests (5 cases: slide navigation, skip button, completion)
- `e2e/onboarding.e2e.ts` — Detox E2E (2 cases: complete flow, skip flow)
- `src/navigation/AppNavigator.tsx` — updated to include OnboardingScreen route
- `src/hooks/useOnboardingStatus.ts` — hook to track first-launch state (AsyncStorage)

## Acceptance Criteria

- [x] 3 slides display correctly on iPhone SE (375px) and iPhone 14 Pro (393px)
- [x] Skip button navigates to HomeScreen
- [x] Completing all slides navigates to HomeScreen and sets onboarding flag
- [x] Onboarding not shown on second app launch
- [x] All 7 tests pass (5 unit + 2 E2E)
```

### ❌ Anti-Pattern — Frontend Task with backend-style artifacts

```markdown
## Artifacts

- `src/api/auth.ts` — auth API client
- `src/api/auth.spec.ts` — unit tests for API calls

## Acceptance Criteria

- [x] API returns token on success
- [x] Tests pass
```

**Why rejected:** The task was to build a Login screen but the artifacts only contain API client code. No component file, no E2E test, no Storybook story, no accessibility test. This task would be blocked at the Handoff Checklist — the review-manager cannot review what was never listed.
<!-- inject:end -->
