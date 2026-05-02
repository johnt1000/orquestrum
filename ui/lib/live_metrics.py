"""live_metrics.py — read .orquestrum/metrics/ via orquestrum.lib.metrics.

Thin wrapper that resolves the metrics dir and exposes the aggregated
session for templates. Returns an empty SessionAggregate when the dir
does not exist (project not yet emitting metrics).

The hook (orquestrum/core/hooks/emit_metrics.py, deployed to
.sdd/scripts/hooks/ in target projects) only appends to events.jsonl —
it does NOT update session.json (keeping the hook lightweight). The UI
rebuilds session.json on every dashboard render so budget queries always
see fresh data.
"""
from __future__ import annotations
from pathlib import Path

from orquestrum.lib.metrics import read_events, aggregate, rebuild_session, SessionAggregate
from orquestrum.lib.budget import check_session_budget, BudgetReport, SOFT_THRESHOLDS


def session_for(metrics_dir: Path | None, tier: str | None = None) -> SessionAggregate:
    """Aggregate events.jsonl. Also rebuilds session.json so budget_for sees fresh data."""
    if metrics_dir is None or not metrics_dir.exists():
        return aggregate([], tier=tier)
    return rebuild_session(metrics_dir, tier=tier)


def budget_for(metrics_dir: Path | None, tier: str) -> BudgetReport | None:
    if metrics_dir is None:
        return None
    return check_session_budget(metrics_dir / 'session.json', tier)
