"""Tests for framework-mode server routes (/, /catalog, /dashboard, /docs)."""
from __future__ import annotations
from pathlib import Path

import httpx
import pytest

from ui.config import UIConfig
from ui.server import _home_stats, create_app


def _make_framework_config(tmp_path: Path) -> UIConfig:
    (tmp_path / 'agents').mkdir()
    (tmp_path / 'skills').mkdir()
    (tmp_path / 'orquestrum').mkdir()
    (tmp_path / 'docs' / 'agent-context').mkdir(parents=True)
    return UIConfig(
        mode='framework',
        root=tmp_path,
        metrics_dir=None,
        targets_path=Path('~/.orquestrum/targets.json').expanduser(),
        port=7700,
    )


@pytest.fixture()
def framework_config(tmp_path: Path) -> UIConfig:
    return _make_framework_config(tmp_path)


@pytest.fixture()
async def fw_client(framework_config: UIConfig) -> httpx.AsyncClient:
    app = create_app(framework_config)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://test',
    ) as c:
        yield c


# ─── _home_stats ─────────────────────────────────────────────────────────────

class TestHomeStats:
    def test_framework_counts_agents(self, framework_config: UIConfig):
        (framework_config.root / 'agents' / 'agent1.md').write_text('---\nname: A1\n---\n')
        (framework_config.root / 'agents' / 'agent2.md').write_text('---\nname: A2\n---\n')
        stats = _home_stats(framework_config)
        assert stats['agents'] == 2

    def test_framework_counts_skills(self, framework_config: UIConfig):
        skill = framework_config.root / 'skills' / 'my-skill'
        skill.mkdir()
        (skill / 'SKILL.md').write_text('---\nname: my-skill\n---\n')
        stats = _home_stats(framework_config)
        assert stats['skills'] == 1

    def test_framework_zero_events(self, framework_config: UIConfig):
        stats = _home_stats(framework_config)
        assert stats['event_count'] == 0
        assert stats['last_event'] is None

    def test_project_counts_agents_in_claude_dir(self, tmp_path: Path):
        cfg = UIConfig(
            mode='project',
            root=tmp_path,
            metrics_dir=tmp_path / '.orquestrum' / 'metrics',
            targets_path=None,
            port=7700,
            linked_project_root=tmp_path,
        )
        d = tmp_path / '.claude' / 'agents'
        d.mkdir(parents=True)
        (d / 'a.md').write_text('---\nname: A\n---\n')
        stats = _home_stats(cfg)
        assert stats['agents'] == 1

    def test_project_reads_events_file(self, tmp_path: Path):
        metrics = tmp_path / '.orquestrum' / 'metrics'
        metrics.mkdir(parents=True)
        (metrics / 'events.jsonl').write_text(
            '{"kind":"llm_call"}\n{"kind":"llm_call"}\n', encoding='utf-8'
        )
        cfg = UIConfig(
            mode='project',
            root=tmp_path,
            metrics_dir=metrics,
            targets_path=None,
            port=7700,
        )
        stats = _home_stats(cfg)
        assert stats['event_count'] == 2

    def test_never_raises_on_bad_state(self, tmp_path: Path):
        cfg = UIConfig(
            mode='project',
            root=tmp_path,
            metrics_dir=tmp_path / 'missing' / 'metrics',
            targets_path=None,
            port=7700,
        )
        # Should not raise
        stats = _home_stats(cfg)
        assert isinstance(stats, dict)


# ─── Framework mode routes ────────────────────────────────────────────────────

class TestFrameworkHome:
    async def test_home_returns_200(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/')
        assert r.status_code == 200

    async def test_home_shows_agent_count(
        self, fw_client: httpx.AsyncClient, framework_config: UIConfig
    ):
        (framework_config.root / 'agents' / 'test.md').write_text(
            '---\nname: Test\n---\n'
        )
        r = await fw_client.get('/')
        assert r.status_code == 200

    async def test_catalog_returns_200(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/catalog')
        assert r.status_code == 200

    async def test_audits_returns_200(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/audits')
        assert r.status_code == 200

    async def test_health_shows_framework_mode(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/health')
        assert r.json()['mode'] == 'framework'
