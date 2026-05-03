"""Tests for the Onda 3 catalog redesign:
- /catalog 303 → /catalog/agents
- /catalog/agents grid renders, contains tier badges + agent cards
- /catalog/skills table renders, contains filter input + dep chips
- PT/EN labels on both pages
"""
from __future__ import annotations
from pathlib import Path

import httpx
import pytest

from ui.config import UIConfig
from ui.server import LOCALE_COOKIE, create_app


def _framework_root_with_canon() -> Path:
    """Use the live repo as a framework — has 8 agents + 25 skills."""
    return Path(__file__).resolve().parents[2]


@pytest.fixture()
def fw_config() -> UIConfig:
    root = _framework_root_with_canon()
    return UIConfig(
        mode='framework',
        root=root,
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


# ─── /catalog redirect ──────────────────────────────────────────────────────

class TestCatalogRedirect:
    async def test_old_catalog_303s_to_agents(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/catalog', follow_redirects=False)
        assert r.status_code == 303
        assert r.headers['location'] == '/catalog/agents'


# ─── /catalog/agents ────────────────────────────────────────────────────────

class TestCatalogAgents:
    async def test_returns_200(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/catalog/agents')
        assert r.status_code == 200

    async def test_renders_grid_markers(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/catalog/agents')
        assert 'agent-grid'   in r.text
        assert 'agent-card'   in r.text
        assert 'tier-badge'   in r.text
        assert 'catalog-tabs' in r.text

    async def test_emoji_rendered_for_canonical_agents(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/catalog/agents')
        # Helm has 🏛️ in its frontmatter; at minimum some non-trivial emoji per agent
        assert 'agent-card-emoji' in r.text

    async def test_pt_labels(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/catalog/agents')
        assert 'Agentes' in r.text
        assert 'chamadas 7d' in r.text

    async def test_en_labels(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/catalog/agents', cookies={LOCALE_COOKIE: 'en'})
        assert 'Agents' in r.text
        assert 'calls 7d' in r.text


# ─── /catalog/skills ────────────────────────────────────────────────────────

class TestCatalogSkills:
    async def test_returns_200(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/catalog/skills')
        assert r.status_code == 200

    async def test_renders_table_markers(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/catalog/skills')
        assert 'skill-table'   in r.text
        assert 'skill-filter'  in r.text
        assert 'catalog-tabs'  in r.text
        assert 'id="skill-search"' in r.text

    async def test_pt_labels(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/catalog/skills')
        assert 'Habilidades' in r.text
        assert 'Depende' in r.text

    async def test_en_labels(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/catalog/skills', cookies={LOCALE_COOKIE: 'en'})
        assert 'Skills' in r.text
        assert 'Depends on' in r.text

    async def test_dep_chips_render_for_skills_with_deps(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/catalog/skills')
        # Some skills have depends_on (e.g. task-manager → epic-manager). At least one chip present.
        assert 'skill-dep-chip' in r.text or 'skill-empty' in r.text


# ─── catalog tabs nav ───────────────────────────────────────────────────────

class TestCatalogTabs:
    async def test_agents_tab_active_on_agents_page(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/catalog/agents')
        assert 'href="/catalog/agents" class="catalog-tab is-active"' in r.text

    async def test_skills_tab_active_on_skills_page(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/catalog/skills')
        assert 'href="/catalog/skills" class="catalog-tab is-active"' in r.text


# ─── AgentRow.emoji ─────────────────────────────────────────────────────────

class TestAgentRowEmoji:
    def test_agent_row_has_emoji_field(self, fw_config: UIConfig):
        from ui.lib.catalog_loader import list_agents
        agents = list_agents(fw_config.root / 'agents')
        assert agents, "framework should have at least one agent"
        for a in agents:
            assert hasattr(a, 'emoji')
            assert a.emoji  # non-empty (frontmatter or '◇' fallback)

    def test_short_name_strips_suffix(self, fw_config: UIConfig):
        from ui.lib.catalog_loader import list_agents
        agents = list_agents(fw_config.root / 'agents')
        for a in agents:
            if ' - ' in a.name:
                assert a.short_name == a.name.split(' - ', 1)[0]
            else:
                assert a.short_name == a.name


# ─── live_metrics catalog helpers ───────────────────────────────────────────

class TestCatalogMetrics:
    def test_agent_calls_series_empty_returns_zero(self):
        from ui.lib.live_metrics import agent_calls_series
        out = agent_calls_series([], short_names=['Helm', 'Forge'])
        assert set(out.keys()) == {'Helm', 'Forge'}
        assert out['Helm'].total == 0
        assert len(out['Helm'].values) == 7
        assert out['Helm'].points  # spark_points renders flat midline even at zero

    def test_skill_calls_period_buckets_to_window(self):
        import datetime as dt
        from ui.lib.live_metrics import skill_calls_period
        evs = [
            {'ts': '2026-05-03T10:00:00Z', 'kind': 'llm_call', 'skill': 'a'},
            {'ts': '2026-05-02T10:00:00Z', 'kind': 'llm_call', 'skill': 'a'},
            {'ts': '2026-04-15T10:00:00Z', 'kind': 'llm_call', 'skill': 'a'},  # outside window
            {'ts': '2026-05-01T10:00:00Z', 'kind': 'llm_call', 'skill': 'b'},
        ]
        out = skill_calls_period(evs, days=7, today=dt.date(2026, 5, 3))
        assert out == {'a': 2, 'b': 1}
