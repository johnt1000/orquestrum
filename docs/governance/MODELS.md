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

¹ No intermediate Claude model available; `sharp` maps to `balanced` for `claude` provider. **See "Provider Parity Caveats" below.**

Canonical source files reference models without provider prefix (e.g. `claude-opus-4-7`). The `convert.py` script resolves the full model ID at conversion time based on the selected provider.

> **Modelo candidato — roadmap:** `zai-coding-plan/glm-5-turbo` (GLM, entre balanced e deep) não tem tier mapeado na versão atual. Será avaliado como tier `sharp` no roadmap de parâmetros. Ver `docs/governance/MODELS.md` seção roadmap abaixo.

### Provider Parity Caveats

Not every provider offers four distinct models. When a tier is unavailable, it **silently collapses** to the next-lower tier with the same canonical model ID. This is the single source of truth — every collapse below is matched by an entry in `TIER_COLLAPSES` (`orquestrum/lib/models.py`) and surfaces as a warning in `orquestrum convert` build output when `--provider` is set.

| Provider | Tier requested | Falls back to | Affected agents | Why |
|----------|----------------|---------------|-----------------|-----|
| `claude` | `sharp` | `balanced` (`anthropic/claude-sonnet-4-6`) | `cipher` | No intermediate Anthropic model between `sonnet-4-6` and `opus-4-7`. Cipher runs on the same model as balanced agents. |

**Operator implication:** if you generate the `claude` integration and rely on Cipher for security gating, you are NOT getting an elevated-quality model — you are getting `balanced`. To get true sharp-tier quality, use `--provider copilot` (`claude-opus-4.6`) or `--provider glm` (`glm-5-turbo`).

When new collapses are introduced (model retirements, provider gaps), update **both** `TIER_COLLAPSES` and this table. The lint check ensures the warning fires; this section ensures the operator understands why.

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

---

## Output Cap (`max_tokens`)

Every orchestrator declares a `max_tokens` ceiling in its frontmatter. The cap bounds **output size per LLM call** — runaway generation is the #1 source of unintended cost in deep-tier agents. Caps are conservative and deliberately tight; if a phase legitimately needs more output, split the work or chain skills.

| Agent | max_tokens | Rationale |
|-------|-----------:|-----------|
| `helm`   | 4096 | Meta-orchestrator emits routing decisions + handoff envelopes; tier-2 sessions can carry several decisions in one response |
| `lore`   | 2048 | Phase 0–1 orchestrator delegates heavy work to skills (spec/adr/glossary); own output is short routing + summaries |
| `forge`  | 4096 | Phase 2–3 orchestrator may emit architecture summaries + epic/task envelopes inline before delegating |
| `cipher` | 3072 | Threat-modeling summaries can list multiple findings with mitigations; tighter than forge because security skills carry the bulk |
| `ward`   | 2048 | Quality gate emits review/QA decisions + delegations; substantive content lives in review-manager / qa-manager artifacts |
| `cast`   | 2048 | Release pipeline is mechanical; output is mostly status + version tags |
| `flux`   | 1536 | Triage/routing — short classifications + handoffs |
| `trace`  | 8192 | Onboarding may emit initial codebase map summary inline before delegating to reverse-spec |

> Skills do NOT declare `max_tokens` — they inherit the orchestrator cap when called. If a skill's artifact is approaching the cap, that's a signal to split into multiple files (e.g., per-ADR, per-task) rather than raise the cap.

### Lint enforcement

`orquestrum lint` (logic in `orquestrum/core/lint.py`) requires `max_tokens` on every agent. Missing field is a hard error.
