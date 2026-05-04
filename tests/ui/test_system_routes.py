"""Tests for the new /system/* routes (installs, doctor, mcp).

These pages mirror the corresponding `orquestrum <subcommand>` CLI
commands. Each route renders, surfaces the same data the CLI would,
and accepts POSTs (prune, mcp add/remove, validate) that delegate to
either the lib helpers (in-process) or the async job runner (subprocess).
"""
from __future__ import annotations
import json
from pathlib import Path

import httpx
import pytest

from ui.config import UIConfig
from ui.server import create_app


def _framework_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture()
def fw_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> UIConfig:
    """Framework-mode config + isolated ORQUESTRUM_HOME so installs.json
    writes (from prune) don't pollute the user's real manifest."""
    home = tmp_path / 'orq-home'
    home.mkdir()
    monkeypatch.setenv('ORQUESTRUM_HOME', str(home))
    return UIConfig(
        mode='framework',
        root=_framework_root(),
        metrics_dir=None,
        targets_path=home / 'targets.json',
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


# ─── /system/installs ──────────────────────────────────────────────────────


class TestInstallsRoute:
    async def test_index_renders_empty_state(
        self, fw_client: httpx.AsyncClient,
    ):
        r = await fw_client.get('/system/installs')
        assert r.status_code == 200
        # Empty manifest → "No installs yet" or similar
        assert 'install' in r.text.lower()

    async def test_index_lists_records_when_present(
        self, fw_client: httpx.AsyncClient, tmp_path: Path,
    ):
        # Seed a fake install record
        from orquestrum.lib import paths
        import os
        manifest_path = paths.orquestrum_home() / 'installs.json'
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        valid_target = tmp_path / 'real-project'
        valid_target.mkdir()
        manifest_path.write_text(json.dumps({
            'schema_version': 1,
            'installs': [{
                'target': str(valid_target),
                'tool': 'claude-code',
                'orquestrum_version': '0.5.1',
                'installed_at': '2026-05-04T10:00:00',
                'files': ['agents/x.md'],
                'directories': ['agents'],
            }, {
                'target': str(tmp_path / 'gone'),  # stale
                'tool': 'claude-code',
                'orquestrum_version': '0.5.0',
                'installed_at': '2026-05-03T10:00:00',
                'files': [], 'directories': [],
            }],
        }), encoding='utf-8')

        r = await fw_client.get('/system/installs')
        assert r.status_code == 200
        # Both records visible
        assert str(valid_target) in r.text
        # Stale marker shown so user knows there's something to prune
        assert 'stale' in r.text.lower()
        # Prune CTA exposes the dead count
        assert 'prune' in r.text.lower() or 'podar' in r.text.lower()

    async def test_prune_post_redirects_to_job(
        self, fw_client: httpx.AsyncClient,
    ):
        r = await fw_client.post('/system/installs/prune', follow_redirects=False)
        assert r.status_code == 303
        assert r.headers['location'].startswith('/jobs/')


# ─── /system/doctor ────────────────────────────────────────────────────────


class TestDoctorRoute:
    async def test_index_renders_with_results(
        self, fw_client: httpx.AsyncClient,
    ):
        """The doctor route spawns the actual CLI as a subprocess. We
        accept any non-error render — the smoke is that `--json` parses
        and the template doesn't crash on the result shape."""
        r = await fw_client.get('/system/doctor')
        assert r.status_code == 200
        # Page renders the summary cards
        text = r.text
        assert 'Erros' in text or 'Errors' in text
        assert 'Avisos' in text or 'Warnings' in text


# ─── /system/mcp ───────────────────────────────────────────────────────────


class TestMcpRoute:
    async def test_index_renders_tool_catalog(
        self, fw_client: httpx.AsyncClient,
    ):
        """The MCP route always lists the orq_* tool catalog (8 tools,
        2 resources) regardless of whether any MCPs are registered."""
        r = await fw_client.get('/system/mcp')
        assert r.status_code == 200
        # Tool catalog rendered (these are static — server.py registry)
        assert 'orq_session_summary' in r.text
        assert 'orq_record_event' in r.text
        # Add form rendered
        assert 'system.mcp.add' in r.text or 'Add MCP' in r.text or 'Adicionar' in r.text

    async def test_add_post_writes_to_settings(
        self, fw_client: httpx.AsyncClient, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # Redirect Path.home() so the add doesn't touch the user's
        # real ~/.claude/settings.json
        fake = tmp_path / 'fake-home'
        fake.mkdir()
        monkeypatch.setattr(Path, 'home', staticmethod(lambda: fake))
        r = await fw_client.post('/system/mcp/add', data={
            'name':        'test-fs',
            'command':     'npx',
            'args':        '-y @modelcontextprotocol/server-filesystem /tmp',
            'server_type': 'stdio',
        }, follow_redirects=False)
        assert r.status_code == 303
        # Wrote settings.json with the entry
        settings_path = fake / '.claude' / 'settings.json'
        assert settings_path.exists()
        data = json.loads(settings_path.read_text())
        assert 'test-fs' in data['mcpServers']
        assert data['mcpServers']['test-fs']['command'] == 'npx'
        assert data['mcpServers']['test-fs']['args'] == [
            '-y', '@modelcontextprotocol/server-filesystem', '/tmp',
        ]

    async def test_remove_protected_orquestrum_without_force(
        self, fw_client: httpx.AsyncClient, tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        fake = tmp_path / 'fake-home'
        (fake / '.claude').mkdir(parents=True)
        (fake / '.claude' / 'settings.json').write_text(json.dumps({
            'mcpServers': {
                'orquestrum': {'command': 'orquestrum', 'args': ['mcp']},
                'filesystem': {'command': 'npx'},
            }
        }), encoding='utf-8')
        monkeypatch.setattr(Path, 'home', staticmethod(lambda: fake))

        # Attempt to remove orquestrum WITHOUT force → should be no-op
        r = await fw_client.post('/system/mcp/remove', data={
            'name': 'orquestrum',
        }, follow_redirects=False)
        assert r.status_code == 303
        # Verify orquestrum still there
        data = json.loads((fake / '.claude' / 'settings.json').read_text())
        assert 'orquestrum' in data['mcpServers']

    async def test_validate_post_redirects_to_job(
        self, fw_client: httpx.AsyncClient,
    ):
        r = await fw_client.post('/system/mcp/validate', follow_redirects=False)
        assert r.status_code == 303
        assert r.headers['location'].startswith('/jobs/')
