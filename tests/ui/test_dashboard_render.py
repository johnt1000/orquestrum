"""End-to-end smoke for the new /dashboard layout: assert the new markers
are present (pipeline rail, KPI cards, heatmap, donut, recent jobs).
"""
from __future__ import annotations
from pathlib import Path

import httpx
import pytest

from ui.config import UIConfig
from ui.server import create_app


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
async def client(project_config: UIConfig) -> httpx.AsyncClient:
    app = create_app(project_config)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://test',
    ) as c:
        yield c


class TestDashboardLayout:
    async def test_renders_with_no_events(self, client: httpx.AsyncClient):
        r = await client.get('/dashboard')
        assert r.status_code == 200
        assert 'pipeline-rail' in r.text
        assert 'kpi-grid'      in r.text
        assert 'heatmap'       in r.text
        assert 'recent-jobs-title' in r.text

    async def test_kpi_labels_in_pt(self, client: httpx.AsyncClient):
        r = await client.get('/dashboard')
        assert 'Custo'      in r.text
        assert 'Chamadas'   in r.text
        assert 'Cache'      in r.text

    async def test_kpi_labels_in_en(self, client: httpx.AsyncClient):
        from ui.server import LOCALE_COOKIE
        r = await client.get('/dashboard', cookies={LOCALE_COOKIE: 'en'})
        assert 'Cost'  in r.text
        assert 'Calls' in r.text

    async def test_renders_with_events(self, client: httpx.AsyncClient, project_config: UIConfig):
        from orquestrum.lib.metrics import append_event
        events = project_config.metrics_dir / 'events.jsonl'
        for i in range(3):
            append_event(events, {
                'kind': 'llm_call',
                'agent': 'Forge - Dev Lead',
                'skill': f'skill-{i}',
                'tier': 'balanced',
                'in_tokens': 1000, 'out_tokens': 200,
                'cached_tokens': 400, 'cost_usd': 0.01,
            })
        r = await client.get('/dashboard')
        assert r.status_code == 200
        assert 'sparkline'  in r.text
        assert 'phase-chip' in r.text
        # The single skill line in the bar list should appear
        assert 'bar-list'   in r.text

    async def test_pipeline_rail_marks_active_phase(self, client: httpx.AsyncClient,
                                                     project_config: UIConfig):
        from orquestrum.lib.metrics import append_event
        events = project_config.metrics_dir / 'events.jsonl'
        # 3 events from Forge → planning phase should be active
        for _ in range(3):
            append_event(events, {
                'kind': 'llm_call', 'agent': 'Forge - Dev Lead',
                'skill': 'task-manager', 'tier': 'balanced',
                'in_tokens': 100, 'out_tokens': 50, 'cached_tokens': 0,
                'cost_usd': 0.001,
            })
        r = await client.get('/dashboard')
        assert 'is-active' in r.text


class TestSidebarCounts:
    async def test_jobs_running_count_zero(self, client: httpx.AsyncClient):
        r = await client.get('/dashboard')
        # Topbar shows the count interpolation; with 0 jobs running it reads "0 em execução"
        assert '0 em execução' in r.text or '0 running' in r.text


class TestEmptyStates:
    async def test_no_project_renders(self, tmp_path: Path):
        cfg = UIConfig(
            mode='framework',
            root=tmp_path,
            metrics_dir=None,
            targets_path=None,
            port=7700,
        )
        # Make it look like framework but with no .orquestrum
        (tmp_path / 'agents').mkdir()
        (tmp_path / 'skills').mkdir()
        app = create_app(cfg)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test',
        ) as c:
            r = await c.get('/dashboard')
        assert r.status_code == 200
        assert 'empty-state' in r.text or 'Visão geral' in r.text
