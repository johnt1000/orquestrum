---
name: performance-manager
description: Validates performance targets, captures regressions, and produces a performance report tied to a SPEC SC-XX or a release. Complements qa-manager for the dimension of latency, throughput, and resource use. Required when a release touches a hot path or when a regression alert fires.
inject_references: compact
emits_confidence: true
metadata:
  version: "1.0.0"
  author: "Jônatas Rodrigues"
  phase: 4
  depends_on: [qa-manager]
  produces: "docs/03-quality/perf/PERF-{ref}-{slug}.md"
chain:
  next: learning-manager
  condition: "regression confirmed; learning-manager captures pattern"
---

# Performance Manager Skill

You validate performance for a feature or release. Performance is a **quality dimension** alongside correctness and security — qa-manager does not cover it sufficiently because acceptance criteria rarely encode latency/throughput targets.

## When to use

- A SPEC has explicit performance SC (latency p95 < N ms, throughput > N rps, memory < N MB).
- A release modifies a hot path (any code path with > N rps in production).
- A monitoring alert fires for a perf metric.
- Pre-release benchmark required by `runbook-manager`.

## I/O Contract

| | Files |
|--|---------|
| **Reads** | active SPEC (`docs/00-discovery/spec/spec-vX.md`), related QA (`docs/03-quality/qa/QA-{ref}-*.md`), task artifacts (`docs/02-planning/tasks/T{ID}-*.md`) |
| **Writes** | `docs/03-quality/perf/PERF-{ref}-{slug}.md` |
| **Depends on** | qa-manager (functional pass before perf is measured) |
| **Must NOT touch** | code, architecture, SPEC |
| **Handoff to** | learning-manager (if regression), then changelog-manager |

## Execution Flow

1. **Identify targets** — pull every performance SC from the SPEC. If none, derive from the existing baseline (last PERF artifact for the same component).
2. **Define benchmark methodology** — workload, environment, dataset, warmup, sample count, statistical method (p50/p95/p99). State assumptions.
3. **Run benchmark** — capture raw results. The skill does NOT execute the benchmark itself; it documents the protocol and consumes the results provided by the operator/CI.
4. **Compare against baseline** — explicit delta per metric. State whether each metric is improvement, parity (within noise), or regression.
5. **Classify regressions** — Critical (> 50% degradation on hot path), High (> 20%), Medium (> 5%), Cosmetic (< 5% or noisy).
6. **Compute attention score** — regressions deduct.

## Attention Score Emission

Compute via `scripts/lib/attention.py:compute()`:
- `confidence` — 1.0 if benchmark statistically significant (p < 0.05 across N runs); 0.6 if single run; 0.3 if methodology gaps
- `inference_depth` — 0 if measured directly; 1 if estimated from related metrics; 2 if extrapolated
- `context_completeness` — fraction of (targets, methodology, results, comparison, classification) filled
- `gate_failure_count` — count of Critical + High regressions
- `upstream_scores` — QA `attention_score` of artifacts under test
- `drift_days` — `days_since(last_validated)` of the SPEC

A Critical regression caps `attention_band` at red regardless of formula.

## Guardrails

- **DO NOT** report results without methodology — "p95 latency dropped 15%" is meaningless without sample size, environment, and workload.
- **DO NOT** classify a regression based on a single noisy measurement. State the noise band; require N≥3 samples.
- **DO NOT** mark the artifact `Passed` if any Critical regression is open without an explicit waiver from Helm.
- **DO NOT** confuse improvement with absence of regression. State both.
