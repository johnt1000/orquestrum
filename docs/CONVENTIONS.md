# Shared Conventions — Orquestrum Skills

Reference document for conventions shared across all skills. Each SKILL.md inherits these rules by reference — they are not repeated inline.

---

## Context Fence

Every skill operates under a strict context boundary:

- Operate exclusively on files declared under `Reads`
- DO NOT read files from later pipeline phases not listed in the I/O Contract
- DO NOT infer context from files not explicitly listed above

---

## Invalid Format

Invalid format: absence of any mandatory section blocks the next gate.

---

## I/O Contract

Every skill defines a 5-row I/O contract (checkpoint-manager uses 4 rows, without `Handoff to`):

```
| | Files |
|--|---------|
| **Reads** | ... |
| **Writes** | ... |
| **Depends on** | ... |
| **Must NOT touch** | ... |
| **Handoff to** | ... |
```

---

## Output Schema

The artifact produced by this skill MUST contain the mandatory sections listed in its `## Output Schema` section.

---

## Filename Slug Rule

Shared naming rules for all artifact-producing skills:

- Derive `{slug}` from the artifact title in kebab-case-lowercase
- Max 50 characters for the slug portion, truncated on the last complete word
- Immutable after creation — title or version changes do not rename the file
- Cross-references always use the short form (e.g. `T{ID}`, `E{ID}`, `ADR-XXX`, `spec-vX`) — never the full filename

Skill-specific exceptions (Tier-0 micro-log, architecture v0, review/QA `{ref}` prefix) are documented in each skill's `## Naming Convention` section.

---

## Pre-execution

Every skill (except checkpoint-manager) reads its reference file before executing:

```
Before any action, read: `./references/{name}-references.md`
```

---

## Context Reflection

Every skill defines its own context reflection — which paths to check for consistency before creating artifacts. This is skill-specific and not shared.
