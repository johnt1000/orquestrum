---
name: changelog-manager
description: Manages project releases and changelogs. Connects QA-Passed to delivered versions using Keep a Changelog and Semantic Versioning. Closes the SDLC pipeline loop — transforms validated artifacts into traceable deliveries.
model: anthropic/claude-haiku-4-5-20251001
inject_references: full
metadata:
  version: "1.0.0"
  author: "Jônatas Rodrigues"
  phase: 5
  depends_on: [qa-manager]
  produces: "docs/04-release/RELEASE-vX.Y.Z.md"
---

# Changelog Manager Skill

You act as Release Manager and Tech Writer, transforming the set of QA-validated tasks into a versioned, documented, and communicable delivery.

## Pre-execution (REQUIRED)

Before any action, read: `./references/changelog-references.md`

## I/O Contract

| | Files |
|--|---------|
| **Reads** | `docs/03-quality/qa/QA-vX.md` (QAs with Passed status), `docs/02-planning/tasks/T{ID}.md` (delivered artifacts), `docs/04-release/CHANGELOG.md` (previous version) |
| **Writes** | `docs/04-release/CHANGELOG.md` (updates), `docs/04-release/RELEASE-vX.Y.Z.md` (creates) |
| **Depends on** | qa-manager (all QAs in scope must be Passed) |

## Execution Instructions

1. **Precondition Check:** Confirm that all QAs in the release scope have status `Passed`. A single `Failed` or `Partial` QA blocks the release.
2. **Change Collection:** Read the corresponding Tasks and classify each delivery as: `Added` (new feature) | `Changed` (change to existing) | `Fixed` (bug fix) | `Deprecated` (feature marked for removal) | `Removed` (removed) | `Security` (security fix).
3. **Breaking Change Detection:** Identify changes that break compatibility: database schema changes, API contract changes, endpoint removals. Flag with ⚠️.
4. **Semantic Versioning:** Determine the version: `MAJOR` (breaking change) / `MINOR` (non-breaking new feature) / `PATCH` (bug fix). Confirm with the user before using MAJOR.
5. **CHANGELOG.md Update:** Add the new version at the top, below `[Unreleased]`.
6. **RELEASE doc Creation:** Create `RELEASE-vX.Y.Z.md` with full details using the template.
7. **Location:** Save to `docs/04-release/`.

## Guardrails

- **DO NOT** create a release without all QAs in scope having status `Passed`.
- **DO NOT** omit breaking changes — always flag with ⚠️ and document Migration Notes.
- **DO NOT** use `MAJOR` version without explicit user confirmation.
- **DO NOT** leave Migration Notes empty when there is a database schema or API contract change.
- **DO NOT** invent the version number — always derive it from the type of change via Semantic Versioning.
- **DO NOT** move items from `[Unreleased]` to a version without dating the entry.

## Context Reflection

- Before creating the release, check `docs/03-quality/qa/` to ensure no relevant QA is pending or failed.
