---
name: rollback-manager
description: Produces a deterministic rollback procedure for a release. Captures pre-conditions, execution steps, verification checks, and the criterion under which the rollback is automatically triggered. Used by Cast as the inverse of changelog-manager.
inject_references: false
emits_confidence: true
metadata:
  version: "1.0.0"
  author: "Jônatas Rodrigues"
  phase: 5
  depends_on: [changelog-manager]
  produces: "docs/04-release/ROLLBACK-vX.Y.Z-{slug}.md"
chain:
  next: runbook-manager
  condition: "rollback procedure recorded; runbook may need cross-references"
---

# Rollback Manager Skill

You produce the rollback artifact for a release. Cast already owns ship; this skill formalizes the **inverse**: how to undo a release safely, without data loss, and with verifiable end state.

A rollback artifact is mandatory for any release that:
- Includes a database migration (forward AND backward path required)
- Changes a public API contract
- Ships a feature behind a flag (define how to disable + clean up)
- Was preceded by a hotfix in the last 30 days (heightened rollback discipline)

## I/O Contract

| | Files |
|--|---------|
| **Reads** | `docs/04-release/CHANGELOG.md` (release scope), `docs/04-release/RUNBOOK.md`, related migration files |
| **Writes** | `docs/04-release/ROLLBACK-vX.Y.Z-{slug}.md` |
| **Depends on** | changelog-manager |
| **Must NOT touch** | code, ADRs, SPEC |
| **Handoff to** | runbook-manager (cross-link), then archive-manager next cycle |

## Execution Flow

1. **Identify reversibility class** — Reversible (config, no migration), Conditionally reversible (migration with backward path), Irreversible (one-way migration / destructive change). Irreversible releases require explicit approval recorded here.
2. **Capture pre-conditions** — what must be true before rollback can run safely (e.g. "no in-flight transactions on table X"; "feature flag is the rollback path, not a redeploy").
3. **Capture execution steps** — ordered, copy-pastable. Each step has an expected outcome. No prose between steps unless it's a safety note.
4. **Capture verification** — explicit observable signals that the rollback succeeded. Not "should work" — actual checks.
5. **Capture trigger** — the automatic condition that calls for rollback (e.g. "error rate > 2% in 5-minute window").
6. **Capture data implications** — any rows/files/state that will be lost or invalidated. If irreversible, this section is mandatory and signed off.
7. **Compute attention score** — irreversible rollbacks default to red.

## Attention Score Emission

Compute via `scripts/lib/attention.py:compute()`:
- `confidence` — 1.0 if Reversible; 0.6 if Conditionally; 0.3 if Irreversible
- `inference_depth` — 0 if procedure was tested in staging; 1 if procedure is theoretical
- `context_completeness` — fraction of (pre-conditions, steps, verification, trigger, data implications) filled
- `gate_failure_count` — 1 if irreversible without sign-off; 1 per missing verification step
- `upstream_scores` — `attention_score` of the release artifact / changelog
- `drift_days` — `days_since(last_validated)` of related migration ADR

Irreversible rollbacks force `attention_band: red` regardless of formula. This is intentional.

## Guardrails

- **DO NOT** publish a rollback artifact whose steps were not at least dry-run in staging (unless the rollback is "redeploy previous tag" with no migration).
- **DO NOT** use vague verification ("looks ok"). State a metric, a query, or an endpoint.
- **DO NOT** mark a release Reversible if it includes any forward-only migration. Even one is enough to be Conditionally Reversible.
- **DO NOT** skip the data implications section for Conditionally or Irreversible classes.
