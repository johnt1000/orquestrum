---
name: incident-postmortem
description: Produces a structured postmortem after a production incident. Captures timeline, root cause analysis, contributing factors, corrective actions, and prevention measures. Distinct from learning-manager — focused on operational incidents, not generic learnings.
inject_references: false
emits_confidence: true
metadata:
  version: "1.0.0"
  author: "Jônatas Rodrigues"
  phase: maintenance
  depends_on: [hotfix-runbook]
  produces: "docs/03-quality/incidents/INC-XXX-{slug}.md"
chain:
  next: learning-manager
  condition: "postmortem complete; learning-manager captures the lasting pattern"
---

# Incident Postmortem Skill

You produce a **blameless postmortem** for a production incident. Distinct from `learning-manager` (which captures any lesson learned): this skill is specifically for incidents — events with measurable production impact, a timeline, and corrective actions.

## I/O Contract

| | Files |
|--|---------|
| **Reads** | `docs/04-release/HOTFIX-*.md` (if hotfix shipped), `docs/CHECKPOINT.md`, monitoring/log evidence (operator pastes or links) |
| **Writes** | `docs/03-quality/incidents/INC-XXX-{slug}.md` |
| **Depends on** | hotfix-runbook (if hotfix was used) or any task that mitigated |
| **Must NOT touch** | code, architecture, SPEC — postmortems analyze, they don't fix |
| **Handoff to** | learning-manager (extract reusable pattern), then archive-manager next cycle |

## Pre-execution

Read the related HOTFIX-*.md if it exists. Read the relevant task logs for the mitigation.

## Execution Flow

1. **Establish timeline** — every event with a timestamp: incident start, detection, escalation, mitigation attempts, resolution, post-incident actions. UTC.
2. **Identify root cause** — apply 5 Whys. Stop when you reach a cause that is **actionable** (not "human error" — that's never a root cause; "missing input validation in handler X" is).
3. **List contributing factors** — what made the incident worse or harder to detect? Monitoring gaps, alert fatigue, runbook missing, on-call rotation.
4. **Define corrective actions** — concrete, owned, with dates. Each action has: owner, due date, success criterion.
5. **Compute prevention measures** — what changes so this class of incident doesn't recur? These are typically architectural, not patches.
6. **Compute attention score** — see Attention Score Emission below.

The postmortem is **blameless**: it focuses on systems, processes, and gaps. Names of individuals appear only as on-call assignments.

## Attention Score Emission

Compute via `orquestrum/lib/attention.py:compute()` with:
- `confidence` — 1.0 if root cause is verified by reproduction; 0.6 if reasoned from logs; 0.3 if speculative
- `inference_depth` — 0 if every timeline entry has direct evidence; 1+ if any reconstructed
- `context_completeness` — fraction of (timeline, root cause, contributing factors, corrective actions, prevention) filled
- `gate_failure_count` — count of corrective actions still without an owner or due date
- `upstream_scores` — `attention_score` of the related HOTFIX (if any)
- `drift_days` — 0 (postmortem is current by definition)

A postmortem with `attention_band: red` indicates the incident is not yet fully understood. Do not chain to `learning-manager` until red bands are addressed.

## Guardrails

- **DO NOT** name individuals as causes. Systems and processes fail; people work within them.
- **DO NOT** mark the postmortem `Resolved` while corrective actions are open.
- **DO NOT** duplicate `learning-manager`'s role — the postmortem is the source; learning-manager extracts the reusable pattern.
- **DO NOT** skip the prevention section because "we already fixed it." The fix mitigates the symptom; prevention addresses the class.
