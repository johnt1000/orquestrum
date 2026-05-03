<!-- compact:auto-generated -->
# Archive Manager — Reference Rubric

Authoritative tier rubric and worked examples for the `archive-manager` skill. Read this **before** any deletion. Skill code lives in `skills/archive-manager/SKILL.md`.

The skill has **two modes** (`release`, `prune`); both use the same rubric below.

---

## The three tiers

```
Tier 1 (hard-delete)            → rm originals; no consolidation
Tier 2 (consolidate-then-delete) → append summary to ARCHIVE-vX.Y.Z.md, then rm originals
Tier 3 (preserve always)        → never touched, regardless of any signal
```

A file falls into **exactly one** tier. When two signals would suggest different tiers, the more conservative one wins (Tier 3 > Tier 2 > Tier 1). When ambiguous → Tier 3.

---

## Tier 1 — Hard-delete

No historical value. Delete on sight. Audit trail (count of removals) goes into the next archive file's "Removed empty stubs" section.

### Signals

| Signal | Threshold | Notes |
|---|---|---|
| Empty stub | File size <200 bytes | Often skeleton placeholders never filled in. |
| OS metadata | Filename matches `.DS_Store`, `Thumbs.db`, `desktop.ini` | macOS / Windows artifacts. |
| Scratch suffix | Filename ends with `.tmp`, `.candidate.md`, `.bak`, `~` | Editor / failed-save leftovers. |
| Stale draft | `status: Draft` in frontmatter AND no git mtime change in >60 days | The work was abandoned — preserve the decision NOT to do it via git, not via an open file. |
| Orphaned task log | `logs/T{ID}-log.md` exists but no `T{ID}-*.md` does | Leftover from a botched archive run. |

### Worked examples

| Path | Why Tier 1 |
|---|---|
| `docs/02-planning/tasks/T024.md` (124 bytes, `# T024\n(none)`) | Empty stub, no narrative content |
| `docs/.DS_Store` | OS metadata |
| `docs/00-discovery/spec/spec-v3-draft.candidate.md` | `.candidate.md` suffix |
| `docs/02-planning/tasks/T091.md` (`status: Draft`, last commit 2025-12-15, today 2026-05-03) | Draft, 138 days stale |
| `docs/02-planning/tasks/logs/T999-log.md` (no T999 file exists) | Orphaned log |

---

## Tier 2 — Consolidate-then-delete

Has historical value, but the value belongs in **one summary section** of an archive file — not in N sprawled originals. Generate the summary, then delete the originals.

### Signals

| Signal | Detection | Goes into archive section |
|---|---|---|
| Superseded spec | `spec-vN-*.md` exists where active SPEC (per CHECKPOINT.md) is `spec-vM` with M > N | "Superseded specs" |
| Superseded architecture | `ARCHITECTURE-vN-*.md` where active is `vM` with M > N | "Superseded architectures" |
| Old major release notes | `RELEASE-vN.x.y.md` where current major in CHANGELOG is M ≥ N+2 | "Released and shipped — historical majors" |
| Completed task (aged) | `T{ID}-*.md` with `status: Completed` AND belongs to a release that shipped >30 days ago | "Tasks consolidated" |
| Task log of consolidated task | `logs/T{ID}-log.md` whose parent T{ID} is also being consolidated | Same archive, one line per log |
| Quality records of consolidated task | `REVIEW-T{ID}-*.md` (Approved) or `QA-T{ID}-*.md` (Passed) for a consolidated T{ID} | "Quality records" — one line each |

### Summary content per source file

When consolidating, extract these fields into a one-paragraph section in the archive file:

- **Task / artifact ID** + slug
- **Final status** (Completed, Approved, Passed)
- **Key artifacts produced** (file paths from the original "Artifacts" section)
- **Acceptance criteria pass count** (e.g., "5/5 SC met")
- **Linked ADRs** (IDs only, since ADRs are Tier 3 and remain on disk)
- **One-sentence summary** of what shipped (extracted from the title/description)

Do NOT include: full body text, full code, transcripts, debug logs. Those belong in git history.

### Worked examples

| Path | Why Tier 2 | Destination |
|---|---|---|
| `docs/00-discovery/spec/spec-v0-extracted.md` (active is `spec-v8`) | 8 versions newer exists | `ARCHIVE-vCURRENT.md` Superseded specs section |
| `docs/01-design/architecture/ARCHITECTURE-v3.md` (active is `v5`) | 2 majors newer exists | `ARCHIVE-vCURRENT.md` Superseded architectures section |
| `docs/04-release/RELEASE-v1.2.0.md` (current is v3.x.x) | Major-2, no operational value | `ARCHIVE-v3.0.0.md` Released and shipped section |
| `docs/02-planning/tasks/T064-redesenho-base-seed-tenants.md` (`status: Completed`, shipped in v3.0.0 on 2026-04-01, today 2026-05-03) | 32 days post-ship | `ARCHIVE-v3.0.0.md` Tasks consolidated section |

---

## Tier 3 — Preserve always

Listed exhaustively. If a path doesn't appear here AND doesn't match Tier 1 or Tier 2 signals → still treat as Tier 3 (preserve on doubt).

### Always-preserved paths

| Path glob | Why |
|---|---|
| `docs/00-discovery/adr/ADR-*.md` | Decisions are forever — current AND retired ADRs are reference material |
| `docs/00-discovery/glossary/GLOSSARY.md` | Domain vocabulary — single source |
| `docs/00-discovery/spec/{active}` | The active spec referenced by CHECKPOINT.md |
| `docs/01-design/architecture/{active}` | The active architecture referenced by CHECKPOINT.md |
| `docs/03-quality/learning/L-*.md` | Learnings are forever — corrective knowledge |
| `docs/04-release/CHANGELOG.md` | Single source of release truth |
| `docs/04-release/RUNBOOK.md` | Operational, current |
| `docs/04-release/RELEASE-v{current-major}.x.y.md` | Current major's release notes — operationally relevant |
| `docs/02-planning/tasks/TASK-INDEX.md` | Task registry — auto-maintained |
| `docs/02-planning/tasks/MICRO-LOG.md` | Tier-0 work log |
| `docs/02-planning/tasks/ARCHIVE-*.md` | The archive destination — never delete the destination |
| `docs/CHECKPOINT.md` | Session continuity |

### Always-preserved by status

| Frontmatter | Reason |
|---|---|
| Any task with `status: In Progress`, `Blocked`, or `Pending` | Active work |
| Any artifact with `status: Active` (specs, architectures) | In use |

---

## Decision algorithm (pseudocode)

```python
def classify(file: Path, *, active_spec: str, active_arch: str,
             current_major: int, today: date) -> Tier:
    # Tier 3 — preserve-always paths
    if matches_preserve_always(file, active_spec, active_arch, current_major):
        return Tier.THREE
    if frontmatter_status(file) in {'In Progress', 'Blocked', 'Pending', 'Active'}:
        return Tier.THREE

    # Tier 1 — hard-delete signals
    if file.stat().st_size < 200:                      return Tier.ONE
    if file.name in {'.DS_Store', 'Thumbs.db'}:        return Tier.ONE
    if file.suffix in {'.tmp', '.bak'}:                return Tier.ONE
    if file.name.endswith('.candidate.md'):            return Tier.ONE
    if is_orphaned_task_log(file):                     return Tier.ONE
    if frontmatter_status(file) == 'Draft' and git_age_days(file) > 60:
        return Tier.ONE

    # Tier 2 — consolidate signals
    if is_superseded_spec(file, active_spec):          return Tier.TWO
    if is_superseded_arch(file, active_arch):          return Tier.TWO
    if is_old_major_release(file, current_major):      return Tier.TWO
    if is_completed_aged_task(file, today, threshold_days=30):
        return Tier.TWO
    if is_log_of_consolidated_task(file):              return Tier.TWO
    if is_quality_record_of_consolidated(file):        return Tier.TWO

    # Default — when in doubt, preserve
    return Tier.THREE
```

The skill executes this conceptually — not necessarily as code. The point: **default is Tier 3**.

---

## Common false positives — DO NOT delete

| Looks like | Why preserve |
|---|---|
| ADR with old date (`ADR-002` from 2024) | ADRs are decisions; rejecting them later is itself an ADR. Preserve all. |
| Learning from years ago (`L-001-...`) | Learnings encode "what we got wrong" — they age, but they don't expire. |
| `spec-vCURRENT-{slug}.md` with `last_validated` >30 days | Drift signal, not staleness — Flux flags drift, doesn't archive active spec. |
| `T-IN-PROGRESS-...md` with no commits in 90 days | Stalled but not abandoned — escalate to Flux for triage, don't archive. |
| `RELEASE-vCURRENT-MAJOR.x.y.md` (current major) | Operational reference — keep entire current major. |

---

## Idempotence

Both modes must be safe to run repeatedly:
- A second run on the same state produces zero changes.
- An archive file already containing a section for a source file → skip that source instead of duplicating.
- A delete that fails mid-batch → record the failure, continue, report at end.

The validation checks at the end of every run guarantee this property.
