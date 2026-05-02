"""live_metrics.py — read .orquestrum/metrics/ via scripts/lib/metrics.py.

Thin wrapper that resolves the metrics dir and exposes the aggregated
session for templates. Returns an empty SessionAggregate when the dir
does not exist (project not yet emitting metrics).

The hook (scripts/hooks/emit_metrics.py) only appends to events.jsonl —
it does NOT update session.json (keeping the hook lightweight). The UI
rebuilds session.json on every dashboard render so budget queries always
see fresh data.
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / 'scripts'))

try:
    from lib.metrics import read_events, aggregate, rebuild_session, SessionAggregate
    from lib.budget import check_session_budget, BudgetReport, SOFT_THRESHOLDS
except ImportError:
    read_events = aggregate = rebuild_session = check_session_budget = None
    SessionAggregate = BudgetReport = None
    SOFT_THRESHOLDS = {}


def session_for(metrics_dir: Path | None, tier: str | None = None):
    """Aggregate events.jsonl. Also rebuilds session.json so budget_for sees fresh data."""
    if metrics_dir is None or aggregate is None or not metrics_dir.exists():
        return aggregate([], tier=tier) if aggregate else None
    if rebuild_session:
        return rebuild_session(metrics_dir, tier=tier)
    events = read_events(metrics_dir / 'events.jsonl')
    return aggregate(events, tier=tier)


def budget_for(metrics_dir: Path | None, tier: str):
    if metrics_dir is None or check_session_budget is None:
        return None
    return check_session_budget(metrics_dir / 'session.json', tier)
