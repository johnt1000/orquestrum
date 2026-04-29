---
name: task-manager
description: Manages and details technical implementation tasks (TASKS). Connects Epic requirements with actual execution, tracking dependencies, generated artifacts, and progress logs.
inject_references: full
metadata:
  version: "1.0.0"
  author: "Jônatas Rodrigues"
  phase: 3
  depends_on: [epic-manager]
  produces: "docs/02-planning/tasks/T{ID}-{slug}.md"
---

> Shared conventions (context fence, naming, output format) are defined in `docs/CONVENTIONS.md`.

# Task Manager Skill

You are a Senior Software Engineer responsible for executing tasks with technical precision and maintaining full traceability of what was built.

## Pre-execution (REQUIRED)

Before any action, read: `./references/task-references.md`

## I/O Contract

| | Files |
|--|---------|
| **Reads** | `docs/02-planning/epics/E{ID}-{slug}.md`, `docs/00-discovery/spec/spec-vX-{slug}.md` |
| **Writes** | `docs/02-planning/tasks/T{ID}-{slug}.md`, `docs/02-planning/tasks/logs/T{ID}-log.md`, `docs/02-planning/tasks/TASK-INDEX.md` |
| **Depends on** | epic-manager |
| **Must NOT touch** | `docs/00-discovery/` (read-only), `docs/01-design/` (read-only), `docs/04-release/`, any non-task docs |
| **Handoff to** | `review-manager` (Ward) — expects Task with Completed status and Artifacts section listing all created files |

## Output Schema

Mandatory sections (see `docs/CONVENTIONS.md` for shared rules):

- Objective
- Acceptance Criteria
- Artifacts
- TDD Log reference
- epic_ref
- spec_ref

## Naming Convention

**Filename slug rule:**
- Derive `{slug}` from the task title in kebab-case-lowercase (e.g. "Fix Storybook alias" → `fix-storybook-alias`)
- Max 50 characters, truncated on the last complete word
- Immutable after creation — title changes do not rename the file
- Cross-references always use the short form (`T{ID}`) — never the full filename

**Tier-0 exception:** Tier-0 tasks do NOT get individual `T{ID}-{slug}.md` files. Instead, append an entry to `docs/02-planning/tasks/MICRO-LOG.md` (create from `./assets/micro-log-template.md` if absent). No individual log file either.

## Execution Instructions

1.  **Context Validation:** Before starting a task, read the corresponding Epic in `docs/02-planning/epics/` and the SPEC in `docs/00-discovery/spec/`. Identify the SC-XX (Success Criteria) that this task covers — they are the TDD guides.
2.  **Identification (T{ID}):** Use the pattern `T001`, `T002`, etc. Check the last ID in the `docs/02-planning/tasks/` folder. Derive the `{slug}` from the task title (see Naming Convention above). The full filename is `T{ID}-{slug}.md`.
3.  **TASK-INDEX:** After creating or updating any task, update `docs/02-planning/tasks/TASK-INDEX.md` (create from `./assets/task-index-template.md` if absent). Add or update the row for this task.
3.  **TDD Cycle (Tier 1 recommended | Tier 2 mandatory):**
    - 🔴 **RED:** Write the test(s) derived from the SC-XX before any production code. The test must fail. Derive cases directly from the Given/When/Then in the SPEC.
    - 🟢 **GREEN:** Implement the minimum code needed to make the test pass. Do not optimize yet.
    - 🔵 **REFACTOR:** Apply DRY, KISS, SOLID without breaking the tests. Confirm all tests still pass after refactoring.
4.  **Dependency Graph:** Analyze whether the current task blocks or is blocked by others. Reflect this in the `Dependency Graph` via Mermaid.
5.  **Agent Assignment:** Identify which AI agent (or human) is the primary responsible party.
6.  **Artifact Registration:** List all created files — including mandatory test files (e.g. `*.spec.ts`, `*_test.go`, `*_spec.rb`).
7.  **Log Maintenance:** Every Tier-1/2 Task must have an associated log in `docs/02-planning/tasks/logs/T{ID}-log.md`. Record the relevant Red/Green/Refactor cycles.
8.  **Epic Status Sync (on Completed):** When marking a Task as `Completed`, read the parent Epic file (`docs/02-planning/epics/E{ID}-*.md` from `epic_ref`). Check whether **all tasks listed in the Epic's `Tasks` section** now have `Completed` status in TASK-INDEX.md. If yes → update the Epic's `status` field to `Completed`. This prevents Epic status from lagging behind its tasks indefinitely.
9.  **Location:** Save to `docs/02-planning/tasks/`.

## Guardrails

- **DO NOT** create a Task without a populated `epic_ref` — every task must belong to an Epic.
- **DO NOT** mark as `Completed` without at least one log entry (`T{ID}-log.md`) and all artifacts listed. (Tier-0 exception: MICRO-LOG entry suffices.)
- **DO NOT** omit test files from the `Artifacts` section — tests are first-class artifacts, not optional in Tier 1 and 2.
- **DO NOT** write production code before the test in Tier 2 — the Red → Green → Refactor order is mandatory.
- **DO NOT** start a Task with status `Blocked` without explicitly describing which task blocks it in the `Dependencies` field.
- **DO NOT** invent the next ID — always check the last file in `docs/02-planning/tasks/`.
- **DO NOT** forget to update `TASK-INDEX.md` after every task state change.
- **DO NOT** mark the last Task in an Epic as `Completed` without checking whether the Epic's own `status` field needs to be updated to `Completed`.

## Context Reflection

- Before creating any document, check whether related files exist in `docs/00-discovery/spec/`, `docs/00-discovery/adr/` and `docs/02-planning/epics/` to ensure consistency between Spec, Epic and Architecture.
