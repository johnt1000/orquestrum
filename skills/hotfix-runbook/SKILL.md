---
name: hotfix-runbook
description: Produces a focused hotfix runbook for a critical production bug. Bypasses the full discovery/design pipeline; preserves traceability, testing, and release artifacts. Used when production is bleeding and waiting for a Tier-2 cycle is not acceptable.
inject_references: false
emits_confidence: true
metadata:
  version: "1.0.0"
  author: "Jônatas Rodrigues"
  phase: maintenance
  depends_on: [task-manager]
  produces: "docs/04-release/HOTFIX-vX.Y.Z-{slug}.md"
chain:
  next: changelog-manager
  condition: "hotfix shipped, changelog and release notes need finalizing"
---

# Hotfix Runbook Skill

You produce the **HOTFIX runbook** — the abbreviated, bleeding-fast path for a critical production bug. The pipeline normally goes Lore → Forge → Cipher → Ward → Cast. A hotfix collapses that into Flux → Forge (task only) → Ward (review only) → Cast (release only).

## When to use

A hotfix is justified when **all** of:
- Production users are impacted right now
- Root cause is known or contained to a small change
- A correct full-pipeline version would arrive too late
- The fix is reversible (small diff, well-tested area)

If any of those is missing, do NOT use this skill. Run the full pipeline.

## I/O Contract

| | Files |
|--|---------|
| **Reads** | `docs/CHECKPOINT.md`, recent `docs/03-quality/learning/L-*.md` (if exists), the affected code |
| **Writes** | `docs/04-release/HOTFIX-vX.Y.Z-{slug}.md` |
| **Depends on** | task-manager (the actual fix Task) |
| **Must NOT touch** | Any architecture, ADR, SPEC — hotfixes do not amend governance |
| **Handoff to** | changelog-manager (release entry), then learning-manager (post-incident) |

## Pre-execution

Read the existing `docs/04-release/RUNBOOK.md` to see how the affected component is normally operated. The HOTFIX runbook does NOT replace it; it amends it for the duration of the patch.

## Execution Flow

1. **Confirm scope.** One Task, one fix, one tested path. If the fix needs an ADR, abort: this is a Tier-2 problem, not a hotfix.
2. **Capture impact** in the artifact: what users see, error rate, started-at timestamp, current mitigation if any.
3. **Capture the fix** as a single Task reference (`T{ID}`) plus a one-paragraph technical description. Skip epic, architecture, pattern.
4. **Capture the test** — even a hotfix needs verification. State the manual test step, the automated test (if any), and the rollback trigger condition.
5. **Capture the release plan** — version bump (always patch), deployment window, monitoring window, rollback procedure (link to `rollback-manager` artifact if produced).
6. **Compute attention score** — hotfixes default to `attention_band: yellow` minimum; never green. The fix is fast and the pipeline is bypassed; reviewer attention is non-negotiable.

## Attention Score Emission

Compute via `scripts/lib/attention.py:compute()` with these inputs:
- `confidence` — 0.6 default (hotfix bypasses full review); 0.3 if rollback-tested
- `inference_depth` — 0 (the bug is observed, not inferred)
- `context_completeness` — fraction of (impact, fix, test, release plan, rollback trigger) sections filled
- `gate_failure_count` — 1 if any of (Cipher security gate, Ward QA full pass) was skipped
- `upstream_scores` — Task `attention_score` of the fix Task
- `drift_days` — `days_since(last_validated)` of the SPEC referenced (if any)

Cap output band at `yellow` minimum (max score 79) regardless of formula — by policy, a hotfix is never routine.

## Guardrails

- **DO NOT** ship without naming a rollback trigger (e.g. "if error rate > 1% in 30 min, run rollback-manager").
- **DO NOT** skip the post-incident `learning-manager` chain — the hotfix is not done until the learning is captured.
- **DO NOT** use this skill for "fast feature" delivery. Hotfix means production is broken. Period.
- **DO NOT** amend the architecture, ADR, or SPEC inline. If the fix reveals a governance issue, file it for the next Lore cycle.
