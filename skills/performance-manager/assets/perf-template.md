---
id: PERF-{ref}
title: "{TITLE}"
status: Pending # Passed | Regressed | Inconclusive
spec_ref: spec-vX
task_ref: [T{ID}]
created: YYYY-MM-DD HH:mm
sample_count: 0
environment: "{staging | prod-shadow | local}"
# Human Attention Mediation
attention_score: 100
attention_band:  green
attention_factors: []
---

# PERF-{ref} — {TITLE}

---

## Targets

> From SPEC SC-XX. If absent, derived from the last PERF artifact for this component.

| ID | Metric | Target | Source |
|----|--------|--------|--------|
| SC-NN | p95 latency | < 200ms | SPEC |
| — | throughput | > 50 rps | baseline PERF-{prev} |

---

## Methodology

| Field | Value |
|-------|-------|
| Workload | {description} |
| Dataset | {size, characteristics} |
| Warmup | {N seconds / requests} |
| Sample count | {N} |
| Statistical method | {p50/p95/p99 + std dev or IQR} |
| Tool | {benchmark harness} |

---

## Results

| Metric | Baseline | Current | Δ | Verdict |
|--------|---------:|--------:|---:|---------|
| p95 latency | 180ms | 195ms | +8.3% | regression (Medium) |
| throughput | 62 rps | 64 rps | +3.2% | parity |

---

## Regression classification

> Only entries that are regressions.

| Metric | Class | Action |
|--------|-------|--------|
| p95 latency | Medium | open improvement Task T{ID}; not a release blocker |

---

## Notes

{free text — explanation, hypotheses, follow-up}

---

## ⚠ Audit Warnings

{populated by self-audit}
