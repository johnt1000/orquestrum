"""dashboard.py — /dashboard route. Computes all data shapes consumed by the
new dashboard.html: KPI series + heatmap + attention donut + recent jobs +
breadcrumb + active pipeline phase. Falls back gracefully on empty data.
"""
from __future__ import annotations
import subprocess
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ui.lib import live_metrics, jobs as jobs_lib
from ui.lib.attention import attention_bands

router = APIRouter()

# Canonical 8 orchestrators (short name → emoji + phase tag for the rail).
# Keep this list in sync with agents/*.md and CLAUDE.md.
CANONICAL_AGENTS: list[tuple[str, str, str]] = [
    ('Helm',   '🏛️', None),               # meta
    ('Trace',  '🗺️', 'onboarding'),
    ('Lore',   '🎯', 'discovery'),
    ('Forge',  '⚙️',  'planning'),
    ('Cipher', '🔐', 'quality'),          # 3.5 maps to closest light/quality bucket
    ('Ward',   '🔍', 'quality'),
    ('Cast',   '🚀', 'release'),
    ('Flux',   '🔄', 'maintenance'),
]


def _git_branch(root: Path | None) -> str | None:
    if root is None:
        return None
    try:
        r = subprocess.run(
            ['git', 'symbolic-ref', '--short', 'HEAD'],
            cwd=str(root), capture_output=True, text=True, timeout=2,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None
    if r.returncode != 0:
        return None
    return (r.stdout or '').strip() or None


def _breadcrumb(root: Path | None) -> dict | None:
    if root is None:
        return None
    return {
        'path':   str(root).replace(str(Path.home()), '~', 1),
        'branch': _git_branch(root),
    }


def _active_phase(events: list[dict]) -> str | None:
    """Pick the phase whose owning agent generated the most events in the last 7 days."""
    counts: dict[str, int] = {}
    for ev in events:
        if ev.get('kind') != 'llm_call':
            continue
        agent_field = (ev.get('agent') or '').strip()
        short = agent_field.split(' - ', 1)[0] if agent_field else ''
        for name, _emoji, phase in CANONICAL_AGENTS:
            if short == name and phase:
                counts[phase] = counts.get(phase, 0) + 1
                break
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _top_skills(sess, top_n: int = 6) -> tuple[list[tuple[str, int, int]], int]:
    if not sess or not sess.by_skill:
        return [], 0
    rows = sorted(
        sess.by_skill.items(),
        key=lambda kv: int(kv[1].get('input_tokens', 0)),
        reverse=True,
    )
    top = rows[:top_n]
    if not top:
        return [], len(rows)
    cap = max(int(rec.get('input_tokens', 0)) for _, rec in top) or 1
    out: list[tuple[str, int, int]] = []
    for name, rec in top:
        in_t = int(rec.get('input_tokens', 0))
        pct  = int(round(in_t / cap * 100))
        # display the skill's call count instead of raw input tokens — easier to read
        out.append((name, int(rec.get('calls', 0)), pct))
    return out, len(rows)


def _budget_cost_pct(sess) -> int:
    """Approximate cost % of monthly soft budget. Placeholder: $50/month → 100%."""
    if not sess:
        return 0
    cost = float(sess.totals.get('cost_usd', 0.0) or 0.0)
    return int(round(min(100.0, cost / 50.0 * 100.0)))


def _recent_jobs(limit: int = 5) -> list:
    items = list(jobs_lib._jobs.values())
    items.sort(key=lambda j: j.started_at, reverse=True)
    return items[:limit]


@router.get('/dashboard', response_class=HTMLResponse)
async def show(request: Request) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    locale    = getattr(request.state, 'locale', 'pt')

    registry_projects: list[dict] = []
    if not cfg.is_linked:
        try:
            from orquestrum.lib.registry import load_registry
            registry_projects = load_registry()
        except Exception:
            pass

    sess   = live_metrics.session_for(cfg.metrics_dir, tier='balanced')
    budget = live_metrics.budget_for(cfg.metrics_dir, tier='balanced')
    events = live_metrics.events_for(cfg.metrics_dir)

    series        = live_metrics.series_by_day(events)
    heatmap_rows, heatmap_days = live_metrics.agent_calls_by_day(
        events,
        agents=[(name, emoji) for name, emoji, _ in CANONICAL_AGENTS],
        locale=locale,
    )
    top_skills, top_skills_total = _top_skills(sess, top_n=6)
    attention      = attention_bands(cfg.linked_project_root or cfg.root)
    last_dt        = live_metrics.last_event_dt(events)
    active_phase   = _active_phase(events)
    breadcrumb     = _breadcrumb(cfg.linked_project_root or cfg.root)
    recent_jobs    = _recent_jobs(limit=5)

    return templates.TemplateResponse(
        request,
        'dashboard.html',
        {
            # session/budget kept for backward-compat fields used elsewhere
            'sess':                 sess,
            'budget':               budget,
            'budget_cost_pct':      _budget_cost_pct(sess),
            'thresholds':           live_metrics.SOFT_THRESHOLDS,
            'is_linked':            cfg.is_linked,
            'linked_project_root':  str(cfg.linked_project_root) if cfg.linked_project_root else None,
            'registry_projects':    registry_projects,
            # new shapes for Onda 2
            'series':               series,
            'top_skills':           top_skills,
            'top_skills_total':     top_skills_total,
            'heatmap_rows':         heatmap_rows,
            'heatmap_days':         heatmap_days,
            'attention':            attention,
            'last_event_dt':        last_dt,
            'active_phase':         active_phase,
            'breadcrumb':           breadcrumb,
            'recent_jobs':          recent_jobs,
        },
    )
