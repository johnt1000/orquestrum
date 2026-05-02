---
name: architecture-manager
description: Manages and updates high-level architecture documents. Maintains the systemic view of the project, flow diagrams, and traceability between specifications and technical decisions (ADRs).
inject_references: compact
inject_fewshot: compact
metadata:
  version: "1.0.0"
  author: "Jônatas Rodrigues"
  phase: 2
  depends_on: [spec-manager, adr-manager]
  produces: "docs/01-design/architecture/ARCHITECTURE-vX-{slug}.md"
---

> Shared conventions (context fence, naming, output format) are defined in `docs/agent-context/CONVENTIONS.md`.

# Architecture Manager Skill

You act as a Solutions Architect, ensuring that the macro vision of the system is always synchronized with code changes and point-in-time decisions.

## Pre-execution (REQUIRED)

Before any action, read: `./references/arch-references.md`

Additional references (read ONLY when needed):
- `./references/arch-fewshot.md` — read on first invocation per session, or when uncertain about output format
- `./references/arch-frontend.md` — read ONLY when the task involves UI, frontend, or mobile components

## I/O Contract

| | Files |
|--|---------|
| **Reads** | `docs/00-discovery/spec/spec-vX-{slug}.md`, `docs/00-discovery/adr/` (all accepted ADRs) |
| **Writes** | `docs/01-design/architecture/ARCHITECTURE-vX-{slug}.md` |
| **Depends on** | spec-manager, adr-manager |
| **Must NOT touch** | `docs/00-discovery/` (read-only), `docs/02-planning/`, any code |
| **Handoff to** | `epic-manager` (Forge) — expects ARCHITECTURE-vX with diagram and component map |

## Output Schema

- Context
- Architecture Diagram
- Component Map
- Technology Decisions
- Integration Points
- Scalability Considerations
- References

## Naming Convention

**Filename slug rule:**
- Derive `{slug}` from the system/feature name in kebab-case-lowercase (e.g. "Core Chat Platform" → `core-chat-platform`)
- Max 50 characters, truncated on the last complete word
- Immutable after creation — version increments keep the same slug (e.g. `ARCHITECTURE-v1-core-chat-platform.md` → `ARCHITECTURE-v2-core-chat-platform.md`)
- Cross-references always use the short form (`ARCHITECTURE-vX`) — never the full filename
- **Exception:** `ARCHITECTURE-v0-as-is.md` produced by `codebase-mapper` keeps that exact name — do not add a slug.

## Execution Instructions

1. **Traceability:** When creating an architecture document, check whether related ADRs exist in `docs/00-discovery/adr/` and list them in the `Decisions` section.
2. **Versioning (vX):** If a previous file exists, increment the version (e.g. v1 to v2) when a component or flow changes. Text corrections or addition of ADRs do not justify a new version — update in-place. The slug remains the same across versions.
3. **Mermaid Diagrams:** Do not keep the static diagram from the template. You must generate a `graph TD` or `sequenceDiagram` that reflects the technical reality discussed in the chat or in the project files.
4. **Field Population:**
   - **Overview:** Must be an explanation for both technical and non-technical stakeholders.
   - **Data Flow:** Describe how information enters the system, is processed, and where it is persisted.
5. **Save Location:** Save to `docs/01-design/architecture/ARCHITECTURE-vX.md`.

## Guardrails

- **DO NOT** use the generic diagram from the template — always replace it with a diagram that reflects the real components of the project.
- **DO NOT** update `Components` without simultaneously updating the `System Diagram` — both must always be in sync.
- **DO NOT** create a new version (v2, v3) for minor changes — increment the version only when components or flows are added or removed.
- **DO NOT** leave the `Decisions` section empty if there are accepted ADRs — every architectural decision must be traceable.
- **DO NOT** mix asynchronous flows (queues, webhooks) and synchronous flows (REST) in the same diagram without visual distinction.

## Context Reflection

- Before creating any document, check whether related files exist in `docs/00-discovery/spec/` and `docs/00-discovery/adr/` to ensure consistency between Spec, ADR and Architecture.
