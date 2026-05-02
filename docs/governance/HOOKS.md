# Hook Integration

How Orquestrum auto-emits metrics from Claude Code sessions via the `Stop` and `SubagentStop` hooks. Companion to `docs/governance/OBSERVABILITY.md` (which defines the schema being emitted).

---

## Why hooks

Without a hook, `.orquestrum/metrics/events.jsonl` only gets populated when a skill or operator explicitly calls `scripts/lib/metrics.py:append_event()`. In practice that means the file is **empty** in real sessions — and the dashboard, attention calibration, and budget warnings all degrade to empty state.

The hook closes the gap: every time a Claude Code turn ends (`Stop`) or a subagent finishes (`SubagentStop`), the hook reads the event JSON from stdin, extracts token usage and the model used, computes the USD cost via `models.estimate_cost()`, and appends one line to `events.jsonl` — automatically, with zero per-skill discipline required.

---

## What gets installed

When you run `uv run scripts/install.py --tool claude-code --target <project>`:

| Path in target | What |
|----------------|------|
| `.claude/settings.json` | hooks declaration (merged into existing settings, never overwritten) |
| `.sdd/scripts/hooks/emit_metrics.py` | the hook handler |
| `.sdd/scripts/lib/` | required for the hook (uses `models.estimate_cost`) |

The handler is executable (`chmod +x`) and runs via `uv run .sdd/scripts/hooks/emit_metrics.py`.

---

## Settings merge behavior

`install.py` merges `settings.json` non-destructively:

| Scenario | Behavior |
|----------|----------|
| Target has no `.claude/settings.json` | Template is copied verbatim |
| Target has `settings.json` without `hooks` | Our hooks are added; other keys preserved |
| Target has `settings.json` with `hooks.Stop` (different command) | Our entry is appended to the array, theirs preserved |
| Target has `settings.json` with same command already | Skipped (idempotent re-install) |
| Target's `settings.json` is malformed JSON | Warning printed; file left untouched; user must merge manually |

You can re-run `install.py` safely — duplicates are detected by exact command match.

---

## Hook contract

The Claude Code hook protocol (confirmed):

### Stop event input (stdin JSON)

```json
{
  "session_id":      "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd":             "/path/to/project",
  "hook_event_name": "Stop",
  "stop_reason":     "end_turn",
  "model":           "claude-sonnet-4-6",
  "usage": {
    "input_tokens":  2048,
    "output_tokens": 1024,
    "cache_read_input_tokens": 800
  }
}
```

### SubagentStop adds

```json
"agent_id":   "sub-abc",
"agent_type": "Forge - Dev Lead"
```

### What we do with it

| Hook field | Maps to event field | Notes |
|------------|--------------------|-----|
| `usage.input_tokens` | `in_tokens` | direct |
| `usage.output_tokens` | `out_tokens` | direct |
| `usage.cache_read_input_tokens` | `cached_tokens` | optional; 0 if absent |
| `model` | `model` | normalized to `anthropic/{model}` |
| `agent_type` (subagent) | `agent` | top-level Stop emits `(top-level)` |
| `agent_type` → `AGENT_TIERS` lookup | `tier` | `unknown` if not in dict |
| `cwd` | location of `.orquestrum/metrics/events.jsonl` | |
| computed via `estimate_cost` | `cost_usd` | from `MODEL_PRICING` table |

### What we explicitly do NOT do

- **Parse the transcript file.** All needed data is in the hook input. Reading the transcript adds I/O cost and risks data drift if Anthropic changes the format.
- **Block the user's response.** The hook always exits 0, even on errors.
- **Write to stdout on success.** Only stderr on errors (and only to debug log; not user-visible).
- **Resolve the active skill.** That info is not in the hook input. `skill` is recorded as `(unknown)` in events. A future enhancement could pass `--skill-hint $CLAUDE_SKILL_HINT` if Claude Code exposes such a var.

---

## Failure modes

| Failure | Hook behavior |
|---------|---------------|
| Empty stdin | Exit 0 silently |
| Malformed JSON on stdin | Log to stderr, exit 0 |
| Missing `cwd` in input | Log to stderr, exit 0, no event appended |
| `cwd` not writable / disk full | Append fails, traceback to stderr, exit 0 |
| `models.estimate_cost` throws | Cost set to 0.0, event still appended |
| Unknown model (not in `MODEL_PRICING`) | Cost = 0.0, event recorded with model name preserved |

The hook is designed to be **invisible when working** and **harmless when broken**. It will never block your turn.

---

## Verifying it works

After installing into a target project, run a real Claude Code session and check:

```bash
cat /path/to/project/.orquestrum/metrics/events.jsonl | tail -5
```

You should see one event per turn. To re-render the dashboard:

```bash
cd /path/to/project
uv run /path/to/orquestrum/scripts/dashboard/render.py --metrics-dir .orquestrum/metrics --tier balanced
```

Or, with the UI:

```bash
uv run /path/to/orquestrum/scripts/ui/serve.py --mode project --root /path/to/project
# → http://127.0.0.1:7700/dashboard
```

---

## Disabling the hook

Edit `.claude/settings.json` and remove the entries with `command: uv run .sdd/scripts/hooks/emit_metrics.py`. The next `install.py` will re-add them — to suppress permanently, add a sentinel comment or skip running install for that target.

You can also disable hooks globally per-session via Claude Code's settings UI / CLI flags without editing the file.

---

## Limitations and roadmap

- **No skill name in events.** Recorded as `(unknown)`. Improving this requires either (a) Claude Code exposing the active skill in the hook input, or (b) a wrapper convention where each skill emits a sentinel event before/after its work.
- **No duration_ms.** Stop hook does not currently expose call duration. Recorded as `null`.
- **Cache creation tokens not separated.** We record `cache_read_input_tokens` only. Cache creation is a one-time write cost that's conceptually different.
- **Other tools (OpenCode, Cursor, etc.)** do not have an equivalent hook today. When they ship one, add a parallel hook script with the appropriate input format.

These limitations are tracked in `docs/governance/ROADMAP.md` (R3 / R13 follow-ups).
