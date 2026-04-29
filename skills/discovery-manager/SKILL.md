---
name: discovery-manager
description: Combined Phase 0-1 skill. Chains glossary creation with spec writing for efficient discovery.
version: "1.0.0"
phase: "0-1"
depends_on: []
produces: "docs/00-discovery/glossary/GLOSSARY.md, docs/00-discovery/spec/spec-vX-{slug}.md"
inject_references: false
chain:
  next: adr-manager
  condition: "SPEC created or updated, architectural decisions needed"
---

You act as the Discovery Manager — combining glossary creation and spec writing into a single efficient flow.

> Shared conventions in `docs/CONVENTIONS.md`.

## Pre-execution (REQUIRED)

Before any action, read: `skills/glossary-manager/SKILL.md` and `skills/spec-manager/SKILL.md`

## Execution Flow

### Step 1: Glossary (Phase 0)

Execute the glossary-manager flow:
1. Read `skills/glossary-manager/references/glossary-references.md`
2. Extract domain terms from the project context
3. Create or update `docs/00-discovery/glossary/GLOSSARY.md` using `skills/glossary-manager/assets/glossary-template.md`
4. Verify at least 5 terms exist

If glossary already exists and is current, skip to Step 2.

### Step 2: SPEC (Phase 1)

Execute the spec-manager flow:
1. Read `skills/spec-manager/references/spec-references.md`
2. Read the glossary produced in Step 1
3. Create `docs/00-discovery/spec/spec-v1-{slug}.md` using `skills/spec-manager/assets/spec-template.md`
4. Verify all mandatory sections are present

### Handoff

After both steps complete, report to Lore:
- Glossary: path + term count
- SPEC: path + status
- Suggested ADR topics (if any architectural decisions are implicit)
