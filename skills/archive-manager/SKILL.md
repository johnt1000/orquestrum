---
name: archive-manager
description: Consolidates obsolete docs into compact summary files and deletes the originals. Two modes — `release` (consolidate completed tasks/logs after a release; default for Cast) and `prune` (proactive hygiene for any obsolete artifact at any time; default for Flux).
inject_references: compact
metadata:
  version: "1.2.0"
  author: "Jônatas Rodrigues"
  phase: 5
  depends_on: [changelog-manager]      # release mode only — prune has no dependencies
  produces: "docs/02-planning/tasks/ARCHIVE-vX.Y.Z.md"
chain:
  next: runbook-manager
  condition: "release mode only — prune mode does not chain"
---

# Archive Manager Skill

You consolidate obsolete artifacts into compact summary files and delete the originals. The skill has two modes:

- **`release` mode (default for Cast):** invoked after a release. Consolidates Completed tasks/logs that belong to the just-released version. Pre-condition: `changelog-manager` has already produced `RELEASE-vX.Y.Z.md`.
- **`prune` mode (default for Flux):** proactive hygiene. Scans `docs/` for any obsolete artifact (superseded versions, empty stubs, stale drafts) regardless of release state. No release pre-condition.

Both modes share the same tier rubric and the same preserve-always list. They differ in what they look for and when they fire.

## I/O Contract

| | Files |
|--|---------|
| **Reads** | `docs/04-release/CHANGELOG.md` (release scopes — release mode), `docs/02-planning/tasks/T{ID}-*.md` (Completed tasks), `docs/02-planning/epics/E{ID}-*.md` (epic scope), `docs/02-planning/tasks/TASK-INDEX.md` (registry), `docs/03-quality/learning/L-XXX.md` (learnings), `docs/CHECKPOINT.md` (active SPEC/Architecture pointers), `docs/00-discovery/spec/spec-v*.md` + `docs/01-design/architecture/ARCHITECTURE-v*.md` (version supersession check) |
| **Writes** | `docs/02-planning/tasks/ARCHIVE-vX.Y.Z.md` (consolidated summary), `docs/02-planning/tasks/TASK-INDEX.md` (updated), `docs/CHECKPOINT.md` (updated) |
| **Deletes** | Tier-1 (hard-delete) + Tier-2 (consolidate-then-delete) artifacts per tables below. Never touches Tier-3 preserve-always. |
| **Depends on** | `changelog-manager` in **release mode only**. **No dependencies in prune mode.** |
| **Must NOT touch** | Anything in the preserve-always list (see below). |
| **Handoff to** | `runbook-manager` (release mode only — runbook may need cleanup of stale references). |

## Pre-execution (REQUIRED)

Before any action — both modes:

1. Read `./references/archive-references.md` for the tier rubric and worked examples.
2. Read `docs/CHECKPOINT.md` to identify the **active SPEC version** and **active Architecture version**. These point to files that must NEVER be deleted, regardless of how many older versions exist.
3. Read `docs/02-planning/tasks/TASK-INDEX.md` for the full task inventory.

Mode-specific:

- **Release mode:** also read `docs/04-release/CHANGELOG.md` to identify the just-released version and which tasks belong to it.
- **Prune mode:** no extra reads — operates on the inventory + freshness signals alone.

---

## Tier Rubric

Every candidate file falls into exactly one tier. The rubric below is the **complete decision tree** — there is no "ad-hoc" tier.

### Tier 1 — Hard-delete (no consolidation)

These have no historical value worth preserving. Delete directly.

| Signal | Example |
|---|---|
| File size <200 bytes (empty stub) | `T024.md` containing only `# T024\n(none)` |
| `.DS_Store`, `.tmp`, `.candidate.md` | macOS metadata + scratch files |
| Draft status with no commit in >60 days | A `T123-{slug}.md` with `status: Draft` whose last git mtime is >60d old |
| Orphaned task log (`logs/T{ID}-log.md`) when `T{ID}-*.md` no longer exists | Leftover from earlier botched archive |

### Tier 2 — Consolidate-then-delete (hybrid retention)

These have historical value but the value belongs in a single summary file, not in many sprawled originals. The archive file gets one section per source file (key facts only); originals are then deleted.

| Signal | Example | Goes into |
|---|---|---|
| Spec version `spec-vN-*.md` where a higher version exists in CHECKPOINT.md as active | `spec-v0`..`spec-v6` when active = `spec-v8` | `ARCHIVE-vX.Y.Z.md` "Superseded specs" section |
| Architecture version `ARCHITECTURE-vN-*.md` where higher version is active | `ARCHITECTURE-v0`..`ARCHITECTURE-v4` when active = `v5` | `ARCHIVE-vX.Y.Z.md` "Superseded architectures" section |
| Release notes `RELEASE-vN.X.Y.md` from major versions superseded by current major (current major − 1 or older) | `RELEASE-v1.x.x.md` when current is v3.x.x | `ARCHIVE-vX.Y.Z.md` "Released and shipped" section |
| Task `T{ID}` with `status: Completed` for >30 days **AND** belongs to a released version | `T064-redesenho-base-seed-tenants.md` shipped in v3.0.0, completed 45 days ago | `ARCHIVE-vX.Y.Z.md` "Tasks consolidated" section |
| Task log `logs/T{ID}-log.md` whose `T{ID}` is being consolidated | Same release as parent task | Same archive file, summarized into one line |
| Approved Review / Passed QA whose Task is being consolidated | `REVIEW-T064-{slug}.md` after T064 is consolidated | `ARCHIVE-vX.Y.Z.md` "Quality records" section (one line per QA) |

### Tier 3 — Preserve always

These are NEVER touched, regardless of age, status, or any other signal.

- All ADRs (`docs/00-discovery/adr/ADR-*.md`)
- Glossary (`docs/00-discovery/glossary/GLOSSARY.md`)
- Active SPEC (the one referenced in `CHECKPOINT.md`)
- Active Architecture (the one referenced in `CHECKPOINT.md`)
- All Learnings (`docs/03-quality/learning/L-*.md`)
- CHANGELOG (`docs/04-release/CHANGELOG.md`)
- RUNBOOK (`docs/04-release/RUNBOOK.md`)
- Current MAJOR release notes (`RELEASE-vCURRENT.x.y.md` — only the most recent major)
- TASK-INDEX (`docs/02-planning/tasks/TASK-INDEX.md`)
- MICRO-LOG (`docs/02-planning/tasks/MICRO-LOG.md`)
- CHECKPOINT (`docs/CHECKPOINT.md`)
- Active tasks — any `T{ID}` with status `In Progress`, `Blocked`, or `Pending`
- Existing `ARCHIVE-*.md` files (the destination — never delete these)

If a file is ambiguous → treat it as Tier 3 (preserve). Never delete on guess.

---

## Execution Flow — Release Mode

### Step 1 — Identify scope

1. Read `CHANGELOG.md`. Identify the just-released version (top entry) and the tasks/epics it lists.
2. Cross-reference `TASK-INDEX.md` to get the complete task list per epic in scope.
3. Build the candidate set: tasks marked `Completed` belonging to the released version. Apply Tier 1 + Tier 2 rules to each.
4. Range verification: every task in the candidate set must exist on disk AND be `Completed`. Skip mismatches; do NOT assume continuity.

### Step 2 — Generate or update archive file

For the just-released version, write `docs/02-planning/tasks/ARCHIVE-vX.Y.Z.md` using `./assets/archive-template.md`. One section per Tier 2 category (Tasks consolidated / Quality records / Superseded specs if any / Superseded architectures if any).

### Step 3 — Delete originals

Delete every file classified as Tier 1 or Tier 2. Use `bundle/archive-cleanup.sh --project . --dry-run` first to preview, then re-run without `--dry-run`. The script honors the same preserve-always list as this skill.

### Step 4 — Update TASK-INDEX + CHECKPOINT

- Remove archived task rows from TASK-INDEX.
- Add an `## Archive` section listing each `ARCHIVE-vX.Y.Z.md` with version + date.
- Update CHECKPOINT.md `Active Artifacts` removing archived items; note the archive op in `Decisions Made This Session`.

### Step 5 — Validation (mandatory — see "Validation" section below)

---

## Execution Flow — Prune Mode

Prune mode walks the entire `docs/` tree and applies the tier rubric to every file. It does **not** require a release to exist or to be just-shipped.

### Step 1 — Build candidate inventory

1. Walk `docs/**/*.md` collecting every artifact.
2. For each file, determine its tier via the rubric. Record `(path, tier, signal)` triples.
3. Group results: Tier 1 (delete-list), Tier 2 (consolidate-list grouped by destination archive), Tier 3 (skip).

### Step 2 — Choose destination archive file(s)

For each Tier 2 candidate, determine which `ARCHIVE-vX.Y.Z.md` it belongs to:
- Tasks/QAs/Reviews → archive of the version that shipped that task (look up via CHANGELOG).
- Superseded specs/architectures → archive of the version that introduced the supersession (or the current latest archive, creating a new one if none exists).
- If no archive exists yet → create `ARCHIVE-prune-YYYY-MM-DD.md` as a special prune archive.

### Step 3 — Dry-run report (mandatory before any deletion)

Print a complete report:

```
Prune candidates:
  Tier 1 (hard-delete):       N files (~K KB)
  Tier 2 (consolidate-delete): M files → P archive sections
  Tier 3 (preserve):          Q files (untouched)

Affected archive files:
  - ARCHIVE-v3.0.0.md (+12 sections)
  - ARCHIVE-v2.5.0.md (+3 sections)

Top 10 candidates by size (Tier 1+2):
  - docs/00-discovery/spec/spec-v0-extracted.md (24 KB, Tier 2)
  - docs/01-design/architecture/ARCHITECTURE-v0-as-is.md (18 KB, Tier 2)
  ...
```

### Step 4 — Confirm + execute

If the caller is interactive (Flux invoked by user), wait for explicit confirmation before deletion. If the caller is automated (Helm scheduled prune), execute when total Tier 1+2 size <500 KB; require human ack above that threshold.

After confirmation: write/update the destination archive files, then delete originals via `bundle/archive-cleanup.sh` with appropriate flags.

### Step 5 — Update TASK-INDEX + CHECKPOINT (same as release mode Step 4)

### Step 6 — Validation (mandatory — same as below)

---

## Validation (both modes — MANDATORY)

After all operations, run these checks. ALL must pass:

**Check 1: Zero empty files**
```bash
find docs/ -name "*.md" -empty
```
Must return ZERO results.

**Check 2: Archive consistency**
For each `ARCHIVE-vX.Y.Z.md`, verify NO original file still exists for any artifact listed in the archive.

**Check 3: Active files match TASK-INDEX**
Count remaining task files = task rows in TASK-INDEX.md.

**Check 4: SPEC/Architecture cleanup**
Only ONE active spec file and ONE active architecture file should remain (the versions referenced in CHECKPOINT.md). Any older versions = bug, must be archived.

**Check 5: No ghost files**
No duplicates (e.g., `T043.md` alongside `T043-{slug}.md`).

**Check 6: Preserve-always intact**
Every Tier 3 path listed in the rubric still exists on disk. ZERO false-positive deletions.

If ANY check fails → report and fix before completing.

---

## Archive File Template

Use `./assets/archive-template.md` as the base. The template has slots for: Tasks consolidated / Quality records / Superseded specs / Superseded architectures / Released and shipped (older majors) / Removed empty stubs (Tier 1 audit trail).

---

## Output Format

```
Archive complete:
  Mode:                {release | prune}
  Releases archived:   vX.Y.Z (release mode) | n/a (prune mode)
  Tier 1 deletions:    N files (~K KB)
  Tier 2 consolidations: M files → P archive sections in {N} archive files
  Tier 3 preserved:    Q files (untouched)
  Space recovered:     {size} (du -sh before/after)
  Remaining files:     {N}
  Validation:          {Check 1-6 each: pass | fail with detail}
```

---

## Guardrails

- **NEVER** delete a Tier 3 file. If in doubt → Tier 3.
- **NEVER** run prune mode without writing the dry-run report first.
- **NEVER** assume a task range is continuous — verify each task individually.
- **NEVER** delete the active SPEC or active Architecture, even if many old versions also exist.
- **NEVER** delete ARCHIVE-*.md files (the destination is sacred).
- **DO** consolidate before deleting — Tier 2 originals only get removed AFTER their summary lands in the archive file.
- **DO** call the cleanup script with `--dry-run` first.
