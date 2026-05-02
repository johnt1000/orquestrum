# Performance Methodology & Targets

How Orquestrum measures latency, how targets are set, and how regressions are caught. Distinct from `docs/governance/COST.md` (which budgets tokens) and `docs/governance/OBSERVABILITY.md` (which describes runtime metrics).

---

## Why this exists

Cost is tracked in tokens; quality is tracked in attention scores; **performance is tracked in time**. Without a methodology, "fast" is an opinion. With one, "p95 latency 220 ms on staging at 50 rps" is reproducible.

This doc is owned by Ward via the `performance-manager` skill (Phase 5).

---

## What is measured

### Per LLM call (runtime)

`duration_ms` is emitted in every `llm_call` event in `.orquestrum/metrics/events.jsonl`. The dashboard surfaces:
- Mean / p50 / p95 / p99 per tier
- Slow-call tail (calls > 2× p95)
- Time-to-first-token if the adapter exposes it (most don't yet)

### Per skill chain (session)

For chained skills (e.g. `glossary → spec → adr → architecture`), the dashboard computes:
- Wall time end-to-end
- Critical-path time (longest path through chain)
- Idle time between skills (time the orchestrator was thinking but not calling)

### Per build (CI)

`scripts/convert.py` and `scripts/lint.py` should complete in single-digit seconds. CI publishes a build-time histogram. A regression > 50% triggers an investigation.

---

## Target tiers

Targets are **soft** — exceeding them does not block release; it triggers a `performance-manager` artifact and (for Ward) a row in MEDIATION.md.

| Operation | p50 target | p95 target | Source |
|-----------|-----------:|-----------:|--------|
| Tier-0 task (single skill, mechanical tier) | 5 s | 12 s | observed median + 2× |
| Tier-1 epic + task chain | 25 s | 60 s | observed |
| Tier-2 full pipeline (greenfield) | 4 min | 10 min | observed |
| `lint.py` build | 2 s | 5 s | tooling |
| `convert.py --all` | 3 s | 8 s | tooling |
| Parity suite | 8 s | 20 s | tooling |

Targets are reset annually (or after a major model upgrade). When a model tier changes, expect re-baselining.

---

## Methodology for `performance-manager` artifacts

The skill itself documents the protocol; this section is the meta-policy.

### Statistical hygiene

- **Sample size:** N ≥ 3 for any reported metric. N ≥ 30 for tail percentiles (p95, p99). Below 30, report only mean/median + std dev.
- **Warmup:** discard first sample (cold cache). For LLM calls, also discard the first call after a context-cache miss.
- **Statistical significance:** report standard deviation alongside mean. A 5% change inside 1σ noise is not a regression.
- **Environment isolation:** measure on dedicated staging or in a network-isolated local. Co-tenant noise invalidates samples.

### Reporting format

Always include:
- Workload definition (rps, concurrency, dataset size)
- Environment (cloud region, instance type, or local hardware)
- Tool used (k6, hey, ab, custom — name and version)
- Number of samples
- Result table with baseline + current + Δ + statistical verdict

### What NOT to do

- Don't compare across environments (staging numbers vs prod numbers means nothing).
- Don't extract a "p99" from 10 samples. p99 needs ~100+ to be meaningful.
- Don't conflate latency and throughput. Both targets must be checked; one improving while the other regresses is a real regression.
- Don't normalize results across model tiers. A balanced model is allowed to be slower than a mechanical one — they're different products.

---

## Regression handling

When `performance-manager` flags a Critical or High regression:

1. The artifact's `attention_band` is `red`.
2. `learning-manager` chain is triggered to capture the pattern.
3. Either fix-forward (new task) or roll back (`rollback-manager`). Cast decides.
4. The release `runbook-manager` artifact is updated with the regression note for downstream operators.

Medium and Cosmetic regressions are recorded but do not block.

---

## When in doubt

The default verdict is **inconclusive**, not "passed." A noisy or under-sampled run produces an inconclusive PERF artifact, which is itself a signal that the methodology needs more rigor before this metric can be trusted.

Inconclusive ≠ broken. It means we don't know yet. Saying "we don't know" is a feature, not a bug.
