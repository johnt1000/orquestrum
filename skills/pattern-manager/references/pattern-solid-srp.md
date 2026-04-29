# SOLID — Single Responsibility (S)

**Layer:** 0 — Engineering Principles

**What it is:** Each module/class/function must have **a single reason to change**. If two different stakeholders could request changes to the same component, it does two things.

**Violation signal:**
```
class UserController:
  createUser(req)         // business logic (domain)
  hashPassword(pwd)       // infrastructure (security)
  sendWelcomeEmail(user)  // side effect (notification)
  validateEmail(email)    // domain (validation)
```

**Correct:** `UserController` only receives the request and delegates. `PasswordHasher`, `EmailNotifier`, `UserValidator` are separate classes.

**Related:** SoC (separated concerns), Facade (aggregate without mixing)
