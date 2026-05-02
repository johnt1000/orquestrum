# Cost & Budget Policy

Per-session token budgets, soft warnings, and the rationale for each threshold. Companion to `docs/governance/MODELS.md` (which assigns models to tiers) and `docs/governance/OBSERVABILITY.md` (which describes how usage is measured).

---

## Soft warning thresholds

Budgets are **soft warnings**, not hard caps — sessions above threshold continue but emit a warning that the operator should investigate. A hard cap would lose work mid-session; a warning lets the human decide.

| Tier | Input tokens | Output tokens | Reasoning |
|------|-------------:|--------------:|-----------|
| **deep**       | 200,000 | 16,000 | Helm meta-orchestration; reads multiple governance docs + chains of skills. Higher input is expected; output stays bounded by `max_tokens`. |
| **balanced**   | 100,000 |  8,000 | Most orchestrator work fits here. Sessions above this typically over-load context (loaded too many references). |
| **mechanical** |  30,000 |  2,000 | Templated output with structured input. A mechanical session above 30K input is almost always loading content the skill doesn't need. |

Warnings include the dominant cost driver: which skill, which artifact category, which adapter.

The thresholds are stored in `orquestrum/lib/budget.py` as a single dict and can be tuned without rebuilding integrations.

---

## How budgets are checked

`checkpoint-manager` reads `.orquestrum/metrics/session.json` (Phase 3) on every checkpoint and calls `budget.check_session_budget()`. If any threshold is exceeded:

1. A warning is printed in the checkpoint output (`⚠ Budget exceeded: balanced tier session has consumed 132,000 input tokens (threshold 100,000)`).
2. The dominant cost driver is named (e.g. `top contributor: review-manager — 48,000 tokens`).
3. The recommendation is action-oriented (`Consider splitting the review across multiple sessions, or switching to inject_references: compact`).

There is no auto-stop. The human decides whether to continue, split the session, or change settings.

---

## Hard caps (configuration)

If an operator wants a real ceiling, they can set hard caps in `pyproject.toml`:

```toml
[tool.orquestrum.budget]
deep_input_max       = 300_000   # hard ceiling, exceeded → error
balanced_input_max   = 150_000
mechanical_input_max = 50_000
```

Hard caps are read by `budget.py` if present; absent values fall back to `None` (no hard cap). Skills consult `budget.is_session_capped()` before launching expensive sub-tasks.

---

## Cost estimation

`orquestrum/lib/models.py:estimate_cost(model, in_tokens, out_tokens)` returns a USD estimate from the `MODEL_PRICING` table. Wired into the metrics emission pipeline (Phase 3); previously dormant.

Pricing is reference-grade (Anthropic public pricing 2025) and may be stale — operators with negotiated rates should override `MODEL_PRICING` in a private config. For the GLM provider, prices are from Z.ai's coding plan tier; copilot prices follow Anthropic's underlying model.

---

## What the budget does NOT cover

- **Wall time / latency**: not budgeted here. See `docs/governance/PERFORMANCE.md` for latency targets.
- **External API calls** (e.g. database queries from skills with `bash: true`): out of scope; they don't consume LLM tokens.
- **Embeddings or vector store costs**: Orquestrum does not use these in its core skill set.
- **Cumulative spend across multiple sessions**: tracked in `.orquestrum/metrics/events.jsonl` but not enforced. The dashboard surfaces weekly/monthly aggregates.

---

## Tuning the thresholds

Thresholds were chosen conservatively. Tune them based on real usage:

1. Run sessions normally for ~2 weeks with metrics enabled.
2. Aggregate via `orquestrum dashboard` and look at the p90/p99 input-token distribution per tier.
3. Adjust thresholds in `orquestrum/lib/budget.py` so that warnings fire on the top ~10% of sessions, not the median.

If warnings never fire, the threshold is too lax. If they fire on every session, it's too tight.
