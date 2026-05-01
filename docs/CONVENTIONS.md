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

---

## Checkpoint-Manager Ownership

`checkpoint-manager` is a cross-cutting skill. Its ownership rules:

- **Flux** — reads CHECKPOINT.md at the start of every maintenance cycle to detect drift and stale artifacts
- **Cast** — writes CHECKPOINT.md after each release (archive-manager finalizes it)
- **Cipher** — writes SEC findings to CHECKPOINT.md when a gate is blocked
- All other orchestrators — may read CHECKPOINT.md for context; must not write it except via checkpoint-manager

---

## Artifact Confidence Fields

All artifact-producing skills should include confidence metadata where applicable. These fields are optional at Echo level, recommended at Pulse, and required at Chronicle.

### Requirements (spec-manager)

Each requirement row in the `## Requirements` table may carry:

```
| ID | Priority | Requirement | confidence | source |
|----|----------|------------|------------|--------|
| RF-01 | M | ... | high | interview |
```

`confidence`: `high` / `medium` / `low`
`source`: `interview` / `code` / `inference` / `standard`

### Architectural Decisions (adr-manager)

ADR frontmatter may include:

```yaml
confidence_rationale: "Decision backed by load test results from 2026-04-10"
```

### Artifact Freshness (all artifact-producing skills)

Artifacts may include the following metadata block in their frontmatter:

```yaml
last_validated: YYYY-MM-DD
validated_by: "{agent or human}"
drift_risk: low # low | medium | high
```

`drift_risk` escalates to `high` when: (a) artifact is >30 days without revalidation, or (b) referenced files were modified since `last_validated`. Flux signals to Helm when drift_risk is `high` at the start of a new cycle.

---

## LLM Self-Audit

Every skill appends a `## ⚠ Audit Warnings` section before completing its handoff. The section is produced by a secondary self-check prompt that verifies:

- All mandatory placeholders (`{...}`) replaced
- No contradictions with accepted ADRs
- All required fields present and non-empty

If no warnings are found, the section contains: `No warnings — artifact passed self-audit.`

This section is consumed by Ward's review-manager for cross-artifact consistency checks.
