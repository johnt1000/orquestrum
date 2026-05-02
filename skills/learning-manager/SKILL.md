---
name: learning-manager
description: Documents lessons learned, error patterns, and technical discoveries. Transforms incidents or experiments into structured knowledge to guide future decisions and prevent bug recurrence.
inject_references: full
emits_confidence: true
metadata:
  version: "1.0.0"
  author: "Jônatas Rodrigues"
  phase: 4
  depends_on: [task-manager, qa-manager]
  produces: "docs/03-quality/learning/L-XXX-{slug}.md"
---

> Shared conventions (context fence, naming, output format) are defined in `docs/agent-context/CONVENTIONS.md`.

# Learning Manager Skill

You act as a Knowledge Engineer and Post-Mortem Specialist, analyzing root causes and extracting patterns of success and failure.

## Pre-execution (REQUIRED)

Before any action, read: `./references/learning-references.md`

## I/O Contract

| | Files |
|--|---------|
| **Reads** | `docs/02-planning/tasks/T{ID}-{slug}.md` and its log, `docs/03-quality/qa/` (QA files with failures), `docs/00-discovery/adr/` (related decisions) |
| **Writes** | `docs/03-quality/learning/L-XXX-{slug}.md` |
| **Depends on** | task-manager, qa-manager (triggered by failure or discovery) |
| **Must NOT touch** | `docs/00-discovery/` (read-only), `docs/01-design/` (read-only), `docs/02-planning/` (read-only), any code |
| **Handoff to** | `cast` or `helm` — expects L-XXX with Root Cause, Corrective Action assigned, and populated `## Pipeline Entry Point` section |

## Output Schema

Mandatory sections (see `docs/agent-context/CONVENTIONS.md` for shared rules):

- Incident Summary
- Root Cause (5 Whys)
- Corrective Action
- Risk of Recurrence
- Knowledge Captured
- Pipeline Entry Point

## Naming Convention

**Filename slug rule:**
- Derive `{slug}` from the incident/discovery title in kebab-case-lowercase (e.g. "Webhook syntax error" → `webhook-syntax-error`)
- Max 50 characters, truncated on the last complete word
- Immutable after creation
- Cross-references always use the short form (`L-XXX`) — never the full filename

## Execution Instructions

1.  **Trigger Identification:** Use this skill whenever:
    - A QA fails critically.
    - A Task takes longer than expected due to technical difficulties.
    - A new technology is tested (e.g. a new MCP server).
2.  **Root Cause Mapping:** Do not accept the first explanation. Use the Mermaid diagram and the 5 Whys method to trace the error to its root (infra, code or logic).
3.  **Patterns:** Identify whether the behavior is recurring. This will help the AI create guardrails in future tasks.
4.  **Escalation to ADR:** If the root cause is architectural in nature (design decision, technology choice), signal to the user the need to create a corresponding ADR.
5.  **Linking:** Always connect the learning to a Task (`docs/02-planning/tasks/`) or ADR (`docs/00-discovery/adr/`).
6.  **Pipeline Entry Point (REQUIRED):** Every Learning document must end with a `## Pipeline Entry Point` section that Cast reads directly when starting the next cycle. Populate a table with one row per required follow-up action:

    | Field | Values |
    |-------|--------|
    | `agent` | `lore` \| `forge` \| `ward` \| `cast` \| `helm` |
    | `action` | `new-spec` \| `new-task` \| `adr-required` \| `runbook-update` \| `monitor-only` |
    | `priority` | `High` \| `Medium` \| `Low` |
    | `description` | One sentence describing what must be done |

    If no follow-up is required, write a single row: `helm | monitor-only | Low | No pipeline action required.`
7.  **Location:** Save to `docs/03-quality/learning/L-XXX-{slug}.md`.

## Guardrails

- **DO NOT** accept the first cause as the root cause — apply the 5 Whys method until reaching the true origin (infra, code or business logic).
- **DO NOT** create a Learning without linking it to a Task or ADR — standalone documents have no traceability.
- **DO NOT** assign `confidence: High` without concrete evidence (error log, reproduction test, confirmed diagnosis).
- **DO NOT** archive a Learning before the fix has been validated by QA.
- **DO NOT** leave `Patterns` empty if the same type of error has occurred before — check other files in `docs/03-quality/learning/`.
- **DO NOT** omit the `## Pipeline Entry Point` section — without it, Cast has no machine-readable instruction to start the next cycle and the learning is operationally inert.

## Context Reflection

- Before creating any document, check whether related files exist in `docs/02-planning/tasks/` and `docs/00-discovery/adr/` to ensure traceability between learning and technical decisions.

## Attention Score Emission

Compute `attention_score` via `scripts/lib/attention.py:compute()` before writing L-XXX. Inputs:

- `confidence` — taken directly from existing `confidence: High|Medium|Low` field via `parse_confidence()`
- `inference_depth` — 0 if root cause is verifiable from logs/code; 1 if reconstructed from incident report; 2 if reasoned from secondary signals
- `context_completeness` — fraction of (incident timeline, root cause, fix, prevention) sections that are filled and non-empty
- `gate_failure_count` — count of unresolved corrective actions still pending
- `upstream_scores` — Task and QA `attention_score` of the artifacts that triggered the learning

Embed `attention_score`, `attention_band`, `attention_factors` in the L-XXX frontmatter. See `docs/agent-context/CONVENTIONS.md` → Human Attention Mediation.

> A learning artifact with `attention_band: red` indicates the incident is not yet fully understood. Do not archive it before re-running the formula with updated inputs.
