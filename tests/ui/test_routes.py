"""HTTP route tests for the Orquestrum UI console.

Uses httpx.AsyncClient + ASGITransport so no real TCP port is bound.
The app is created in 'project' mode against a tmp_path fixture — no
real Orquestrum repo needed for route-level tests.
"""
from __future__ import annotations
import pytest
import httpx
from pathlib import Path

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


class TestHealthRoute:
    async def test_healthz_returns_200(self, client: httpx.AsyncClient):
        r = await client.get('/healthz')
        assert r.status_code == 200

    async def test_healthz_returns_ok_status(self, client: httpx.AsyncClient):
        r = await client.get('/healthz')
        data = r.json()
        assert data['status'] == 'ok'

    async def test_healthz_includes_mode(self, client: httpx.AsyncClient):
        r = await client.get('/healthz')
        assert r.json()['mode'] == 'project'


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


class TestNotFoundRoute:
    async def test_html_404_for_browser_request(self, client: httpx.AsyncClient):
        r = await client.get('/this-does-not-exist', headers={'Accept': 'text/html'})
        assert r.status_code == 404
        assert 'text/html' in r.headers.get('content-type', '')

    async def test_json_404_when_accept_json(self, client: httpx.AsyncClient):
        r = await client.get('/this-does-not-exist', headers={'Accept': 'application/json'})
        assert r.status_code == 404
        data = r.json()
        assert 'error' in data


class TestJobsRoute:
    async def test_unknown_job_returns_404(self, client: httpx.AsyncClient):
        r = await client.get('/jobs/nonexistent_id')
        assert r.status_code == 404

    async def test_unknown_job_partial_returns_404(self, client: httpx.AsyncClient):
        r = await client.get('/jobs/nonexistent_id/partial')
        assert r.status_code == 404
