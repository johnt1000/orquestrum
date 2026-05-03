"""Tests for the Onda 2 extensions of ui.lib.live_metrics:
spark_points, series_by_day, agent_calls_by_day, last_event_dt.
"""
from __future__ import annotations
import datetime as dt
from typing import Any

import pytest

from ui.lib import live_metrics as lm


def _ev(ts_iso: str, *, agent: str = 'Forge - Dev Lead', skill: str = 'task-manager',
        in_tokens: int = 100, out_tokens: int = 50, cached: int = 0,
        cost: float = 0.001, kind: str = 'llm_call') -> dict[str, Any]:
    return {
        'ts': ts_iso, 'kind': kind, 'agent': agent, 'skill': skill,
        'in_tokens': in_tokens, 'out_tokens': out_tokens,
        'cached_tokens': cached, 'cost_usd': cost,
    }


# ─── spark_points ───────────────────────────────────────────────────────────

class TestSparkPoints:
    def test_empty_returns_empty_string(self):
        assert lm.spark_points([]) == ''

    def test_single_value_renders_flat_midline(self):
        assert lm.spark_points([5]) == '0,12.00 100,12.00'

    def test_constant_series_renders_flat_midline(self):
        pts = lm.spark_points([3, 3, 3, 3]).split()
        ys = [float(p.split(',')[1]) for p in pts]
        assert all(y == 12.0 for y in ys)

    def test_increasing_series_y_decreases(self):
        # Higher values should map to lower y (svg origin is top-left).
        pts = lm.spark_points([0, 5, 10])
        ys  = [float(p.split(',')[1]) for p in pts.split()]
        assert ys[0] > ys[1] > ys[2]

    def test_x_spans_full_width(self):
        pts = lm.spark_points([1, 2, 3, 4, 5])
        xs  = [float(p.split(',')[0]) for p in pts.split()]
        assert xs[0] == 0.0
        assert xs[-1] == 100.0


# ─── last_event_dt ──────────────────────────────────────────────────────────

class TestLastEventDt:
    def test_empty_returns_none(self):
        assert lm.last_event_dt([]) is None

    def test_picks_max(self):
        evs = [_ev('2026-04-01T10:00:00Z'), _ev('2026-05-01T10:00:00Z'), _ev('2026-04-15T10:00:00Z')]
        latest = lm.last_event_dt(evs)
        assert latest is not None and latest.month == 5

    def test_ignores_invalid_ts(self):
        evs = [_ev('not a date'), _ev('2026-05-01T10:00:00Z')]
        latest = lm.last_event_dt(evs)
        assert latest is not None and latest.year == 2026


# ─── series_by_day ──────────────────────────────────────────────────────────

class TestSeriesByDay:
    @pytest.fixture()
    def today(self):
        return dt.date(2026, 5, 3)

    def test_empty_events_zero_totals(self, today):
        s = lm.series_by_day([], today=today)
        assert s['cost'].formatted == '$0.0000'
        assert s['calls'].formatted == '0'
        assert s['cached'].formatted == '0%'
        assert s['skills'].formatted == '0'
        assert all(v == 0 for v in s['cost'].values)
        assert s['cost'].sparkline_points  # not empty — flat line for the empty 7-day window

    def test_one_event_today(self, today):
        ts = '2026-05-03T10:00:00Z'
        s = lm.series_by_day([_ev(ts, in_tokens=1000, out_tokens=200, cached=400, cost=0.01)], today=today)
        assert s['calls'].formatted == '1'
        assert s['cost'].formatted == '$0.0100'
        assert s['cached'].formatted == '40%'
        assert s['skills'].formatted == '1'
        # Today is the last bucket, value should be > 0 there
        assert s['calls'].values[-1] == 1.0

    def test_returns_seven_buckets(self, today):
        s = lm.series_by_day([], days=7, today=today)
        assert len(s['cost'].values) == 7
        assert len(s['calls'].values) == 7

    def test_delta_against_previous_period(self, today):
        # 5 events in current week, 2 in previous → calls delta = +3
        cur  = [_ev('2026-05-01T10:00:00Z') for _ in range(5)]
        prev = [_ev('2026-04-25T10:00:00Z') for _ in range(2)]
        s = lm.series_by_day(cur + prev, today=today)
        assert s['calls'].delta_text == '+3'
        assert s['calls'].delta_cls  == 'is-up-good'

    def test_cost_up_is_warn(self, today):
        cur  = [_ev('2026-05-01T10:00:00Z', cost=1.0)]
        prev = [_ev('2026-04-25T10:00:00Z', cost=0.5)]
        s = lm.series_by_day(cur + prev, today=today)
        assert s['cost'].delta_cls == 'is-up-bad'

    def test_skill_completion_event_is_ignored(self, today):
        evs = [{
            'ts': '2026-05-01T10:00:00Z', 'kind': 'skill_completion',
            'skill': 'spec-manager', 'agent': 'Helm - Architect',
        }]
        s = lm.series_by_day(evs, today=today)
        assert s['calls'].formatted == '0'


# ─── agent_calls_by_day ─────────────────────────────────────────────────────

class TestAgentCallsByDay:
    AGENTS = [('Helm', '🏛️'), ('Forge', '⚙️'), ('Lore', '🎯')]

    def test_empty_events_returns_zero_rows(self):
        rows, days = lm.agent_calls_by_day([], agents=self.AGENTS)
        assert len(rows) == 3
        assert all(c.count == 0 for r in rows for c in r.cells)
        assert len(days) == 7

    def test_matches_short_name_prefix(self):
        evs = [
            _ev('2026-05-03T10:00:00Z', agent='Forge - Dev Lead'),
            _ev('2026-05-03T11:00:00Z', agent='Helm - The Architect'),
            _ev('2026-05-02T10:00:00Z', agent='Forge - Dev Lead'),
        ]
        rows, _ = lm.agent_calls_by_day(
            evs, agents=self.AGENTS, today=dt.date(2026, 5, 3)
        )
        forge = next(r for r in rows if r.name == 'Forge')
        helm  = next(r for r in rows if r.name == 'Helm')
        assert sum(c.count for c in forge.cells) == 2
        assert sum(c.count for c in helm.cells) == 1

    def test_opacity_normalized(self):
        # 1 event for Helm, 5 for Forge — Forge should have a darker max cell
        evs = [_ev('2026-05-03T10:00:00Z', agent='Helm - The Architect')]
        evs += [_ev('2026-05-03T10:00:00Z', agent='Forge - Dev Lead') for _ in range(5)]
        rows, _ = lm.agent_calls_by_day(
            evs, agents=self.AGENTS, today=dt.date(2026, 5, 3)
        )
        helm  = next(r for r in rows if r.name == 'Helm').cells[-1]
        forge = next(r for r in rows if r.name == 'Forge').cells[-1]
        assert forge.opacity > helm.opacity
        assert forge.opacity <= 1.0
        assert helm.opacity > 0.0

    def test_locale_picks_day_labels(self):
        _, days_pt = lm.agent_calls_by_day([], agents=self.AGENTS, locale='pt')
        _, days_en = lm.agent_calls_by_day([], agents=self.AGENTS, locale='en')
        assert all(d in {'seg','ter','qua','qui','sex','sáb','dom'} for d in days_pt)
        assert all(d in {'mon','tue','wed','thu','fri','sat','sun'} for d in days_en)
