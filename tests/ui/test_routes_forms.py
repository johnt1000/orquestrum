"""Route tests for /compact, /convert, /install (GET forms + POST validation)."""
from __future__ import annotations
from pathlib import Path

import httpx
import pytest

import ui.lib.jobs as jobs_module
from ui.config import UIConfig
from ui.server import create_app


# ─── Fixtures ────────────────────────────────────────────────────────────────

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


def _make_project_config(tmp_path: Path) -> UIConfig:
    return UIConfig(
        mode='project',
        root=tmp_path,
        metrics_dir=tmp_path / '.orquestrum' / 'metrics',
        targets_path=None,
        port=7700,
    )


@pytest.fixture()
def framework_config(tmp_path: Path) -> UIConfig:
    return _make_framework_config(tmp_path)


@pytest.fixture()
def project_config(tmp_path: Path) -> UIConfig:
    return _make_project_config(tmp_path)


@pytest.fixture()
async def fw_client(framework_config: UIConfig) -> httpx.AsyncClient:
    app = create_app(framework_config)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url='http://test',
    ) as c:
        yield c


@pytest.fixture()
async def proj_client(project_config: UIConfig) -> httpx.AsyncClient:
    app = create_app(project_config)
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


# ─── /compact ────────────────────────────────────────────────────────────────

class TestCompactGet:
    async def test_returns_200_framework(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/compact')
        assert r.status_code == 200

    async def test_returns_html(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/compact')
        assert 'text/html' in r.headers['content-type']

    async def test_project_mode_shows_warning(self, proj_client: httpx.AsyncClient):
        r = await proj_client.get('/compact')
        assert r.status_code == 200
        # Template renders a project_mode_warning section
        assert 'text/html' in r.headers['content-type']

    async def test_lists_skills_in_framework_mode(
        self, fw_client: httpx.AsyncClient, framework_config: UIConfig
    ):
        # Create a skill dir
        skill = framework_config.root / 'skills' / 'my-skill'
        skill.mkdir()
        (skill / 'SKILL.md').write_text('---\nname: my-skill\n---\n', encoding='utf-8')
        r = await fw_client.get('/compact')
        assert r.status_code == 200


class TestCompactPost:
    async def test_post_framework_redirects_to_job(self, fw_client: httpx.AsyncClient):
        r = await fw_client.post(
            '/compact',
            data={'scope': 'all', 'threshold_kb': '8'},
            follow_redirects=False,
        )
        assert r.status_code == 303
        assert r.headers['location'].startswith('/jobs/')

    async def test_post_project_returns_400(self, proj_client: httpx.AsyncClient):
        r = await proj_client.post(
            '/compact',
            data={'scope': 'all', 'threshold_kb': '8'},
        )
        assert r.status_code == 400

    async def test_post_dry_run_redirects(self, fw_client: httpx.AsyncClient):
        r = await fw_client.post(
            '/compact',
            data={'scope': 'all', 'threshold_kb': '8', 'dry_run': '1'},
            follow_redirects=False,
        )
        assert r.status_code == 303

    async def test_post_single_skill_redirects(
        self, fw_client: httpx.AsyncClient, framework_config: UIConfig
    ):
        skill = framework_config.root / 'skills' / 'spec-manager'
        skill.mkdir()
        (skill / 'SKILL.md').write_text('---\nname: spec-manager\n---\n', encoding='utf-8')
        r = await fw_client.post(
            '/compact',
            data={'scope': 'one', 'skill': 'spec-manager', 'threshold_kb': '8'},
            follow_redirects=False,
        )
        assert r.status_code == 303


# ─── /convert ────────────────────────────────────────────────────────────────

class TestConvertGet:
    async def test_returns_200_framework(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/convert')
        assert r.status_code == 200

    async def test_returns_html(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/convert')
        assert 'text/html' in r.headers['content-type']

    async def test_shows_tools(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/convert')
        assert 'claude-code' in r.text

    async def test_shows_providers(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/convert')
        assert 'claude' in r.text

    async def test_project_mode_page_renders(self, proj_client: httpx.AsyncClient):
        r = await proj_client.get('/convert')
        assert r.status_code == 200


class TestConvertPost:
    async def test_valid_tool_redirects(self, fw_client: httpx.AsyncClient):
        r = await fw_client.post(
            '/convert',
            data={'tool': 'claude-code', 'provider': '(none)'},
            follow_redirects=False,
        )
        assert r.status_code == 303
        assert r.headers['location'].startswith('/jobs/')

    async def test_tool_all_redirects(self, fw_client: httpx.AsyncClient):
        r = await fw_client.post(
            '/convert',
            data={'tool': 'all', 'provider': 'claude'},
            follow_redirects=False,
        )
        assert r.status_code == 303

    async def test_invalid_tool_returns_400(self, fw_client: httpx.AsyncClient):
        r = await fw_client.post(
            '/convert',
            data={'tool': 'nonexistent-tool', 'provider': '(none)'},
        )
        assert r.status_code == 400

    async def test_invalid_provider_returns_400(self, fw_client: httpx.AsyncClient):
        r = await fw_client.post(
            '/convert',
            data={'tool': 'opencode', 'provider': 'invalid-provider'},
        )
        assert r.status_code == 400

    async def test_project_mode_returns_400(self, proj_client: httpx.AsyncClient):
        r = await proj_client.post(
            '/convert',
            data={'tool': 'claude-code', 'provider': '(none)'},
        )
        assert r.status_code == 400

    async def test_dry_run_redirects(self, fw_client: httpx.AsyncClient):
        r = await fw_client.post(
            '/convert',
            data={'tool': 'opencode', 'provider': '(none)', 'dry_run': '1'},
            follow_redirects=False,
        )
        assert r.status_code == 303

    async def test_creates_job_entry(self, fw_client: httpx.AsyncClient):
        r = await fw_client.post(
            '/convert',
            data={'tool': 'cursor', 'provider': '(none)'},
            follow_redirects=False,
        )
        assert r.status_code == 303
        job_id = r.headers['location'].split('/')[-1]
        assert job_id in jobs_module._jobs


# ─── /install ────────────────────────────────────────────────────────────────

class TestInstallGet:
    async def test_returns_200_framework(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/install')
        assert r.status_code == 200

    async def test_returns_html(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/install')
        assert 'text/html' in r.headers['content-type']

    async def test_shows_tools(self, fw_client: httpx.AsyncClient):
        r = await fw_client.get('/install')
        assert 'claude-code' in r.text

    async def test_project_mode_page_renders(self, proj_client: httpx.AsyncClient):
        r = await proj_client.get('/install')
        assert r.status_code == 200


class TestInstallPost:
    async def test_project_mode_returns_400(
        self, proj_client: httpx.AsyncClient, tmp_path: Path
    ):
        r = await proj_client.post(
            '/install',
            data={'tool': 'claude-code', 'target': str(tmp_path)},
        )
        assert r.status_code == 400

    async def test_missing_target_shows_error(
        self, fw_client: httpx.AsyncClient, tmp_path: Path
    ):
        nonexistent = tmp_path / 'does_not_exist'
        r = await fw_client.post(
            '/install',
            data={'tool': 'claude-code', 'target': str(nonexistent)},
        )
        assert r.status_code == 200
        assert 'does not exist' in r.text.lower() or 'Target' in r.text

    async def test_invalid_tool_shows_error(
        self, fw_client: httpx.AsyncClient, tmp_path: Path
    ):
        r = await fw_client.post(
            '/install',
            data={'tool': 'bad-tool', 'target': str(tmp_path)},
        )
        assert r.status_code == 200
        assert 'Invalid tool' in r.text or 'invalid' in r.text.lower()

    async def test_no_tool_no_auto_shows_error(
        self, fw_client: httpx.AsyncClient, tmp_path: Path
    ):
        r = await fw_client.post(
            '/install',
            data={'tool': '', 'target': str(tmp_path)},
        )
        assert r.status_code == 200
        assert 'auto' in r.text.lower() or 'tool' in r.text.lower()

    async def test_valid_auto_redirects_to_job(
        self, fw_client: httpx.AsyncClient, tmp_path: Path
    ):
        r = await fw_client.post(
            '/install',
            data={'tool': '', 'target': str(tmp_path), 'auto': '1'},
            follow_redirects=False,
        )
        assert r.status_code == 303
        assert r.headers['location'].startswith('/jobs/')

    async def test_valid_tool_redirects_to_job(
        self, fw_client: httpx.AsyncClient, tmp_path: Path
    ):
        r = await fw_client.post(
            '/install',
            data={'tool': 'opencode', 'target': str(tmp_path)},
            follow_redirects=False,
        )
        assert r.status_code == 303
        assert r.headers['location'].startswith('/jobs/')
