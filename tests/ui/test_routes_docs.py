"""Route tests for /docs, /docs/search, /docs/view."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

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


@pytest.fixture()
def project_with_docs(tmp_path: Path) -> UIConfig:
    """A project config whose root has a docs/ tree."""
    docs_gov = tmp_path / 'docs' / 'governance'
    docs_gov.mkdir(parents=True)
    (docs_gov / 'MODELS.md').write_text('# Models\nContent.\n', encoding='utf-8')

    docs_ctx = tmp_path / 'docs' / 'agent-context'
    docs_ctx.mkdir(parents=True)
    (docs_ctx / 'SDLC.md').write_text('# SDLC\nPipeline.\n', encoding='utf-8')

    (tmp_path / 'README.md').write_text('# Readme\nHello.\n', encoding='utf-8')
    return UIConfig(
        mode='project',
        root=tmp_path,
        metrics_dir=tmp_path / '.orquestrum' / 'metrics',
        targets_path=None,
        port=7700,
    )


@pytest.fixture()
async def docs_client(project_with_docs: UIConfig) -> httpx.AsyncClient:
    app = create_app(project_with_docs)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://test',
    ) as c:
        yield c


# ─── /docs (index) ───────────────────────────────────────────────────────────

class TestDocsIndex:
    async def test_returns_200(self, client: httpx.AsyncClient):
        r = await client.get('/docs')
        assert r.status_code == 200

    async def test_returns_html(self, client: httpx.AsyncClient):
        r = await client.get('/docs')
        assert 'text/html' in r.headers['content-type']

    async def test_shows_doc_titles(self, docs_client: httpx.AsyncClient):
        r = await docs_client.get('/docs')
        assert r.status_code == 200
        assert 'Models' in r.text

    async def test_shows_readme(self, docs_client: httpx.AsyncClient):
        r = await docs_client.get('/docs')
        assert 'Readme' in r.text

    async def test_empty_root_shows_page(self, client: httpx.AsyncClient):
        r = await client.get('/docs')
        assert r.status_code == 200


# ─── /docs/search ────────────────────────────────────────────────────────────

class TestDocsSearch:
    async def test_returns_200_no_query(self, client: httpx.AsyncClient):
        r = await client.get('/docs/search')
        assert r.status_code == 200

    async def test_returns_200_with_query(self, docs_client: httpx.AsyncClient):
        with patch('shutil.which', return_value=None):
            r = await docs_client.get('/docs/search?q=Pipeline')
        assert r.status_code == 200

    async def test_finds_content(self, docs_client: httpx.AsyncClient):
        with patch('shutil.which', return_value=None):
            r = await docs_client.get('/docs/search?q=Pipeline')
        assert 'Pipeline' in r.text

    async def test_empty_query_shows_page(self, docs_client: httpx.AsyncClient):
        r = await docs_client.get('/docs/search?q=')
        assert r.status_code == 200

    async def test_no_match_shows_page(self, docs_client: httpx.AsyncClient):
        with patch('shutil.which', return_value=None):
            r = await docs_client.get('/docs/search?q=zzznomatch')
        assert r.status_code == 200


# ─── /docs/view ──────────────────────────────────────────────────────────────

class TestDocsView:
    async def test_view_existing_doc(self, docs_client: httpx.AsyncClient):
        r = await docs_client.get('/docs/view?p=docs/governance/MODELS.md')
        assert r.status_code == 200
        assert 'Models' in r.text

    async def test_view_readme(self, docs_client: httpx.AsyncClient):
        r = await docs_client.get('/docs/view?p=README.md')
        assert r.status_code == 200

    async def test_view_nonexistent_returns_404(self, docs_client: httpx.AsyncClient):
        r = await docs_client.get('/docs/view?p=docs/governance/MISSING.md')
        assert r.status_code == 404

    async def test_view_non_md_returns_404(self, docs_client: httpx.AsyncClient, project_with_docs):
        (project_with_docs.root / 'notes.txt').write_text('hello', encoding='utf-8')
        r = await docs_client.get('/docs/view?p=notes.txt')
        assert r.status_code == 404

    async def test_view_path_escape_returns_400(self, docs_client: httpx.AsyncClient):
        r = await docs_client.get('/docs/view?p=../../../etc/passwd')
        assert r.status_code == 400

    async def test_view_renders_markdown_html(self, docs_client: httpx.AsyncClient):
        r = await docs_client.get('/docs/view?p=docs/agent-context/SDLC.md')
        assert r.status_code == 200
        # rendered markdown has HTML tags
        assert '<h1>' in r.text or '<p>' in r.text
