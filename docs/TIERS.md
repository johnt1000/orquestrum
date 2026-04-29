# Pipeline Tiers — Orquestrum

Work classification guide for each job's process level. The goal is proportional to impact: hotfixes don't need a SPEC; architectural features need everything.

> **Note:** This document is a human-readable reference. The Helm agent uses an inline decision matrix for tier classification — this file is no longer read at bootstrap.

---

## The 3 Tiers

```
TIER 0 — Micro      → Task + Log                      (~2 LLM calls)
TIER 1 — Standard   → Epic + Task + Log + QA          (~5 LLM calls)
TIER 2 — Full       → Complete pipeline               (~13 LLM calls)
```

---

## Classification by Activity Type

**Identify the type before applying size criteria.** Some types have override rules that replace the size questions.

| Activity Type | SPEC | ADR | Architecture | Base tier | Size override |
|--------------|------|-----|-------------|----------|---------------|
| New feature | ✅ new | if new decision | if structural change | **2** | — |
| Feature in existing SPEC | update if needed | — | — | **1** | — |
| Bug fix | only if behavior was wrong in SPEC | — | — | **0–1** | yes |
| Refactoring | ❌ never¹ | only if pattern changes | only if structure changes | **0–1** | **ignore file count** |
| Improvement (NFR) | update RNF | if new decision | if structural change | **1** | — |
| Security patch | if interface changes | ✅ recommended | — | **1** | — |
| Dependency upgrade | — | if breaking change | — | **0–1** | — |
| Docs-only | — | — | — | **0** | ignore everything |
| Breaking change / Deprecation | ✅ migration notes | ✅ required | ✅ | **2** | — |

¹ **Refactoring rule:** file count does NOT elevate the tier when the activity is pure refactoring (zero change in observable behavior). A 20-file refactoring remains Tier 1. Only elevates to Tier 2 if it implies a new architectural decision (e.g.: migrating from monolith to modular, introducing a new integration pattern).

---

## Classification Criteria by Size

Apply these questions **after** identifying the type. For Refactoring and Docs-only, ignore the size questions and use the base tier from the table above.

The **first "Yes" answer from top to bottom** determines the minimum tier.

| Question | Yes → Minimum tier |
|---------|-------------------|
| Does it change a public interface, API contract, or database schema? | **Tier 2** |
| Is it a new feature not covered by the existing SPEC? | **Tier 2** |
| Does it require a new architectural decision (new database, framework, or pattern)? | **Tier 2** |
| Does it involve more than 10 files or more than 1 day of work? (except Refactoring) | **Tier 2** |
| Is it a new feature within an already existing SPEC? | **Tier 1** |
| Does it change the database schema without altering the public interface? | **Tier 1** |
| Does it involve 3–10 files or up to 1 day of work? | **Tier 1** |
| None of the above (simple bug fix, config, text, 1–2 files, < 2h) | **Tier 0** |

---

## Artifacts per Tier

| Artifact | Tier 0 | Tier 1 | Tier 2 |
|---------|:------:|:------:|:------:|
| GLOSSARY | — | — | ✅ if new domain |
| SPEC | — | — | ✅ |
| ADR | — | — | ✅ if new decision |
| PATTERNS | — | — | ✅ if new pattern |
| ARCHITECTURE | — | — | ✅ if structural change |
| EPIC | — | ✅ | ✅ |
| TASK | ✅ | ✅ | ✅ |
| LOG | ✅ | ✅ | ✅ |
| REVIEW | — | Optional¹ | ✅ |
| QA | Informal² | ✅ | ✅ |
| LEARNING | — | — | ✅ if critical failure |
| CHANGELOG | — | Accumulates³ | ✅ |
| RUNBOOK | — | — | ✅ if infra change |

**Notes:**
1. Optional in Tier 1: run REVIEW when the task touches security, authentication, payment, or personal data code.
2. Informal in Tier 0: no QA document is created — just confirm the task criterion was met.
3. Accumulates in Tier 1: add to the `[Unreleased]` section of CHANGELOG, without creating a RELEASE document.

---

## Minimum Reading Context per Tier

Reducing unnecessary reads is the primary lever for reducing token cost.

### Tier 0 — Read only:
- Task template (`skills/task-manager/assets/task-template.md`)
- Directly affected code

### Tier 1 — Read only:
- Existing SPEC in `docs/00-discovery/spec/` (active version only)
- Corresponding Epic (if it exists)
- **DO NOT re-read:** ADRs, Architecture, PATTERNS, Glossary

### Tier 2 — Read what is needed for each phase:
- Lore: Glossary + existing SPEC
- Forge: active SPEC + accepted ADRs + PATTERNS
- Ward: active SPEC + Task Artifacts
- Cast: QA Passed + current CHANGELOG

---

## Routing by Tier

### Tier 0 → Forge (direct)
```
Helm classifies as Tier 0
  ↓
forge → task-manager (Task + Log)
  ↓
Informal confirmation that criterion was met
  ↓
Done
```

### Tier 1 → Forge + Ward
```
Helm classifies as Tier 1
  ↓
forge → epic-manager (if epic doesn't exist) → task-manager
  ↓
ward → qa-manager
  ↓
Done (changelog accumulates)
```

### Tier 2 → Full pipeline
```
Helm classifies as Tier 2
  ↓
lore → (glossary) → spec → adr → (pattern)
  ↓
forge → architecture → epic → task
  ↓
ward → review → qa → (learning)
  ↓
cast → changelog → runbook
```

---

## Conditional Gates

Pipeline gates only apply at the corresponding tier:

| Gate | Applies in |
|------|-----------|
| Gate 0→1 (Glossary exists) | Tier 2 only |
| Gate 1→2 (SPEC + ADR exist) | Tier 2 only |
| Gate 2→3 (Architecture exists) | Tier 2 only |
| Gate 3→4 (Task Completed + Artifacts) | Tier 1 and Tier 2 |
| Gate 4→5 (Review Approved + QA Passed) | Tier 2 only |
| Gate 5→Release (Release + Runbook) | Tier 2 only |

---

## Tier Upgrade (Mid-flight)

During execution, the tier can be promoted if something unexpected arises:

| Situation | Promotion |
|-----------|----------|
| Tier 0 Task discovers it needs to change the database schema | Tier 0 → Tier 1 |
| Tier 1 Task discovers the SPEC is incomplete | Tier 1 → Tier 2 |
| Review finds an architectural issue | Any → Tier 2 |

**Rule:** never demote the tier. Only promote.

---

## Quick Examples

| Work | Type | Tier |
|------|------|------|
| Fix typo in error message | Bug / Docs-only | 0 |
| Adjust request timeout in `.env` | Config | 0 |
| Update API docs without changing code | Docs-only | 0 |
| Fix validation bug in a form | Bug | 0–1¹ |
| Rename variables + extract functions in 20 files | Refactoring | 1² |
| Add filter field to existing endpoint | Feature (existing SPEC) | 1 |
| Create new endpoint within already specified feature | Feature (existing SPEC) | 1 |
| Improve response time of critical query | Improvement (NFR) | 1 |
| Add observability metrics | Improvement (NFR) | 1 |
| Fix vulnerability without changing public interface | Security patch | 1 |
| Update dependency with minor breaking change | Dependency upgrade | 1 |
| Integrate new email provider | New feature | 2 |
| Create payment module from scratch | New feature | 2 |
| Migrate authentication from JWT to OAuth | Breaking change | 2 |
| Extract monolith into independent modules | Refactoring + architectural decision | 2³ |

¹ If the bug is in critical business logic: Tier 1. If cosmetic/textual: Tier 0.
² Refactoring ignores file count — base tier is 0–1. Only elevates to 2 if there is a new architectural decision.
³ Refactoring that introduces a new architecture (e.g.: module separation, new integration pattern) elevates to Tier 2.
