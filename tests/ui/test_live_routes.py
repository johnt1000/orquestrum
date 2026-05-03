"""Tests for the Onda 4 / R13 live observability pages.

Covers:
- /live/session full + partial endpoints, filter narrowing
- /live/routing aggregation
- /live/attention scatter rendering
- live_metrics.recent_events / event_facets / routing_matrix / event_density
- attention.attention_timeline / scatter_points
"""
from __future__ import annotations
import datetime as dt
from pathlib import Path

import httpx
import pytest

from ui.config import UIConfig
from ui.lib import live_metrics as lm
from ui.lib.attention import attention_timeline, scatter_points, AttentionItem
from ui.server import LOCALE_COOKIE, create_app


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture()
def project_config(tmp_path: Path) -> UIConfig:
    metrics = tmp_path / '.orquestrum' / 'metrics'
    metrics.mkdir(parents=True)
    return UIConfig(
        mode='project',
        root=tmp_path,
        metrics_dir=metrics,
        targets_path=None,
        port=7700,
        linked_project_root=tmp_path,
    )


@pytest.fixture()
def project_with_events(project_config: UIConfig) -> UIConfig:
    from orquestrum.lib.metrics import append_event
    events = project_config.metrics_dir / 'events.jsonl'
    base = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
    pairs = [
        ('Forge - Dev Lead',          'task-manager'),
        ('Forge - Dev Lead',          'task-manager'),
        ('Helm - The Architect',      'spec-manager'),
        ('Lore - Product Strategist', 'spec-manager'),
        ('Forge - Dev Lead',          'qa-manager'),
    ]
    for i, (agent, skill) in enumerate(pairs):
        ts = (base + dt.timedelta(minutes=i)).strftime('%Y-%m-%dT%H:%M:%SZ')
        append_event(events, {
            'ts': ts, 'kind': 'llm_call',
            'agent': agent, 'skill': skill, 'tier': 'balanced',
            'in_tokens': 1000, 'out_tokens': 200,
            'cached_tokens': 0, 'cost_usd': 0.001,
        })
    return project_config


@pytest.fixture()
async def client(project_with_events: UIConfig) -> httpx.AsyncClient:
    app = create_app(project_with_events)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://test',
    ) as c:
        yield c


# ─── live_metrics helpers ───────────────────────────────────────────────────

def _ev(ts: str, *, agent: str = 'Forge - Dev Lead', skill: str = 'task-manager',
        kind: str = 'llm_call') -> dict:
    return {
        'ts': ts, 'kind': kind, 'agent': agent, 'skill': skill,
        'in_tokens': 100, 'out_tokens': 50, 'cached_tokens': 0, 'cost_usd': 0.001,
    }


class TestRecentEvents:
    def test_empty_returns_empty(self):
        assert lm.recent_events([]) == []

    def test_newest_first(self):
        evs = [_ev('2026-05-01T10:00:00Z'), _ev('2026-05-03T10:00:00Z'), _ev('2026-05-02T10:00:00Z')]
        out = lm.recent_events(evs)
        assert out[0]['ts'] == '2026-05-03T10:00:00Z'
        assert out[-1]['ts'] == '2026-05-01T10:00:00Z'

    def test_limit_caps_results(self):
        evs = [_ev(f'2026-05-{i:02d}T10:00:00Z') for i in range(1, 11)]
        assert len(lm.recent_events(evs, limit=3)) == 3

    def test_agent_filter_matches_short_name(self):
        evs = [_ev('2026-05-03T10:00:00Z', agent='Forge - Dev Lead'),
               _ev('2026-05-03T11:00:00Z', agent='Helm - The Architect')]
        out = lm.recent_events(evs, agent='Helm')
        assert len(out) == 1 and 'Helm' in out[0]['agent']

    def test_empty_filter_means_no_filter(self):
        evs = [_ev('2026-05-03T10:00:00Z')]
        assert lm.recent_events(evs, agent=None, skill=None) == evs

    def test_skill_filter(self):
        evs = [_ev('2026-05-03T10:00:00Z', skill='a'), _ev('2026-05-03T11:00:00Z', skill='b')]
        out = lm.recent_events(evs, skill='b')
        assert len(out) == 1 and out[0]['skill'] == 'b'


class TestEventFacets:
    def test_empty_yields_empty_lists(self):
        out = lm.event_facets([])
        assert out == {'agents': [], 'skills': [], 'kinds': []}

    def test_dedupes_and_sorts(self):
        evs = [
            _ev('2026-05-03T10:00:00Z', agent='Forge - Dev Lead', skill='a'),
            _ev('2026-05-03T11:00:00Z', agent='Helm - Architect',  skill='b'),
            _ev('2026-05-03T12:00:00Z', agent='Forge - Dev Lead', skill='a'),
        ]
        out = lm.event_facets(evs)
        assert out['agents'] == ['Forge', 'Helm']
        assert out['skills'] == ['a', 'b']
        assert out['kinds']  == ['llm_call']


class TestRoutingMatrix:
    def test_empty_returns_empty(self):
        assert lm.routing_matrix([]) == []

    def test_aggregates_pairs(self):
        evs = [
            _ev('2026-05-03T10:00:00Z', agent='Forge - X', skill='a'),
            _ev('2026-05-03T11:00:00Z', agent='Forge - X', skill='a'),
            _ev('2026-05-03T12:00:00Z', agent='Helm - Y',  skill='b'),
        ]
        rows = lm.routing_matrix(evs, today=dt.date(2026, 5, 3))
        # Forge/a counted 2, Helm/b counted 1
        first = rows[0]
        assert first.agent == 'Forge' and first.skill == 'a' and first.count == 2
        assert first.pct == 100
        assert any(r.agent == 'Helm' and r.skill == 'b' and r.count == 1 for r in rows)

    def test_skips_outside_window(self):
        evs = [
            _ev('2026-04-15T10:00:00Z', agent='Forge - X', skill='a'),  # too old
            _ev('2026-05-03T10:00:00Z', agent='Helm - Y',  skill='b'),
        ]
        rows = lm.routing_matrix(evs, days=7, today=dt.date(2026, 5, 3))
        assert len(rows) == 1 and rows[0].agent == 'Helm'

    def test_tier_hint_for_canonical_agents(self):
        evs = [_ev('2026-05-03T10:00:00Z', agent='Helm - Architect', skill='x')]
        rows = lm.routing_matrix(evs, today=dt.date(2026, 5, 3))
        assert rows[0].agent_tier == 'deep'


class TestEventDensity:
    def test_empty_yields_zero_buckets(self):
        out = lm.event_density([], buckets=10, bucket_minutes=2)
        assert out == [0] * 10

    def test_recent_event_lands_in_last_bucket(self):
        now = dt.datetime.now(dt.timezone.utc)
        ts  = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        out = lm.event_density([_ev(ts)], buckets=10, bucket_minutes=2, now=now)
        assert sum(out) == 1
        assert out[-1] == 1


# ─── attention_timeline ─────────────────────────────────────────────────────

class TestAttentionTimeline:
    def test_no_root_returns_empty(self):
        assert attention_timeline(None) == []

    def test_picks_up_score_with_frontmatter_ts(self, tmp_path: Path):
        d = tmp_path / 'docs' / '03-quality' / 'review'
        d.mkdir(parents=True)
        (d / 'r1.md').write_text(
            '---\nattention_score: 75\nts: 2026-05-01T10:00:00Z\nskill: spec-manager\n---\n# r1\n',
            encoding='utf-8',
        )
        items = attention_timeline(tmp_path, days=30, today=dt.date(2026, 5, 3))
        assert len(items) == 1
        assert items[0].score == 75
        assert items[0].band == 'green'
        assert items[0].skill == 'spec-manager'

    def test_falls_back_to_file_mtime(self, tmp_path: Path):
        d = tmp_path / 'docs' / '03-quality'
        d.mkdir(parents=True)
        (d / 'a.md').write_text('---\nattention_score: 40\n---\n', encoding='utf-8')
        items = attention_timeline(tmp_path, days=365)
        assert len(items) == 1 and items[0].score == 40

    def test_skips_outside_window(self, tmp_path: Path):
        d = tmp_path / 'docs' / '03-quality'
        d.mkdir(parents=True)
        (d / 'old.md').write_text(
            '---\nattention_score: 90\nts: 2024-01-01T00:00:00Z\n---\n',
            encoding='utf-8',
        )
        items = attention_timeline(tmp_path, days=30, today=dt.date(2026, 5, 3))
        assert items == []


class TestScatterPoints:
    def test_empty_returns_empty(self):
        assert scatter_points([]) == []

    def test_centers_single_point(self):
        item = AttentionItem(
            ts=dt.datetime(2026, 5, 1, tzinfo=dt.timezone.utc),
            score=72, band='green', skill='x', drift_risk='', factors=[], source='x',
        )
        pts = scatter_points([item], width=400, height=200, padding=20)
        assert len(pts) == 1
        assert pts[0].cx == 200.0  # centered

    def test_higher_score_yields_lower_y(self):
        items = [
            AttentionItem(ts=dt.datetime(2026, 5, 1, tzinfo=dt.timezone.utc), score=10,
                          band='red', skill='lo', drift_risk='', factors=[], source='lo'),
            AttentionItem(ts=dt.datetime(2026, 5, 2, tzinfo=dt.timezone.utc), score=90,
                          band='green', skill='hi', drift_risk='', factors=[], source='hi'),
        ]
        pts = scatter_points(items, height=100, padding=10)
        lo = next(p for p in pts if p.score == 10)
        hi = next(p for p in pts if p.score == 90)
        assert hi.cy < lo.cy


# ─── HTTP routes ────────────────────────────────────────────────────────────

class TestLiveSessionRoute:
    async def test_returns_200(self, client: httpx.AsyncClient):
        r = await client.get('/live/session')
        assert r.status_code == 200

    async def test_renders_filter_chips(self, client: httpx.AsyncClient):
        r = await client.get('/live/session')
        assert 'filter-chips' in r.text
        assert 'name="agent"' in r.text
        assert 'name="skill"' in r.text

    async def test_renders_event_tail(self, client: httpx.AsyncClient):
        r = await client.get('/live/session')
        assert 'id="event-tail"' in r.text
        assert 'event-row' in r.text  # 5 events fixture

    async def test_partial_returns_swap_target(self, client: httpx.AsyncClient):
        r = await client.get('/live/session/partial')
        assert r.status_code == 200
        # The partial is just the wrapper div, no <html> shell
        assert 'id="event-tail"' in r.text
        assert '<html' not in r.text

    async def test_filter_narrows_results(self, client: httpx.AsyncClient):
        r_all  = await client.get('/live/session/partial')
        r_helm = await client.get('/live/session/partial?agent=Helm')
        all_count  = r_all.text.count('event-row')
        helm_count = r_helm.text.count('event-row')
        assert helm_count > 0
        assert helm_count < all_count

    async def test_pt_labels(self, client: httpx.AsyncClient):
        r = await client.get('/live/session')
        assert 'Sessão' in r.text
        assert 'Agente' in r.text
        assert 'atualizando a cada 2s' in r.text

    async def test_en_labels(self, client: httpx.AsyncClient):
        r = await client.get('/live/session', cookies={LOCALE_COOKIE: 'en'})
        assert 'Session' in r.text
        assert 'updating every 2s' in r.text


class TestLiveRoutingRoute:
    async def test_returns_200(self, client: httpx.AsyncClient):
        r = await client.get('/live/routing')
        assert r.status_code == 200

    async def test_renders_routing_grid(self, client: httpx.AsyncClient):
        r = await client.get('/live/routing')
        assert 'routing-grid' in r.text
        assert 'routing-bar'  in r.text

    async def test_shows_aggregated_pairs(self, client: httpx.AsyncClient):
        r = await client.get('/live/routing')
        # Forge/task-manager appears twice in fixture → top row
        assert 'Forge' in r.text
        assert 'task-manager' in r.text


class TestLiveAttentionRoute:
    async def test_returns_200_empty(self, client: httpx.AsyncClient):
        r = await client.get('/live/attention')
        assert r.status_code == 200
        # No quality docs in fixture → empty state
        assert 'live.attention.empty' not in r.text  # i18n resolves it
        assert 'Sem scores' in r.text or 'No attention' in r.text

    async def test_renders_scatter_with_data(self, project_config: UIConfig):
        d = project_config.linked_project_root / 'docs' / '03-quality' / 'review'
        d.mkdir(parents=True)
        (d / 'r1.md').write_text('---\nattention_score: 80\n---\n', encoding='utf-8')
        (d / 'r2.md').write_text('---\nattention_score: 30\n---\n', encoding='utf-8')
        app = create_app(project_config)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test',
        ) as c:
            r = await c.get('/live/attention')
        assert r.status_code == 200
        assert 'attention-svg' in r.text
        assert '<circle' in r.text


class TestLiveSidebar:
    async def test_sidebar_links_to_live_pages(self, client: httpx.AsyncClient):
        r = await client.get('/dashboard')
        assert 'href="/live/session"'   in r.text
        assert 'href="/live/routing"'   in r.text
        assert 'href="/live/attention"' in r.text
        # No more disabled markers for the live group
        # (other groups may still have is-disabled — just confirm Live items are anchors)
