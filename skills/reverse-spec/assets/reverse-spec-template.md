---
id: spec-v0-extracted
project: "{PROJECT_NAME}"
extracted_at: YYYY-MM-DD
source_architecture: "docs/01-design/architecture/ARCHITECTURE-v0-as-is.md"
status: Draft  # Always Draft — human validation required before Active
confidence_legend: "🟢 High (explicit/tested) | 🟡 Medium (inferred) | 🔴 Low (speculation)"
---

# Extracted Spec v0 — {PROJECT_NAME}

> **Status: Draft** — This document was generated automatically by code analysis.
> Documented current behavior ≠ confirmed correct requirement.
> Each item marked with `❓ Confirm:` requires human validation before promoting to `Active`.

---

## System Summary

**What the system does today (inferred from code):**

{Description in 2–4 sentences of the system's purpose based exclusively on what the code does — do not invent intention}

**Identified scope:**
- {functional area 1}
- {functional area 2}

**Out of scope (not found in code):**
- {functionality that might be expected but does not exist}

---

## Extracted Functional Requirements

> Each requirement comes from concrete evidence in the code. The file:line reference is mandatory.

### RF-01 — {Requirement Name}

**Confidence:** 🟢 High | 🟡 Medium | 🔴 Low

**Current behavior:**
{Describe exactly what the code does — use requirement language (the system must...)}

**Evidence in code:**
- `{file:line}` — {what this line does}
- `{file:line}` — {additional context}

**Input:**
- {parameter}: {type} — {required/optional}

**Output / Side Effect:**
- {response body / emitted event / created record / etc}

**Implicit business rules:**
- {validation found in code}
- {hardcoded limit: e.g. maximum 100 items}

**Tests covering this behavior:**
- `{test file:line}` — `{test name}`
- `[No tests identified]`

❓ **Confirm:** {specific question to the user — e.g.: "Is this limit of 100 items intentional or provisional?"}

---

### RF-02 — {Requirement Name}

_(repeat the block above for each entry point / behavior identified)_

---

## Extracted Non-Functional Requirements

### RNF-01 — Performance

**Confidence:** 🟢 | 🟡 | 🔴

| Configuration found | Value | File | Interpretation |
|---------------------|-------|------|---------------|
| Request timeout | {value} | `{file}` | Response requirement in < {N}ms |
| Connection pool | {value} | `{file}` | Supports up to {N} simultaneous connections |
| Cache TTL | {value} | `{file}` | Data valid for {N} seconds |

> If not identified: `[Not identified in code]`

---

### RNF-02 — Security

**Confidence:** 🟢 | 🟡 | 🔴

| Mechanism | Implementation found | File | Scope |
|-----------|---------------------|------|-------|
| Authentication | {JWT/Session/OAuth/etc} | `{file}` | {which routes it protects} |
| Authorization | {RBAC/ACL/etc} | `{file}` | {granularity} |
| Rate limiting | {middleware/lib} | `{file}` | {limit: N req/min} |
| HTTPS | {forced/optional} | `{file}` | {production/all} |
| Input sanitization | {library} | `{file}` | {which fields} |

> If not identified: `[Not identified in code]`

❓ **Confirm:** {question about ambiguous security decision}

---

### RNF-03 — Resilience

**Confidence:** 🟢 | 🟡 | 🔴

| Mechanism | Configuration | File |
|-----------|--------------|------|
| Retry policy | {N attempts, delay} | `{file}` |
| Circuit breaker | {threshold} | `{file}` |
| Health check endpoint | `{/path}` | `{file}` |
| Graceful shutdown | {Yes/No} | `{file}` |

> If not identified: `[Not identified in code]`

---

### RNF-04 — Observability

**Confidence:** 🟢 | 🟡 | 🔴

| Type | Implementation | File |
|------|--------------|------|
| Logging | {lib + level} | `{file}` |
| Metrics | {prometheus/datadog/etc} | `{file}` |
| Tracing | {opentelemetry/etc} | `{file}` |
| Error tracking | {sentry/bugsnag/etc} | `{file}` |

> If not identified: `[Not identified in code]`

---

## Implicit Data Model

> Extracted from models, schemas, migrations or ORM definitions.

### Entity: {Name}

| Field | Type | Validations found | Required |
|-------|------|-----------------|---------|
| `{field}` | {type} | {presence, format, etc} | Yes/No |

**Identified relationships:**
- {Name} belongs to {OtherEntity} via `{fk_field}`
- {Name} has many {OtherEntity}

❓ **Confirm:** {question about ambiguous relationship or validation}

---

## Suspicious Behaviors

> Behaviors found in the code that may be historical bugs or intentional decisions.
> They are NOT omitted — the user decides if they become requirements or correction tasks.

### ⚠️ Suspicious behavior BS-01

**Location:** `{file:line}`

**Observed behavior:** {what the code does}

**Why it is suspicious:** {inconsistency, unhandled edge case, strange hardcoded value, etc}

**Possible interpretations:**
- a) It is a bug — should do {X}
- b) It is intentional — {possible justification}

❓ **Confirm:** "Is this behavior in `{file}` intentional or a historical bug?"

---

## Areas Without Spec Coverage

> Functionality that probably should exist but was not found in the code.

| Area | Reason for suspicion | Recommendation |
|------|---------------------|---------------|
| {e.g.: soft delete} | {model has `deleted_at` but no restore method} | ❓ Confirm need |
| {e.g.: pagination} | {endpoint lists all records without limit} | ❓ Confirm if requirement |

---

## Documentation Gaps

> Sections of this spec that could not be filled due to lack of evidence in the code.

- `[Not identified in code]` — {area}: {reason why it was not possible to infer}

---

## References

| Type | File |
|------|------|
| As-is architecture | `docs/01-design/architecture/ARCHITECTURE-v0-as-is.md` |
| Source code analyzed | `{root directory}` |
| Tests analyzed | `{test directory}` |
| Previous documentation (if existed) | `{file or "did not exist"}` |

---

## Validation Pending

> Checklist for the user before promoting to `Active`:

- [ ] RF-01: {confirmation question}
- [ ] RF-02: {confirmation question}
- [ ] BS-01: bug or intention?
- [ ] {remaining items with ❓ Confirm}

**Instruction:** After all confirmations, update the status from `Draft` to `Active` and remove or answer each `❓ Confirm`.
