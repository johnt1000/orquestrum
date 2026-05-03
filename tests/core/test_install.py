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

    # cursor: just rules dir
    cursor = integrations / 'cursor'
    (cursor / '.cursor' / 'rules').mkdir(parents=True)
    (cursor / '.cursor' / 'rules' / 'sdlc.mdc').write_text('rules', encoding='utf-8')

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

    def test_detects_cursor_via_target_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ):
        target = tmp_path / 'target'
        (target / '.cursor').mkdir(parents=True)
        fake_home = tmp_path / 'home'
        fake_home.mkdir()
        monkeypatch.setattr(Path, 'home', staticmethod(lambda: fake_home))
        monkeypatch.setattr(shutil, 'which', lambda name: None)
        found = core_install.detect_tools(target)
        assert 'cursor' in found

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
        # Remove cursor integration
        shutil.rmtree(fake_integrations / 'cursor')
        target = tmp_path / 'target'
        target.mkdir()
        ok = core_install.install_tool('cursor', target)
        assert ok is False
        err = capsys.readouterr().err
        assert 'Run first: orquestrum convert' in err

    def test_copies_cursor_payload(
        self, tmp_path: Path, fake_integrations: Path,
    ):
        target = tmp_path / 'target'
        target.mkdir()
        ok = core_install.install_tool('cursor', target)
        assert ok is True
        assert (target / '.cursor' / 'rules' / 'sdlc.mdc').is_file()

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
            core_install.main(['--tool', 'cursor', '--target', str(tmp_path / 'nope')])
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
        monkeypatch.setattr(core_install, 'detect_tools', lambda t: ['cursor', 'opencode'])
        monkeypatch.setattr(core_install, 'install_tool',
                            lambda tool, t: installed.append(tool) or True)
        core_install.main(['--auto', '--target', str(target)])
        assert installed == ['cursor', 'opencode']

    def test_explicit_tool_failure_exits_1(
        self, tmp_path: Path, fake_integrations: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        target = tmp_path / 'target'
        target.mkdir()
        monkeypatch.setattr(core_install, 'install_tool', lambda *a, **kw: False)
        with pytest.raises(SystemExit) as exc:
            core_install.main(['--tool', 'cursor', '--target', str(target)])
        assert exc.value.code == 1
