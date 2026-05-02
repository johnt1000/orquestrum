# Observability

How Orquestrum tracks token usage, cost, and skill performance per session, and how the operator reads it.

Companion to `docs/governance/COST.md` (budget thresholds) and `docs/governance/MODELS.md` (which models cost what).

---

## Where data lives

```
.orquestrum/metrics/
├── events.jsonl    # append-only event log; one line per LLM call or skill completion
├── session.json    # rolled-up session summary; rewritten atomically
└── dashboard.md    # rendered on demand by `orquestrum dashboard` (optional)
```

`.orquestrum/metrics/` is per-project, gitignored by default. It is **not** propagated by `orquestrum convert` — the runtime emits it inside the user's project.

---

## Emission protocol

Skills and agents emit metrics by **appending one JSON line** to `.orquestrum/metrics/events.jsonl` via the Write tool (or shell via `bash` tool when available).

There is no central agent for emission. Each skill/agent writes its own events. This avoids a single point of failure and matches the existing artifact-writing pattern.

### Per-LLM-call event

Emit immediately after the LLM call returns and you have the token counts:

```json
{
  "ts":            "2026-05-01T14:32:11Z",
  "kind":          "llm_call",
  "agent":         "Forge - Dev Lead",
  "skill":         "task-manager",
  "tier":          "balanced",
  "model":         "anthropic/claude-sonnet-4-6",
  "in_tokens":     1240,
  "out_tokens":    320,
  "cached_tokens": 800,
  "cost_usd":      0.00852,
  "duration_ms":   2310
}
```

`cost_usd` is computed via `orquestrum/lib/models.py:estimate_cost(model, in, out)`. `cached_tokens` represents tokens served from prompt cache (Anthropic returns this in usage); use 0 when the adapter doesn't expose it.

### Per-skill-completion event

Emit when a skill finishes (success or failure):

```json
{
  "ts":                "2026-05-01T14:34:55Z",
  "kind":              "skill_completion",
  "skill":             "task-manager",
  "agent":             "Forge - Dev Lead",
  "status":            "completed",
  "gates_passed":      2,
  "gates_failed":      0,
  "artifacts_emitted": ["T0042"],
  "confidence_avg":    0.85
}
```

`status` ∈ {`completed`, `failed`, `partial`}. `confidence_avg` is the mean confidence of artifacts emitted (see Phase 4 attention scoring).

---

## What is NOT emitted

- **Raw prompts.** Tokens are recorded; prompt content is not. This was previously a privacy guard in `checkpoint-manager`; the rule has been refined: counts yes, content no.
- **Personally identifying or business-confidential payloads.** Skills must not emit user-supplied content into `events.jsonl`.
- **Synthetic semantic-quality scores.** No LLM-judged effectiveness metric is emitted in this phase. Effectiveness is inferred indirectly from `gates_failed`, `confidence_avg`, and downstream `attention_score` (Phase 4).

---

## Aggregation

The library `orquestrum/lib/metrics.py` provides:

| Function | Purpose |
|---|---|
| `append_event(path, event)` | Atomically append one event line |
| `read_events(path)` | Parse all events |
| `aggregate(events, tier)` | Roll up totals + by-skill + by-agent |
| `update_session(path, sess)` | Atomically rewrite `session.json` |
| `rebuild_session(metrics_dir, tier)` | One-shot: read → aggregate → write |

`checkpoint-manager` calls `rebuild_session()` at the start and end of every checkpoint. Mid-session, the operator can rebuild on demand:

```bash
uv run python -c "from orquestrum.lib.metrics import rebuild_session; from pathlib import Path; \
  s = rebuild_session(Path('.orquestrum/metrics'), tier='balanced'); \
  print('cost so far: $', s.totals['cost_usd'])"
```

---

## Dashboard

`orquestrum dashboard` (logic in `orquestrum/core/dashboard/render.py`) reads `.orquestrum/metrics/events.jsonl` and produces:

- `.orquestrum/metrics/dashboard.md` — terminal-friendly view; always written
- `.orquestrum/metrics/dashboard.html` — single-file vanilla HTML/JS chart (optional; `--html` flag)

Both are static. There is no server, no auto-refresh. The operator runs the renderer on demand; the dashboard is a cortesia, not a product.

---

## Schema versioning

Both event lines and `session.json` carry no explicit `schema_version` field today. They are append-only and forward-compatible: aggregators ignore unknown keys, and missing keys default to zero.

When a breaking schema change is needed:

1. Bump the version in `orquestrum/lib/metrics.py:SCHEMA_VERSION` (introduce as needed).
2. Add migration in `aggregate()` that handles both old and new shapes.
3. Document the change here.

---

## Privacy & retention

`.orquestrum/metrics/` is local-only and **not** in the default install path. Users who want to ship metrics to an external observability stack pipe `events.jsonl` themselves:

```bash
tail -f .orquestrum/metrics/events.jsonl | curl -X POST <my-collector> --data-binary @-
```

Orquestrum does not ship a built-in collector or telemetry endpoint. That is intentional — the framework owns measurement, the operator owns transport.

---

## Failure modes

| Failure | Behavior |
|---------|----------|
| `events.jsonl` corrupted (non-JSON line) | `read_events` skips bad lines silently; aggregation continues |
| Disk full | Append fails noisily; the failing skill should treat metrics as best-effort and proceed |
| Multiple writers race | `O_APPEND` makes line writes atomic for events ≤ PIPE_BUF (~4 KB). Larger events should split into multiple lines. |
| `session.json` corrupted | `rebuild_session` overwrites it from events; events are the source of truth |

The session.json file is **derived** — if it ever disagrees with events.jsonl, the events win.
