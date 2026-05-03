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
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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
