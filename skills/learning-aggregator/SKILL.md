---
name: learning-aggregator
description: Aggregates individual L-XXX learning documents, detects recurrence patterns, and produces a LEARNING-SUMMARY with cross-cutting insights and prevention recommendations.
inject_references: false
metadata:
  version: "1.0.0"
  author: "Jônatas Rodrigues"
  phase: 4
  depends_on: [learning-manager]
  produces: "docs/03-quality/learning/LEARNING-SUMMARY-v{N}.md"
---

> Shared conventions (context fence, naming, output format) are defined in `docs/CONVENTIONS.md`.

# Learning Aggregator Skill

You act as a Pattern Analyst, scanning all existing `L-XXX` learning documents to surface recurring failure modes, cross-cutting technical debt signals, and systemic improvement opportunities.

## I/O Contract

| | Files |
|--|---------|
| **Reads** | All `docs/03-quality/learning/L-XXX-*.md` files |
| **Writes** | `docs/03-quality/learning/LEARNING-SUMMARY-v{N}.md` |
| **Depends on** | At least 3 learning documents must exist before aggregation is meaningful |
| **Must NOT touch** | Any individual `L-XXX` file (read-only input), any code or planning files |

## Execution Flow

### Step 1 — Inventory

List all `docs/03-quality/learning/L-XXX-*.md` files. If fewer than 3 exist, report: "Insufficient data for aggregation — minimum 3 learning documents required" and stop.

### Step 2 — Extract signals

For each learning document, extract:
- `id`, `title`, `root_cause`, `category` (if present)
- The primary failure pattern (one sentence)
- Whether the issue was a recurrence (already documented in a previous L-XXX)

### Step 3 — Cluster by pattern

Group extracted signals into pattern clusters. Name each cluster with a short label (e.g., "Missing input validation", "DB migration ordering", "Untested edge case").

Minimum cluster size to report: 2 occurrences. Single-occurrence signals go into **Isolated incidents**.

### Step 4 — Rank by frequency and impact

Order clusters by:
1. Frequency (how many L-XXX documents reference this pattern)
2. Impact (High > Medium > Low — infer from severity or title language)

### Step 5 — Generate recommendations

For each cluster with 2+ occurrences, produce one concrete prevention action:
- A convention change, checklist item, or tooling suggestion
- Reference the specific L-XXX documents that support it

### Step 6 — Write LEARNING-SUMMARY

Use `./assets/learning-aggregator-template.md`. Determine the next version number by checking existing LEARNING-SUMMARY files.

## Output naming

`docs/03-quality/learning/LEARNING-SUMMARY-v{N}.md` where `N` is incremented from the last existing summary (start at v1 if none exist).
