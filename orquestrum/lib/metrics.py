"""metrics.py — append-only metrics emission and aggregation.

Every LLM call and skill completion emits one event line in
`.orquestrum/metrics/events.jsonl`. The session summary in `.orquestrum/metrics/session.json`
is rebuilt by aggregating events.

Schema (per-LLM-call event):
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

Schema (per-skill-completion event):
    {
      "ts":               "2026-05-01T14:34:55Z",
      "kind":             "skill_completion",
      "skill":            "task-manager",
      "agent":            "Forge - Dev Lead",
      "status":           "completed",
      "gates_passed":     2,
      "gates_failed":     0,
      "artifacts_emitted":["T0042"],
      "confidence_avg":   0.85
    }

See docs/governance/OBSERVABILITY.md for the emission protocol.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def append_event(events_path: Path, event: dict[str, Any]) -> None:
    """Append one event line. Creates the file and parent dirs if missing.

    Append is atomic at the OS level for small writes (< PIPE_BUF, typically 4 KB)
    when opened with O_APPEND. Larger payloads should be split into multiple events.
    """
    events_path.parent.mkdir(parents=True, exist_ok=True)
    if 'ts' not in event:
        event = {'ts': now_iso(), **event}
    line = json.dumps(event, separators=(',', ':'), ensure_ascii=False)
    with events_path.open('a', encoding='utf-8') as f:
        f.write(line + '\n')


def read_events(events_path: Path) -> list[dict[str, Any]]:
    if not events_path.exists():
        return []
    out: list[dict[str, Any]] = []
    with events_path.open('r', encoding='utf-8') as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                out.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return out


@dataclass
class SessionAggregate:
    tier:           str | None
    totals:         dict[str, int | float]   = field(default_factory=dict)
    by_skill:       dict[str, dict[str, Any]] = field(default_factory=dict)
    by_agent:       dict[str, dict[str, Any]] = field(default_factory=dict)
    started_at:     str | None = None
    ended_at:       str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'tier':       self.tier,
            'started_at': self.started_at,
            'ended_at':   self.ended_at,
            'totals':     self.totals,
            'by_skill':   self.by_skill,
            'by_agent':   self.by_agent,
        }


def aggregate(events: list[dict[str, Any]], tier: str | None = None) -> SessionAggregate:
    """Roll up events into a session summary."""
    sess = SessionAggregate(tier=tier)
    sess.totals = {
        'input_tokens':  0,
        'output_tokens': 0,
        'cached_tokens': 0,
        'cost_usd':      0.0,
        'calls':         0,
        'skill_calls':   0,
    }

    timestamps: list[str] = []

    for ev in events:
        ts = ev.get('ts')
        if ts:
            timestamps.append(ts)
        kind = ev.get('kind')

        if kind == 'llm_call':
            in_t  = int(ev.get('in_tokens',     0))
            out_t = int(ev.get('out_tokens',    0))
            cac_t = int(ev.get('cached_tokens', 0))
            cost  = float(ev.get('cost_usd',    0.0))

            sess.totals['input_tokens']  += in_t
            sess.totals['output_tokens'] += out_t
            sess.totals['cached_tokens'] += cac_t
            sess.totals['cost_usd']       = round(float(sess.totals['cost_usd']) + cost, 6)
            sess.totals['calls']         += 1

            skill_key = ev.get('skill') or '(no-skill)'
            agent_key = ev.get('agent') or '(no-agent)'

            for bucket, key in ((sess.by_skill, skill_key), (sess.by_agent, agent_key)):
                rec = bucket.setdefault(key, {
                    'input_tokens':  0,
                    'output_tokens': 0,
                    'cached_tokens': 0,
                    'cost_usd':      0.0,
                    'calls':         0,
                })
                rec['input_tokens']  += in_t
                rec['output_tokens'] += out_t
                rec['cached_tokens'] += cac_t
                rec['cost_usd']       = round(float(rec['cost_usd']) + cost, 6)
                rec['calls']         += 1

        elif kind == 'skill_completion':
            sess.totals['skill_calls'] += 1
            skill_key = ev.get('skill') or '(no-skill)'
            rec = sess.by_skill.setdefault(skill_key, {
                'input_tokens':  0, 'output_tokens': 0, 'cached_tokens': 0,
                'cost_usd':      0.0, 'calls': 0,
            })
            rec.setdefault('completions', 0)
            rec['completions'] = int(rec.get('completions', 0)) + 1
            if ev.get('status') == 'failed':
                rec.setdefault('failures', 0)
                rec['failures'] = int(rec.get('failures', 0)) + 1

    if timestamps:
        sess.started_at = min(timestamps)
        sess.ended_at   = max(timestamps)
    return sess


def update_session(session_path: Path, sess: SessionAggregate) -> None:
    """Atomically rewrite the session summary."""
    session_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='session-', suffix='.json', dir=str(session_path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(sess.to_dict(), f, indent=2, ensure_ascii=False)
        os.replace(tmp, session_path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def rebuild_session(metrics_dir: Path, tier: str | None = None) -> SessionAggregate:
    """Convenience: read events, aggregate, write session.json. Returns the aggregate."""
    events = read_events(metrics_dir / 'events.jsonl')
    sess   = aggregate(events, tier=tier)
    update_session(metrics_dir / 'session.json', sess)
    return sess
