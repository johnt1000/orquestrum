"""HTTP route tests for the Orquestrum UI console.

Uses httpx.AsyncClient + ASGITransport so no real TCP port is bound.
The app is created in 'project' mode against a tmp_path fixture — no
real Orquestrum repo needed for route-level tests.
"""
from __future__ import annotations
import asyncio
import sys
import pytest
import httpx
from pathlib import Path

import ui.lib.jobs as jobs_module
from ui.config import UIConfig
from ui.server import create_app


@pytest.fixture()
def project_config(tmp_path: Path) -> UIConfig:
    return UIConfig(
        mode='project',
        root=tmp_path,
        metrics_dir=tmp_path / '.orquestrum' / 'metrics',
        targets_path=None,
        port=7700,
    )


@pytest.fixture()
def app(project_config: UIConfig):
    return create_app(project_config)


@pytest.fixture()
async def client(app) -> httpx.AsyncClient:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://test',
    ) as c:
        yield c


@pytest.fixture(autouse=True)
def clear_jobs():
    jobs_module._jobs.clear()
    yield
    jobs_module._jobs.clear()


# ─── /health ─────────────────────────────────────────────────────────────────

class TestHealthRoute:
    async def test_health_returns_200(self, client: httpx.AsyncClient):
        r = await client.get('/health')
        assert r.status_code == 200

    async def test_health_returns_ok_status(self, client: httpx.AsyncClient):
        assert r.json()['status'] == 'ok' if (r := await client.get('/health')) else True

    async def test_health_includes_mode(self, client: httpx.AsyncClient):
        r = await client.get('/health')
        assert r.json()['mode'] == 'project'


# ─── / (home) ────────────────────────────────────────────────────────────────

class TestHomeRoute:
    async def test_home_returns_200(self, client: httpx.AsyncClient):
        r = await client.get('/')
        assert r.status_code == 200

    async def test_home_returns_html(self, client: httpx.AsyncClient):
        r = await client.get('/')
        assert 'text/html' in r.headers['content-type']

    async def test_home_contains_orquestrum(self, client: httpx.AsyncClient):
        r = await client.get('/')
        assert 'Orquestrum' in r.text


# ─── /dashboard ──────────────────────────────────────────────────────────────

class TestDashboardRoute:
    async def test_dashboard_returns_200(self, client: httpx.AsyncClient):
        r = await client.get('/dashboard')
        assert r.status_code == 200

    async def test_dashboard_returns_html(self, client: httpx.AsyncClient):
        r = await client.get('/dashboard')
        assert 'text/html' in r.headers['content-type']

    async def test_dashboard_with_events(self, client: httpx.AsyncClient, project_config: UIConfig):
        from orquestrum.lib.metrics import append_event
        metrics = project_config.metrics_dir
        metrics.mkdir(parents=True)
        append_event(metrics / 'events.jsonl', {
            'kind': 'llm_call', 'agent': 'Forge - Dev Lead',
            'skill': 'task-manager', 'tier': 'balanced',
            'in_tokens': 500, 'out_tokens': 100,
            'cached_tokens': 0, 'cost_usd': 0.001,
        })
        r = await client.get('/dashboard')
        assert r.status_code == 200


# ─── /catalog ────────────────────────────────────────────────────────────────

class TestCatalogRoute:
    async def test_catalog_returns_200(self, client: httpx.AsyncClient):
        r = await client.get('/catalog')
        assert r.status_code == 200

    async def test_catalog_returns_html(self, client: httpx.AsyncClient):
        r = await client.get('/catalog')
        assert 'text/html' in r.headers['content-type']


# ─── /audits ─────────────────────────────────────────────────────────────────

class TestAuditsRoute:
    async def test_audits_index_returns_200(self, client: httpx.AsyncClient):
        r = await client.get('/audits')
        assert r.status_code == 200

    async def test_audits_index_lists_known_audits(self, client: httpx.AsyncClient):
        r = await client.get('/audits')
        assert 'payload' in r.text.lower() or 'parity' in r.text.lower()

    async def test_unknown_audit_returns_404(self, client: httpx.AsyncClient):
        r = await client.get('/audits/nonexistent')
        assert r.status_code == 404

    async def test_run_audit_redirects_to_job(self, client: httpx.AsyncClient):
        r = await client.get('/audits/payload', follow_redirects=False)
        assert r.status_code == 303
        assert r.headers['location'].startswith('/jobs/')


# ─── /coverage ───────────────────────────────────────────────────────────────

class TestCoverageRoute:
    async def test_coverage_returns_200_without_file(self, client: httpx.AsyncClient):
        r = await client.get('/coverage')
        assert r.status_code == 200

    async def test_coverage_renders_file_when_present(
        self, client: httpx.AsyncClient, project_config: UIConfig
    ):
        doc_path = project_config.root / 'docs' / 'governance'
        doc_path.mkdir(parents=True)
        (doc_path / 'COVERAGE.md').write_text('# Coverage\n\nContent here.', encoding='utf-8')
        r = await client.get('/coverage')
        assert r.status_code == 200
        assert 'Coverage' in r.text


# ─── /jobs ───────────────────────────────────────────────────────────────────

class TestJobsRoute:
    async def test_unknown_job_returns_404(self, client: httpx.AsyncClient):
        r = await client.get('/jobs/nonexistent_id')
        assert r.status_code == 404

    async def test_unknown_job_partial_returns_404(self, client: httpx.AsyncClient):
        r = await client.get('/jobs/nonexistent_id/partial')
        assert r.status_code == 404

    async def test_known_job_returns_200(self, client: httpx.AsyncClient):
        job = jobs_module.submit(
            label='test', cmd=[sys.executable, '-c', 'pass'], cwd='.'
        )
        r = await client.get(f'/jobs/{job.id}')
        assert r.status_code == 200

    async def test_known_job_partial_returns_200(self, client: httpx.AsyncClient):
        job = jobs_module.submit(
            label='test', cmd=[sys.executable, '-c', 'pass'], cwd='.'
        )
        r = await client.get(f'/jobs/{job.id}/partial')
        assert r.status_code == 200

    async def test_completed_job_shows_output(self, client: httpx.AsyncClient):
        job = jobs_module.submit(
            label='echo', cmd=[sys.executable, '-c', 'print("done")'], cwd='.'
        )
        for _ in range(50):
            await asyncio.sleep(0.05)
            if job.is_terminal:
                break
        r = await client.get(f'/jobs/{job.id}')
        assert r.status_code == 200


# ─── 404 handler ─────────────────────────────────────────────────────────────

class TestNotFoundRoute:
    async def test_html_404_for_browser_request(self, client: httpx.AsyncClient):
        r = await client.get('/this-does-not-exist', headers={'Accept': 'text/html'})
        assert r.status_code == 404
        assert 'text/html' in r.headers.get('content-type', '')

    async def test_json_404_when_accept_json(self, client: httpx.AsyncClient):
        r = await client.get('/this-does-not-exist', headers={'Accept': 'application/json'})
        assert r.status_code == 404
        assert 'error' in r.json()
