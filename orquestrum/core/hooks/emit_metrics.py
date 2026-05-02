#!/usr/bin/env python3
"""emit_metrics.py — Claude Code Stop / SubagentStop hook.

Receives event JSON on stdin, extracts token usage + model, computes USD
cost, appends one event to `<cwd>/.orquestrum/metrics/events.jsonl`.

CRITICAL CONTRACT
-----------------
- Always exits 0. NEVER blocks the user's response.
- Writes nothing to stdout on success.
- Errors go to stderr only (debug log; not shown to user).
- Reads ONLY the hook input JSON from stdin. Does NOT parse the transcript.

Input JSON shape (Claude Code Stop / SubagentStop):
    {
      "session_id":      "...",
      "transcript_path": "/path/to/transcript.jsonl",
      "cwd":             "/path/to/project",
      "hook_event_name": "Stop" | "SubagentStop",
      "stop_reason":     "end_turn" | ...,
      "model":           "claude-sonnet-4-6",
      "usage": {
        "input_tokens":  2048,
        "output_tokens": 1024,
        "cache_read_input_tokens":     800   # optional
        "cache_creation_input_tokens":  0    # optional
      },
      "agent_id":   "..."  // SubagentStop only
      "agent_type": "Forge - Dev Lead"  // SubagentStop only
    }

Install via Claude Code settings.json:
    {
      "hooks": {
        "Stop": [{
          "matcher": "",
          "hooks": [{
            "type": "command",
            "command": "uv run .sdd/scripts/hooks/emit_metrics.py"
          }]
        }],
        "SubagentStop": [{
          "matcher": "",
          "hooks": [{
            "type": "command",
            "command": "uv run .sdd/scripts/hooks/emit_metrics.py"
          }]
        }]
      }
    }

DEPLOYMENT NOTE: This file is copied to .sdd/scripts/hooks/ in target projects.
The sys.path manipulation below resolves lib/ from the deployed location:
  .sdd/scripts/hooks/emit_metrics.py → parent = .sdd/scripts/ → has lib/
"""
from __future__ import annotations
import datetime as dt
import json
import sys
import traceback
from pathlib import Path

# Resolve lib/ at runtime — the hook lives at .sdd/scripts/hooks/ in the
# target project, so lib/ is a sibling of hooks/.
_HOOK_DIR  = Path(__file__).resolve().parent
_LIB_DIR   = _HOOK_DIR.parent / 'lib'
sys.path.insert(0, str(_HOOK_DIR.parent))


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_model(model: str | None) -> str:
    """Claude Code returns bare names (e.g. 'claude-sonnet-4-6'). MODEL_PRICING
    is keyed by full IDs (e.g. 'anthropic/claude-sonnet-4-6'). Hook always runs
    inside Claude Code, so prefix with 'anthropic/' unless already prefixed.
    """
    if not model:
        return ''
    if '/' in model:
        return model
    return f'anthropic/{model}'


def _resolve_agent_and_tier(input_json: dict) -> tuple[str, str]:
    """Best-effort agent + tier resolution.

    SubagentStop provides agent_type. Top-level Stop does not — we use a generic
    label so the dashboard doesn't conflate top-level turns with subagent turns.
    """
    agent_type = input_json.get('agent_type')
    if agent_type:
        agent = str(agent_type)
        try:
            from lib.models import AGENT_TIERS
            tier = AGENT_TIERS.get(agent, 'unknown')
        except ImportError:
            try:
                from orquestrum.lib.models import AGENT_TIERS
                tier = AGENT_TIERS.get(agent, 'unknown')
            except ImportError:
                tier = 'unknown'
        return agent, tier
    return '(top-level)', 'unknown'


def _emit(input_json: dict) -> None:
    cwd = input_json.get('cwd')
    if not cwd:
        sys.stderr.write('emit_metrics: no cwd in hook input — skipping\n')
        return
    metrics_dir = Path(cwd) / '.orquestrum' / 'metrics'
    events_path = metrics_dir / 'events.jsonl'

    usage = input_json.get('usage') or {}
    in_t  = _safe_int(usage.get('input_tokens'))
    out_t = _safe_int(usage.get('output_tokens'))
    cached = _safe_int(usage.get('cache_read_input_tokens'))

    raw_model = input_json.get('model')
    model = _normalize_model(raw_model)

    cost = 0.0
    try:
        from lib.models import estimate_cost
        cost = round(estimate_cost(model, in_t, out_t), 6)
    except ImportError:
        try:
            from orquestrum.lib.models import estimate_cost
            cost = round(estimate_cost(model, in_t, out_t), 6)
        except ImportError:
            pass

    agent, tier = _resolve_agent_and_tier(input_json)

    event = {
        'ts':            _now_iso(),
        'kind':          'llm_call',
        'agent':         agent,
        'skill':         '(unknown)',  # not derivable from hook input alone
        'tier':          tier,
        'model':         model or (raw_model or ''),
        'in_tokens':     in_t,
        'out_tokens':    out_t,
        'cached_tokens': cached,
        'cost_usd':      cost,
        'duration_ms':   None,  # not exposed by Stop hook today
        'session_id':    input_json.get('session_id'),
        'event_kind':    input_json.get('hook_event_name'),
    }

    metrics_dir.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, separators=(',', ':'), ensure_ascii=False)
    with events_path.open('a', encoding='utf-8') as f:
        f.write(line + '\n')


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        input_json = json.loads(raw)
        _emit(input_json)
    except json.JSONDecodeError as e:
        sys.stderr.write(f'emit_metrics: invalid JSON on stdin: {e}\n')
    except Exception:
        # Defensive: never block the user. Log full traceback to stderr.
        sys.stderr.write('emit_metrics: unexpected error (non-blocking):\n')
        traceback.print_exc(file=sys.stderr)


if __name__ == '__main__':
    main()
    sys.exit(0)  # ALWAYS exit 0 — never block the user's response.
