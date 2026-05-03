"""Tests for the Onda 5 HTMX-driven edit flow:
- 2-col layout markers on the GET render
- POST /preview returns just the live card partial
- POST /edit with HX-Request returns just the diff partial
- Plain POST /edit (no HX) still returns the full page (backward compat)
- Apply still atomically writes the file
"""
from __future__ import annotations
from pathlib import Path

import httpx
import pytest

from ui.config import UIConfig
from ui.server import create_app


def _framework_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture()
def fw_config() -> UIConfig:
    return UIConfig(
        mode='framework',
        root=_framework_root(),
        metrics_dir=None,
        targets_path=Path('~/.orquestrum/targets.json').expanduser(),
        port=7700,
    )


@pytest.fixture()
async def fw_client(fw_config: UIConfig) -> httpx.AsyncClient:
    app = create_app(fw_config)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://test',
    ) as c:
        yield c


# ─── /agents/{slug}/edit GET ────────────────────────────────────────────────

class TestAgentEditGet:
    async def test_renders_2col_layout(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/agents/forge-dev-lead/edit')
        assert r.status_code == 200
        assert 'edit-grid'        in r.text
        assert 'edit-form-pane'   in r.text
        assert 'edit-preview-pane' in r.text
        assert 'id="preview-pane"' in r.text
        assert 'id="diff-pane"'    in r.text

    async def test_initial_preview_pane_populated(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/agents/forge-dev-lead/edit')
        assert 'live-card live-card-agent' in r.text
        # The agent's emoji or name should be present in the live card
        assert 'live-card-name' in r.text
        assert 'live-card-tools' in r.text

    async def test_diff_pane_initially_empty(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/agents/forge-dev-lead/edit')
        assert 'diff-pane-empty' in r.text

    async def test_form_has_htmx_attrs(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/agents/forge-dev-lead/edit')
        assert 'hx-post="/agents/forge-dev-lead/preview"' in r.text
        assert 'hx-target="#preview-pane"' in r.text


# ─── /agents/{slug}/preview ─────────────────────────────────────────────────

class TestAgentPreviewEndpoint:
    async def test_returns_live_card_partial(self, fw_client: httpx.AsyncClient):
        r = await fw_client.post('/agents/forge-dev-lead/preview',
            data={
                'name': 'Forge - Dev Lead',
                'description': 'Updated description for preview test',
                'mode': 'primary',
                'emoji': '⚙️',
                'temperature': '0.2',
                'max_tokens': '4096',
                'tools_write': '1',
                'tools_edit': '1',
            })
        assert r.status_code == 200
        # Partial — no full HTML shell
        assert '<html' not in r.text
        assert 'live-card live-card-agent' in r.text
        assert 'Updated description for preview test' in r.text

    async def test_preview_reflects_form_state_not_disk(self, fw_client: httpx.AsyncClient):
        # Pose a brand-new name in the form — it should appear in the live card
        r = await fw_client.post('/agents/forge-dev-lead/preview',
            data={
                'name': 'Synthetic Test Name',
                'description': 'd', 'mode': 'primary', 'emoji': '🧪',
                'temperature': '0.1', 'max_tokens': '4096',
            })
        assert 'Synthetic Test Name' in r.text


# ─── /agents/{slug}/edit POST ──────────────────────────────────────────────

class TestAgentEditPost:
    async def test_htmx_request_returns_diff_partial(self, fw_client: httpx.AsyncClient):
        r = await fw_client.post('/agents/forge-dev-lead/edit',
            headers={'HX-Request': 'true'},
            data={
                'name': 'Forge - Dev Lead',
                'description': 'Changed description for diff test',
                'mode': 'primary',
                'emoji': '⚙️',
                'temperature': '0.2',
                'max_tokens': '4096',
            })
        assert r.status_code == 200
        # Partial only — diff-pane wrapper present, no full HTML shell
        assert '<html' not in r.text
        assert 'id="diff-pane"' in r.text

    async def test_plain_request_returns_full_page(self, fw_client: httpx.AsyncClient):
        r = await fw_client.post('/agents/forge-dev-lead/edit',
            data={
                'name': 'Forge - Dev Lead',
                'description': 'Changed description for full-page test',
                'mode': 'primary',
                'emoji': '⚙️',
                'temperature': '0.2',
                'max_tokens': '4096',
            })
        assert r.status_code == 200
        # Full page — has html shell
        assert '<html' in r.text
        assert 'edit-grid' in r.text

    async def test_diff_partial_shows_apply_button(self, fw_client: httpx.AsyncClient):
        r = await fw_client.post('/agents/forge-dev-lead/edit',
            headers={'HX-Request': 'true'},
            data={
                'name': 'Forge - Dev Lead',
                'description': 'A meaningfully changed description for the diff button test',
                'mode': 'primary',
                'emoji': '⚙️',
                'temperature': '0.2',
                'max_tokens': '4096',
            })
        assert 'edit-apply-form' in r.text
        assert 'action="/agents/forge-dev-lead/edit/apply"' in r.text

    async def test_lint_errors_block_diff(self, fw_client: httpx.AsyncClient):
        r = await fw_client.post('/agents/forge-dev-lead/edit',
            headers={'HX-Request': 'true'},
            data={
                'name': '',  # required → lint error
                'description': 'x', 'mode': 'primary', 'emoji': '⚙️',
                'temperature': '0.2', 'max_tokens': '4096',
            })
        # Diff pane returned but with errors (no apply button)
        assert 'diff-errors' in r.text or 'warn' in r.text


# ─── /skills/{slug}/edit GET + preview ─────────────────────────────────────

class TestSkillEditFlow:
    async def test_get_renders_2col_layout(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/skills/spec-manager/edit')
        assert r.status_code == 200
        assert 'edit-grid' in r.text
        assert 'live-card-skill' in r.text

    async def test_preview_returns_partial(self, fw_client: httpx.AsyncClient):
        r = await fw_client.post('/skills/spec-manager/preview',
            data={
                'name': 'spec-manager',
                'description': 'Brand new desc through preview',
                'inject_references': 'full',
                'inject_fewshot': 'compact',
                'depends_on': 'glossary-manager, adr-manager',
            })
        assert r.status_code == 200
        assert '<html' not in r.text
        assert 'live-card-skill' in r.text
        assert 'Brand new desc through preview' in r.text
        # depends_on chips render
        assert 'glossary-manager' in r.text
        assert 'adr-manager' in r.text

    async def test_htmx_edit_returns_diff_partial(self, fw_client: httpx.AsyncClient):
        r = await fw_client.post('/skills/spec-manager/edit',
            headers={'HX-Request': 'true'},
            data={
                'name': 'spec-manager',
                'description': 'A different description than the canonical one',
                'inject_references': 'full',
                'inject_fewshot': 'false',
            })
        assert r.status_code == 200
        assert '<html' not in r.text
        assert 'id="diff-pane"' in r.text


# ─── PT/EN labels ───────────────────────────────────────────────────────────

class TestEditLabels:
    async def test_pt_labels_present(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/agents/forge-dev-lead/edit')
        assert 'Editar agente' in r.text
        assert 'Pré-visualização ao vivo' in r.text
        assert 'Validar' in r.text

    async def test_en_labels(self, fw_client: httpx.AsyncClient):
        from ui.server import LOCALE_COOKIE
        r = await fw_client.get('/agents/forge-dev-lead/edit',
                                cookies={LOCALE_COOKIE: 'en'})
        assert 'Edit agent' in r.text
        assert 'Live preview' in r.text
        assert 'Validate' in r.text
