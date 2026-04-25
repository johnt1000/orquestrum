---
id: PATTERNS
project: "{PROJECT_NAME}"
last_updated: YYYY-MM-DD
status: Active  # Active | Draft
---

# Pattern Catalog — {PROJECT_NAME}

> This catalog defines which design patterns are approved for use in this project.
> Every pattern adoption must be recorded in the "Adoptions" section and associated with an ADR.
> Prohibited patterns are as important as adopted ones — both reduce ad-hoc decisions.

---

## Adopted Patterns

| Pattern | Layer | Components / Modules | ADR | Adopted on |
|---------|-------|---------------------|-----|-----------|
| {Repository} | Structural | `{services/*, repositories/*}` | [ADR-00X](../../adr/ADR-00X.md) | YYYY-MM-DD |
| {Circuit Breaker} | Integration | `{services/external/*}` | [ADR-00X](../../adr/ADR-00X.md) | YYYY-MM-DD |

> Add a row for each adoption recorded via `pattern-adoption-template.md`

---

## Patterns Under Evaluation

| Pattern | Layer | Reason for Evaluation | Decision expected by |
|---------|-------|----------------------|--------------------|
| {CQRS} | Architectural | {Growing read volume — evaluate separation} | {YYYY-MM-DD or "next sprint"} |

---

## Prohibited Patterns

| Pattern | Reason for Prohibition | Adopted Alternative |
|---------|----------------------|---------------------|
| {Singleton} | Violates testability and creates implicit global state | Dependency Injection |
| {God Object} | Violates SRP — hinders maintenance and testing | Decomposition into specialized services |

---

## Recorded Adoptions

> Each adoption has its detailed document. This section is an index.

| # | Pattern | Component | Document |
|---|---------|----------|---------|
| PA-001 | {Repository} | `{UserRepository}` | [PA-001](./PA-001-repository-users.md) |
| PA-002 | {Circuit Breaker} | `{PaymentService}` | [PA-002](./PA-002-circuit-breaker-payments.md) |

---

## References

| Type | File |
|------|------|
| Pattern catalog | `./references/pattern-references.md` |
| Project ADRs | `docs/00-discovery/adr/` |
| Architecture | `docs/01-design/architecture/ARCHITECTURE-vX.md` |
