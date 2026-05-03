"""Unit tests for orquestrum/core/install.py — the integration installer."""
from __future__ import annotations
import json
import shutil
from pathlib import Path

import pytest

from orquestrum.core import install as core_install


@pytest.fixture()
def fake_integrations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a minimal `integrations/` tree and point INTEGRATIONS at it."""
    integrations = tmp_path / 'integrations'

    # claude-code: agents + .sdd + settings.json
    claude = integrations / 'claude-code'
    (claude / '.claude' / 'agents').mkdir(parents=True)
    (claude / '.claude' / 'agents' / 'helm-the-architect.md').write_text(
        '---\nname: Helm - The Architect\n---\nbody', encoding='utf-8',
    )
    (claude / '.sdd' / 'docs').mkdir(parents=True)
    (claude / '.sdd' / 'docs' / 'SDLC.md').write_text('# SDLC', encoding='utf-8')
    (claude / '.claude' / 'settings.json').write_text(json.dumps({
        'hooks': {
            'Stop': [{'matcher': '', 'hooks': [
                {'type': 'command', 'command': 'uv run .sdd/scripts/hooks/emit_metrics.py'},
            ]}],
        },
    }), encoding='utf-8')

    # opencode: docs use the placeholder
    opencode = integrations / 'opencode'
    (opencode / 'agents').mkdir(parents=True)
    (opencode / 'agents' / 'helm-the-architect.md').write_text(
        'See __OPENCODE_ROOT__/docs/SDLC.md', encoding='utf-8',
    )
    (opencode / 'docs').mkdir()
    (opencode / 'docs' / 'SDLC.md').write_text('# SDLC', encoding='utf-8')

    monkeypatch.setattr(core_install, 'INTEGRATIONS', integrations)
    return integrations


class TestDetectTools:
    def test_detects_opencode_via_target_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        target = tmp_path / 'target'
        (target / '.opencode').mkdir(parents=True)
        # Stop other detectors from triggering by faking which() and HOME
        fake_home = tmp_path / 'home'
        fake_home.mkdir()
        monkeypatch.setattr(Path, 'home', staticmethod(lambda: fake_home))
        monkeypatch.setattr(shutil, 'which', lambda name: None)
        found = core_install.detect_tools(target)
        assert 'opencode' in found

    def test_detects_claude_code_via_home(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        fake_home = tmp_path / 'home'
        (fake_home / '.claude').mkdir(parents=True)
        monkeypatch.setattr(Path, 'home', staticmethod(lambda: fake_home))
        monkeypatch.setattr(shutil, 'which', lambda name: None)
        target = tmp_path / 'target'
        target.mkdir()
        found = core_install.detect_tools(target)
        assert 'claude-code' in found

    def test_returns_empty_when_nothing_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        fake_home = tmp_path / 'home'
        fake_home.mkdir()
        monkeypatch.setattr(Path, 'home', staticmethod(lambda: fake_home))
        monkeypatch.setattr(shutil, 'which', lambda name: None)
        target = tmp_path / 'target'
        target.mkdir()
        assert core_install.detect_tools(target) == []


class TestInstallTool:
    def test_rejects_unknown_tool(
        self, tmp_path: Path, fake_integrations: Path,
        capsys: pytest.CaptureFixture,
    ):
        target = tmp_path / 'target'
        target.mkdir()
        ok = core_install.install_tool('made-up', target)
        assert ok is False
        err = capsys.readouterr().err
        assert 'Unknown tool' in err

    def test_rejects_dot_claude_target_for_claude_code(
        self, tmp_path: Path, fake_integrations: Path,
        capsys: pytest.CaptureFixture,
    ):
        """User mistake: `--target ~/.claude` causes ~/.claude/.claude/.
        Refuse before copying anything."""
        target = tmp_path / '.claude'
        target.mkdir()
        ok = core_install.install_tool('claude-code', target)
        assert ok is False
        err = capsys.readouterr().err
        assert 'double-nested' in err
        # Files must NOT have been written into the bad target
        assert not (target / '.claude').exists()

    def test_install_plan_printed_before_copy(
        self, tmp_path: Path, fake_integrations: Path,
        capsys: pytest.CaptureFixture,
    ):
        """The user must see what will happen before any file is touched."""
        target = tmp_path / 'project'
        target.mkdir()
        core_install.install_tool('opencode', target)
        out = capsys.readouterr().out
        # Plan shows new file count
        assert 'new' in out


class TestInstallPersistsManifest:
    """install_tool() must record what it created in
    ~/.orquestrum/installs.json so future uninstalls are surgical."""

    def test_records_files_and_dirs_after_opencode_install(
        self, tmp_path: Path, fake_integrations: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # Sandbox ORQUESTRUM_HOME for the test
        home = tmp_path / 'orq-home'
        home.mkdir()
        monkeypatch.setenv('ORQUESTRUM_HOME', str(home))

        target = tmp_path / 'project'
        target.mkdir()
        ok = core_install.install_tool('opencode', target)
        assert ok is True

        from orquestrum.lib import installs_manifest
        record = installs_manifest.get_install('opencode', target)
        assert record is not None
        assert record.tool == 'opencode'
        # At least one .md agent file recorded
        assert any(rel.endswith('.md') for rel in record.files)
        # The agents/ dir was created by orquestrum and recorded
        assert any('agents' in d for d in record.directories)

    def test_records_settings_json_for_claude_code(
        self, tmp_path: Path, fake_integrations: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        home = tmp_path / 'orq-home'
        home.mkdir()
        monkeypatch.setenv('ORQUESTRUM_HOME', str(home))

        target = tmp_path / 'project'
        target.mkdir()
        core_install.install_tool('claude-code', target)
        from orquestrum.lib import installs_manifest
        record = installs_manifest.get_install('claude-code', target)
        assert record is not None
        # settings.json (handled by merge path, not classify) should still
        # be recorded so uninstall can scrub or remove it.
        assert any('settings.json' in f for f in record.files)

class TestMcpServersMerge:
    """The settings.json merge must register the orquestrum MCP server
    without clobbering other mcpServers entries the user has installed."""

    def _build_claude_with_mcp(self, integrations_root: Path) -> None:
        cc = integrations_root / 'claude-code'
        (cc / '.claude' / 'agents').mkdir(parents=True, exist_ok=True)
        (cc / '.claude' / 'agents' / 'helm-the-architect.md').write_text(
            '---\nname: x\n---', encoding='utf-8',
        )
        (cc / '.sdd').mkdir(parents=True, exist_ok=True)
        (cc / '.claude' / 'settings.json').write_text(json.dumps({
            'hooks': {
                'Stop': [{'matcher': '', 'hooks': [
                    {'type': 'command',
                     'command': 'uv run .claude/sdd/scripts/hooks/emit_metrics.py'},
                ]}],
            },
            'mcpServers': {
                'orquestrum': {
                    'command': 'orquestrum',
                    'args': ['mcp'],
                    'type': 'stdio',
                },
            },
        }), encoding='utf-8')

    def test_registers_orquestrum_mcp_on_first_install(
        self, tmp_path: Path, fake_integrations: Path,
    ):
        self._build_claude_with_mcp(fake_integrations)
        target = tmp_path / 'project'
        target.mkdir()
        core_install.install_tool('claude-code', target)
        out = json.loads((target / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        assert 'orquestrum' in out['mcpServers']
        assert out['mcpServers']['orquestrum']['command'] == 'orquestrum'
        assert out['mcpServers']['orquestrum']['args'] == ['mcp']

    def test_preserves_user_mcp_servers_on_install(
        self, tmp_path: Path, fake_integrations: Path,
    ):
        self._build_claude_with_mcp(fake_integrations)
        target = tmp_path / 'project'
        (target / '.claude').mkdir(parents=True)
        # User already has their own MCP servers
        (target / '.claude' / 'settings.json').write_text(json.dumps({
            'theme': 'dark',
            'mcpServers': {
                'filesystem': {'command': 'mcp-filesystem', 'args': ['/']},
                'github':     {'command': 'mcp-github',     'args': []},
            },
        }), encoding='utf-8')

        core_install.install_tool('claude-code', target)
        out = json.loads((target / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        # User entries preserved
        assert 'filesystem' in out['mcpServers']
        assert out['mcpServers']['filesystem']['command'] == 'mcp-filesystem'
        assert 'github' in out['mcpServers']
        # Orquestrum added alongside
        assert 'orquestrum' in out['mcpServers']
        # Theme key untouched
        assert out['theme'] == 'dark'

    def test_replaces_outdated_orquestrum_mcp_on_reinstall(
        self, tmp_path: Path, fake_integrations: Path,
    ):
        self._build_claude_with_mcp(fake_integrations)
        target = tmp_path / 'project'
        (target / '.claude').mkdir(parents=True)
        # Previous install used a different command
        (target / '.claude' / 'settings.json').write_text(json.dumps({
            'mcpServers': {
                'orquestrum': {'command': 'old-cmd', 'args': ['legacy']},
            },
        }), encoding='utf-8')

        core_install.install_tool('claude-code', target)
        out = json.loads((target / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        # Latest config wins
        assert out['mcpServers']['orquestrum']['command'] == 'orquestrum'
        assert out['mcpServers']['orquestrum']['args'] == ['mcp']


    def test_suggests_claude_code_on_typo(
        self, tmp_path: Path, fake_integrations: Path,
        capsys: pytest.CaptureFixture,
    ):
        target = tmp_path / 'target'
        target.mkdir()
        ok = core_install.install_tool('claude', target)
        assert ok is False
        err = capsys.readouterr().err
        assert 'claude-code' in err

    def test_returns_false_when_integration_dir_missing(
        self, tmp_path: Path, fake_integrations: Path,
        capsys: pytest.CaptureFixture,
    ):
        # Remove opencode integration to trigger missing-dir branch
        shutil.rmtree(fake_integrations / 'opencode')
        target = tmp_path / 'target'
        target.mkdir()
        ok = core_install.install_tool('opencode', target)
        assert ok is False
        err = capsys.readouterr().err
        assert 'Run first: orquestrum convert' in err

    def test_resolves_opencode_placeholder(
        self, tmp_path: Path, fake_integrations: Path,
    ):
        target = tmp_path / 'target'
        target.mkdir()
        core_install.install_tool('opencode', target)
        text = (target / 'agents' / 'helm-the-architect.md').read_text(encoding='utf-8')
        assert '__OPENCODE_ROOT__' not in text
        assert str(target.resolve()) in text

    def test_claude_code_merges_settings_when_already_present(
        self, tmp_path: Path, fake_integrations: Path,
    ):
        target = tmp_path / 'target'
        (target / '.claude').mkdir(parents=True)
        existing = {'theme': 'dark', 'hooks': {'Stop': [
            {'matcher': '', 'hooks': [
                {'type': 'command', 'command': 'echo user-hook'},
            ]},
        ]}}
        (target / '.claude' / 'settings.json').write_text(
            json.dumps(existing), encoding='utf-8',
        )

        ok = core_install.install_tool('claude-code', target)
        assert ok is True
        merged = json.loads((target / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        assert merged['theme'] == 'dark'
        cmds = [h['command'] for blk in merged['hooks']['Stop'] for h in blk['hooks']]
        assert 'echo user-hook' in cmds
        assert any('emit_metrics.py' in c for c in cmds)

    def test_claude_code_creates_settings_when_missing(
        self, tmp_path: Path, fake_integrations: Path,
    ):
        target = tmp_path / 'target'
        target.mkdir()
        core_install.install_tool('claude-code', target)
        out = json.loads((target / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        assert 'hooks' in out
        cmds = [h['command'] for blk in out['hooks']['Stop'] for h in blk['hooks']]
        assert any('emit_metrics.py' in c for c in cmds)


class TestMain:
    def test_target_must_exist(
        self, tmp_path: Path, fake_integrations: Path,
        capsys: pytest.CaptureFixture,
    ):
        with pytest.raises(SystemExit) as exc:
            core_install.main(['--tool', 'opencode', '--target', str(tmp_path / 'nope')])
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert 'does not exist' in err

    def test_auto_with_no_tools_exits_1(
        self, tmp_path: Path, fake_integrations: Path,
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        target = tmp_path / 'target'
        target.mkdir()
        monkeypatch.setattr(core_install, 'detect_tools', lambda t: [])
        with pytest.raises(SystemExit) as exc:
            core_install.main(['--auto', '--target', str(target)])
        assert exc.value.code == 1

    def test_auto_iterates_detected_tools(
        self, tmp_path: Path, fake_integrations: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        target = tmp_path / 'target'
        target.mkdir()
        installed: list = []
        verified: list = []
        monkeypatch.setattr(core_install, 'detect_tools',
                            lambda t: ['claude-code', 'opencode'])
        monkeypatch.setattr(core_install, 'install_tool',
                            lambda tool, t, **kw: installed.append(tool) or True)
        # Verification is exercised separately in tests/lib/test_verify.py;
        # here we just confirm main() iterates each detected tool.
        monkeypatch.setattr(core_install, 'verify_install',
                            lambda tool, t: verified.append(tool) or True)
        core_install.main(['--auto', '--target', str(target)])
        assert installed == ['claude-code', 'opencode']
        assert verified == ['claude-code', 'opencode']

    def test_explicit_tool_failure_exits_1(
        self, tmp_path: Path, fake_integrations: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        target = tmp_path / 'target'
        target.mkdir()
        monkeypatch.setattr(core_install, 'install_tool', lambda *a, **kw: False)
        with pytest.raises(SystemExit) as exc:
            core_install.main(['--tool', 'opencode', '--target', str(target)])
        assert exc.value.code == 1

    def test_install_failure_when_verification_fails(
        self, tmp_path: Path, fake_integrations: Path,
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
    ):
        # Copy succeeds but verify rejects (e.g., placeholder unresolved or
        # critical file missing). main() must exit 1.
        target = tmp_path / 'target'
        target.mkdir()
        monkeypatch.setattr(core_install, 'install_tool', lambda *a, **kw: True)
        monkeypatch.setattr(core_install, 'verify_install', lambda *a, **kw: False)
        with pytest.raises(SystemExit) as exc:
            core_install.main(['--tool', 'opencode', '--target', str(target)])
        assert exc.value.code == 1


class TestVerifyInstall:
    def test_returns_true_on_complete_install(
        self, tmp_path: Path, capsys: pytest.CaptureFixture,
    ):
        # Build a complete opencode integration in-place at the target
        # with the real orquestrum agent .md filenames the verifier expects.
        from orquestrum.lib.verify import _expected_agent_md_filenames
        target = tmp_path / 'target'
        agents = target / 'agents'
        agents.mkdir(parents=True)
        for fname in _expected_agent_md_filenames():
            (agents / fname).write_text('---\nname: x\n---\nbody', encoding='utf-8')
        (target / 'docs').mkdir()
        (target / 'skills').mkdir()
        assert core_install.verify_install('opencode', target) is True
        out = capsys.readouterr().out
        assert 'verify: install:opencode' in out

    def test_returns_false_when_target_missing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture,
    ):
        target = tmp_path / 'never-created'
        assert core_install.verify_install('opencode', target) is False
        err = capsys.readouterr().err
        assert 'verification failed' in err
