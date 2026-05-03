"""attention.py — scan project artifacts for attention scores and bucket into bands.

Sources: any *.md under docs/03-quality/ (review, qa, learning) whose frontmatter
declares an `attention_score` (0–100). This is a project-side artifact convention
documented in docs/agent-context/CONVENTIONS.md (R2/R13 wave).

Bands:
  green  → score >= 67
  yellow → 34–66
  red    → score <= 33

Returns None when no artifacts are found so the dashboard can hide the panel
without error.
"""
from __future__ import annotations
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import frontmatter


@dataclass
class AttentionReport:
    green:  int
    yellow: int
    red:    int
    avg:    int          # rounded mean
    p95:    int          # rounded 95th percentile
    total:  int
    score:  int          # alias for avg, surfaced as the donut center number


def _band(score: int) -> str:
    if score >= 67:
        return 'green'
    if score >= 34:
        return 'yellow'
    return 'red'


def _percentile(values: list[int], pct: float) -> int:
    if not values:
        return 0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round(pct / 100 * (len(s) - 1)))))
    return s[k]


def _iter_quality_md(root: Path) -> Iterable[Path]:
    base = root / 'docs' / '03-quality'
    if not base.is_dir():
        return []
    return base.rglob('*.md')


def attention_bands(root: Path | None) -> AttentionReport | None:
    """Scan docs/03-quality/ for attention_score frontmatter. None if no data."""
    if root is None or not Path(root).is_dir():
        return None

    scores: list[int] = []
    for md in _iter_quality_md(Path(root)):
        try:
            post = frontmatter.load(md)
        except Exception:
            continue
        raw = post.metadata.get('attention_score')
        if raw is None:
            continue
        try:
            s = int(raw)
        except (TypeError, ValueError):
            continue
        if 0 <= s <= 100:
            scores.append(s)

    if not scores:
        return None

    bands = {'green': 0, 'yellow': 0, 'red': 0}
    for s in scores:
        bands[_band(s)] += 1
    avg = round(sum(scores) / len(scores))
    return AttentionReport(
        green=bands['green'],
        yellow=bands['yellow'],
        red=bands['red'],
        avg=avg,
        p95=_percentile(scores, 95),
        total=len(scores),
        score=avg,
    )


# ─── timeline + scatter (Onda 4 / R13 /live/attention) ─────────────────────

@dataclass
class AttentionItem:
    ts:         dt.datetime
    score:      int
    band:       str
    skill:      str
    drift_risk: str
    factors:    list[str]
    source:     str   # path relative to project root


@dataclass
class ScatterPoint:
    ts:         dt.datetime
    score:      int
    band:       str
    skill:      str
    drift_risk: str
    factors:    list[str]
    source:     str
    cx:         float
    cy:         float


def _coerce_dt(raw: Any) -> dt.datetime | None:
    if raw is None:
        return None
    if isinstance(raw, dt.datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=dt.timezone.utc)
    if isinstance(raw, dt.date):
        return dt.datetime(raw.year, raw.month, raw.day, tzinfo=dt.timezone.utc)
    if isinstance(raw, str):
        try:
            d = dt.datetime.fromisoformat(raw.replace('Z', '+00:00'))
            return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
        except ValueError:
            return None
    return None


def attention_timeline(root: Path | None,
                       days: int = 30,
                       today: dt.date | None = None) -> list[AttentionItem]:
    """Per-artifact attention scores within the trailing window.

    Date source priority: frontmatter `ts` → `updated_at` → `created` → file mtime.
    """
    if root is None or not Path(root).is_dir():
        return []
    today = today or dt.datetime.now(dt.timezone.utc).date()
    cutoff = today - dt.timedelta(days=days)

    out: list[AttentionItem] = []
    base = Path(root) / 'docs' / '03-quality'
    if not base.is_dir():
        return []
    for md in base.rglob('*.md'):
        try:
            post = frontmatter.load(md)
        except Exception:
            continue
        raw_score = post.metadata.get('attention_score')
        if raw_score is None:
            continue
        try:
            score = int(raw_score)
        except (TypeError, ValueError):
            continue
        if not (0 <= score <= 100):
            continue

        ts = (
            _coerce_dt(post.metadata.get('ts'))
            or _coerce_dt(post.metadata.get('updated_at'))
            or _coerce_dt(post.metadata.get('created'))
        )
        if ts is None:
            try:
                ts = dt.datetime.fromtimestamp(md.stat().st_mtime, tz=dt.timezone.utc)
            except OSError:
                continue
        if ts.date() < cutoff:
            continue

        try:
            rel = str(md.relative_to(root))
        except ValueError:
            rel = md.name

        factors = post.metadata.get('attention_factors') or []
        if isinstance(factors, str):
            factors = [factors]

        out.append(AttentionItem(
            ts=ts,
            score=score,
            band=_band(score),
            skill=str(post.metadata.get('skill') or md.stem),
            drift_risk=str(post.metadata.get('drift_risk') or ''),
            factors=list(factors),
            source=rel,
        ))

    out.sort(key=lambda it: it.ts)
    return out


def scatter_points(items: list[AttentionItem],
                   width: int = 800,
                   height: int = 240,
                   padding: int = 24) -> list[ScatterPoint]:
    """Map timeline items to SVG (cx, cy) coordinates.

    x: linear time within [t_min, t_max]; y: 0..100 with 100 at the top.
    Single-point series renders centered on the x axis.
    """
    if not items:
        return []
    times = [it.ts.timestamp() for it in items]
    t_min, t_max = min(times), max(times)
    t_rng = t_max - t_min
    inner_w = width  - 2 * padding
    inner_h = height - 2 * padding

    out: list[ScatterPoint] = []
    for it in items:
        if t_rng > 0:
            x = padding + (it.ts.timestamp() - t_min) / t_rng * inner_w
        else:
            # Single point or all-same-timestamp: center horizontally.
            x = width / 2
        # Score 100 → top, 0 → bottom
        y = padding + (1 - it.score / 100) * inner_h
        out.append(ScatterPoint(
            ts=it.ts, score=it.score, band=it.band, skill=it.skill,
            drift_risk=it.drift_risk, factors=it.factors, source=it.source,
            cx=round(x, 1), cy=round(y, 1),
        ))
    return out
