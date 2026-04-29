# DRY — Don't Repeat Yourself

**Layer:** 0 — Engineering Principles

**What it is:** Every piece of knowledge must have a single, unambiguous, authoritative representation in the system. Duplication of logic, not data.

**Violation signal:**
```
// Same email validation rule in 3 places:
UserService:  if email.includes('@') ...
AuthService:  if email.includes('@') ...
ImportService: if email.includes('@') ...
```

**Correct:**
```
EmailValidator.isValid(email)  // a single place, called by all 3
```

**When NOT to apply:** DRY applies to *business logic*, not structural code. Two functions that do `return id` do not violate DRY — they are coincidences, not knowledge duplications.

**Cost of ignoring:** A business rule change requires N edits in N places. One will be forgotten.

**Related:** SoC (separate to avoid duplication), Repository (centralize data access)
