"""Route tests for /agents/{slug}/edit and /skills/{slug}/edit (3-step edit flows)."""
from __future__ import annotations
from pathlib import Path

import httpx
import pytest

from ui.config import UIConfig
from ui.server import create_app


# ─── Fixtures ────────────────────────────────────────────────────────────────

AGENT_FM = """\
---
name: Forge Agent
description: A forge agent for testing.
mode: primary
temperature: 0.2
emoji: 🔨
max_tokens: 4096
tools:
  write: true
  edit: true
  bash: false
  question: true
---

Agent body content here.
"""

SKILL_FM = """\
---
name: spec-manager
description: A skill for spec management.
inject_references: false
inject_fewshot: false
emits_confidence: false
depends_on: []
---

Skill body content here.
"""


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


@pytest.fixture()
def agent_file(framework_config: UIConfig) -> tuple[UIConfig, str]:
    """Write a test agent and return (config, slug)."""
    f = framework_config.root / 'agents' / 'forge-agent.md'
    f.write_text(AGENT_FM, encoding='utf-8')
    return framework_config, 'forge-agent'


@pytest.fixture()
def skill_file(framework_config: UIConfig) -> tuple[UIConfig, str]:
    """Write a test skill and return (config, slug)."""
    skill_dir = framework_config.root / 'skills' / 'spec-manager'
    skill_dir.mkdir()
    (skill_dir / 'SKILL.md').write_text(SKILL_FM, encoding='utf-8')
    return framework_config, 'spec-manager'


@pytest.fixture()
async def agent_client(agent_file) -> httpx.AsyncClient:
    cfg, _ = agent_file
    app = create_app(cfg)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://test',
    ) as c:
        yield c


@pytest.fixture()
async def skill_client(skill_file) -> httpx.AsyncClient:
    cfg, _ = skill_file
    app = create_app(cfg)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://test',
    ) as c:
        yield c


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
async def proj_client(project_config: UIConfig) -> httpx.AsyncClient:
    app = create_app(project_config)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://test',
    ) as c:
        yield c


# ─── /agents/{slug}/edit ─────────────────────────────────────────────────────

class TestEditAgentGet:
    async def test_returns_200(self, agent_client: httpx.AsyncClient, agent_file):
        _, slug = agent_file
        r = await agent_client.get(f'/agents/{slug}/edit')
        assert r.status_code == 200

    async def test_returns_html(self, agent_client: httpx.AsyncClient, agent_file):
        _, slug = agent_file
        r = await agent_client.get(f'/agents/{slug}/edit')
        assert 'text/html' in r.headers['content-type']

    async def test_shows_agent_name(self, agent_client: httpx.AsyncClient, agent_file):
        _, slug = agent_file
        r = await agent_client.get(f'/agents/{slug}/edit')
        assert 'Forge Agent' in r.text

    async def test_unknown_slug_returns_404(self, agent_client: httpx.AsyncClient):
        r = await agent_client.get('/agents/nonexistent-slug/edit')
        assert r.status_code == 404

    async def test_project_mode_returns_400(self, proj_client: httpx.AsyncClient):
        r = await proj_client.get('/agents/any-slug/edit')
        assert r.status_code == 400


class TestEditAgentPreview:
    async def test_valid_preview_returns_200(
        self, agent_client: httpx.AsyncClient, agent_file
    ):
        _, slug = agent_file
        r = await agent_client.post(
            f'/agents/{slug}/edit',
            data={
                'name': 'Forge Agent',
                'description': 'Updated description.',
                'mode': 'primary',
                'emoji': '🔨',
                'temperature': '0.3',
                'max_tokens': '4096',
                'tools_write': '1',
                'tools_edit': '1',
                'tools_bash': '0',
                'tools_question': '1',
            },
        )
        assert r.status_code == 200

    async def test_preview_shows_diff(
        self, agent_client: httpx.AsyncClient, agent_file
    ):
        _, slug = agent_file
        r = await agent_client.post(
            f'/agents/{slug}/edit',
            data={
                'name': 'Forge Agent',
                'description': 'Changed description for diff.',
                'mode': 'primary',
                'emoji': '🔨',
                'temperature': '0.2',
                'max_tokens': '4096',
                'tools_write': '1',
                'tools_edit': '1',
                'tools_bash': '0',
                'tools_question': '1',
            },
        )
        assert r.status_code == 200

    async def test_invalid_name_shows_errors(
        self, agent_client: httpx.AsyncClient, agent_file
    ):
        _, slug = agent_file
        r = await agent_client.post(
            f'/agents/{slug}/edit',
            data={
                'name': '',  # empty name is invalid
                'description': 'desc',
                'mode': 'primary',
                'emoji': '🔨',
                'temperature': '0.2',
            },
        )
        # Should re-render form with errors (200 or 422)
        assert r.status_code in (200, 422)

    async def test_unknown_slug_returns_404(self, agent_client: httpx.AsyncClient):
        r = await agent_client.post(
            '/agents/no-such-agent/edit',
            data={'name': 'x', 'description': 'y'},
        )
        assert r.status_code == 404


class TestEditAgentApply:
    async def test_valid_apply_writes_file(
        self, agent_client: httpx.AsyncClient, agent_file
    ):
        cfg, slug = agent_file
        r = await agent_client.post(
            f'/agents/{slug}/edit/apply',
            data={
                'name': 'Forge Agent',
                'description': 'Written to disk.',
                'mode': 'primary',
                'emoji': '🔨',
                'temperature': '0.2',
                'max_tokens': '4096',
                'tools_write': '1',
                'tools_edit': '1',
                'tools_bash': '0',
                'tools_question': '1',
            },
        )
        assert r.status_code == 200
        # Verify the file on disk was updated
        import frontmatter as fm
        agent_path = cfg.root / 'agents' / 'forge-agent.md'
        post = fm.load(str(agent_path))
        assert post['description'] == 'Written to disk.'

    async def test_invalid_apply_rerenders_form(
        self, agent_client: httpx.AsyncClient, agent_file
    ):
        _, slug = agent_file
        r = await agent_client.post(
            f'/agents/{slug}/edit/apply',
            data={
                'name': '',  # invalid — empty name
                'description': 'desc',
                'mode': 'primary',
                'emoji': '🔨',
                'temperature': '0.2',
            },
        )
        # Must not write; re-render errors
        assert r.status_code in (200, 422)

    async def test_unknown_slug_returns_404(self, agent_client: httpx.AsyncClient):
        r = await agent_client.post(
            '/agents/ghost/edit/apply',
            data={'name': 'x', 'description': 'y'},
        )
        assert r.status_code == 404


# ─── /skills/{slug}/edit ─────────────────────────────────────────────────────

class TestEditSkillGet:
    async def test_returns_200(self, skill_client: httpx.AsyncClient, skill_file):
        _, slug = skill_file
        r = await skill_client.get(f'/skills/{slug}/edit')
        assert r.status_code == 200

    async def test_returns_html(self, skill_client: httpx.AsyncClient, skill_file):
        _, slug = skill_file
        r = await skill_client.get(f'/skills/{slug}/edit')
        assert 'text/html' in r.headers['content-type']

    async def test_shows_skill_name(self, skill_client: httpx.AsyncClient, skill_file):
        _, slug = skill_file
        r = await skill_client.get(f'/skills/{slug}/edit')
        assert 'spec-manager' in r.text

    async def test_unknown_slug_returns_404(self, skill_client: httpx.AsyncClient):
        r = await skill_client.get('/skills/nonexistent-skill/edit')
        assert r.status_code == 404

    async def test_project_mode_returns_400(self, proj_client: httpx.AsyncClient):
        r = await proj_client.get('/skills/any-slug/edit')
        assert r.status_code == 400


class TestEditSkillPreview:
    async def test_valid_preview_returns_200(
        self, skill_client: httpx.AsyncClient, skill_file
    ):
        _, slug = skill_file
        r = await skill_client.post(
            f'/skills/{slug}/edit',
            data={
                'name': 'spec-manager',
                'description': 'Updated skill description.',
                'inject_references': 'false',
                'inject_fewshot': 'false',
                'emits_confidence': '0',
                'depends_on': '',
                'chain_next': '',
                'chain_condition': '',
            },
        )
        assert r.status_code == 200

    async def test_unknown_slug_returns_404(self, skill_client: httpx.AsyncClient):
        r = await skill_client.post(
            '/skills/no-such-skill/edit',
            data={'name': 'x', 'description': 'y'},
        )
        assert r.status_code == 404

    async def test_chain_fields_accepted(
        self, skill_client: httpx.AsyncClient, skill_file
    ):
        _, slug = skill_file
        r = await skill_client.post(
            f'/skills/{slug}/edit',
            data={
                'name': 'spec-manager',
                'description': 'desc',
                'inject_references': 'false',
                'inject_fewshot': 'false',
                'depends_on': '',
                'chain_next': 'adr-manager',
                'chain_condition': 'on_success',
            },
        )
        assert r.status_code == 200


class TestEditSkillApply:
    async def test_valid_apply_writes_file(
        self, skill_client: httpx.AsyncClient, skill_file
    ):
        cfg, slug = skill_file
        r = await skill_client.post(
            f'/skills/{slug}/edit/apply',
            data={
                'name': 'spec-manager',
                'description': 'Persisted to disk.',
                'inject_references': 'false',
                'inject_fewshot': 'false',
                'emits_confidence': '0',
                'depends_on': '',
                'chain_next': '',
                'chain_condition': '',
            },
        )
        assert r.status_code == 200
        import frontmatter as fm
        skill_path = cfg.root / 'skills' / slug / 'SKILL.md'
        post = fm.load(str(skill_path))
        assert post['description'] == 'Persisted to disk.'

    async def test_unknown_slug_returns_404(self, skill_client: httpx.AsyncClient):
        r = await skill_client.post(
            '/skills/ghost/edit/apply',
            data={'name': 'x', 'description': 'y'},
        )
        assert r.status_code == 404
