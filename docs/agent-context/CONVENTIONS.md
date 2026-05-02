# Shared Conventions — Orquestrum Skills

Reference document for conventions shared across all skills. Each SKILL.md inherits these rules by reference — they are not repeated inline.

---

## Context Fence

Every skill operates under a strict context boundary:

- Operate exclusively on files declared under `Reads`
- DO NOT read files from later pipeline phases not listed in the I/O Contract
- DO NOT infer context from files not explicitly listed above

---

## Invalid Format

Invalid format: absence of any mandatory section blocks the next gate.

---

## I/O Contract

Every skill defines a 5-row I/O contract (checkpoint-manager uses 4 rows, without `Handoff to`):

```
| | Files |
|--|---------|
| **Reads** | ... |
| **Writes** | ... |
| **Depends on** | ... |
| **Must NOT touch** | ... |
| **Handoff to** | ... |
```

---

## Output Schema

The artifact produced by this skill MUST contain the mandatory sections listed in its `## Output Schema` section.

---

## Filename Slug Rule

Shared naming rules for all artifact-producing skills:

- Derive `{slug}` from the artifact title in kebab-case-lowercase
- Max 50 characters for the slug portion, truncated on the last complete word
- Immutable after creation — title or version changes do not rename the file
- Cross-references always use the short form (e.g. `T{ID}`, `E{ID}`, `ADR-XXX`, `spec-vX`) — never the full filename

Skill-specific exceptions (Tier-0 micro-log, architecture v0, review/QA `{ref}` prefix) are documented in each skill's `## Naming Convention` section.

---

## Pre-execution

Every skill (except checkpoint-manager) reads its reference file before executing:

```
Before any action, read: `./references/{name}-references.md`
```

---

## Context Reflection

Every skill defines its own context reflection — which paths to check for consistency before creating artifacts. This is skill-specific and not shared.

---

## Checkpoint-Manager Ownership

`checkpoint-manager` is a cross-cutting skill. Its ownership rules:

- **Flux** — reads CHECKPOINT.md at the start of every maintenance cycle to detect drift and stale artifacts
- **Cast** — writes CHECKPOINT.md after each release (archive-manager finalizes it)
- **Cipher** — writes SEC findings to CHECKPOINT.md when a gate is blocked
- All other orchestrators — may read CHECKPOINT.md for context; must not write it except via checkpoint-manager

---

## Artifact Confidence Fields

All artifact-producing skills should include confidence metadata where applicable. These fields are optional at Echo level, recommended at Pulse, and required at Chronicle.

### Requirements (spec-manager)

Each requirement row in the `## Requirements` table may carry:

```
| ID | Priority | Requirement | confidence | source |
|----|----------|------------|------------|--------|
| RF-01 | M | ... | high | interview |
```

`confidence`: `high` / `medium` / `low`
`source`: `interview` / `code` / `inference` / `standard`

### Architectural Decisions (adr-manager)

ADR frontmatter may include:

```yaml
confidence_rationale: "Decision backed by load test results from 2026-04-10"
```

### Artifact Freshness (all artifact-producing skills)

Artifacts may include the following metadata block in their frontmatter:

```yaml
last_validated: YYYY-MM-DD
validated_by: "{agent or human}"
drift_risk: low # low | medium | high
```

`drift_risk` escalates to `high` when: (a) artifact is >30 days without revalidation, or (b) referenced files were modified since `last_validated`. Flux signals to Helm when drift_risk is `high` at the start of a new cycle.

---

## LLM Self-Audit

Every skill appends a `## ⚠ Audit Warnings` section before completing its handoff. The section is produced by a secondary self-check prompt that verifies:

- All mandatory placeholders (`{...}`) replaced
- No contradictions with accepted ADRs
- All required fields present and non-empty

If no warnings are found, the section contains: `No warnings — artifact passed self-audit.`

This section is consumed by Ward's review-manager for cross-artifact consistency checks.

---

## Cache Segmentation Markers

Canonical agent and skill prompts may declare which body regions are **stable** (rarely change between runs) versus **volatile** (change per session). Adapters that support segmented prompt caching (e.g. Anthropic's `cache_control: ephemeral`) translate these markers into native cache directives. Adapters that do not support caching strip the markers without behavior change.

### Convention

Use HTML comments to wrap regions:

```markdown
<!-- cache:stable -->
{content that changes rarely — agent role description, governance refs, skill triggers}
<!-- /cache:stable -->

<!-- cache:volatile -->
{content that changes per session — recent context, dynamic state}
<!-- /cache:volatile -->
```

Default (no markers): treated as **volatile** — no cache benefit but also no risk of caching dynamic content.

### Rules

1. **Markers live only in canonical source** (`agents/`, `skills/`, `docs/`). Never in runtime artifacts under `.orquestrum/metrics/` or in tool-installed paths.
2. **Stable blocks must be deterministic.** No timestamps, no session IDs, no per-tier branching inline. If a block contains conditional content, it is volatile.
3. **Markers are stripped for adapters without cache support.** Output is character-identical save for the comment removal.
4. **Hit-rate priority** (cache the highest-leverage first):
   - Governance docs (`docs/agent-context/CONVENTIONS.md`, `docs/agent-context/SDLC.md`, `docs/governance/MODELS.md`) — read every session
   - Agent role/preamble blocks — same agent fires repeatedly within a session
   - Skill `references/*.md` resolved via `inject_references: full` — large payload, low churn
5. **Do NOT cache:** few-shot examples (high churn), user-provided artifacts, anything in `.orquestrum/metrics/`.

### Adapter behavior

| Adapter | Today's behavior |
|---------|------------------|
| `claude-code` | Markers preserved as comments; Anthropic backend auto-caches stable system prompts ≥1024 tokens. Native segmented caching may be added when Claude Code exposes the API. |
| `opencode` | Markers stripped (no cache support today). |
| `cursor`, `aider`, `windsurf` | Markers stripped; static RAG already shrinks per-session payload. |

The single source of truth for adapter cache support is `_segment_for_cache()` in `orquestrum/core/convert.py`. When a tool gains native cache support, only that adapter changes — canonical sources remain untouched.

---

## Human Attention Mediation

Every artifact-emitting skill computes a deterministic **attention score** (0–100, lower = more attention required) and embeds it in the artifact's frontmatter. The score derives from countable signals — never from another LLM call. LLMs systematically over-rate their own outputs; the formula is the guard.

### Frontmatter convention

```yaml
attention_score:   73          # int [0, 100]
attention_band:    yellow       # green (80-100) | yellow (50-79) | red (0-49)
attention_factors: [drift_days:42, inference_depth:2]   # list of dominant deductions
```

The aggregator artifact `MEDIATION.md` (emitted by `checkpoint-manager` per session) lists every artifact with its score sorted ascending — the lowest scores demand attention first.

### Bands

- **🟢 80–100 (green)** — routine review.
- **🟡 50–79 (yellow)** — focused review on the listed factors.
- **🔴 0–49 (red)** — block merge / escalate to senior approval.

### Inputs and weights

The formula lives in `orquestrum/lib/attention.py`. Skills MUST NOT reimplement or override the weights. Inputs:

| Input | Source | Deduction (max) |
|-------|--------|----------------:|
| `confidence` (0..1) | from artifact's confidence rating field | 25 × (1 − confidence) |
| `drift_days` | days since `last_validated` | min(20, drift / 2) |
| `inference_depth` (0..3) | 0 verbatim, 1 summarized, 2 inferred, 3 speculative | 10 × depth |
| `gate_failure_count` | gates that failed during emission | 5 × N |
| `context_completeness` (0..1) | required-fields-filled / required-fields-total | 15 × (1 − completeness) |
| `test_coverage_delta` | +1 bonus when coverage improved | +5 if positive |

### Propagation rule

A downstream artifact's score is **capped** at `min(own_score, max(upstream_scores) + 10)`. In words: a yellow input contaminates the chain — downstream artifacts cannot become green until the upstream concern is resolved.

**Override mechanism:** an explicit `human_review.md` artifact with sign-off resets the cap for declared dependents. The override is a manual act; no skill self-clears its inputs.

### Where it is implemented

| Skill | What it emits |
|-------|--------------|
| `review-manager` | computes scores for each REVIEW artifact |
| `qa-manager` | computes scores for each QA artifact |
| `security-manager` | computes scores for each SEC finding (criticality maps to confidence) |
| `learning-manager` | computes scores for each LEARNING artifact |
| `checkpoint-manager` | aggregates all per-session scores into `MEDIATION.md` |

Skills that emit confidence-bearing artifacts must declare `emits_confidence: true` in their frontmatter (lint-enforced).

### What this is NOT

- Not a quality score from another LLM.
- Not a tunable per-user setting (operators tune **thresholds**; the framework tunes **weights**).
- Not a hard gate (red ≠ blocked merge automatically; the framework signals, the human decides).
- Not a substitute for human review on critical paths — it directs attention, it doesn't replace judgment.
