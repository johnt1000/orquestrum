# Hook Integration

How Orquestrum auto-emits metrics from Claude Code sessions via the `Stop` and `SubagentStop` hooks. Companion to `docs/governance/OBSERVABILITY.md` (which defines the schema being emitted).

---

## Why hooks

Without a hook, `.orquestrum/metrics/events.jsonl` only gets populated when a skill or operator explicitly calls `orquestrum.lib.metrics:append_event()`. In practice that means the file is **empty** in real sessions — and the dashboard, attention calibration, and budget warnings all degrade to empty state.

The hook closes the gap: every time a Claude Code turn ends (`Stop`) or a subagent finishes (`SubagentStop`), the hook reads the event JSON from stdin, extracts token usage and the model used, computes the USD cost via `models.estimate_cost()`, and appends one line to `events.jsonl` — automatically, with zero per-skill discipline required.

---

## What gets installed

Since v0.5.1 the hook is the `orquestrum hook` CLI subcommand — there is **no script copied into the project**. The handler logic lives only in the orquestrum package (`orquestrum/core/hooks/emit_metrics.py`) and is invoked via PATH lookup, so it works regardless of which directory Claude Code was launched from.

When `orquestrum setup` runs (or `orquestrum install --tool claude-code --target ~`):

| Path | What |
|----------------|------|
| `~/.claude/settings.json` | hooks declaration registered globally; merged into existing settings (user keys preserved) |

The settings.json entry registers exactly:

```json
{
  "hooks": {
    "Stop": [{"matcher": "", "hooks": [{"type": "command", "command": "orquestrum hook"}]}],
    "SubagentStop": [{"matcher": "", "hooks": [{"type": "command", "command": "orquestrum hook"}]}]
  }
}
```

The command is `orquestrum hook` (no path), resolved via `$PATH` — same as the MCP server registration. This sidesteps the historical bug where a relative path like `uv run .claude/sdd/scripts/hooks/emit_metrics.py` failed with ENOENT whenever Claude Code was launched from a directory that did not contain that exact path tree.

### Legacy form (≤v0.5.0)

Older installs registered `uv run .claude/sdd/scripts/hooks/emit_metrics.py`. The merge logic in `orquestrum.lib.settings_io.is_orquestrum_hook` recognises both forms — re-running `orquestrum setup` or `orquestrum install` on an old install replaces the legacy entry with the new one and removes the orphan `.claude/sdd/scripts/` files (handled by `orquestrum uninstall`).

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

You can re-run `orquestrum install` safely — duplicates are detected by exact command match.

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
orquestrum dashboard --metrics-dir .orquestrum/metrics --tier balanced
```

Or, with the UI:

```bash
orquestrum web --target /path/to/project --mode project
# → http://127.0.0.1:7700/dashboard
```

---

## Disabling the hook

Edit `~/.claude/settings.json` and remove the entries whose `command` contains `orquestrum hook` (or, on legacy installs, `emit_metrics.py`). Cleaner: run `orquestrum uninstall --self` (removes the CLI entirely) or manually delete the `Stop` and `SubagentStop` blocks created by orquestrum.

The next `orquestrum setup` (or `orquestrum install --tool claude-code --target ~`) re-registers them. To suppress permanently, skip running setup/install for that target — or wrap the entry with `false_disabled` (orquestrum's merge ignores entries it doesn't own).

You can also disable hooks globally per-session via Claude Code's settings UI / CLI flags without editing the file.

---

## Limitations and roadmap

- **No skill name in events.** Recorded as `(unknown)`. Improving this requires either (a) Claude Code exposing the active skill in the hook input, or (b) a wrapper convention where each skill emits a sentinel event before/after its work.
- **No duration_ms.** Stop hook does not currently expose call duration. Recorded as `null`.
- **Cache creation tokens not separated.** We record `cache_read_input_tokens` only. Cache creation is a one-time write cost that's conceptually different.
- **Other tools (OpenCode, Cursor, etc.)** do not have an equivalent hook today. When they ship one, add a parallel hook script with the appropriate input format.

These limitations are tracked in `docs/governance/ROADMAP.md` (R3 / R13 follow-ups).
