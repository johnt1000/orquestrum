---
name: checkpoint-manager
description: Manages CHECKPOINT.md — the persistent session state file written at the end of every session and read at the start of the next. Ensures continuity across context boundaries without requiring the orchestrator to re-read the entire pipeline.
inject_references: false
metadata:
  version: "1.0.0"
  author: "Jônatas Rodrigues"
  phase: cross-cutting
  depends_on: []
  produces: "docs/CHECKPOINT.md"
---

# Checkpoint Manager Skill

You manage the session continuity file (`docs/CHECKPOINT.md`) that allows orchestrators to resume work across context boundaries without reading the entire pipeline from scratch.

## I/O Contract

| | Files |
|--|---------|
| **Reads** | `docs/CHECKPOINT.md` (if exists) |
| **Writes** | `docs/CHECKPOINT.md` |
| **Depends on** | none |
| **Must NOT touch** | Any artifact outside `docs/CHECKPOINT.md` |

## Protocol

### On session START (read)

1. Check whether `docs/CHECKPOINT.md` exists.
2. If it exists → read it. Restore: tier, phase, active orchestrator, active artifact paths, pending work.
3. If it does not exist → this is a fresh project. Skip and proceed with normal BOOTSTRAP (SDLC detection).
4. Validate: do the active artifact paths listed actually exist on disk? Flag any that are missing.
5. **Cross-validate task state (stale checkpoint detection):** For every task listed under `Pending Work` with a task reference (`T{ID}`), read its actual file at `docs/02-planning/tasks/T{ID}-*.md` (or check `docs/02-planning/tasks/TASK-INDEX.md`). If the task's `status` field is `Completed` in the file but the checkpoint lists it as pending → the checkpoint is **stale** for that item. Log a warning: `⚠️ STALE: T{ID} is Completed on disk but listed as pending in checkpoint.` Remove the item from `Pending Work` and update the checkpoint before proceeding. Do not resume work on a task that is already done.

### On session END (write)

After completing any meaningful unit of work, write `docs/CHECKPOINT.md` using `./assets/checkpoint-template.md` as the base:

1. Set `session_id` to the current session identifier (date + short hash, e.g. `2026-04-27-a3f2`).
2. Set `updated` to current timestamp.
3. Set `tier`, `phase`, `orchestrator` to current values.
4. Fill `Active Artifacts` with the **most recent authoritative path** for each type. Leave blank types that have not been produced yet.
5. Fill `Pending Work` with any items that were started but not completed.
6. Remove completed `Pending Work` items from the previous checkpoint.
7. Record decisions made this session in `Decisions Made This Session`.
8. **Rebuild the metrics session summary** if `.orquestrum/metrics/events.jsonl` exists: run `orquestrum.lib.metrics:rebuild_session()` (or call via the bash tool). Then read `.orquestrum/metrics/session.json` and populate the `## Metrics Summary` section with: total calls, input/output tokens, cached tokens, estimated cost, top 3 skills by input tokens. If a budget warning fires (`orquestrum.lib.budget:check_session_budget()`), include the formatted warning verbatim.
9. Overwrite the existing file — do not append.

### MEDIATION.md aggregation

After writing CHECKPOINT.md, scan `docs/03-quality/{review,qa,security,learning}/` for artifacts emitted in the current session and aggregate their `attention_score`, `attention_band`, `attention_factors` frontmatter into a single `docs/MEDIATION.md` table sorted ascending by score (lowest = most attention required first):

| Artifact | Band | Score | Dominant factors |
|----------|------|------:|------------------|
| `REVIEW-vX-{slug}` | 🔴 | 32 | drift_days:60, inference_depth:3 |
| `QA-vX-{slug}`     | 🟡 | 64 | gate_failures:1, context_incomplete:0.30 |

If no artifacts have attention metadata yet (Phase 4 not enabled in this project), skip emission. Do NOT fabricate scores.

The propagation rule (`min(own, max(upstream)+10)`) is applied by the emitting skill, not here. checkpoint-manager only consolidates already-computed values.

See `docs/agent-context/CONVENTIONS.md` → Human Attention Mediation for the formula and the override mechanism.

### Enrichment by other orchestrators

Any orchestrator may update specific sections of `docs/CHECKPOINT.md` without rewriting the whole file:
- **Forge** must update `Active Artifacts` after producing a new Task, Epic, or Architecture.
- **Ward** must update `Active Artifacts` after producing a Review or QA.
- **Cast** must update `Active Artifacts` after producing a Release.
- **Lore** must update `Active Artifacts` after producing a Spec or ADR.
- Any orchestrator may add items to `Pending Work` when it discovers work that needs to happen but is out of its current scope.

## Template Usage

Use `./assets/checkpoint-template.md` as the base structure. Do not change the section names — they are parsed by Helm.

## Guardrails

- **DO NOT** leave `Pending Work` items that were completed in the previous session — clean them before writing.
- **DO NOT** write artifact paths that do not exist on disk.
- **DO NOT** create CHECKPOINT.md if no meaningful work was done in the session.
- **DO NOT** record raw prompts, full message content, or user-supplied confidential payloads in CHECKPOINT.md — it is a project artifact, not a transcript.
- **DO** record aggregated metrics (token counts, cached-token ratio, cost estimate, top skills by spend) in `## Metrics Summary`. These are operational signals required by `docs/governance/COST.md` and `docs/governance/OBSERVABILITY.md`. Counts yes; content no.
