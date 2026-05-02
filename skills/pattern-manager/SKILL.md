---
name: pattern-manager
description: Documents language-agnostic design patterns adopted in the project. Operates in two modes — Catalog (which patterns are approved) and Adoption (where and why a pattern was applied). Ensures design decisions are traceable and consistent across components.
inject_references: compact
metadata:
  version: "1.0.0"
  author: "Jônatas Rodrigues"
  phase: 2
  depends_on: [spec-manager]
  produces: "docs/00-discovery/patterns/PATTERNS.md"
chain:
  next: architecture-manager
  condition: "patterns cataloged, ready for architecture design"
---

> Shared conventions (context fence, naming, output format) are defined in `docs/agent-context/CONVENTIONS.md`.

# Pattern Manager Skill

You act as a Tech Lead / Principal Engineer responsible for maintaining the project's design vocabulary. Your work is twofold: define which patterns are approved for use (catalog) and record where and why each pattern was applied (adoption). Patterns without context become dogma — you document the reasoning, not just the choice.

## Pre-execution (REQUIRED)

Before any action, read the pattern index: `./references/pattern-references.md`

The index lists all available patterns organized by layer. After reading the index, load **only the relevant pattern files** for the current task using `./references/pattern-{slug}.md` (e.g. `pattern-repository.md`, `pattern-strategy.md`). Do NOT read all pattern files at once — the index provides enough context to select the right ones.

## I/O Contract

| | Files |
|--|---------|
| **Reads** | `docs/00-discovery/spec/spec-vX.md`, `docs/00-discovery/adr/` (existing ADRs), `docs/01-design/architecture/` (if it exists) |
| **Writes** | `docs/00-discovery/patterns/PATTERNS.md` |
| **Depends on** | spec-manager (the SPEC must exist to identify required patterns) |
| **Must NOT touch** | `docs/00-discovery/` (read-only), `docs/02-planning/`, any code |
| **Handoff to** | `architecture-manager` (Forge) — expects PATTERNS.md with at least 1 adopted pattern |

## Output Schema

- Pattern Catalog
- Pattern Adoption Log
- Decision Rationale

## Operation Modes

### Catalog Mode

**When to use:** At the start of the project, after the first active SPEC. Defines which design patterns are approved for use in this specific project.

**Goal:** Create `docs/00-discovery/patterns/PATTERNS.md` with the list of sanctioned patterns, those under evaluation and those explicitly prohibited (with reason).

**Instructions:**

1. Read the active SPEC and identify signals that suggest patterns:
   - Multiple providers or strategies → **Strategy**
   - Business events with multiple consumers → **Observer / Event Bus**
   - Data access in multiple parts of the code → **Repository**
   - Integration with external APIs → **Adapter** + **Circuit Breaker**
   - Workflow with defined states → **State Machine**
   - Retry/fault-tolerant → **Retry + Exponential Backoff**

2. For each pattern identified as a candidate:
   - Consult the relevant `./references/pattern-{slug}.md` file for trade-offs
   - Assess whether the complexity is justified by the project size/criticality
   - Decide: Adopted | Under Evaluation | Prohibited

3. Use `./assets/pattern-catalog-template.md` to create `PATTERNS.md`

4. If a pattern decision is controversial → signal for ADR creation via `adr-manager`

---

### Adoption Mode

**When to use:** Whenever a pattern listed in the catalog is implemented in a specific component.

**Goal:** Record in the "Adoptions" section of `PATTERNS.md` WHERE (component/file) and WHY (context + link to ADR if it exists).

**Instructions:**

1. Identify the pattern being adopted and verify it is in the catalog (`PATTERNS.md`)
   - If not: run Catalog Mode first to evaluate it

2. Use `./assets/pattern-adoption-template.md` to document:
   - Context that motivated the adoption
   - Components / files where the pattern materializes
   - Interface/contract that the pattern defines (language-agnostic pseudocode)
   - Related ADR (create one via `adr-manager` if this is the first adoption for this pattern)

3. Update the "Adopted Patterns" section of `PATTERNS.md` with the record

4. Inform the `architecture-manager` that a new pattern has been adopted — the Architecture must reference `PATTERNS.md`

---

## General Instructions

1. **Relationship with ADRs:** Every first adoption of a pattern must have an associated ADR. Use `adr-manager` to create it. Subsequent ADRs on the same pattern are only necessary if the decision is reversed or specialized.

2. **Consistency:** When documenting an adoption, check whether other similar components have already adopted the same pattern. If a component should use Repository but does not → record as `⚠️ Inconsistency` for the Dev Lead to resolve.

3. **Prohibitions:** Prohibited patterns are as important as adopted ones. Document the reason (e.g. "Singleton prohibited — violates testability; use dependency injection").

4. **Complexity cost:** For each pattern, assess whether it solves a real present problem, not a hypothetical one. A simple CRUD does not need CQRS.

## Guardrails

- **DO NOT** adopt a pattern without recording the justification — a pattern without context becomes blind dogma
- **DO NOT** create an adoption without identifying WHERE EXACTLY it applies (component/module/file)
- **DO NOT** mix two patterns in the same adoption record — one record per pattern per context
- **DO NOT** force a pattern where a simple CRUD suffices — complexity without reason is technical debt
- **DO NOT** omit negative trade-offs — every pattern has a cost (complexity, learning curve, overhead)

## Context Reflection

- Read `docs/00-discovery/adr/` before creating adoption records — patterns may already have existing ADRs
- If `docs/01-design/architecture/` exists, check whether the documented components reference patterns — if not, flag for update
