# Skill Registry

Central reference: every skill, its trigger condition, owning orchestrator, and minimum tier.

Agents use this table to check whether a task requires skill loading before proceeding.

---

## Trigger → Skill → Orchestrator

| Trigger condition | Skill | Orchestrator | Tier min | Phase |
|---|---|---|:---:|:---:|
| Extract or define domain terms | `glossary-manager` | lore | 0 | 0–1 |
| Write or update a SPEC | `spec-manager` | lore | 1 | 0–1 |
| Document a technical decision | `adr-manager` | lore / trace | 1 | 1 / -1 |
| Fast-path combined discovery | `discovery-manager` | lore | 1 | 0 |
| Map an existing codebase | `codebase-mapper` | trace | 1 | -1 |
| Extract behaviors from existing code | `reverse-spec` | trace | 1 | -1 |
| Define or adopt design patterns | `pattern-manager` | forge | 1 | 1 |
| Design system architecture | `architecture-manager` | forge | 2 | 2 |
| Break SPEC into epics | `epic-manager` | forge | 1 | 3 |
| Detail execution tasks | `task-manager` | forge | 0 | 3 |
| Review code for quality and security | `review-manager` | ward | 1 | 4 |
| Validate against SPEC success criteria | `qa-manager` | ward | 1 | 4 |
| Capture lessons from failures | `learning-manager` | ward | 1 | 4 |
| Aggregate patterns across all L-XXX docs | `learning-aggregator` | ward | 1 | 4 |
| Run security analysis (threat modeling, OWASP, deps) | `security-manager` | cipher | 1 | 3.5 |
| Map SPEC SC-XX to E2E scenarios (pre-implementation) | `e2e-manager` | ward / forge | 2 | 3–4 |
| Run E2E regression against target environment | `e2e-manager` | ward | 1 | 4 |
| Generate changelog or release notes | `changelog-manager` | cast | 1 | 5 |
| Write or update operational runbook | `runbook-manager` | cast | 2 | 5 |
| Archive completed tasks and logs | `archive-manager` | cast | 1 | 5 |
| Update session checkpoint | `checkpoint-manager` | all | 0 | any |

---

## Rules

- **Load before execute**: always call `skill(name="<skill-name>")` before producing any artifact the skill governs.
- **Tier minimum**: skills marked Tier 1+ are not invoked in Tier 0 (micro) work unless the agent explicitly escalates.
- **Trace is sequential**: codebase-mapper → reverse-spec → adr-manager → glossary-manager. Order is mandatory.
- **None match?** Proceed without skill loading.
