# YAGNI — You Aren't Gonna Need It

**Layer:** 0 — Engineering Principles

**What it is:** Do not implement functionality until it is needed. Speculative code is technical debt — it has maintenance cost without business value.

**Violation signal:**
```
// Task only asked to create a user. But the dev added:
createUser(data, options?: {
  sendWelcomeEmail?: bool,       // not requested
  createDefaultWorkspace?: bool, // not requested
  assignDefaultRole?: string,    // not requested
})
```

**Correct:** Only what the SPEC/Task requested. If the parameter did not come from a requirement, it does not exist.

**Cost of ignoring:** Code that nobody uses, tests, or understands. Increases attack surface. Increases onboarding time.

**Related:** KISS (do not complicate), task-manager guardrail ("do not mark as Completed with extra unrequested functionality")
