---
name: archive-manager
description: Consolidates completed tasks, logs, QAs, and reviews into summary files per release. Reduces repository clutter while preserving traceability.
inject_references: compact
metadata:
  version: "1.1.0"
  author: "Jônatas Rodrigues"
  phase: 5
  depends_on: [changelog-manager]
  produces: "docs/02-planning/tasks/ARCHIVE-vX.Y.Z.md"
chain:
  next: runbook-manager
  condition: "archive complete, runbook may need cleanup of stale references"
---

# Archive Manager Skill

You act as Release Archivist, consolidating completed artifacts into compact summary files after each release. This keeps the repository clean while preserving full traceability.

## I/O Contract

| | Files |
|--|---------|
| **Reads** | `docs/04-release/CHANGELOG.md` (releases + their scopes), `docs/02-planning/tasks/T{ID}-*.md` (completed tasks), `docs/02-planning/epics/E{ID}-*.md` (epic scope), `docs/02-planning/tasks/TASK-INDEX.md` (task registry), `docs/03-quality/learning/L-XXX.md` (learnings) |
| **Writes** | `docs/02-planning/tasks/ARCHIVE-vX.Y.Z.md` (consolidated summary), `docs/02-planning/tasks/TASK-INDEX.md` (updated), `docs/CHECKPOINT.md` (updated) |
| **Deletes** | Completed task files, completed log files, superseded SPEC/Architecture versions |

## Pre-execution (REQUIRED)

Before any action:
1. Read `docs/04-release/CHANGELOG.md` to identify releases and their scopes
2. Read `docs/02-planning/tasks/TASK-INDEX.md` to get the full task inventory
3. Read `docs/CHECKPOINT.md` to identify active SPEC and Architecture versions

## NEVER Archive (Protected Artifacts)

These files are **permanently protected** and must NEVER be deleted:

- **ADRs** — `docs/00-discovery/adr/ADR-*.md` — always keep
- **Glossary** — `docs/00-discovery/glossary/GLOSSARY.md` — always keep
- **Learnings** — `docs/03-quality/learning/L-*.md` — always keep
- **CHANGELOG** — `docs/04-release/CHANGELOG.md` — always keep
- **RUNBOOK** — `docs/04-release/RUNBOOK.md` — always keep
- **Active SPEC** — only the latest version (the one referenced in CHECKPOINT.md)
- **Active Architecture** — only the latest version (the one referenced in CHECKPOINT.md)
- **Active tasks** — any task with status `In Progress`, `Blocked`, `Draft`, or `Pending`

## Execution Flow

### Step 1 — Identify Archive Scope

1. Read CHANGELOG.md and identify all releases (sections starting with `## [X.Y.Z]`)
2. For each release, extract:
   - Version number
   - Date
   - Epics/tasks mentioned in the changelog entries
3. Cross-reference with TASK-INDEX.md to get complete task lists per epic
4. Identify which tasks are `Completed` and belong to a released version
5. **Range verification:** For each release, confirm EVERY task in the range actually exists AND is `Completed`. If a task is missing or has a different status, adjust the range or skip that task — do NOT assume the range is continuous.

### Step 2 — Verify No Active Work Will Be Affected

**CRITICAL: Before deleting ANY file, verify:**

1. Every task to be archived has status `Completed`
2. No task with status `In Progress`, `Blocked`, or `Draft` will be affected
3. The active SPEC and Architecture versions (from CHECKPOINT.md) are NOT in the deletion list
4. If ANY doubt exists → skip that file and report it as "skipped for safety"

### Step 3 — Generate Archive Files

For each release that has completed tasks not yet archived:

1. Group tasks by Epic
2. For each task, extract: ID, title, key artifacts produced, acceptance criteria status
3. Extract key learnings from `docs/03-quality/learning/` that relate to tasks in this release
4. List ADRs created during this release's tasks
5. Generate `docs/02-planning/tasks/ARCHIVE-vX.Y.Z.md` using the archive template

### Step 4 — Physically Delete Archived Files

Run the deterministic cleanup script to delete all files that were consolidated into the archives:

```bash
# Always run dry-run first to preview what will be deleted
bundle/archive-cleanup.sh --project . --dry-run

# Review the output carefully, then execute
bundle/archive-cleanup.sh --project .
```

**What the script deletes:**
- Completed task files (`T{ID}*.md`) and their logs
- Superseded SPEC and Architecture versions (keeps only active from CHECKPOINT.md)
- Passed QA and Approved Review files for archived epics
- Any empty `.md` files (cleanup of previous failed attempts)

**What the script protects (never deletes):**
- ADRs, Glossary, Learnings, CHANGELOG, RUNBOOK, MICRO-LOG, TASK-INDEX, CHECKPOINT
- Active SPEC and Architecture versions
- ARCHIVE-*.md files themselves

**If the script is unavailable**, fall back to manual `rm` via Bash tool — one file at a time. NEVER truncate or empty files.

### Step 5 — Update Registry

1. Update `docs/02-planning/tasks/TASK-INDEX.md`:
   - Remove rows for archived tasks
   - Add a section `## Archive` listing archive files with version and date
   - Verify that remaining rows match actual files on disk exactly
2. Update `docs/CHECKPOINT.md`:
   - Update Active Artifacts section to remove archived items
   - Add note about archive in "Decisions Made This Session"

### Step 6 — Validation (MANDATORY)

After all operations, run these checks. ALL must pass:

**Check 1: Zero empty files**
```bash
find docs/ -name "*.md" -empty
```
Must return ZERO results. If any empty files exist → delete them.

**Check 2: Archive consistency**
For each ARCHIVE-vX.Y.Z.md, verify that NO original task/log file still exists for any task listed in the archive.

**Check 3: Active files match TASK-INDEX**
Count remaining task files → must equal task rows in TASK-INDEX.md.

**Check 4: SPEC/Architecture cleanup**
Only ONE spec file and ONE architecture file should remain (the active versions from CHECKPOINT.md).

**Check 5: No ghost files**
No duplicate or orphaned files (e.g., T043.md alongside T043-slug.md).

**If ANY check fails → report the failure and fix before completing.**

## Archive File Template

Use `./assets/archive-template.md` as the base template for each archive file.

## Output Format

Upon completion, report:

```
Archive complete:
  Releases archived: vX.Y.Z, vA.B.C
  Tasks consolidated: {N} → {M} archive files
  Files deleted: {N} tasks + {N} logs + {N} old versions = {total}
  Space recovered: {size} (use du -sh before/after)
  Remaining active files: {N}
  Validation: {list each check and its result}
```
