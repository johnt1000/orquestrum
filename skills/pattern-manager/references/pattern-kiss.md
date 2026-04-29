# KISS — Keep It Simple, Stupid

**Layer:** 0 — Engineering Principles

**What it is:** The simplest solution that works is the correct one. Complexity that does not solve a real problem is pre-paid technical debt without justification.

**Violation signal:**
```
// Abstraction for a single use:
class UserEmailValidationStrategyFactory:
  createStrategy(type): IValidationStrategy
    return new EmailValidationStrategy()   // only this one exists

// Simple and sufficient:
function isValidEmail(email): bool
```

**When NOT to apply:** When immediate simplicity creates future complexity. E.g.: hardcoding a value that will change → extraction to config is KISS in the right context.

**Cost of ignoring:** Code that is hard to read, test, and modify. New members take days to understand what could be understood in minutes.

**Related:** YAGNI (do not build what you do not need), Facade (simplify without hiding real complexity)
