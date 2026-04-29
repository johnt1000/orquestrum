# SOLID — Dependency Inversion (D)

**Layer:** 0 — Engineering Principles

**What it is:** High-level modules must not depend on low-level modules. Both must depend on abstractions. Abstractions must not depend on details.

**Violation signal:**
```
class UserService:
  constructor():
    this.repo = new PostgresUserRepository()  // coupled to PostgreSQL
    this.email = new SendgridEmailClient()     // coupled to Sendgrid
```

**Correct:**
```
class UserService:
  constructor(repo: IUserRepository, email: IEmailClient)  // dependency injection
```

**Cost of ignoring:** Impossible to test without a real database and without Sendgrid. Switching providers requires rewriting the service.

**Related:** Repository, Adapter, any dependency injection
