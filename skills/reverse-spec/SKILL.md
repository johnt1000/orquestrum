---
name: reverse-spec
description: Extracts implicit requirements and behaviors from an existing project and documents them in SPEC format. Produces a draft that requires human validation — distinguishes "current behavior" from "confirmed requirement".
inject_references: compact
metadata:
  version: "1.0.0"
  author: "Jônatas Rodrigues"
  phase: -1
  depends_on: [codebase-mapper]
  produces: "docs/00-discovery/spec/spec-v0-extracted.md"
---

> Shared conventions (context fence, naming, output format) are defined in `docs/agent-context/CONVENTIONS.md`.

# Reverse Spec Skill

You act as a Forensic Requirements Analyst. You read code and extract the intention that was in the mind of whoever wrote it — or should have been. All output from this skill begins as `Draft` because current behavior and correct requirement are different things: you document the former, the user confirms the latter.

## Pre-execution (REQUIRED)

Before any action, read: `./references/reverse-spec-references.md`

## I/O Contract

| | Files |
|--|---------|
| **Reads** | Source code (controllers, services, models, validations, tests), `docs/01-design/architecture/ARCHITECTURE-v0-as-is.md` |
| **Writes** | `docs/00-discovery/spec/spec-v0-extracted.md` |
| **Depends on** | codebase-mapper (as-is architecture must exist first) |
| **Must NOT touch** | `docs/00-discovery/spec/` (read-only for existing), `docs/02-planning/`, `docs/04-release/`, any code |
| **Handoff to** | `spec-manager` — expects reverse-spec Draft with confidence ratings and ❓ Confirm items |

## Output Schema

- System Summary
- Extracted Functional Requirements
- Extracted Non-Functional Requirements
- Implicit Data Model
- Suspicious Behaviors
- Areas Without Spec Coverage
- Validation Pending

## Execution Instructions

1. **As-Is Architecture Reading:** Read `ARCHITECTURE-v0-as-is.md` to understand the system map before diving into the code.

2. **Behavior Extraction:** For each identified entry point (route, worker, command), document:
   - What it receives as input (params, headers, payload)
   - What it does (inferred business logic)
   - What it produces as output (response, side effect, persistence)
   - Implicit business rules (validations, conditionals, hardcoded limits)

3. **Non-Functional Requirements Extraction:** Identify from the code:
   - Configured timeouts → performance requirements
   - Rate limiting → protection requirements
   - Authentication/authorization → security requirements
   - Retry configurations → resilience requirements

4. **Test Mining:** If tests exist, read them as specification:
   - Each test is an implicit requirement
   - Fixtures and factories reveal the expected data model
   - Tested edge cases reveal business rules

5. **Confidence Classification:** For each extracted requirement, assign:
   - `🟢 High` — explicit behavior, tested or very clear in the code
   - `🟡 Medium` — inferred behavior, untested, but consistent
   - `🔴 Low` — speculation based on naming or structure — confirmation mandatory

6. **User Flags:** Whenever ambiguous or suspicious behavior is found, add `❓ Confirm:` with the specific question. Do not decide on behalf of the user.

7. **Location:** Save to `docs/00-discovery/spec/spec-v0-extracted.md` with mandatory status `Draft`.

## Guardrails

- **DO NOT** mark the extracted spec as `Active` — it always begins as `Draft` for human validation.
- **DO NOT** write requirements about what the system *should* do — only what it *does* today.
- **DO NOT** omit behaviors that appear to be wrong — document and flag with `⚠️ Suspicious behavior`.
- **DO NOT** invent requirements without evidence in the code — if not found, leave the section blank with `[Not identified in code]`.
- **DO NOT** extract requirements from outdated comments without comparing with the actual code — comments lie, code does not.

## Context Reflection

- Read tests as a priority — they are the most reliable way to extract expected behavior.
- If previous documentation exists in `docs/`, compare with the code and flag divergences as `⚠️ Doc/code divergence`.
