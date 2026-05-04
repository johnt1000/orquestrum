"""Tests for `orquestrum setup --advanced` — the 9-prompt wizard.

Covers:
  - argparse: --advanced flag is exposed and routes to advanced handler
  - --yes silently runs all sections with defaults
  - Each section function returns the expected shape
  - Section dispatch invokes the right downstream commands (mocked)
  - --yes ignored mode falls back to fast path

Sections live in `orquestrum/commands/setup_sections.py` — tested
in isolation here; integration via `_run_setup_advanced` exercised end
to end with stubs.
"""
from __future__ import annotations
import argparse
from pathlib import Path

import pytest

from orquestrum.commands import setup
from orquestrum.commands import setup_sections as sections


# ─── shared fixtures (mirror test_setup.py) ────────────────────────────────


@pytest.fixture()
def isolated_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / 'orq-home'
    home.mkdir()
    monkeypatch.setenv('ORQUESTRUM_HOME', str(home))
    return home


@pytest.fixture()
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fake = tmp_path / 'fake-home'
    fake.mkdir()
    monkeypatch.setattr(Path, 'home', staticmethod(lambda: fake))
    return fake


@pytest.fixture()
def stub_install_pipeline(monkeypatch: pytest.MonkeyPatch):
    """Patch all the downstream install paths so the advanced wizard can
    run end-to-end without touching the user's real env."""
    calls = {
        'convert': [], 'install': [], 'extras': [], 'deps': [], 'mcp_add': [],
    }

    from orquestrum.core import convert as core_convert
    from orquestrum.core import install as core_install
    from orquestrum.core import deps as core_deps
    from orquestrum.commands import extras as cmd_extras
    from orquestrum.commands import mcp as cmd_mcp
    from orquestrum.lib import paths

    def fake_convert(argv):  calls['convert'].append(list(argv or []))
    def fake_install(argv):  calls['install'].append(list(argv or []))
    def fake_deps(argv):     calls['deps'].append(list(argv or []))
    def fake_extras(names):
        calls['extras'].append(list(names))
        return 0
    def fake_mcp_add(ns):
        calls['mcp_add'].append({
            'name': ns.name, 'command': ns.command, 'args': ns.args,
        })
        return 0

    monkeypatch.setattr(core_convert, 'main', fake_convert)
    monkeypatch.setattr(core_install, 'main', fake_install)
    monkeypatch.setattr(core_deps, 'main', fake_deps)
    monkeypatch.setattr(cmd_extras, '_install', fake_extras)
    monkeypatch.setattr(cmd_mcp, '_add', fake_mcp_add)

    fake_cache = Path('/tmp/orq-cache-stub-advanced')
    fake_cache.mkdir(exist_ok=True)
    (fake_cache / 'claude-code').mkdir(exist_ok=True)
    (fake_cache / 'opencode').mkdir(exist_ok=True)
    monkeypatch.setattr(paths, 'convert_output_root', lambda: fake_cache)
    return calls


# ─── argparse ──────────────────────────────────────────────────────────────


class TestArgparse:
    def test_advanced_flag_registered(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest='cmd')
        setup.register(sub)
        # parse `setup --advanced` and verify the flag flips
        ns = parser.parse_args(['setup', '--advanced'])
        assert ns.advanced is True
        assert ns.non_interactive is False

    def test_advanced_with_yes(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest='cmd')
        setup.register(sub)
        ns = parser.parse_args(['setup', '--advanced', '--yes'])
        assert ns.advanced is True
        assert ns.non_interactive is True


class TestHandlerRouting:
    def test_handler_dispatches_to_advanced(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline, monkeypatch: pytest.MonkeyPatch,
    ):
        called_advanced: list[bool] = []
        called_fast: list[bool] = []
        monkeypatch.setattr(setup, '_run_setup_advanced',
                            lambda *, interactive: called_advanced.append(interactive) or 0)
        monkeypatch.setattr(setup, '_run_setup',
                            lambda *, interactive: called_fast.append(interactive) or 0)
        ns = argparse.Namespace(non_interactive=True, advanced=True)
        rc = setup._handler(ns)
        assert rc == 0
        assert called_advanced == [False]   # interactive=False because of --yes
        assert called_fast == []

    def test_handler_dispatches_to_fast_when_no_advanced(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline, monkeypatch: pytest.MonkeyPatch,
    ):
        called_fast: list[bool] = []
        monkeypatch.setattr(setup, '_run_setup',
                            lambda *, interactive: called_fast.append(interactive) or 0)
        ns = argparse.Namespace(non_interactive=True, advanced=False)
        setup._handler(ns)
        assert called_fast == [False]


# ─── section functions in isolation ────────────────────────────────────────


class TestSectionCore:
    def test_returns_choices(self):
        state = {
            'claude-code': {'installed': False, 'target': Path('/tmp')},
            'opencode':    {'installed': False, 'target': Path('/tmp/oc')},
        }
        result = sections.section_core(interactive=False, state=state)
        assert result['install_cc'] is True   # default Y for fresh
        assert result['install_oc'] is False  # default N
        assert result['provider'] == 'claude' # default 'c'

    def test_re_install_defaults_no(self):
        state = {
            'claude-code': {'installed': True, 'target': Path('/tmp')},
            'opencode':    {'installed': False, 'target': Path('/tmp/oc')},
        }
        result = sections.section_core(interactive=False, state=state)
        assert result['install_cc'] is False  # default flips when already installed


class TestSectionExtras:
    def test_defaults(self):
        result = sections.section_extras(interactive=False)
        assert result['install_ui'] is True       # default Y (visible feature)
        assert result['install_webview'] is False # default N (niche)


class TestSectionDeps:
    def test_defaults_all_no(self):
        result = sections.section_deps(interactive=False)
        # Both default N — large downloads, opt-in
        assert result['install_agency'] is False
        assert result['install_skills'] is False


class TestSectionMcp:
    def test_skip_when_user_says_no(self, tmp_path: Path,
                                     monkeypatch: pytest.MonkeyPatch):
        from orquestrum.lib import prompts
        # Force interactive-but-scripted with first answer 'n'
        monkeypatch.setattr(prompts, '_is_interactive', lambda: True)
        monkeypatch.setattr(prompts, '_read_line', lambda p: 'n')
        result = sections.section_mcp(interactive=True, target=tmp_path)
        assert result == []

    def test_lists_currently_registered(
        self, tmp_path: Path, capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ):
        # Pre-seed a settings.json with one server
        path = tmp_path / '.claude' / 'settings.json'
        path.parent.mkdir()
        import json
        path.write_text(json.dumps({
            'mcpServers': {
                'orquestrum': {'command': 'orquestrum', 'args': ['mcp']},
            }
        }), encoding='utf-8')

        from orquestrum.lib import prompts
        monkeypatch.setattr(prompts, '_is_interactive', lambda: True)
        # Answers: yes manage MCP; then n to all common MCPs
        answers = iter(['y', 'n', 'n', 'n'])
        monkeypatch.setattr(prompts, '_read_line', lambda p: next(answers, ''))

        sections.section_mcp(interactive=True, target=tmp_path)
        out = capsys.readouterr().out
        assert 'orquestrum' in out  # currently registered shown


class TestSectionOpencodeMcp:
    def test_returns_false_when_opencode_not_installed(self):
        result = sections.section_opencode_mcp(
            interactive=False, opencode_being_installed=False,
        )
        assert result is False  # never asks


# ─── _run_setup_advanced end-to-end ────────────────────────────────────────


class TestRunSetupAdvanced:
    def test_yes_installs_claude_code_and_ui_skips_extras_deps_mcp(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline,
    ):
        rc = setup._run_setup_advanced(interactive=False)
        assert rc == 0
        # Defaults: cc=Y, oc=N, provider=claude, ui=Y, webview=N,
        # agency=N, skills=N, mcp_manage=Y but no MCPs added by default
        installs = stub_install_pipeline['install']
        tools = [c[c.index('--tool') + 1] for c in installs if '--tool' in c]
        assert 'claude-code' in tools
        assert 'opencode' not in tools
        # ui extra installed (default Y)
        assert ['ui'] in stub_install_pipeline['extras']
        # No deps
        assert stub_install_pipeline['deps'] == []
        # No MCPs added (defaults all N for common MCPs)
        assert stub_install_pipeline['mcp_add'] == []

    def test_ui_and_webview_combined_into_single_extras_call(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline, monkeypatch: pytest.MonkeyPatch,
    ):
        """REGRESSION GUARD: when both ui and webview are selected, they
        MUST be installed in a single `_install` call. Calling them
        sequentially makes `uv tool install --with X` clobber the prior
        package set (real bug observed in production: ui got installed,
        then webview install dropped fastapi/jinja2)."""
        # Override the section to request BOTH ui and webview
        monkeypatch.setattr(sections, 'section_extras',
            lambda **kw: {'install_ui': True, 'install_webview': True})
        # Pin everything else to defaults / no-ops
        monkeypatch.setattr(sections, 'section_core',
            lambda **kw: {'install_cc': False, 'install_oc': False, 'provider': 'claude'})
        monkeypatch.setattr(sections, 'section_deps',
            lambda **kw: {'install_agency': False, 'install_skills': False})
        monkeypatch.setattr(sections, 'section_mcp', lambda **kw: [])
        monkeypatch.setattr(sections, 'section_opencode_mcp', lambda **kw: False)

        setup._run_setup_advanced(interactive=False)
        # Exactly ONE call to _install carrying BOTH names
        assert stub_install_pipeline['extras'] == [['ui', 'webview']]

    def test_no_changes_path_emits_friendly_message(
        self, isolated_manifest: Path, fake_home: Path,
        stub_install_pipeline, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ):
        # Force every section to return no-ops by mocking them
        monkeypatch.setattr(sections, 'section_core',
            lambda **kw: {'install_cc': False, 'install_oc': False, 'provider': 'claude'})
        monkeypatch.setattr(sections, 'section_extras',
            lambda **kw: {'install_ui': False, 'install_webview': False})
        monkeypatch.setattr(sections, 'section_deps',
            lambda **kw: {'install_agency': False, 'install_skills': False})
        monkeypatch.setattr(sections, 'section_mcp', lambda **kw: [])
        monkeypatch.setattr(sections, 'section_opencode_mcp', lambda **kw: False)

        rc = setup._run_setup_advanced(interactive=False)
        assert rc == 0
        out = capsys.readouterr().out
        assert 'No changes selected' in out
        # Always mentions web in next steps
        assert 'orquestrum web' in out
