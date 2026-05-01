# Model Assignment — Orquestrum Pipeline

Consolidated reference for which LLM model each agent and skill uses, with justification.

The goal is proportional to the level of reasoning required: more expensive models where ambiguity and deep reasoning are critical; mechanical models where output is structured and predictable.

---

## Provider Profiles

Models are organized in three tiers. Use `--provider <name>` with `convert.py` to generate integrations for a specific provider.

| Tier | `claude` | `copilot` | `glm` | When to use |
|------|----------|-----------|-------|-------------|
| **Deep** | `anthropic/claude-opus-4-7` | `github-copilot/claude-opus-4.7` | `zai-coding-plan/glm-5.1` | Requirements elicitation, trade-off analysis, inference from code |
| **Sharp** | `anthropic/claude-sonnet-4-6`¹ | `github-copilot/claude-opus-4.6` | `zai-coding-plan/glm-5-turbo` | Threat modeling, security analysis — structured reasoning with elevated quality |
| **Balanced** | `anthropic/claude-sonnet-4-6` | `github-copilot/claude-sonnet-4.6` | `zai-coding-plan/glm-4.7` | Structured design, code review, validation, decomposition |
| **Mechanical** | `anthropic/claude-haiku-4-5-20251001` | `github-copilot/claude-haiku-4.5` | `zai-coding-plan/glm-4.5-air` | Release formatting, term definition, operational doc updates |

¹ No intermediate Claude model available; `sharp` maps to `balanced` for `claude` provider.

Canonical source files reference models without provider prefix (e.g. `claude-opus-4-7`). The `convert.py` script resolves the full model ID at conversion time based on the selected provider.

> **Modelo candidato — roadmap:** `zai-coding-plan/glm-5-turbo` (GLM, entre balanced e deep) não tem tier mapeado na versão atual. Será avaliado como tier `sharp` no roadmap de parâmetros. Ver `docs/MODELS.md` seção roadmap abaixo.

---

## Assignment by Tier

### Deep — Primary Agents

| Agent | Justification |
|-------|--------------|
| `helm` | Meta-orchestrator; tier error = cascading waste across the entire pipeline |

### Deep — Skills

| Skill | Justification |
|-------|--------------|
| `spec-manager` | Most critical pipeline input; wrong spec = cascading failure across all subsequent artifacts |
| `adr-manager` | Trade-off analysis and technical decision consequences; requires deep reasoning |
| `reverse-spec` | Requirements inference from ambiguous code — weak signal, high error risk |

### Sharp — Primary Agents

| Agent | Justification |
|-------|--------------|
| `cipher` | Threat modeling and OWASP gap analysis; elevated quality needed to avoid missed attack vectors without paying deep-tier cost |

### Balanced — Primary Agents

| Agent | Justification |
|-------|--------------|
| `lore` | Structured orchestration; critical sub-skills (spec, adr) already use deep |
| `forge` | Orchestration; translates SPEC into structured plans; design follows patterns and ADRs |
| `ward` | Structured validation against defined criteria; checklists with reasoning |
| `trace` | Reading + structured categorization of code; critical sub-skills use deep |
| `flux` | Incident triage and routing; classification against known patterns |

### Balanced — Skills

| Skill | Justification |
|-------|--------------|
| `architecture-manager` | Structured design; follows established patterns and accepted ADRs |
| `pattern-manager` | Structured catalog and adoption; selection against known pattern list |
| `epic-manager` | Structured decomposition of SPEC into vertical slices |
| `task-manager` | Structured execution + test case derivation (TDD) from SC-XX |
| `security-manager` | Threat modeling + OWASP gap analysis; structured but requires security reasoning |
| `review-manager` | Security checklist + reasoning about architectural conformance |
| `qa-manager` | Structured Given/When/Then validation; SC-XX → test mapping |
| `learning-manager` | Structured root cause analysis (5 Whys method) |
| `learning-aggregator` | Cross-cutting pattern detection across multiple L-XXX documents |
| `codebase-mapper` | Reading + structured categorization of stack, components and entry points |

### Mechanical — Primary Agents

| Agent | Justification |
|-------|--------------|
| `cast` | Structured triage; changelog and runbook are highly mechanical |

### Mechanical — Skills

| Skill | Justification |
|-------|--------------|
| `glossary-manager` | Domain term extraction and definition — fixed structure, predictable output |
| `changelog-manager` | Release formatting (Keep a Changelog + SemVer) — highly mechanical |
| `runbook-manager` | Operational documentation updates — template-driven, no creativity required |
| `checkpoint-manager` | CHECKPOINT.md writes — purely structural, fixed format |

---

## Estimated Cost per Tier

| Tier | Agents/Skills involved | Active tiers | Note |
|------|----------------------|--------------|------|
| **Tier 0** | task-manager, log | balanced | ~2 balanced calls |
| **Tier 1** | epic-manager, task-manager, qa-manager | balanced | ~5 balanced calls |
| **Tier 2** | full pipeline | deep (spec, adr) + balanced (majority) + mechanical (changelog, runbook, glossary) | ~13 calls; deep concentrated in discovery phase |
