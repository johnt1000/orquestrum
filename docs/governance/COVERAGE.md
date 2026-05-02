# Coverage Matrix

Maps every dev-team scenario to the orchestrator(s) and skill(s) that handle it. Used to validate that the 8-orchestrator surface stays sufficient before proposing a 9th.

If a row is marked **Gap**, either a skill is missing or an existing orchestrator needs hardening. Adding a new orchestrator is the **last** option — extending an existing skill chain is preferred.

---

## Scenario × Capability matrix

| Scenario | Primary orchestrator | Skills involved | Verdict | Gap closer |
|----------|---------------------|----------------|:-------:|------------|
| Greenfield feature, full pipeline | Helm → Lore → Forge → Cipher → Ward → Cast | spec, adr, architecture, epic, task, review, qa, security, changelog, runbook, archive | 🟢 Strong | — |
| Bug triage from production | Flux → Forge | (triage), task | 🟡 OK | Add `incident-postmortem` (P5) |
| Hotfix release (skip full pipeline) | Flux → Cast | hotfix-runbook (new), changelog, runbook | 🟢 with P5 | `hotfix-runbook` skill |
| Incident response (live ongoing) | Flux | incident-postmortem (new) | 🟢 with P5 | `incident-postmortem` skill |
| Rollback to prior release | Cast | rollback-manager (new), runbook | 🟢 with P5 | `rollback-manager` skill |
| Performance regression | Ward | performance-manager (new), qa | 🟢 with P5 | `performance-manager` skill |
| Data migration (schema change) | Forge | data-migration-manager (new), task, security | 🟢 with P5 | `data-migration-manager` skill |
| Security audit ad-hoc | Cipher | security | 🟢 Strong | — |
| Onboarding to existing codebase | Trace | codebase-mapper, reverse-spec, adr, glossary | 🟢 Strong | — |
| Architecture review (no code change) | Helm → Lore | adr, architecture | 🟢 Strong | — |
| Tech-debt sweep (refactor) | Forge | epic, task, review | 🟢 Strong (T0/T1, no tier elevation) | — |
| Docs-only change | Forge → Cast | task, runbook, changelog | 🟢 Strong | — |
| Spike / experiment | Lore → Forge | spec (light), task, learning | 🟢 Strong | — |
| Release artifact regeneration | Cast | changelog, runbook, archive | 🟢 Strong | — |
| Cross-team handoff | Helm | (orchestration only) | 🟢 Strong | — |

---

## What we explicitly chose NOT to add

- **`devops-manager` orchestrator.** CI/CD, infra, deploys → these are implementation concerns. The 8 orchestrators delegate to specialized agents from `agency-agents` (e.g. `devops-engineer`, `cloud-architect`) at task-execution time. Adding a meta-orchestrator for them would duplicate routing.
- **`data-engineer` orchestrator.** Same logic — Forge delegates to `data-engineer`/`data-architect` agents from agency-agents when tasks require it. The new `data-migration-manager` skill formalizes the migration-specific path.
- **`incident-commander` orchestrator.** Flux + new `incident-postmortem` skill covers it. A separate orchestrator would fragment maintenance work.
- **`product-manager` orchestrator.** Lore already governs product strategy / discovery / specs.

---

## When a 9th orchestrator IS justified

Only when:
1. A scenario consistently requires **multiple new skills** that don't fit any current orchestrator's domain.
2. The new domain has its own gates and handoff envelope.
3. Routing pressure on an existing orchestrator is measurably high (Helm fast-path keeps misfiring, or one orchestrator owns >40% of all skill calls).

Until then: add skills, expand existing orchestrators.

---

## How to update this matrix

When a new scenario emerges:
1. Add the row.
2. Decide: extend a skill, add a new skill, or expand an orchestrator? In that order.
3. If you add an orchestrator, document the rationale in this doc and in `docs/governance/MODELS.md` (tier assignment).
4. Re-run `orquestrum lint` and the parity tests (`orquestrum audit parity`).
