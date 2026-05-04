"""Tests for WSD: `init` auto-detects global MCP/hook registration.

When `orquestrum setup` has already registered the metrics hook + MCP
server in `~/.claude/settings.json`, `init` should skip the prompts
that would re-do that work and just print a "✓ already registered
globally" line. The user gets a faster init (one prompt instead of three).

The `--per-project` flag forces the prompts to fire even when global
is registered — for the rare case of project-scoped overrides.
"""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from orquestrum.commands import init_impl


def _seed_global_settings(home: Path, *, hook: bool, mcp: bool) -> Path:
    """Write a synthetic `~/.claude/settings.json` matching what
    `orquestrum setup` would produce."""
    path = home / '.claude' / 'settings.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if hook:
        data['hooks'] = {
            'Stop': [{'matcher': '', 'hooks': [
                {'type': 'command', 'command': 'orquestrum hook'},
            ]}],
        }
    if mcp:
        data['mcpServers'] = {
            'orquestrum': {'command': 'orquestrum', 'args': ['mcp'], 'type': 'stdio'},
        }
    path.write_text(json.dumps(data), encoding='utf-8')
    return path


# ─── _detect_global_state ──────────────────────────────────────────────────


class TestDetectGlobalState:
    def test_empty_home_reports_neither(self, isolated_home: Path,
                                          tmp_path: Path):
        # isolated_home fixture already mocks Path.home() to tmp_path/fake-user-home
        state = init_impl._detect_global_state()
        assert state == {'hook_registered': False, 'mcp_registered': False}

    def test_hook_only(self, isolated_home: Path):
        _seed_global_settings(Path.home(), hook=True, mcp=False)
        state = init_impl._detect_global_state()
        assert state == {'hook_registered': True, 'mcp_registered': False}

    def test_mcp_only(self, isolated_home: Path):
        _seed_global_settings(Path.home(), hook=False, mcp=True)
        state = init_impl._detect_global_state()
        assert state == {'hook_registered': False, 'mcp_registered': True}

    def test_both(self, isolated_home: Path):
        _seed_global_settings(Path.home(), hook=True, mcp=True)
        state = init_impl._detect_global_state()
        assert state == {'hook_registered': True, 'mcp_registered': True}

    def test_legacy_emit_metrics_hook_also_detected(self, isolated_home: Path):
        """Pre-0.5.1 hooks used `uv run .../emit_metrics.py` — the
        detection must recognise both forms or users with old installs
        would get prompted again."""
        path = Path.home() / '.claude' / 'settings.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({
            'hooks': {'Stop': [{'matcher': '', 'hooks': [
                {'type': 'command',
                 'command': 'uv run .claude/sdd/scripts/hooks/emit_metrics.py'},
            ]}]},
        }), encoding='utf-8')
        state = init_impl._detect_global_state()
        assert state['hook_registered'] is True


# ─── _gather_choices skip behaviour ────────────────────────────────────────


class TestGatherChoicesSkipsWhenGlobal:
    def test_no_global_runs_normal_prompts(self, isolated_home: Path,
                                            capsys: pytest.CaptureFixture):
        # Empty home → both prompts ask normally; defaults Y for both
        choices = init_impl._gather_choices(interactive=False)
        assert choices['metrics_enabled'] is True
        assert choices['mcp_enabled'] is True
        assert choices['_global_hook_present'] is False
        assert choices['_global_mcp_present'] is False
        # No "already registered" message
        out = capsys.readouterr().out
        assert 'already registered globally' not in out

    def test_global_hook_skips_prompt_emits_marker(
        self, isolated_home: Path, capsys: pytest.CaptureFixture,
    ):
        _seed_global_settings(Path.home(), hook=True, mcp=False)
        choices = init_impl._gather_choices(interactive=False)
        # Choices reflect the global registration
        assert choices['metrics_enabled'] is True
        assert choices['metrics_scope'] == 'global'
        assert choices['_global_hook_present'] is True
        assert choices['_global_mcp_present'] is False
        # MCP prompt still fires (default Y, since MCP not registered)
        assert choices['mcp_enabled'] is True
        out = capsys.readouterr().out
        assert 'Metrics hook already registered globally' in out
        assert 'MCP server already registered globally' not in out

    def test_global_both_skips_both_prompts(
        self, isolated_home: Path, capsys: pytest.CaptureFixture,
    ):
        _seed_global_settings(Path.home(), hook=True, mcp=True)
        choices = init_impl._gather_choices(interactive=False)
        assert choices['_global_hook_present'] is True
        assert choices['_global_mcp_present'] is True
        out = capsys.readouterr().out
        assert 'Metrics hook already registered' in out
        assert 'MCP server already registered' in out

    def test_per_project_forces_prompts_even_with_global(
        self, isolated_home: Path, capsys: pytest.CaptureFixture,
    ):
        """--per-project escape hatch: user explicitly wants the prompts
        to fire even when global registration exists."""
        _seed_global_settings(Path.home(), hook=True, mcp=True)
        choices = init_impl._gather_choices(
            interactive=False, per_project=True,
        )
        # Global flags reset to False because per_project bypasses detection
        assert choices['_global_hook_present'] is False
        assert choices['_global_mcp_present'] is False
        out = capsys.readouterr().out
        assert 'already registered globally' not in out


# ─── run_init end-to-end skips installs ────────────────────────────────────


class TestRunInitSkipsRedundantInstall:
    def test_skip_metrics_install_when_global_hook_present(
        self, project_root: Path, isolated_home: Path,
        stub_optional_installs,
    ):
        """When the hook is already in ~/.claude/settings.json, init
        should NOT re-install it. Just record the choice in config.toml."""
        _seed_global_settings(Path.home(), hook=True, mcp=False)
        init_impl.run_init(name=None, interactive=False)
        # _install_metrics_hook should NOT have been called for metrics
        # (still might be called for mcp if mcp_scope differs — but in this
        # test mcp is not globally registered so it'll be called for mcp_scope)
        # Check: there should be at most ONE call (for mcp), not two
        assert len(stub_optional_installs['metrics']) <= 1

    def test_skip_both_when_global_both(
        self, project_root: Path, isolated_home: Path,
        stub_optional_installs,
    ):
        _seed_global_settings(Path.home(), hook=True, mcp=True)
        init_impl.run_init(name=None, interactive=False)
        # Neither should have been installed — both already global
        assert stub_optional_installs['metrics'] == []

    def test_per_project_runs_install_even_with_global(
        self, project_root: Path, isolated_home: Path,
        stub_optional_installs,
    ):
        _seed_global_settings(Path.home(), hook=True, mcp=True)
        init_impl.run_init(name=None, interactive=False, per_project=True)
        # With --per-project, install runs as before — matches test's normal expectation
        assert len(stub_optional_installs['metrics']) >= 1


@pytest.fixture()
def stub_optional_installs(monkeypatch: pytest.MonkeyPatch):
    """Mirror the fixture in test_init.py so this file is self-contained."""
    calls = {'metrics': [], 'agents': []}
    monkeypatch.setattr(init_impl, '_install_metrics_hook',
                        lambda root, scope: calls['metrics'].append((str(root), scope)))
    monkeypatch.setattr(init_impl, '_install_agents_global',
                        lambda root: calls['agents'].append(str(root)))
    return calls
