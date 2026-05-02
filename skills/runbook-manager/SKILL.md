---
name: runbook-manager
description: Creates and maintains operational system documentation. Documents deploy, rollback, health check, backup, and diagnostic procedures for the production environment. Ensures any agent or human can operate the system without relying on memory.
inject_references: full
metadata:
  version: "1.0.0"
  author: "Jônatas Rodrigues"
  phase: 5
  depends_on: [architecture-manager, changelog-manager]
  produces: "docs/04-release/RUNBOOK.md"
---

> Shared conventions (context fence, naming, output format) are defined in `docs/agent-context/CONVENTIONS.md`.

# Runbook Manager Skill

You act as an SRE (Site Reliability Engineer) and DevOps Engineer, ensuring that the operational knowledge of the system is documented clearly, actionably and safely.

## Pre-execution (REQUIRED)

Before any action, read: `./references/runbook-references.md`

## I/O Contract

| | Files |
|--|---------|
| **Reads** | `docs/01-design/architecture/ARCHITECTURE-vX.md` (components and infrastructure), `docs/04-release/RELEASE-vX.Y.Z.md` (what was delivered in the current release) |
| **Writes** | `docs/04-release/RUNBOOK.md` (updated each release) |
| **Depends on** | architecture-manager, changelog-manager |
| **Must NOT touch** | `docs/00-discovery/`, `docs/01-design/`, `docs/02-planning/`, `docs/03-quality/`, any code |
| **Handoff to** | end of pipeline (Cast) — expects RUNBOOK.md with deploy steps and rollback procedure |

## Output Schema

- Environment Variables
- Deploy Steps
- Rollback
- Health Checks
- Log Reading
- Common Problems

## Execution Instructions

1. **Component Mapping:** Read the architecture document and list all components that require operational procedures (containers, services, databases, n8n workers, etc.).
2. **Mandatory Procedures:** For each relevant component, document: Deploy, Rollback, Health Check, Log Reading.
3. **Environment Variables:** List all required environment variables and secrets — only the **names**, never the values.
4. **Backup and Restore:** Document the data backup procedure and how to perform a restore in the event of failure.
5. **Common Problem Diagnosis:** For each known failure (identified in Learnings), document the symptom, diagnosis and resolution.
6. **Expected Result:** Each step of each procedure must have an "Expected result" — the operator must know whether the step worked or not.
7. **Location:** Save to `docs/04-release/RUNBOOK.md` — single updated file, do not version separately.

## Guardrails

- **DO NOT** document secret values, tokens or passwords — only variable names (e.g. `DATABASE_URL`, not the actual value).
- **DO NOT** write a procedure without the "Expected result" field at each step.
- **DO NOT** omit the Rollback procedure for any Deploy operation.
- **DO NOT** create the runbook without covering at least: Deploy, Rollback, Health Check and Log Reading.
- **DO NOT** describe ambiguous steps — use exact commands where possible (e.g. `docker compose up -d` instead of "bring up the containers").
- **DO NOT** consult the Learning Manager for already-documented problems — reference the Learning directly in the diagnostics section.

## Context Reflection

- Before updating the runbook, check `docs/03-quality/learning/` to incorporate diagnostics from already-documented incidents.
