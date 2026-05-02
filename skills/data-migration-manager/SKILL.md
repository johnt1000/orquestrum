---
name: data-migration-manager
description: Plans and documents a data migration — schema change, data backfill, or store-to-store move. Captures the forward path, the backward path (or explicit irreversibility), test data shape, dual-write/cutover plan, and rollback compatibility. Required for any release with a migration; called by Forge as a specialization of task-manager.
inject_references: full
emits_confidence: true
metadata:
  version: "1.0.0"
  author: "Jônatas Rodrigues"
  phase: 3
  depends_on: [task-manager]
  produces: "docs/02-planning/migrations/MIG-XXX-{slug}.md"
chain:
  next: security-manager
  condition: "migration plan affects data access; security-manager validates LGPD/PII implications"
---

# Data Migration Manager Skill

You plan a data migration. Migrations are the highest-risk operation in any system: they touch persistent state, often without a rollback, and a bad migration corrupts data permanently. This skill formalizes the discipline.

## When to use

- Schema change (DDL): add/drop column, change type, add/drop index, change constraint.
- Data backfill: populate new column, denormalize, deduplicate.
- Store move: data moves between databases / engines / regions.
- Index rebuild on a hot table.

## I/O Contract

| | Files |
|--|---------|
| **Reads** | active SPEC, related ADR (if architectural), Task `T{ID}` that owns the migration code |
| **Writes** | `docs/02-planning/migrations/MIG-XXX-{slug}.md` |
| **Depends on** | task-manager (the migration is a Task with code) |
| **Must NOT touch** | the migration code itself — the task owns the code, this skill owns the plan |
| **Handoff to** | security-manager (PII/LGPD review), then rollback-manager (rollback compatibility) |

## Execution Flow

1. **Classify migration** — Online (no service downtime, dual-write or trigger), Offline (service stopped during migration), Lazy (data migrated on read). State the choice and why.
2. **Reversibility class** — Reversible (backward DDL exists and tested), Conditionally reversible (backward path with data loss), Irreversible (forward only). Tied to `rollback-manager`.
3. **Forward path** — ordered, copy-pastable. Each step states its **commit window** (transactional? batched? lockless?).
4. **Backward path** — same level of detail, OR an explicit "Irreversible: see ROLLBACK for compensating action."
5. **Test data shape** — what does the data look like before and after, on a representative sample? Include row counts and at least one full example.
6. **Cutover plan** — for Online migrations: dual-write start, backfill batch size, cutover trigger, dual-write end. For Offline: pre/post scripts and the downtime budget.
7. **Rollback compatibility** — what `rollback-manager` will do if the migration runs but the release rolls back. State the matrix.
8. **PII/LGPD note** — does the migration touch sensitive data? If yes, security-manager handoff is mandatory.
9. **Compute attention score** — irreversible migrations default to red.

## Attention Score Emission

Compute via `orquestrum/lib/attention.py:compute()`:
- `confidence` — 1.0 if dry-run completed on prod-clone with row-count parity; 0.6 if dry-run on synthetic data; 0.3 if no dry-run
- `inference_depth` — 0 if every step is a tested DDL; 1+ if any step is theoretical
- `context_completeness` — fraction of (classification, reversibility, forward, backward, test data, cutover, rollback compat, PII note) filled
- `gate_failure_count` — 1 per missing rollback step; +1 if PII without security-manager review
- `upstream_scores` — Task `attention_score` of the migration Task
- `drift_days` — `days_since(last_validated)` of the related ADR

Irreversible migrations force `attention_band: red` regardless of formula.

## Guardrails

- **DO NOT** publish the migration plan without a tested forward path (dry-run on prod-clone for Online; full run on staging for Offline).
- **DO NOT** mark Reversible if any forward step is destructive (DROP COLUMN, TRUNCATE, etc) without a backup-restore companion.
- **DO NOT** skip the test data shape section. Row counts and one example are minimum.
- **DO NOT** treat Lazy migration as zero-cost. Lazy means each read pays; cumulative cost may be larger than Online.
- **DO NOT** dual-write without a cutover trigger and an end date. Dual-writes left running indefinitely become the new bug.
