# Model Assignment — Orquestrum Pipeline

Consolidated reference for which LLM model each agent and skill uses, with justification.

The goal is proportional to the level of reasoning required: more expensive models where ambiguity and deep reasoning are critical; mechanical models where output is structured and predictable.

---

## Available Models

| Model | Profile | When to use |
|-------|---------|------------|
| `claude-opus-4-6` | Deep reasoning, ambiguity resolution, creative synthesis | Requirements elicitation, trade-off analysis, inference from code |
| `claude-sonnet-4-6` | Balanced, non-trivial structured tasks | Structured design, code review, validation, decomposition |
| `claude-haiku-4-5-20251001` | Fast, mechanical, template-driven | Release formatting, term definition, operational doc updates |

---

## Primary Agents

| Agent | Model | Justification |
|-------|-------|--------------|
| `helm` | `claude-opus-4-6` | Meta-orchestrator; tier error = cascading waste across the entire pipeline |
| `lore` | `claude-sonnet-4-6` | Structured orchestration; critical sub-skills (spec, adr) already use opus |
| `forge` | `claude-sonnet-4-6` | Orchestration; translates SPEC into structured plans; design follows patterns and ADRs |
| `ward` | `claude-sonnet-4-6` | Structured validation against defined criteria; checklists with reasoning |
| `cast` | `claude-haiku-4-5-20251001` | Structured triage; changelog and runbook are highly mechanical |
| `trace` | `claude-sonnet-4-6` | Reading + structured categorization of code; critical sub-skills use opus |

---

## Skills

### Opus — Deep Reasoning

| Skill | Model | Justification |
|-------|-------|--------------|
| `spec-manager` | `claude-opus-4-6` | Most critical pipeline input; wrong spec = cascading failure across all subsequent artifacts |
| `adr-manager` | `claude-opus-4-6` | Trade-off analysis and technical decision consequences; requires deep reasoning |
| `reverse-spec` | `claude-opus-4-6` | Requirements inference from ambiguous code — weak signal, high error risk |

### Sonnet — Structured Non-Trivial

| Skill | Model | Justification |
|-------|-------|--------------|
| `architecture-manager` | `claude-sonnet-4-6` | Structured design; follows established patterns and accepted ADRs |
| `pattern-manager` | `claude-sonnet-4-6` | Structured catalog and adoption; selection against known pattern list |
| `epic-manager` | `claude-sonnet-4-6` | Structured decomposition of SPEC into vertical slices |
| `task-manager` | `claude-sonnet-4-6` | Structured execution + test case derivation (TDD) from SC-XX |
| `review-manager` | `claude-sonnet-4-6` | Security checklist + reasoning about architectural conformance |
| `qa-manager` | `claude-sonnet-4-6` | Structured Given/When/Then validation; SC-XX → test mapping |
| `learning-manager` | `claude-sonnet-4-6` | Structured root cause analysis (5 Whys method) |
| `codebase-mapper` | `claude-sonnet-4-6` | Reading + structured categorization of stack, components and entry points |

### Haiku — Mechanical / Template-Driven

| Skill | Model | Justification |
|-------|-------|--------------|
| `glossary-manager` | `claude-haiku-4-5-20251001` | Domain term extraction and definition — fixed structure, predictable output |
| `changelog-manager` | `claude-haiku-4-5-20251001` | Release formatting (Keep a Changelog + SemVer) — highly mechanical |
| `runbook-manager` | `claude-haiku-4-5-20251001` | Operational documentation updates — template-driven, no creativity required |

---

## Model Propagation

Each primary agent defines its sub-skill models in the `MODEL PER SUB-SKILL` section of its file. The propagation flow is:

```
Helm — The Architect (opus)
  ↓ instructs orchestrator model
Lore — Product Strategist (sonnet)
  ↓ instructs sub-skill model
  ├── glossary-manager (haiku)
  ├── spec-manager (opus)
  └── adr-manager (opus)

Forge — Dev Lead (sonnet)
  ├── architecture-manager (sonnet)
  ├── pattern-manager (sonnet)
  ├── epic-manager (sonnet)
  └── task-manager (sonnet)

Ward — Quality Lead (sonnet)
  ├── review-manager (sonnet)
  ├── qa-manager (sonnet)
  └── learning-manager (sonnet)

Cast — Ship & Support Lead (haiku)
  ├── changelog-manager (haiku)
  └── runbook-manager (haiku)

Trace — Onboarding Lead (sonnet)
  ├── codebase-mapper (sonnet)
  ├── reverse-spec (opus)
  ├── adr-manager (opus)
  └── glossary-manager (haiku)
```

---

## Estimated Cost per Tier

| Tier | Agents/Skills involved | Active models | Note |
|------|----------------------|--------------|------|
| **Tier 0** | task-manager, log | sonnet | ~2 sonnet calls |
| **Tier 1** | epic-manager, task-manager, qa-manager | sonnet | ~5 sonnet calls |
| **Tier 2** | full pipeline | opus (spec, adr) + sonnet (majority) + haiku (changelog, runbook, glossary) | ~13 calls; opus concentrated in discovery phase |
