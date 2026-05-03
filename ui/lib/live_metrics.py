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
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

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


def events_for(metrics_dir: Path | None) -> list[dict[str, Any]]:
    """Return raw events. Empty list if dir or file missing."""
    if metrics_dir is None:
        return []
    return read_events(metrics_dir / 'events.jsonl')


# ─── time helpers ────────────────────────────────────────────────────────────

def _parse_ts(ev: dict[str, Any]) -> dt.datetime | None:
    ts = ev.get('ts')
    if not ts or not isinstance(ts, str):
        return None
    try:
        # Stored as 'YYYY-MM-DDTHH:MM:SSZ' (UTC, append 'Z'). Handle both with and without Z.
        s = ts.replace('Z', '+00:00')
        return dt.datetime.fromisoformat(s)
    except ValueError:
        return None


def last_event_dt(events: Iterable[dict[str, Any]]) -> dt.datetime | None:
    latest: dt.datetime | None = None
    for ev in events:
        d = _parse_ts(ev)
        if d and (latest is None or d > latest):
            latest = d
    return latest


# ─── sparkline points ────────────────────────────────────────────────────────

def spark_points(values: list[float], width: int = 100, height: int = 24) -> str:
    """Format a 'x,y x,y ...' polyline string for inline SVG sparklines.

    Constant series and empty series render as flat midline so the SVG never
    collapses into a single point.
    """
    if not values:
        return ''
    n = len(values)
    mid = height / 2
    if n == 1:
        return f'0,{mid:.2f} {width},{mid:.2f}'
    lo, hi = min(values), max(values)
    rng = hi - lo
    pts: list[str] = []
    for i, v in enumerate(values):
        x = (i / (n - 1)) * width
        y = mid if rng == 0 else (height - 1 - ((v - lo) / rng) * (height - 2))
        pts.append(f'{x:.2f},{y:.2f}')
    return ' '.join(pts)


# ─── per-day series for dashboard KPIs ───────────────────────────────────────

@dataclass
class KPISeries:
    label_key:        str       # i18n key, e.g. 'kpi.cost'
    formatted:        str       # display value, e.g. '$0.4231'
    values:           list[float]
    sparkline_points: str
    delta_text:       str       # '+12.4%' or '−5.2%' or ''
    delta_cls:        str       # 'is-up-good' | 'is-up-bad' | 'is-down-good' | 'is-down-bad' | 'is-neutral'


def _bucket_dates(days: int, today: dt.date | None = None) -> list[dt.date]:
    """Return `days` consecutive dates ending today (oldest first)."""
    today = today or dt.datetime.now(dt.timezone.utc).date()
    return [today - dt.timedelta(days=days - 1 - i) for i in range(days)]


def _fmt_delta_pct(cur: float, prev: float) -> str:
    if prev == 0:
        return ''
    pct = (cur - prev) / prev * 100
    sign = '+' if pct >= 0 else '−'
    return f'{sign}{abs(pct):.1f}%'


def _fmt_delta_int(cur: float, prev: float) -> str:
    delta = int(round(cur - prev))
    if delta == 0:
        return ''
    sign = '+' if delta > 0 else '−'
    return f'{sign}{abs(delta)}'


def _fmt_delta_pp(cur_pct: float, prev_pct: float) -> str:
    delta = cur_pct - prev_pct
    if abs(delta) < 0.5:
        return ''
    sign = '+' if delta >= 0 else '−'
    return f'{sign}{abs(delta):.0f}pp'


def _delta_cls(cur: float, prev: float, *, up_is_good: bool) -> str:
    if cur == prev:
        return 'is-neutral'
    going_up = cur > prev
    if going_up:
        return 'is-up-good' if up_is_good else 'is-up-bad'
    return 'is-down-bad' if up_is_good else 'is-down-good'


def series_by_day(events: list[dict[str, Any]], days: int = 7,
                  today: dt.date | None = None) -> dict[str, KPISeries]:
    """Compute the 4 dashboard KPIs as 7-day series with deltas vs previous 7d.

    Returned keys: 'cost', 'calls', 'cached', 'skills'.
    """
    today  = today or dt.datetime.now(dt.timezone.utc).date()
    cur    = _bucket_dates(days, today)
    prev   = _bucket_dates(days, today - dt.timedelta(days=days))
    window = set(cur) | set(prev)

    # buckets[date] = {'cost', 'calls', 'in_tokens', 'cached_tokens', 'skills': set()}
    buckets: dict[dt.date, dict[str, Any]] = {
        d: {'cost': 0.0, 'calls': 0, 'in_tokens': 0, 'cached_tokens': 0, 'skills': set()}
        for d in window
    }

    for ev in events:
        if ev.get('kind') != 'llm_call':
            continue
        d_at = _parse_ts(ev)
        if not d_at:
            continue
        day = d_at.astimezone(dt.timezone.utc).date()
        if day not in buckets:
            continue
        b = buckets[day]
        b['cost']          += float(ev.get('cost_usd') or 0.0)
        b['calls']         += 1
        b['in_tokens']     += int(ev.get('in_tokens') or 0)
        b['cached_tokens'] += int(ev.get('cached_tokens') or 0)
        skill = ev.get('skill')
        if skill:
            b['skills'].add(skill)

    def _series(field: str) -> tuple[list[float], float, float]:
        cur_values  = [float(buckets[d][field]) for d in cur]
        cur_total   = sum(cur_values)
        prev_total  = sum(float(buckets[d][field]) for d in prev)
        return cur_values, cur_total, prev_total

    def _cached_pct(period: list[dt.date]) -> float:
        in_t  = sum(int(buckets[d]['in_tokens']) for d in period)
        cached= sum(int(buckets[d]['cached_tokens']) for d in period)
        return (cached / in_t * 100) if in_t else 0.0

    def _skills_unique(period: list[dt.date]) -> int:
        u: set[str] = set()
        for d in period:
            u |= buckets[d]['skills']
        return len(u)

    # cost
    cost_v, cost_cur, cost_prev = _series('cost')
    cost_series = KPISeries(
        label_key='kpi.cost',
        formatted=f'${cost_cur:.4f}',
        values=cost_v,
        sparkline_points=spark_points(cost_v),
        delta_text=_fmt_delta_pct(cost_cur, cost_prev),
        delta_cls=_delta_cls(cost_cur, cost_prev, up_is_good=False),
    )

    # calls
    calls_v, calls_cur, calls_prev = _series('calls')
    calls_series = KPISeries(
        label_key='kpi.calls',
        formatted=f'{int(calls_cur):,}'.replace(',', '.'),
        values=calls_v,
        sparkline_points=spark_points(calls_v),
        delta_text=_fmt_delta_int(calls_cur, calls_prev),
        delta_cls=_delta_cls(calls_cur, calls_prev, up_is_good=True),
    )

    # cached % per day, then aggregate
    cached_v: list[float] = []
    for d in cur:
        in_t = int(buckets[d]['in_tokens'])
        c    = int(buckets[d]['cached_tokens'])
        cached_v.append((c / in_t * 100) if in_t else 0.0)
    cur_cached_pct  = _cached_pct(cur)
    prev_cached_pct = _cached_pct(prev)
    cached_series = KPISeries(
        label_key='kpi.cached',
        formatted=f'{cur_cached_pct:.0f}%',
        values=cached_v,
        sparkline_points=spark_points(cached_v),
        delta_text=_fmt_delta_pp(cur_cached_pct, prev_cached_pct),
        delta_cls=_delta_cls(cur_cached_pct, prev_cached_pct, up_is_good=True),
    )

    # skills unique per day, then total unique
    skills_v: list[float] = [float(len(buckets[d]['skills'])) for d in cur]
    cur_unique  = _skills_unique(cur)
    prev_unique = _skills_unique(prev)
    skills_series = KPISeries(
        label_key='kpi.skills',
        formatted=str(cur_unique),
        values=skills_v,
        sparkline_points=spark_points(skills_v),
        delta_text=_fmt_delta_int(cur_unique, prev_unique),
        delta_cls=_delta_cls(cur_unique, prev_unique, up_is_good=True),
    )

    return {
        'cost':   cost_series,
        'calls':  calls_series,
        'cached': cached_series,
        'skills': skills_series,
    }


# ─── agent activity heatmap ──────────────────────────────────────────────────

DAY_LABELS = {
    'pt': ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'],
    'en': ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'],
}


@dataclass
class HeatmapCell:
    count:     int
    opacity:   float       # 0..1
    day_label: str         # short weekday in user's locale


@dataclass
class HeatmapRow:
    name:    str
    emoji:   str
    cells:   list[HeatmapCell]


def agent_calls_by_day(events: list[dict[str, Any]],
                       agents: list[tuple[str, str]],
                       days: int = 7,
                       today: dt.date | None = None,
                       locale: str = 'pt') -> tuple[list[HeatmapRow], list[str]]:
    """For each (agent_full_name, emoji), return per-day call counts as a HeatmapRow.

    Matches events by `agent` field's prefix before ' - ' (e.g. 'Forge - Dev Lead' → 'Forge').

    Returns (rows, day_labels). Opacity is normalized to the global max so cells
    of similar magnitude stay readable.
    """
    today = today or dt.datetime.now(dt.timezone.utc).date()
    bucket_dates = _bucket_dates(days, today)
    labels       = DAY_LABELS.get(locale, DAY_LABELS['pt'])

    # Per-agent (by short name) per-date counts
    counts: dict[str, dict[dt.date, int]] = {short: {d: 0 for d in bucket_dates} for short, _ in agents}

    for ev in events:
        if ev.get('kind') != 'llm_call':
            continue
        agent_field = (ev.get('agent') or '').strip()
        short = agent_field.split(' - ', 1)[0] if agent_field else ''
        if short not in counts:
            continue
        d_at = _parse_ts(ev)
        if not d_at:
            continue
        day = d_at.astimezone(dt.timezone.utc).date()
        if day not in counts[short]:
            continue
        counts[short][day] += 1

    # Find max for opacity normalization (avoid div-by-zero)
    flat = [c for per in counts.values() for c in per.values()]
    cap  = max(flat) if flat else 0

    rows: list[HeatmapRow] = []
    for short, emoji in agents:
        cells: list[HeatmapCell] = []
        for d in bucket_dates:
            c       = counts[short].get(d, 0)
            opacity = (c / cap) if cap else 0.0
            # Lift baseline so 1 call is still visible (>= .12) but 0 stays near transparent.
            opacity = (0.12 + 0.88 * opacity) if c > 0 else 0.04
            day_lbl = labels[d.weekday()]
            cells.append(HeatmapCell(count=c, opacity=round(opacity, 3), day_label=day_lbl))
        rows.append(HeatmapRow(name=short, emoji=emoji, cells=cells))

    header_labels = [labels[d.weekday()] for d in bucket_dates]
    return rows, header_labels


# ─── catalog metrics (per-agent + per-skill last 7d) ─────────────────────────

@dataclass
class AgentSeries:
    short_name: str
    total:      int
    values:     list[int]
    points:     str    # SVG polyline points for sparkline


def agent_calls_series(events: list[dict[str, Any]],
                       short_names: list[str],
                       days: int = 7,
                       today: dt.date | None = None) -> dict[str, AgentSeries]:
    """Per-agent 7-day call counts + sparkline points, keyed by short name."""
    today = today or dt.datetime.now(dt.timezone.utc).date()
    bucket_dates = _bucket_dates(days, today)
    counts: dict[str, dict[dt.date, int]] = {n: {d: 0 for d in bucket_dates} for n in short_names}

    for ev in events:
        if ev.get('kind') != 'llm_call':
            continue
        agent_field = (ev.get('agent') or '').strip()
        short = agent_field.split(' - ', 1)[0] if agent_field else ''
        if short not in counts:
            continue
        d_at = _parse_ts(ev)
        if not d_at:
            continue
        day = d_at.astimezone(dt.timezone.utc).date()
        if day in counts[short]:
            counts[short][day] += 1

    out: dict[str, AgentSeries] = {}
    for n in short_names:
        vals = [counts[n][d] for d in bucket_dates]
        out[n] = AgentSeries(
            short_name=n,
            total=sum(vals),
            values=vals,
            points=spark_points([float(v) for v in vals]),
        )
    return out


def skill_calls_period(events: list[dict[str, Any]],
                        days: int = 7,
                        today: dt.date | None = None) -> dict[str, int]:
    """Total calls per skill across the trailing `days` window."""
    today = today or dt.datetime.now(dt.timezone.utc).date()
    cutoff = dt.datetime.combine(
        today - dt.timedelta(days=days - 1),
        dt.time.min,
        tzinfo=dt.timezone.utc,
    )
    counts: dict[str, int] = {}
    for ev in events:
        if ev.get('kind') != 'llm_call':
            continue
        d_at = _parse_ts(ev)
        if not d_at or d_at < cutoff:
            continue
        skill = ev.get('skill')
        if skill:
            counts[skill] = counts.get(skill, 0) + 1
    return counts


# ─── live page helpers (Onda 4) ──────────────────────────────────────────────

def recent_events(events: list[dict[str, Any]],
                  *,
                  limit: int = 50,
                  agent: str | None = None,
                  skill: str | None = None,
                  kind:  str | None = None) -> list[dict[str, Any]]:
    """Return events filtered + sorted newest first, capped to `limit`.

    `agent` matches the short prefix (before ' - '). Empty filter values
    (None or '') mean 'no filter'.
    """
    out: list[dict[str, Any]] = []
    for ev in events:
        if agent:
            short = (ev.get('agent') or '').split(' - ', 1)[0]
            if short != agent:
                continue
        if skill and ev.get('skill') != skill:
            continue
        if kind and ev.get('kind') != kind:
            continue
        out.append(ev)
    out.sort(key=lambda e: e.get('ts') or '', reverse=True)
    return out[:limit]


def event_facets(events: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Unique values for the filter dropdowns. Empty lists if no events."""
    agents: set[str] = set()
    skills: set[str] = set()
    kinds:  set[str] = set()
    for ev in events:
        a = (ev.get('agent') or '').split(' - ', 1)[0]
        if a:
            agents.add(a)
        s = ev.get('skill')
        if s:
            skills.add(s)
        k = ev.get('kind')
        if k:
            kinds.add(k)
    return {
        'agents': sorted(agents),
        'skills': sorted(skills),
        'kinds':  sorted(kinds),
    }


@dataclass
class RoutingRow:
    agent:      str          # short name (e.g. 'Forge')
    skill:      str
    count:      int
    pct:        int          # 0..100 — width of the bar relative to busiest pair
    agent_tier: str          # for color hinting; '?' if unknown


# Map canonical agent short name → tier id used for the routing bar color.
# Mirrors AGENT_TIERS in orquestrum.lib.models but indexed by short name.
_AGENT_SHORT_TIER: dict[str, str] = {
    'Helm':   'deep',
    'Trace':  'balanced',
    'Lore':   'balanced',
    'Forge':  'balanced',
    'Cipher': 'balanced',
    'Ward':   'balanced',
    'Cast':   'mechanical',
    'Flux':   'balanced',
}


def routing_matrix(events: list[dict[str, Any]],
                   days: int = 7,
                   today: dt.date | None = None,
                   limit: int = 30) -> list[RoutingRow]:
    """Per-(agent, skill) call counts over the trailing window.

    Returns rows sorted by count desc, capped to `limit` (so the page stays
    readable even when many pairs exist).
    """
    today = today or dt.datetime.now(dt.timezone.utc).date()
    cutoff = dt.datetime.combine(
        today - dt.timedelta(days=days - 1),
        dt.time.min,
        tzinfo=dt.timezone.utc,
    )
    counts: dict[tuple[str, str], int] = {}
    for ev in events:
        if ev.get('kind') != 'llm_call':
            continue
        d_at = _parse_ts(ev)
        if not d_at or d_at < cutoff:
            continue
        agent_field = (ev.get('agent') or '').strip()
        short = agent_field.split(' - ', 1)[0] if agent_field else ''
        skill = ev.get('skill') or ''
        if not short or not skill:
            continue
        counts[(short, skill)] = counts.get((short, skill), 0) + 1

    if not counts:
        return []

    pairs = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    cap   = pairs[0][1]
    return [
        RoutingRow(
            agent=a,
            skill=s,
            count=c,
            pct=int(round(c / cap * 100)) if cap else 0,
            agent_tier=_AGENT_SHORT_TIER.get(a, '?'),
        )
        for (a, s), c in pairs
    ]


def event_density(events: list[dict[str, Any]],
                  *,
                  buckets: int = 30,
                  bucket_minutes: int = 2,
                  now: dt.datetime | None = None) -> list[int]:
    """Density of events per `bucket_minutes` slots, oldest→newest, len=`buckets`.

    Used to render the mini timeline at the bottom of /live/session
    (default: 30 buckets × 2 min = trailing 60 minutes).
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    bucket_s = bucket_minutes * 60
    starts = [now - dt.timedelta(minutes=bucket_minutes * (buckets - i)) for i in range(buckets)]
    counts = [0] * buckets
    earliest = starts[0]
    for ev in events:
        d_at = _parse_ts(ev)
        if not d_at or d_at < earliest:
            continue
        delta = (d_at - earliest).total_seconds()
        idx = int(delta // bucket_s)
        if 0 <= idx < buckets:
            counts[idx] += 1
    return counts
